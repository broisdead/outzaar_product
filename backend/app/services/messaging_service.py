"""Channel-agnostic Conversations/Messages logic shared by WhatsApp and email."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from backend.app.models.messaging import Conversation, Message, PendingStatus

log = logging.getLogger("outzaar.messaging")

# Delivery only ever moves forward (a late "sent" must not overwrite "read").
RANK = {"failed": -1, "sending": 0, "sent": 1, "delivered": 2, "read": 3}


class SendError(Exception):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt: datetime) -> str:
    return dt.replace(tzinfo=timezone.utc).isoformat()


def normalize_address(channel: str, address: str) -> str:
    if channel == "whatsapp":
        return "".join(c for c in address if c.isdigit())
    return address.strip().lower()


def _find_conv(db: Session, channel: str, address: str) -> Conversation | None:
    return db.scalar(
        select(Conversation).where(Conversation.channel == channel, Conversation.address == address)
    )


def get_or_create_conversation(db: Session, channel: str, address: str, name: str = "", **fields) -> Conversation:
    address = normalize_address(channel, address)
    conv = _find_conv(db, channel, address)
    if conv is None:
        conv = Conversation(channel=channel, address=address, contact_name=name or address, **fields)
        db.add(conv)
        try:
            db.commit()
        except IntegrityError:  # created concurrently by another request
            db.rollback()
            conv = _find_conv(db, channel, address)
    elif name and conv.contact_name == conv.address:
        conv.contact_name = name  # replace the placeholder name once we learn the real one
    return conv


def add_inbound(
    db: Session,
    channel: str,
    address: str,
    body: str,
    external_id: str,
    name: str = "",
    sent_at: datetime | None = None,
    **fields,
) -> Message | None:
    """Store a prospect message. Returns None when external_id was already stored (duplicate)."""
    if db.scalar(select(Message.id).where(Message.channel == channel, Message.external_id == external_id)):
        return None
    conv = get_or_create_conversation(db, channel, address, name, **fields)
    sent_at = sent_at or utcnow()
    msg = Message(
        conversation_id=conv.id, sender="prospect", channel=channel,
        body=body, sent_at=sent_at, external_id=external_id,
    )
    db.add(msg)
    conv.unread = True
    conv.last_message_at = max(conv.last_message_at, sent_at)
    if conv.status == "awaiting":  # they replied, so it now needs a human/AI follow-up
        conv.status = "followup"
    if fields.get("subject"):
        conv.subject = fields["subject"]
    try:
        db.commit()
    except IntegrityError:  # lost a race with a duplicate webhook delivery
        db.rollback()
        return None
    return msg


def create_outbound(db: Session, conv: Conversation, body: str) -> Message:
    now = utcnow()
    msg = Message(
        conversation_id=conv.id, sender="outzaar", channel=conv.channel,
        body=body, sent_at=now, delivery="sending",
    )
    db.add(msg)
    conv.last_message_at = now
    db.commit()
    return msg


def _advance(msg: Message, status: str, error: str | None = None) -> None:
    cur = RANK.get(msg.delivery or "sending", 0)
    if status == "failed":
        if cur >= RANK["delivered"]:
            return
    elif RANK.get(status, -1) <= cur:
        return
    msg.delivery = status
    msg.error = (error or "")[:500] or None if status == "failed" else None


def _find_msg(db: Session, channel: str, external_id: str) -> Message | None:
    return db.scalar(select(Message).where(Message.channel == channel, Message.external_id == external_id))


def apply_pending(db: Session, msg: Message) -> None:
    """Apply statuses that arrived before msg.external_id was saved; also purge stale rows."""
    rows = db.scalars(
        select(PendingStatus).where(PendingStatus.external_id == msg.external_id).order_by(PendingStatus.id)
    ).all()
    for r in rows:
        _advance(msg, r.status, r.error)
    ids = [r.id for r in rows]
    if ids:
        db.execute(delete(PendingStatus).where(PendingStatus.id.in_(ids)))
    db.execute(delete(PendingStatus).where(PendingStatus.created_at < utcnow() - timedelta(days=1)))


def apply_status(db: Session, channel: str, external_id: str, status: str, error: str | None = None) -> bool:
    """Idempotent, monotonic status update. Buffers the status if the message isn't saved yet."""
    msg = _find_msg(db, channel, external_id)
    if msg is None:
        db.add(PendingStatus(external_id=external_id, status=status, error=error))
        db.commit()
        msg = _find_msg(db, channel, external_id)  # sender may have saved the id meanwhile
        if msg is None:
            return False
        apply_pending(db, msg)
    else:
        _advance(msg, status, error)
    db.commit()
    return True


def message_out(m: Message) -> dict:
    out = {"id": m.id, "sender": m.sender, "body": m.body, "sentAt": iso(m.sent_at), "channel": m.channel}
    if m.delivery:
        out["delivery"] = m.delivery
    if m.error:
        out["error"] = m.error
    return out


def conversation_out(c: Conversation) -> dict:
    msgs = sorted(c.messages, key=lambda m: (m.sent_at, m.created_at))
    return {
        "id": c.id,
        "contact": {"name": c.contact_name, "title": c.title},
        "company": c.company,
        "industry": c.industry,
        "context": c.context,
        "status": c.status,
        "channel": c.channel,
        "unread": c.unread,
        "messages": [message_out(m) for m in msgs],
        # Placeholder until /conversations/{id}/analyze is implemented.
        "analysis": {
            "intent": "", "confidence": 0, "summary": "", "recommendedAction": "",
            "actionKind": "wait", "suggestedResponse": "", "signals": [],
        },
    }


def list_conversations(db: Session) -> list[dict]:
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.messages.any())  # the UI assumes at least one message
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.last_message_at.desc())
    ).all()
    return [conversation_out(c) for c in rows]
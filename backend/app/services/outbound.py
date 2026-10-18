"""Background delivery of outbound messages with retry + exponential backoff."""
import logging
import time

from backend.app.core.database import SessionLocal
from backend.app.models.messaging import Conversation, Message
from backend.app.services import email_service, whatsapp_service
from backend.app.services.messaging_service import SendError, apply_pending

log = logging.getLogger("outzaar.outbound")

BACKOFF = (0, 2, 6, 15)  # seconds before each attempt (4 attempts total)


def _send(conv: Conversation, msg: Message) -> str:
    if conv.channel == "whatsapp":
        return whatsapp_service.send_text(conv.address, msg.body)
    return email_service.send_email(conv.address, conv.subject, msg.body)


def deliver(message_id: str) -> None:
    db = SessionLocal()
    try:
        msg = db.get(Message, message_id)
        if msg is None or msg.delivery != "sending":
            return  # already handled: never send twice
        conv = db.get(Conversation, msg.conversation_id)
        error = "unknown error"
        for delay in BACKOFF:
            if delay:
                time.sleep(delay)
            try:
                msg.external_id = _send(conv, msg)
                msg.delivery, msg.error = "sent", None
                db.commit()
                apply_pending(db, msg)  # status webhooks that beat us here
                db.commit()
                return
            except SendError as e:
                error = str(e)
                log.warning("send attempt failed (retryable=%s): %s", e.retryable, error)
                if not e.retryable:
                    break
        msg.delivery, msg.error = "failed", error[:500]
        db.commit()
    except Exception:
        log.exception("deliver crashed for message %s", message_id)
        db.rollback()
        try:
            m = db.get(Message, message_id)
            if m is not None and m.delivery == "sending":
                m.delivery, m.error = "failed", "internal error"
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()
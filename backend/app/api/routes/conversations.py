from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.messaging import Conversation
from backend.app.services import email_service
from backend.app.services.messaging_service import (
    conversation_out, create_outbound, get_or_create_conversation,
    list_conversations, message_out, normalize_address,
)
from backend.app.services.outbound import deliver

router = APIRouter()


class NewConversation(BaseModel):
    channel: Literal["email", "whatsapp"]
    address: str  # phone number (with country code) or email address
    name: str = ""
    title: str = ""
    company: str = ""
    industry: str = ""
    context: str = ""
    subject: str = ""


class NewMessage(BaseModel):
    body: str
    channel: str | None = None  # accepted for UI compatibility; the conversation's channel is used


@router.get("/conversations")
def get_conversations(db: Session = Depends(get_db)):
    return list_conversations(db)


@router.post("/conversations")
def start_conversation(data: NewConversation, db: Session = Depends(get_db)):
    """Create (or fetch) the thread for a prospect so you can message them first."""
    address = normalize_address(data.channel, data.address)
    if data.channel == "whatsapp" and not 8 <= len(address) <= 15:
        raise HTTPException(status_code=422, detail="Phone must include country code (8-15 digits)")
    if data.channel == "email" and not email_service.EMAIL_RE.match(address):
        raise HTTPException(status_code=422, detail="Invalid email address")
    conv = get_or_create_conversation(
        db, data.channel, address, data.name,
        title=data.title, company=data.company, industry=data.industry,
        context=data.context, subject=email_service.clean_subject(data.subject),
    )
    db.commit()
    return {"id": conv.id, "channel": conv.channel, "address": conv.address}


@router.post("/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: str, data: NewMessage, background: BackgroundTasks, db: Session = Depends(get_db)
):
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    body = data.body.strip()
    if not body or len(body) > 4096:
        raise HTTPException(status_code=422, detail="Message must be 1-4096 characters")
    msg = create_outbound(db, conv, body)
    background.add_task(deliver, msg.id)  # sends with retries; status updates arrive via webhook
    return message_out(msg)


@router.post("/conversations/{conversation_id}/read")
def mark_read(conversation_id: str, db: Session = Depends(get_db)):
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.unread = False
    db.commit()
    return {"ok": True}
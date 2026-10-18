import hmac
import json
import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.services import email_service, whatsapp_service

log = logging.getLogger("outzaar.webhooks")
router = APIRouter()


def _same(a: str | None, b: str) -> bool:
    return bool(a) and bool(b) and hmac.compare_digest(a.encode(), b.encode())


# ---------------------------------------------------------------- WhatsApp

@router.get("/webhooks/whatsapp")
def whatsapp_verify(
    mode: str | None = Query(None, alias="hub.mode"),
    token: str | None = Query(None, alias="hub.verify_token"),
    challenge: str | None = Query(None, alias="hub.challenge"),
):
    """Meta's one-time subscription handshake."""
    if mode == "subscribe" and challenge is not None and _same(token, settings.WHATSAPP_VERIFY_TOKEN):
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


def _handle_whatsapp(payload: dict) -> None:
    db = SessionLocal()
    try:
        whatsapp_service.process_payload(db, payload)
    except SQLAlchemyError:
        db.rollback()
        log.exception("WhatsApp webhook DB error")
        raise HTTPException(status_code=500, detail="Temporary error")  # Meta will retry; processing is idempotent
    finally:
        db.close()


@router.post("/webhooks/whatsapp")
async def whatsapp_receive(request: Request):
    if not settings.WHATSAPP_APP_SECRET:
        raise HTTPException(status_code=503, detail="WhatsApp webhook not configured")
    raw = await request.body()
    if not whatsapp_service.verify_signature(raw, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=403, detail="Invalid signature")
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    await run_in_threadpool(_handle_whatsapp, payload)
    return {"status": "ok"}


# ------------------------------------------------------------------- Email

class InboundEmail(BaseModel):
    from_email: str
    from_name: str = ""
    subject: str = ""
    text: str = Field(min_length=1)
    message_id: str = Field(min_length=1, max_length=255)  # the email's Message-ID header (dedupe key)


def _handle_email(data: InboundEmail) -> bool:
    db = SessionLocal()
    try:
        return email_service.ingest_inbound(
            db, data.from_email, data.from_name, data.subject, data.text, data.message_id
        )
    except SQLAlchemyError:
        db.rollback()
        log.exception("Email webhook DB error")
        raise HTTPException(status_code=500, detail="Temporary error")
    finally:
        db.close()


@router.post("/webhooks/email")
async def email_receive(data: InboundEmail, request: Request):
    """Point your inbound-email provider (Mailgun/SendGrid/forwarder) here with header X-Webhook-Secret."""
    if not settings.EMAIL_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Email webhook not configured")
    if not _same(request.headers.get("X-Webhook-Secret"), settings.EMAIL_WEBHOOK_SECRET):
        raise HTTPException(status_code=403, detail="Invalid secret")
    if not email_service.EMAIL_RE.match(data.from_email.strip()):
        raise HTTPException(status_code=422, detail="Invalid from_email")
    stored = await run_in_threadpool(_handle_email, data)
    return {"status": "ok" if stored else "duplicate"}
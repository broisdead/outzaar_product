"""WhatsApp Cloud API: webhook signature check, inbound/status parsing, outbound send."""
import hashlib
import hmac
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.services.messaging_service import SendError, add_inbound, apply_status

log = logging.getLogger("outzaar.whatsapp")

RETRYABLE_CODES = {130429, 131056}  # Meta throughput / pair rate limits


def verify_signature(raw: bytes, header: str | None) -> bool:
    """Check Meta's X-Hub-Signature-256 (HMAC-SHA256 of the raw body with the App Secret)."""
    secret = settings.WHATSAPP_APP_SECRET
    if not secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.encode(), header[7:].encode())


def send_text(to: str, body: str) -> str:
    """Send a text message; returns the wamid. Raises SendError(retryable=...)."""
    if not (settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID):
        raise SendError("WhatsApp is not configured", retryable=False)
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body[:4096]},
    }
    try:
        r = httpx.post(
            url, json=payload, timeout=15,
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
        )
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        raise SendError(f"connection failed: {e.__class__.__name__}", retryable=True)  # nothing was sent
    except httpx.HTTPError as e:
        # e.g. read timeout: WhatsApp may have accepted it, so do NOT auto-retry (would duplicate).
        raise SendError(f"no response, delivery unconfirmed: {e.__class__.__name__}", retryable=False)
    if r.status_code == 200:
        try:
            return r.json()["messages"][0]["id"]
        except (KeyError, IndexError, TypeError, ValueError):
            raise SendError("unexpected response from WhatsApp", retryable=False)
    try:
        err = (r.json() or {}).get("error") or {}
    except ValueError:
        err = {}
    code = err.get("code")
    detail = err.get("error_data", {}).get("details") if isinstance(err.get("error_data"), dict) else None
    raise SendError(
        f"{r.status_code} code={code}: {detail or err.get('message') or r.text[:200]}",
        retryable=r.status_code == 429 or r.status_code >= 500 or code in RETRYABLE_CODES,
    )


def _inbound_body(m: dict) -> str | None:
    t = m.get("type")
    if t == "reaction":
        return None
    if t == "text":
        return (m.get("text") or {}).get("body") or None
    if t == "button":
        return (m.get("button") or {}).get("text") or None
    if t == "interactive":
        i = m.get("interactive") or {}
        return (i.get("button_reply") or i.get("list_reply") or {}).get("title") or None
    media = m.get(t) if isinstance(m.get(t), dict) else {}
    caption = media.get("caption")
    return f"[{t}] {caption}" if caption else f"[{t}]"


def process_payload(db: Session, payload: dict) -> None:
    """Handle one webhook POST. Idempotent: Meta redelivers, so duplicates are harmless.

    Malformed items are logged and skipped; database errors propagate so the route
    returns 500 and Meta retries the delivery.
    """
    if payload.get("object") != "whatsapp_business_account":
        return
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            if change.get("field") != "messages":
                continue
            value = change.get("value") or {}
            pid = (value.get("metadata") or {}).get("phone_number_id")
            if settings.WHATSAPP_PHONE_NUMBER_ID and pid != settings.WHATSAPP_PHONE_NUMBER_ID:
                continue
            names = {c.get("wa_id"): (c.get("profile") or {}).get("name", "") for c in value.get("contacts") or []}

            for m in value.get("messages") or []:
                try:
                    body = _inbound_body(m)
                    if not body:
                        continue
                    sender = m["from"]
                    sent_at = datetime.fromtimestamp(int(m["timestamp"]), timezone.utc).replace(tzinfo=None)
                    add_inbound(db, "whatsapp", sender, body, m["id"], names.get(sender, ""), sent_at)
                except (KeyError, TypeError, ValueError, AttributeError):
                    log.warning("skipping malformed WhatsApp message")

            for s in value.get("statuses") or []:
                try:
                    status = s["status"]
                    if status not in ("sent", "delivered", "read", "failed"):
                        continue
                    errs = s.get("errors") or [{}]
                    err = None
                    if status == "failed":
                        e = errs[0]
                        err = f"{e.get('code')}: {e.get('title') or e.get('message')}"
                    apply_status(db, "whatsapp", s["id"], status, err)
                except (KeyError, TypeError, ValueError, AttributeError):
                    log.warning("skipping malformed WhatsApp status")
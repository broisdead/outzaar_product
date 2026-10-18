"""Email channel: outbound via SMTP, inbound via a secured webhook (Mailgun/SendGrid/forwarder)."""
import re
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.services.messaging_service import SendError, add_inbound

EMAIL_RE = re.compile(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")


def clean_subject(subject: str) -> str:
    return " ".join((subject or "").split())[:200]  # no newlines => no header injection


def send_email(to: str, subject: str, body: str) -> str:
    """Send via SMTP; returns the Message-ID. Raises SendError(retryable=...)."""
    if not (settings.SMTP_HOST and settings.SMTP_FROM):
        raise SendError("SMTP is not configured", retryable=False)
    subject = clean_subject(subject)
    if subject and not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject or "Following up"
    mid = make_msgid(domain=settings.SMTP_FROM.rsplit("@", 1)[-1].strip("> ") or "outzaar.local")
    msg["Message-ID"] = mid
    msg.set_content(body)
    try:
        smtp = (
            smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)
            if settings.SMTP_PORT == 465
            else smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)
        )
        with smtp as s:
            if settings.SMTP_PORT != 465:
                s.starttls()
            if settings.SMTP_USER:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.send_message(msg)
    except (smtplib.SMTPAuthenticationError, smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused) as e:
        raise SendError(f"SMTP rejected: {e}", retryable=False)
    except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError) as e:
        raise SendError(f"SMTP connection: {e}", retryable=True)
    except smtplib.SMTPException as e:
        raise SendError(f"SMTP error: {e}", retryable=False)
    except OSError as e:  # DNS / refused / timeout before sending
        raise SendError(f"SMTP network error: {e}", retryable=True)
    return mid


def ingest_inbound(db: Session, from_email: str, from_name: str, subject: str, text: str, message_id: str) -> bool:
    """Store an inbound email. Returns False if this Message-ID was already stored."""
    msg = add_inbound(
        db, "email", from_email, text.strip()[:20000], message_id.strip(),
        name=from_name.strip()[:255], subject=clean_subject(subject),
    )
    return msg is not None
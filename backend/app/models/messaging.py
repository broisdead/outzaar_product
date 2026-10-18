import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


def _now() -> datetime:
    # Stored as naive UTC everywhere (SQLite has no tz support).
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _id() -> str:
    return uuid.uuid4().hex


class Conversation(Base):
    """One thread per (channel, address): phone digits for WhatsApp, lowercase email for email."""

    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("channel", "address", name="uq_conv_channel_address"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    channel: Mapped[str] = mapped_column(String(16))
    address: Mapped[str] = mapped_column(String(255))
    contact_name: Mapped[str] = mapped_column(String(255), default="")
    title: Mapped[str] = mapped_column(String(255), default="")
    company: Mapped[str] = mapped_column(String(255), default="")
    industry: Mapped[str] = mapped_column(String(255), default="")
    context: Mapped[str] = mapped_column(Text, default="")
    subject: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(16), default="awaiting")
    unread: Mapped[bool] = mapped_column(Boolean, default=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        order_by="Message.sent_at",
        cascade="all, delete-orphan",
    )


class Message(Base):
    __tablename__ = "messages"
    # Duplicate protection: the same provider message id can only be stored once per channel.
    # (NULL external_ids, e.g. outbound not yet sent, are allowed multiple times.)
    __table_args__ = (UniqueConstraint("channel", "external_id", name="uq_msg_channel_external"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    sender: Mapped[str] = mapped_column(String(16))  # outzaar | prospect | system
    channel: Mapped[str] = mapped_column(String(16))
    body: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    delivery: Mapped[str | None] = mapped_column(String(16), nullable=True)  # sending|sent|delivered|read|failed
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # wamid / email Message-ID
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class PendingStatus(Base):
    """A delivery status that arrived before we saved the message's provider id (race with send)."""

    __tablename__ = "pending_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(16))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
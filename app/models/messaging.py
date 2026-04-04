import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.core.database import Base

_now = lambda: datetime.now(timezone.utc)


class MessageTemplate(Base):
    """Admin-editable message templates used by the bulk messaging system."""

    __tablename__ = "message_templates"

    id = Column(String(100), primary_key=True)           # slug key, e.g. "event_reminder"
    name = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)               # {variable} placeholders
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False, server_default="false")

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())


class ScheduledMessageStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledMessage(Base):
    """Persistent queue entry for messages to be dispatched at a future time."""

    __tablename__ = "scheduled_messages"

    id = Column(Integer, primary_key=True, index=True)

    # Who to send to
    parishioner_ids = Column(JSON, nullable=False)  # List[str] of UUID strings

    # What to send
    channel = Column(String(10), nullable=False)         # email | sms | both
    template = Column(String(100), nullable=False)       # template_id or "custom_message"
    custom_message = Column(Text, nullable=True)
    subject = Column(String(300), nullable=True)

    # Context variables for event-related templates
    event_name = Column(String(200), nullable=True)
    event_date = Column(String(50), nullable=True)
    event_time = Column(String(50), nullable=True)

    # Scheduling
    send_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(
        Enum(ScheduledMessageStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ScheduledMessageStatus.PENDING,
        server_default=ScheduledMessageStatus.PENDING.value,
        index=True,
    )

    # Result tracking
    sent_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_now,
        server_default=func.now(),
        onupdate=func.now(),
    )

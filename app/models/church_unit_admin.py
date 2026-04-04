import enum
import uuid as _uuid
from datetime import datetime, timezone
from sqlalchemy import UUID, Boolean, Column, Date, DateTime, ForeignKey, Integer, SmallInteger, String, Text, Time, Enum, func
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base

_now = lambda: datetime.now(timezone.utc)


class RecurrenceFrequency(str, enum.Enum):
    DAILY   = "daily"
    WEEKLY  = "weekly"
    MONTHLY = "monthly"
    YEARLY  = "yearly"


class EventMessageType(str, enum.Enum):
    REMINDER     = "reminder"
    ANNOUNCEMENT = "announcement"
    NOTE         = "note"


class LeadershipRole(str, enum.Enum):
    # Clergy
    PRIEST_IN_CHARGE   = "priest_in_charge"
    ASSISTANT_PRIEST   = "assistant_priest"
    DEACON             = "deacon"
    # Parish administration
    CHURCH_ADMINISTRATOR = "church_administrator"
    CHURCH_SECRETARY     = "church_secretary"
    # Parish Pastoral Council (PPC)
    PPC_CHAIRMAN       = "ppc_chairman"
    PPC_VICE_CHAIRMAN  = "ppc_vice_chairman"
    PPC_SECRETARY      = "ppc_secretary"
    PPC_TREASURER      = "ppc_treasurer"
    PPC_MEMBER         = "ppc_member"
    # Catch-all
    OTHER              = "other"


class ChurchUnitLeadership(Base):
    __tablename__ = "church_unit_leadership"

    id             = Column(Integer, primary_key=True, index=True)
    church_unit_id = Column(Integer, ForeignKey("church_units.id", ondelete="CASCADE"), nullable=False, index=True)
    role           = Column(Enum(LeadershipRole, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    custom_role    = Column(String(200), nullable=True)   # used when role=OTHER
    name           = Column(String(200), nullable=False)
    phone          = Column(String(50),  nullable=True)
    email          = Column(String(200), nullable=True)
    is_current     = Column(Boolean, nullable=False, default=True, server_default="true")
    start_date     = Column(Date, nullable=True)
    end_date       = Column(Date, nullable=True)   # NULL means still in office
    notes          = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())

    church_unit = db_relationship("ChurchUnit", back_populates="leadership")


class ChurchEvent(Base):
    __tablename__ = "church_events"

    id             = Column(Integer, primary_key=True, index=True)
    church_unit_id = Column(Integer, ForeignKey("church_units.id", ondelete="CASCADE"), nullable=False, index=True)
    name           = Column(String(300), nullable=False)
    description    = Column(Text, nullable=True)
    event_date     = Column(Date, nullable=False, index=True)
    start_time     = Column(Time, nullable=True)
    end_time       = Column(Time, nullable=True)
    location       = Column(String(500), nullable=True)
    is_public      = Column(Boolean, nullable=False, default=True, server_default="true")

    # ── Recurrence ────────────────────────────────────────────────────────────
    is_recurring           = Column(Boolean, nullable=False, default=False, server_default="false", index=True)
    recurrence_frequency   = Column(
        Enum(RecurrenceFrequency, values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
    )
    # 0=Sunday … 6=Saturday (matches PostgreSQL extract(dow)).  Used for weekly recurrence.
    recurrence_day_of_week = Column(SmallInteger, nullable=True)
    recurrence_end_date    = Column(Date, nullable=True)   # series ends naturally on this date
    terminated_at          = Column(DateTime(timezone=True), nullable=True)  # manually ended

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())

    church_unit = db_relationship("ChurchUnit", back_populates="events")
    messages    = db_relationship("EventMessage", back_populates="event", cascade="all, delete-orphan", order_by="EventMessage.created_at")


class EventMessage(Base):
    """A note, announcement, or reminder attached to a church event."""
    __tablename__ = "event_messages"

    id           = Column(Integer, primary_key=True, index=True)
    event_id     = Column(Integer, ForeignKey("church_events.id", ondelete="CASCADE"), nullable=False, index=True)
    message_type = Column(
        Enum(EventMessageType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=EventMessageType.NOTE,
    )
    title        = Column(String(300), nullable=True)
    content      = Column(Text, nullable=False)
    # Optional: when to surface/send this reminder
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    is_sent      = Column(Boolean, nullable=False, default=False, server_default="false")
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())

    event      = db_relationship("ChurchEvent", back_populates="messages")
    created_by = db_relationship("User")

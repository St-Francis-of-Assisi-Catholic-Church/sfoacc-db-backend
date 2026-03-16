import enum
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, Time, Enum, func
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base

_now = lambda: datetime.now(timezone.utc)


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
    role           = Column(Enum(LeadershipRole), nullable=False)
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

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())

    church_unit = db_relationship("ChurchUnit", back_populates="events")

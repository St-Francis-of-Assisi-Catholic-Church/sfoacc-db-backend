import enum
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Time, Enum, func
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base

_now = lambda: datetime.now(timezone.utc)


class ChurchUnitType(str, enum.Enum):
    PARISH = "parish"
    OUTSTATION = "outstation"


class DayOfWeek(str, enum.Enum):
    SUNDAY = "sunday"
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"


class MassType(str, enum.Enum):
    SUNDAY = "sunday"
    WEEKDAY = "weekday"
    SATURDAY = "saturday"
    HOLY_DAY = "holy_day"
    SPECIAL = "special"


class ChurchUnit(Base):
    __tablename__ = "church_units"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(ChurchUnitType), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("church_units.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(200), nullable=False)
    diocese = Column(String(200), nullable=True)
    address = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    website = Column(String(200), nullable=True)
    established_date = Column(Date, nullable=True)

    # Outstation-specific (nullable for parish-type units)
    location_description = Column(String(500), nullable=True)
    google_maps_url = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    priest_in_charge = Column(String(200), nullable=True)
    priest_phone = Column(String(50), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())

    # Hierarchy: outstation -> parent parish
    parent = db_relationship("ChurchUnit", back_populates="children", remote_side=[id])
    children = db_relationship("ChurchUnit", back_populates="parent")

    settings = db_relationship("ParishSettings", back_populates="church_unit", cascade="all, delete-orphan")
    mass_schedules = db_relationship("MassSchedule", back_populates="church_unit", cascade="all, delete-orphan")
    communities = db_relationship("ChurchCommunity", back_populates="church_unit")
    parishioners = db_relationship("Parishioner", back_populates="church_unit")
    societies = db_relationship("Society", back_populates="church_unit")
    leadership = db_relationship("ChurchUnitLeadership", back_populates="church_unit", cascade="all, delete-orphan")
    events = db_relationship("ChurchEvent", back_populates="church_unit", cascade="all, delete-orphan")


class MassSchedule(Base):
    __tablename__ = "mass_schedules"

    id = Column(Integer, primary_key=True, index=True)
    church_unit_id = Column(Integer, ForeignKey("church_units.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Enum(DayOfWeek), nullable=False)
    time = Column(Time, nullable=False)
    mass_type = Column(Enum(MassType), nullable=False, default=MassType.SUNDAY)
    language = Column(String(100), nullable=False, default="English")
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())

    church_unit = db_relationship("ChurchUnit", back_populates="mass_schedules")


# Backward-compat aliases
Parish = ChurchUnit
Outstation = ChurchUnit
Station = ChurchUnit

from datetime import datetime, timezone
from sqlalchemy import UUID, Column, DateTime, Integer, String, Enum, ForeignKey, func
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base

from app.models.common import LifeStatus

_now = lambda: datetime.now(timezone.utc)


class Occupation(Base):
    __tablename__ = "par_occupations"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(UUID(as_uuid=True), ForeignKey("parishioners.id", ondelete="CASCADE"), unique=True)
    role = Column(String, nullable=False)
    employer = Column(String, nullable=False)

    parishioner_ref = db_relationship("Parishioner", back_populates="occupation_rel")

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())


class FamilyInfo(Base):
    __tablename__ = "par_family"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(UUID(as_uuid=True), ForeignKey("parishioners.id", ondelete="CASCADE"), unique=True)

    spouse_name = Column(String, nullable=True)
    spouse_status = Column(Enum(LifeStatus), nullable=True)
    spouse_phone = Column(String, nullable=True)

    father_name = Column(String, nullable=True)
    father_status = Column(Enum(LifeStatus), nullable=True)
    mother_name = Column(String, nullable=True)
    mother_status = Column(Enum(LifeStatus), nullable=True)

    parishioner_ref = db_relationship("Parishioner", back_populates="family_info_rel")
    children_rel = db_relationship("Child", back_populates="family_ref", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())


class Child(Base):
    __tablename__ = "par_children"

    id = Column(Integer, primary_key=True, index=True)
    family_info_id = Column(Integer, ForeignKey("par_family.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)

    family_ref = db_relationship("FamilyInfo", back_populates="children_rel")

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())


class EmergencyContact(Base):
    __tablename__ = "par_emergency_contacts"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(UUID(as_uuid=True), ForeignKey("parishioners.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    relationship = Column(String, nullable=False)
    primary_phone = Column(String, nullable=False)
    alternative_phone = Column(String, nullable=True)

    parishioner_ref = db_relationship("Parishioner", back_populates="emergency_contacts_rel")

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())

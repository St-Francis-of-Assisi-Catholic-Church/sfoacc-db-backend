from datetime import datetime, timezone
from sqlalchemy import UUID, Column, DateTime, Integer, String, ForeignKey, Text, func
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base

from app.models.parishioner.core import parishioner_skills

_now = lambda: datetime.now(timezone.utc)


class MedicalCondition(Base):
    __tablename__ = "par_medical_conditions"

    id = Column(Integer, primary_key=True, index=True)
    parishioner_id = Column(UUID(as_uuid=True), ForeignKey("parishioners.id", ondelete="CASCADE"))
    condition = Column(String, nullable=False)
    notes = Column(Text, nullable=True)

    parishioner_ref = db_relationship("Parishioner", back_populates="medical_conditions_rel")

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())


class Skill(Base):
    __tablename__ = "par_skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    parishioners_ref = db_relationship("Parishioner", secondary=parishioner_skills, back_populates="skills_rel")

    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())

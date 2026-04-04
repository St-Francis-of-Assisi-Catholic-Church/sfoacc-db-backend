from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base

_now = lambda: datetime.now(timezone.utc)


class ParishSettings(Base):
    __tablename__ = "parish_settings"

    id = Column(Integer, primary_key=True, index=True)
    church_unit_id = Column(Integer, ForeignKey("church_units.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(200), nullable=False, unique=True)
    value = Column(Text, nullable=True)
    label = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())

    church_unit = db_relationship("ChurchUnit", back_populates="settings")

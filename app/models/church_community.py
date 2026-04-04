from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base

class ChurchCommunity(Base):
    __tablename__ = "church_communities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    church_unit_id = Column(Integer, ForeignKey("church_units.id", ondelete="RESTRICT"), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)

    church_unit = db_relationship("ChurchUnit", back_populates="communities")
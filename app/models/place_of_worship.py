from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, func
from app.core.database import Base

class PlaceOfWorship(Base):
    __tablename__ = "places_of_worship"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    address = Column(String, nullable=True)
    mass_schedule = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)
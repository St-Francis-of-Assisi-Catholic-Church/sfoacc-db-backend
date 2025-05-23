from datetime import datetime
import enum
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from app.core.database import Base

class SacramentType(str, enum.Enum):
    BAPTISM = "Baptism"
    FIRST_COMMUNION = "First Communion"
    CONFIRMATION = "Confirmation"
    PENANCE = "Penance"
    ANOINTING = "Anointing of the Sick"
    HOLY_ORDERS = "Holy Orders"
    MATRIMONY = "Holy Matrimony"


class Sacrament(Base):
    __tablename__ = "sacrament"

    id = Column(Integer, primary_key = True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=False)
    once_only = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)
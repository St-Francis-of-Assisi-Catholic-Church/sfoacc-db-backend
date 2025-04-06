from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, func
from app.core.database import Base
from sqlalchemy.orm import relationship as db_relationship
from app.models.parishioner import parishioner_languages

class Language(Base):
    __tablename__ = "languages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Relationship with parishioners
    parishioners_ref = db_relationship("Parishioner", secondary=parishioner_languages, back_populates="languages_rel")
 
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now(), onupdate=datetime.utcnow)
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class VerificationRecord(Base):
    __tablename__ = "verification_records"

    id = Column(String, primary_key=True)  # UUID for the verification
    parishioner_id = Column(Integer, ForeignKey("parishioners.id", ondelete="CASCADE"))
    html_content = Column(Text, nullable=False)  # Store the generated HTML
    access_code = Column(String, nullable=False)  # Store the access code
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Set expiration time
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, server_default=func.now())
    
    # Relationship to parishioner
    parishioner = relationship("Parishioner", backref="verification_records")
    
    @classmethod
    def create_with_expiration(cls, id, parishioner_id, html_content, access_code, expiration_hours=48):
        """Create a verification record with an expiration time"""
        expires_at = datetime.utcnow() + timedelta(hours=expiration_hours)
        return cls(
            id=id,
            parishioner_id=parishioner_id,
            html_content=html_content,
            access_code=access_code,
            expires_at=expires_at
        )
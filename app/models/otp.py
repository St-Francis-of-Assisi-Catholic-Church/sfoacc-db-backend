from datetime import datetime, timezone
import uuid as _uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UUID, func
from app.core.database import Base

_now = lambda: datetime.now(timezone.utc)


class OTPCode(Base):
    """Short-lived one-time codes used for passwordless login."""
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    # SHA-256 hash of the raw code (fast to verify, sufficient for short-lived OTPs)
    code_hash = Column(String(64), nullable=False)
    # "sms" or "email"
    delivery = Column(String(10), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=_now, server_default=func.now())

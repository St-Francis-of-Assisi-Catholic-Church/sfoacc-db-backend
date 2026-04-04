from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base

_now = lambda: datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    method = Column(String(10), nullable=False)          # GET, POST, PUT, DELETE …
    path = Column(String(500), nullable=False)
    status_code = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    summary = Column(String(500), nullable=True)         # human-readable: "Updated church_community 12"
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), index=True)

    user = db_relationship("User", foreign_keys=[user_id], lazy="select")

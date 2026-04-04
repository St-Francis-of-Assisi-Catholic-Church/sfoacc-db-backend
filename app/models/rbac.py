from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base

_now = lambda: datetime.now(timezone.utc)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)  # e.g. "parishioner:write"
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    module = Column(String(100), nullable=False, index=True)  # "parishioners", "admin", etc.

    roles = db_relationship("Role", secondary=role_permissions, back_populates="permissions")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # "super_admin", "parish_admin"
    label = Column(String(200), nullable=False)  # "Super Admin", "Parish Admin"
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)  # system roles can't be deleted
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, server_default=func.now(), onupdate=func.now())

    permissions = db_relationship("Permission", secondary=role_permissions, back_populates="roles")
    users = db_relationship("User", back_populates="role_ref")

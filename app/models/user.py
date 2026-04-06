from datetime import datetime, timezone
import uuid
from sqlalchemy import UUID, Column, DateTime, String, Integer, ForeignKey, Enum, func, event
import enum
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base


class UserChurchUnit(Base):
    """
    A user's membership in a church unit, with a unit-specific role.
    A user can belong to multiple units, each with a different role.
    e.g. user is 'parish_admin' in St Francis but only 'viewer' in St Andrews.
    """
    __tablename__ = "user_church_units"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    church_unit_id = Column(Integer, ForeignKey("church_units.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)

    user = db_relationship("User", back_populates="unit_memberships")
    church_unit = db_relationship("ChurchUnit")
    role = db_relationship("Role")


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    RESET_REQUIRED = "reset_required"


class LoginMethod(str, enum.Enum):
    PASSWORD = "password"
    EMAIL_OTP = "email_otp"
    SMS_OTP = "sms_otp"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    phone = Column(String(20), nullable=True, index=True)  # digits + country code, e.g. 233543460633
    login_method = Column(
        Enum(LoginMethod),
        nullable=False,
        default=LoginMethod.PASSWORD,
        server_default=LoginMethod.PASSWORD.value,
    )
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True, index=True)
    status = Column(
        Enum(UserStatus),
        nullable=False,
        default=UserStatus.RESET_REQUIRED.value,
    )
    # Set to now() when role/permissions change — any token issued before this timestamp is rejected
    tokens_invalidated_before = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    role_ref = db_relationship("Role", back_populates="users")
    unit_memberships = db_relationship("UserChurchUnit", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


@event.listens_for(User, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.now(timezone.utc)

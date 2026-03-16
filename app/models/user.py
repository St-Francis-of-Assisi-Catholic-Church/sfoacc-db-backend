from datetime import datetime, timezone
import uuid
from sqlalchemy import UUID, Boolean, Column, DateTime, String, Integer, ForeignKey, Enum, func, event
import enum
from sqlalchemy.orm import relationship as db_relationship
from app.core.database import Base


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
    church_unit_id = Column(Integer, ForeignKey("church_units.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(
        Enum(UserStatus),
        nullable=False,
        default=UserStatus.RESET_REQUIRED.value,
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
    church_unit = db_relationship("ChurchUnit", back_populates="users")

    def __repr__(self):
        return f"<User {self.email}>"


@event.listens_for(User, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.now(timezone.utc)

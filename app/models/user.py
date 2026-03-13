from datetime import datetime, timezone
import uuid
from sqlalchemy import UUID, Column, DateTime, String, Enum, func, event
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    RESET_REQUIRED = "reset_required"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER.value)
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

    def __repr__(self):
        return f"<User {self.email}>"


@event.listens_for(User, "before_update")
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.now(timezone.utc)

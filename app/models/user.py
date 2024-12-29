from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Enum, func, text, event
import enum
from app.core.database import Base

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER)
    is_active = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=datetime.utcnow
    )


    def __repr__(self):
        return f"<User {self.email}>"
    
@event.listens_for(User, 'before_update')
def receive_before_update(mapper, connection, target):
    target.updated_at = datetime.utcnow()
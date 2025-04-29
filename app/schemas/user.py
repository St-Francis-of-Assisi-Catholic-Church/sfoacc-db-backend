from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from app.models.user import UserRole, UserStatus

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    # role: UserRole
    role: Optional[UserRole] = UserRole.USER
    status: Optional[UserStatus] = UserStatus.RESET_REQUIRED

class UserCreate(UserBase):
    password: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[UserStatus]) -> Optional[UserStatus]:
        if v is not None and v not in [status for status in UserStatus]:
            raise ValueError(f"Invalid status. Must be one of: {', '.join([s.value for s in UserStatus])}")
        return v

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: Optional[UserRole]) -> Optional[UserRole]:
        if v is not None and v not in [role for role in UserRole]:
            raise ValueError(f"Invalid role. Must be one of: {', '.join([r.value for r in UserRole])}")
        return v

class UserInDB(UserBase):
    id: UUID
    status: UserStatus
    hashed_password: str

    class Config:
        from_attributes = True

class User(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginResponse(Token):
    user: User
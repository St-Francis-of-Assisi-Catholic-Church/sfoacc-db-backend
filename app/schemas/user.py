import re
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from app.models.user import UserStatus, LoginMethod


def _validate_phone(v: Optional[str]) -> Optional[str]:
    """Strip non-digits; require 7-15 digits for international format (e.g. 233543460633)."""
    if v is None:
        return v
    digits = re.sub(r"\D", "", v)
    if not (7 <= len(digits) <= 15):
        raise ValueError(
            "Phone must be 7–15 digits including country code (e.g. 233543460633)"
        )
    return digits


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    status: Optional[UserStatus] = UserStatus.RESET_REQUIRED


class UserCreate(UserBase):
    password: Optional[str] = None
    phone: Optional[str] = None
    login_method: Optional[LoginMethod] = LoginMethod.PASSWORD
    role_name: Optional[str] = None        # looked up by name
    church_unit_id: Optional[int] = None   # scope to a specific unit

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone(v)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    login_method: Optional[LoginMethod] = None
    role_name: Optional[str] = None
    status: Optional[UserStatus] = None
    church_unit_id: Optional[int] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone(v)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[UserStatus]) -> Optional[UserStatus]:
        if v is not None and v not in list(UserStatus):
            raise ValueError(
                f"Invalid status. Must be one of: {', '.join(s.value for s in UserStatus)}"
            )
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
    phone: Optional[str] = None
    login_method: LoginMethod = LoginMethod.PASSWORD
    role: Optional[str] = None
    role_label: Optional[str] = None
    church_unit_id: Optional[int] = None
    church_unit_name: Optional[str] = None
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if hasattr(obj, "role_ref"):
            return cls(
                id=obj.id,
                email=obj.email,
                full_name=obj.full_name,
                phone=getattr(obj, "phone", None),
                login_method=getattr(obj, "login_method", LoginMethod.PASSWORD),
                role=obj.role_ref.name if obj.role_ref else None,
                role_label=obj.role_ref.label if obj.role_ref else None,
                church_unit_id=obj.church_unit_id,
                church_unit_name=obj.church_unit.name if obj.church_unit else None,
                status=obj.status,
                created_at=obj.created_at,
                updated_at=obj.updated_at,
            )
        return super().model_validate(obj, *args, **kwargs)

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginResponse(Token):
    user: User


class PasswordResetRequest(BaseModel):
    email: EmailStr
    temp_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("New password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("New password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("New password must contain at least one number")
        return v


class PasswordResetResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"
    user: User

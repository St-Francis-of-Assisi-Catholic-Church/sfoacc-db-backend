import re
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional
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


class ChurchUnitAssignment(BaseModel):
    church_unit_id: int
    role_name: Optional[str] = None   # role scoped to this unit; falls back to user's global role


class UserCreate(UserBase):
    password: Optional[str] = None
    phone: Optional[str] = None
    login_method: Optional[LoginMethod] = LoginMethod.PASSWORD
    role_name: Optional[str] = None        # global role looked up by name
    church_units: Optional[List[ChurchUnitAssignment]] = None  # multi-unit assignments

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
    permissions: List[str] = []
    unit_memberships: List["ChurchUnitSummary"] = []
    status: UserStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if hasattr(obj, "role_ref"):
            memberships = []
            # Collect permissions from global role AND all unit-level roles
            perm_set: set[str] = set()

            if obj.role_ref:
                perm_set.update(p.code for p in obj.role_ref.permissions)

            for m in (getattr(obj, "unit_memberships", None) or []):
                cu = m.church_unit
                if cu is None:
                    continue
                if m.role:
                    perm_set.update(p.code for p in m.role.permissions)
                memberships.append(ChurchUnitSummary(
                    id=cu.id,
                    name=cu.name,
                    type=cu.type.value if hasattr(cu.type, "value") else str(cu.type),
                    role=m.role.name if m.role else (obj.role_ref.name if obj.role_ref else None),
                    role_label=m.role.label if m.role else (obj.role_ref.label if obj.role_ref else None),
                ))

            # Determine the effective role to surface: global role takes precedence,
            # fall back to the first unit-level role if no global role is set.
            effective_role = obj.role_ref
            if effective_role is None and memberships:
                for m in (getattr(obj, "unit_memberships", None) or []):
                    if m.role:
                        effective_role = m.role
                        break

            return cls(
                id=obj.id,
                email=obj.email,
                full_name=obj.full_name,
                phone=getattr(obj, "phone", None),
                login_method=getattr(obj, "login_method", LoginMethod.PASSWORD),
                role=effective_role.name if effective_role else None,
                role_label=effective_role.label if effective_role else None,
                permissions=sorted(perm_set),
                unit_memberships=memberships,
                status=obj.status,
                created_at=obj.created_at,
                updated_at=obj.updated_at,
            )
        return super().model_validate(obj, *args, **kwargs)

    class Config:
        from_attributes = True


class ChurchUnitSummary(BaseModel):
    id: int
    name: str
    type: str
    role: Optional[str] = None        # role name for this unit, e.g. "parish_admin"
    role_label: Optional[str] = None  # human label, e.g. "Parish Admin"

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginResponse(Token):
    user: User
    accessible_units: list[ChurchUnitSummary] = []

    # Routing hint for the frontend:
    #   "super_admin"    — unrestricted access, go to super-admin dashboard
    #   "unit_dashboard" — scoped to exactly one unit, go straight to that unit's dashboard
    #   "unit_selection" — multiple units, show the unit-picker screen first
    #   "no_access"      — authenticated but no unit assigned and not super admin
    routing: str = "no_access"

    # Populated only when routing == "unit_dashboard" (the single accessible unit)
    default_unit: Optional[ChurchUnitSummary] = None


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
    accessible_units: list[ChurchUnitSummary] = []
    routing: str = "no_access"
    default_unit: Optional[ChurchUnitSummary] = None

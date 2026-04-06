import time
from collections import defaultdict
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, field_validator

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.api.deps import SessionDep, CurrentUser, check_user_status

from app.schemas.user import LoginResponse, PasswordResetRequest, PasswordResetResponse, User, ChurchUnitSummary
from app.models.user import User as UserModel, UserStatus, LoginMethod
from app.services.otp_service import (
    generate_otp, verify_otp, send_otp_sms, send_otp_email,
    is_method_enabled,
)

router = APIRouter()

# ── Rate limiter (in-memory) ─────────────────────────────────────────────────

_login_attempts: dict = defaultdict(list)
_RATE_LIMIT_WINDOW = 60
_RATE_LIMIT_MAX = 10


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW
    attempts = [t for t in _login_attempts[ip] if t > window_start]
    _login_attempts[ip] = attempts
    if len(attempts) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )
    _login_attempts[ip].append(now)


def _issue_token(user: UserModel) -> str:
    return create_access_token(
        user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def _unit_summary(cu, role_ref=None, membership_role=None) -> ChurchUnitSummary:
    role = membership_role.name if membership_role else (role_ref.name if role_ref else None)
    role_label = membership_role.label if membership_role else (role_ref.label if role_ref else None)
    return ChurchUnitSummary(
        id=cu.id,
        name=cu.name,
        type=cu.type.value if hasattr(cu.type, "value") else str(cu.type),
        role=role,
        role_label=role_label,
    )


_ADMIN_PORTAL_PERMISSIONS = {"admin:all", "admin:parish", "admin:outstation", "admin:settings", "reporting:read"}


def _build_login_context(user: UserModel) -> dict:
    """
    Returns the routing hint, accessible units list, and default unit for the LoginResponse.

    Routing rules:
      super_admin    — role has admin:all → unrestricted admin portal, no unit selection
      admin_portal   — role has any admin-level permission (parish/outstation admin) →
                       scoped admin portal; unit selection if multiple units
      unit_dashboard — exactly one accessible unit, no admin perms → regular portal
      unit_selection — two or more units, no admin perms → unit-picker screen
      no_access      — authenticated but no unit and not super admin
    """
    # Collect all effective permissions: global role + all unit-level roles
    all_perms: set[str] = set()
    if user.role_ref:
        all_perms.update(p.code for p in user.role_ref.permissions)
    for membership in (user.unit_memberships or []):
        if membership.role:
            all_perms.update(p.code for p in membership.role.permissions)

    is_super = "admin:all" in all_perms
    if is_super:
        return {"routing": "super_admin", "accessible_units": [], "default_unit": None}

    # Collect accessible units from multi-unit memberships
    units: dict[int, ChurchUnitSummary] = {}
    for membership in (user.unit_memberships or []):
        cu = membership.church_unit
        if cu is None:
            continue
        units[cu.id] = _unit_summary(cu, role_ref=user.role_ref, membership_role=membership.role)

    unit_list = list(units.values())

    if len(unit_list) == 0:
        return {"routing": "no_access", "accessible_units": [], "default_unit": None}

    # Any admin-level permission → route to admin portal
    is_admin = bool(all_perms & _ADMIN_PORTAL_PERMISSIONS)
    if is_admin:
        default = unit_list[0] if len(unit_list) == 1 else None
        routing = "admin_portal" if len(unit_list) == 1 else "admin_unit_selection"
        return {"routing": routing, "accessible_units": unit_list, "default_unit": default}

    if len(unit_list) == 1:
        return {"routing": "unit_dashboard", "accessible_units": unit_list, "default_unit": unit_list[0]}
    else:
        return {"routing": "unit_selection", "accessible_units": unit_list, "default_unit": None}


def _lookup_user(session, identifier: str) -> UserModel | None:
    """Resolve email address or phone number to a User."""
    if "@" in identifier:
        return session.query(UserModel).filter(UserModel.email == identifier).first()
    digits = "".join(c for c in identifier if c.isdigit())
    return session.query(UserModel).filter(UserModel.phone == digits).first()


# ── Password login ────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    session: SessionDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """Password login. Accepts email or phone as username."""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    if not is_method_enabled(session, "password"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password login is disabled. Please use OTP login.",
        )

    user = _lookup_user(session, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")

    check_user_status(user)
    request.state.audit_user_id = str(user.id)

    return LoginResponse(
        access_token=_issue_token(user),
        token_type="bearer",
        user=User.model_validate(user),
        **_build_login_context(user),
    )


# ── OTP schemas ───────────────────────────────────────────────────────────────

class OTPRequestBody(BaseModel):
    """identifier: email address OR phone number with country code (e.g. 233543460633)"""
    identifier: str

    @field_validator("identifier")
    @classmethod
    def strip_identifier(cls, v: str) -> str:
        return v.strip()


class OTPVerifyBody(BaseModel):
    """identifier: email address OR phone number"""
    identifier: str
    code: str

    @field_validator("identifier")
    @classmethod
    def strip_identifier(cls, v: str) -> str:
        return v.strip()


# ── OTP request ───────────────────────────────────────────────────────────────

@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_otp(
    request: Request,
    session: SessionDep,
    body: OTPRequestBody,
) -> Any:
    """
    Request a one-time login code.
    One code is generated and sent to ALL available channels simultaneously:
      - Email (if otp_email_enabled and user has an email)
      - SMS   (if otp_sms_enabled and user has a phone number)

    Always returns 202 regardless of outcome (anti-enumeration).
    """
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    # At least one OTP method must be enabled
    email_enabled = is_method_enabled(session, "otp_email")
    sms_enabled = is_method_enabled(session, "otp_sms")
    if not email_enabled and not sms_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OTP login is not enabled on this system.",
        )

    user = _lookup_user(session, body.identifier)

    if not user or user.status == UserStatus.DISABLED:
        return {"message": "If that account exists, a code has been sent."}

    raw_code = generate_otp(session, user)
    session.commit()

    # Send to every available channel in parallel — fire and forget failures
    if email_enabled:
        await send_otp_email(user, raw_code)

    if sms_enabled and user.phone:
        send_otp_sms(user, raw_code)

    return {"message": "If that account exists, a code has been sent."}


# ── OTP verify ────────────────────────────────────────────────────────────────

@router.post("/otp/verify", response_model=LoginResponse)
async def verify_otp_login(
    request: Request,
    session: SessionDep,
    body: OTPVerifyBody,
) -> Any:
    """
    Verify a one-time code and receive a JWT token.
    identifier: email or phone number.
    """
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    user = _lookup_user(session, body.identifier)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid code")

    if user.status == UserStatus.DISABLED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled.")

    if not verify_otp(session, user, raw_code=body.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code")

    session.commit()
    request.state.audit_user_id = str(user.id)

    return LoginResponse(
        access_token=_issue_token(user),
        token_type="bearer",
        user=User.model_validate(user),
        **_build_login_context(user),
    )


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(current_user: CurrentUser) -> Any:
    """
    Record a logout event. JWTs are stateless so the server cannot invalidate
    the token — the client must discard it. This endpoint exists solely so that
    the audit middleware can log the logout action against the authenticated user.
    """
    return {"message": "Logged out successfully"}


# ── Current user ──────────────────────────────────────────────────────────────

@router.get("/me", response_model=User)
async def read_users_me(current_user: CurrentUser) -> Any:
    return User.model_validate(current_user)


@router.post("/test-token", response_model=User)
async def test_token(current_user: CurrentUser) -> Any:
    return User.model_validate(current_user)


# ── Password reset ────────────────────────────────────────────────────────────

@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(reset_data: PasswordResetRequest, session: SessionDep) -> Any:
    """First-login password reset. Requires the temporary password set by admin."""
    user = session.query(UserModel).filter(UserModel.email == reset_data.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.status != UserStatus.RESET_REQUIRED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Password reset not required for this user")

    if not verify_password(reset_data.temp_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid temporary password")

    user.hashed_password = get_password_hash(reset_data.new_password)
    user.status = UserStatus.ACTIVE
    session.commit()
    session.refresh(user)
    request.state.audit_user_id = str(user.id)

    return PasswordResetResponse(
        message="Password reset successful. You are now logged in.",
        access_token=_issue_token(user),
        token_type="bearer",
        user=User.model_validate(user),
        **_build_login_context(user),
    )

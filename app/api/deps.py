from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError, api_jwt
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.core.database import db
from app.models.user import User as UserModel, UserStatus, UserChurchUnit


class TokenPayload(BaseModel):
    sub: str | None = None
    iat: int | None = None


reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


def get_db() -> Generator[Session, None, None]:
    with db.session() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def check_user_status(user: UserModel) -> None:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            headers={"X-Reset-Required": "true"},
        )

    if user.status == UserStatus.DISABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled. Please contact support for assistance.",
            headers={"X-Reset-Required": "true"},
        )
    elif user.status == UserStatus.RESET_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password reset required. Please reset your password before continuing.",
            headers={"X-Reset-Required": "true"},
        )
    elif user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not active. Please verify your account or contact support.",
            headers={"X-Reset-Required": "true"},
        )


def get_current_user(
    session: SessionDep,
    token: TokenDep,
) -> UserModel:
    try:
        payload = api_jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token_data.sub is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(token_data.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid user ID format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.query(UserModel).filter(UserModel.id == user_id).first()
    check_user_status(user)

    # Check if this token was issued before the user's last role/permission change
    if user.tokens_invalidated_before is not None and token_data.iat is not None:
        token_issued_at = datetime.fromtimestamp(token_data.iat, tz=timezone.utc)
        if token_issued_at < user.tokens_invalidated_before:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session is no longer valid. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return user


CurrentUser = Annotated[UserModel, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> UserModel:
    if current_user.role_ref is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No role assigned to this user.",
        )
    user_permissions = {p.code for p in current_user.role_ref.permissions}
    if "admin:all" not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges. This action requires super admin access.",
        )
    return current_user


def _resolve_permissions(
    current_user: UserModel,
    x_church_unit_id: int | None,
) -> set[str]:
    """
    Return the effective permission set for this request.

    - Super admins (admin:all on global role): always full permissions.
    - Unit selected via header: use the role assigned to the user for THAT unit.
      Falls back to global role if no unit-specific role is set.
    - No unit header: use the global role.
    """
    global_perms: set[str] = set()
    if current_user.role_ref:
        global_perms = {p.code for p in current_user.role_ref.permissions}

    # Super admin bypass — always wins
    if "admin:all" in global_perms:
        return global_perms

    if x_church_unit_id is not None:
        # Find the membership row for the selected unit
        membership = next(
            (m for m in current_user.unit_memberships if m.church_unit_id == x_church_unit_id),
            None,
        )
        if membership and membership.role:
            return {p.code for p in membership.role.permissions}
        # No unit-specific role — fall back to global role
        return global_perms

    return global_perms


def require_permission(permission_code: str):
    """
    Dependency factory that checks if the current user has a specific permission,
    resolving permissions against the unit selected via X-Church-Unit-Id header.
    """
    def _checker(
        current_user: Annotated[UserModel, Depends(get_current_user)],
        x_church_unit_id: Annotated[int | None, Header(alias="X-Church-Unit-Id")] = None,
    ) -> UserModel:
        if current_user.role_ref is None and not current_user.unit_memberships:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No role assigned to this user",
            )
        effective_perms = _resolve_permissions(current_user, x_church_unit_id)
        if "admin:all" in effective_perms or permission_code in effective_perms:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission_code} required",
        )
    return Depends(_checker)


def is_super_admin(current_user: CurrentUser) -> bool:
    """Check if user is super admin (has admin:all permission)."""
    if current_user.role_ref is None:
        return False
    return any(p.code == "admin:all" for p in current_user.role_ref.permissions)


def is_admin(user: "UserModel") -> bool:
    """True for super_admin or any user with admin:all permission."""
    if user.role_ref is None:
        return False
    return any(p.code == "admin:all" for p in user.role_ref.permissions)


def has_permission(user: "UserModel", permission_code: str) -> bool:
    """Check if user has a specific permission (or admin:all)."""
    if user.role_ref is None:
        return False
    perms = {p.code for p in user.role_ref.permissions}
    return "admin:all" in perms or permission_code in perms


def get_church_unit_scope(
    current_user: CurrentUser,
    x_church_unit_id: Annotated[int | None, Header(alias="X-Church-Unit-Id")] = None,
) -> int | None:
    """
    Returns the church_unit_id the current user is scoped to, or None for parish-wide access.

    Resolution order:
    1. Super admins always get None (no scope restriction).
    2. If the client sends X-Church-Unit-Id header, validate the user has access
       to that unit (via unit_memberships), then use it.
    3. If the user has exactly one unit membership, auto-scope to it.
    4. Multiple memberships and no header → None (caller must send the header).
    """
    if is_super_admin(current_user):
        return None

    accessible_ids = {m.church_unit_id for m in current_user.unit_memberships}

    if x_church_unit_id is not None:
        if x_church_unit_id not in accessible_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to the selected church unit.",
            )
        return x_church_unit_id

    # Auto-scope when the user belongs to exactly one unit
    if len(accessible_ids) == 1:
        return next(iter(accessible_ids))

    return None


OutstationScope = Annotated[int | None, Depends(get_church_unit_scope)]
ChurchUnitScope = Annotated[int | None, Depends(get_church_unit_scope)]

RequireSuperAdmin = require_permission("admin:all")
RequireParishAdmin = require_permission("admin:parish")
RequireManageUsers = require_permission("user:write")
RequireManageRoles = require_permission("admin:roles")

import logging
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser, ChurchUnitScope, require_permission, is_super_admin
from app.core.config import settings
from app.core.security import get_password_hash
from app.schemas.common import APIResponse
from app.schemas.user import ChurchUnitAssignment, User, UserCreate, UserUpdate
from app.models.user import User as UserModel, UserChurchUnit, UserStatus
from app.models.rbac import Role
from app.models.parish import ChurchUnit

logger = logging.getLogger(__name__)

router = APIRouter()


def _assert_user_in_unit(user: UserModel, unit_scope: int) -> None:
    """Raise 403 if the target user has no membership in the given unit."""
    unit_ids = {m.church_unit_id for m in (user.unit_memberships or [])}
    if unit_scope not in unit_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage users who belong to your church unit.",
        )


@router.get("/{user_id}", response_model=APIResponse)
async def get_user(
    user_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
) -> Any:
    user = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if unit_scope is not None:
        _assert_user_in_unit(user, unit_scope)
    return APIResponse(message="User retrieved successfully", data=User.model_validate(user))


@router.get("", response_model=APIResponse, dependencies=[require_permission("user:read")])
async def get_users(
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    q = session.query(UserModel)
    if unit_scope is not None:
        unit_user_ids = [
            m.user_id
            for m in session.query(UserChurchUnit.user_id)
            .filter(UserChurchUnit.church_unit_id == unit_scope)
            .all()
        ]
        q = q.filter(UserModel.id.in_(unit_user_ids))
    users = q.offset(skip).limit(limit).all()
    return APIResponse(
        message="Users retrieved successfully",
        data=[User.model_validate(user) for user in users],
    )


@router.put("/{user_id}", response_model=APIResponse, dependencies=[require_permission("user:write")])
async def update_user(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
    user_id: UUID,
    user_in: UserUpdate,
) -> Any:
    user = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    if user.email == settings.SUPER_ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify the main super admin account",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update your own profile through this endpoint. Please use the profile update endpoint",
        )

    # Unit-scoped users can only edit users in their unit
    if unit_scope is not None:
        _assert_user_in_unit(user, unit_scope)

    update_data = user_in.model_dump(exclude_unset=True)

    # Handle role_name -> role_id resolution
    if "role_name" in update_data:
        role_name = update_data.pop("role_name")
        if role_name is not None:
            role = session.query(Role).filter(Role.name == role_name).first()
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role '{role_name}' not found",
                )
            # Only super admins can assign the super_admin role
            if role.name == "super_admin" and not is_super_admin(current_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only a super admin can assign the super_admin role",
                )
            update_data["role_id"] = role.id
        else:
            update_data["role_id"] = None

    # Validate login_method requires phone for sms_otp
    if update_data.get("login_method") == "sms_otp":
        phone = update_data.get("phone", user.phone)
        if not phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A phone number is required when setting login method to sms_otp",
            )

    role_changed = "role_id" in update_data and update_data["role_id"] != user.role_id

    for field, value in update_data.items():
        setattr(user, field, value)

    # Invalidate all existing tokens so the user must re-login with their new role
    if role_changed:
        user.tokens_invalidated_before = datetime.now(timezone.utc)

    try:
        session.add(user)
        session.commit()
        session.refresh(user)
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating user")

    return APIResponse(message="User updated successfully", data=User.model_validate(user))


@router.delete("/{user_id}", response_model=APIResponse, dependencies=[require_permission("user:delete")])
async def delete_user(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
    user_id: UUID,
) -> Any:
    user = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    if user.email == settings.SUPER_ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify the main super admin account",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete your own user account",
        )

    # Unit-scoped users can only delete users in their unit
    if unit_scope is not None:
        _assert_user_in_unit(user, unit_scope)

    user_data = User.model_validate(user)
    session.delete(user)
    session.commit()
    return APIResponse(message="User deleted successfully", data=user_data)


@router.post("", response_model=APIResponse, dependencies=[require_permission("user:write")])
async def create_user(
    *,
    session: SessionDep,
    user_in: UserCreate,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
) -> Any:
    try:
        temp_password = secrets.token_urlsafe(12)

        # Resolve role by name if provided
        role_id = None
        if user_in.role_name:
            role = session.query(Role).filter(Role.name == user_in.role_name).first()
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role '{user_in.role_name}' not found",
                )
            # Only super admins can create users with the super_admin role
            if role.name == "super_admin" and not is_super_admin(current_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only a super admin can assign the super_admin role",
                )
            role_id = role.id

        # Unit-scoped users must assign the new user to their unit
        church_units = user_in.church_units or []
        if unit_scope is not None:
            provided_unit_ids = {a.church_unit_id for a in church_units}
            if not provided_unit_ids:
                # Auto-assign to the creator's unit
                church_units = [ChurchUnitAssignment(church_unit_id=unit_scope)]
            elif unit_scope not in provided_unit_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only create users assigned to your church unit.",
                )
            # Strip any units outside the creator's scope
            church_units = [a for a in church_units if a.church_unit_id == unit_scope]

        from app.models.user import LoginMethod
        user = UserModel(
            email=user_in.email,
            full_name=user_in.full_name,
            phone=user_in.phone,
            login_method=user_in.login_method or LoginMethod.PASSWORD,
            role_id=role_id,
            hashed_password=get_password_hash(temp_password),
            status=user_in.status or UserStatus.RESET_REQUIRED,
        )
        session.add(user)
        session.flush()

        # Assign church unit memberships
        if church_units:
            from app.models.rbac import Role as RoleModel
            for assignment in church_units:
                unit = session.query(ChurchUnit).filter(ChurchUnit.id == assignment.church_unit_id).first()
                if not unit:
                    raise HTTPException(status_code=400, detail=f"Church unit {assignment.church_unit_id} not found")
                unit_role_id = None
                if assignment.role_name:
                    r = session.query(RoleModel).filter(RoleModel.name == assignment.role_name).first()
                    if not r:
                        raise HTTPException(status_code=400, detail=f"Role '{assignment.role_name}' not found")
                    unit_role_id = r.id
                session.add(UserChurchUnit(user_id=user.id, church_unit_id=assignment.church_unit_id, role_id=unit_role_id))

        session.commit()
        session.refresh(user)

        from app.services.email.service import email_service
        from app.services.sms.service import sms_service

        email_sent = await email_service.send_welcome_email(
            email=user.email,
            full_name=user.full_name,
            temp_password=temp_password,
        )
        if not email_sent:
            logger.warning(f"Failed to send welcome email to {user.email}")

        sms_sent = False
        if user.phone:
            sms_result = sms_service.send_user_account_created(
                phone=user.phone,
                full_name=user.full_name,
                email=user.email,
                temp_password=temp_password,
            )
            sms_sent = sms_result.get("success", False)
            if not sms_sent:
                logger.warning(f"Failed to send account creation SMS to {user.phone}")

        notifications = []
        if email_sent:
            notifications.append("email")
        if sms_sent:
            notifications.append("SMS")

        msg = "User created successfully"
        if notifications:
            msg += f" — notifications sent via {' and '.join(notifications)}"

        return APIResponse(
            message=msg,
            data=User.model_validate(user),
        )

    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating user")


# ── Church unit assignments ────────────────────────────────────────────────────

def _get_user_or_404(session, user_id: UUID) -> UserModel:
    user = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/{user_id}/church-units", response_model=APIResponse,
            dependencies=[require_permission("user:read")])
async def get_user_church_units(
    user_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
) -> Any:
    """List all church units assigned to a user."""
    user = _get_user_or_404(session, user_id)
    if unit_scope is not None:
        _assert_user_in_unit(user, unit_scope)
    data = []
    for m in (user.unit_memberships or []):
        cu = m.church_unit
        if not cu:
            continue
        # Unit-scoped: only return the scoped unit's membership
        if unit_scope is not None and cu.id != unit_scope:
            continue
        data.append({
            "church_unit_id": cu.id,
            "church_unit_name": cu.name,
            "church_unit_type": cu.type.value if hasattr(cu.type, "value") else str(cu.type),
            "role": m.role.name if m.role else None,
            "role_label": m.role.label if m.role else None,
        })
    return APIResponse(message=f"{len(data)} church unit(s) assigned", data=data)


@router.post("/{user_id}/church-units", response_model=APIResponse,
             dependencies=[require_permission("user:write")])
async def assign_church_units(
    user_id: UUID,
    assignments: list[ChurchUnitAssignment],
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
) -> Any:
    """
    Assign one or more church units to a user.
    Already-assigned units are updated in-place (role changed if provided).
    Unit-scoped callers can only assign their own unit.
    """
    from app.models.rbac import Role as RoleModel

    user = _get_user_or_404(session, user_id)
    if unit_scope is not None:
        _assert_user_in_unit(user, unit_scope)
        assignments = [a for a in assignments if a.church_unit_id == unit_scope]

    existing = {
        m.church_unit_id: m
        for m in session.query(UserChurchUnit).filter(UserChurchUnit.user_id == user_id).all()
    }

    for a in assignments:
        unit = session.query(ChurchUnit).filter(ChurchUnit.id == a.church_unit_id).first()
        if not unit:
            raise HTTPException(status_code=400, detail=f"Church unit {a.church_unit_id} not found")

        unit_role_id = None
        if a.role_name:
            r = session.query(RoleModel).filter(RoleModel.name == a.role_name).first()
            if not r:
                raise HTTPException(status_code=400, detail=f"Role '{a.role_name}' not found")
            unit_role_id = r.id

        if a.church_unit_id in existing:
            existing[a.church_unit_id].role_id = unit_role_id
        else:
            session.add(UserChurchUnit(user_id=user_id, church_unit_id=a.church_unit_id, role_id=unit_role_id))

    session.commit()
    return APIResponse(message=f"{len(assignments)} church unit(s) assigned successfully", data=None)


@router.put("/{user_id}/church-units", response_model=APIResponse,
            dependencies=[require_permission("user:write")])
async def replace_church_units(
    user_id: UUID,
    assignments: list[ChurchUnitAssignment],
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
) -> Any:
    """
    Replace all church unit assignments for a user atomically.
    Unit-scoped callers only replace their own unit's assignment (other units are preserved).
    """
    from app.models.rbac import Role as RoleModel

    user = _get_user_or_404(session, user_id)
    if unit_scope is not None:
        _assert_user_in_unit(user, unit_scope)
        # Only replace the scoped unit; strip anything outside scope
        assignments = [a for a in assignments if a.church_unit_id == unit_scope]

    # Validate all units and roles before making changes
    resolved = []
    for a in assignments:
        unit = session.query(ChurchUnit).filter(ChurchUnit.id == a.church_unit_id).first()
        if not unit:
            raise HTTPException(status_code=400, detail=f"Church unit {a.church_unit_id} not found")
        unit_role_id = None
        if a.role_name:
            r = session.query(RoleModel).filter(RoleModel.name == a.role_name).first()
            if not r:
                raise HTTPException(status_code=400, detail=f"Role '{a.role_name}' not found")
            unit_role_id = r.id
        resolved.append((a.church_unit_id, unit_role_id))

    if unit_scope is not None:
        # Only delete the scoped unit's membership; leave others intact
        session.query(UserChurchUnit).filter(
            UserChurchUnit.user_id == user_id,
            UserChurchUnit.church_unit_id == unit_scope,
        ).delete()
    else:
        session.query(UserChurchUnit).filter(UserChurchUnit.user_id == user_id).delete()

    for church_unit_id, role_id in resolved:
        session.add(UserChurchUnit(user_id=user_id, church_unit_id=church_unit_id, role_id=role_id))

    session.commit()
    return APIResponse(message=f"Church units updated — {len(resolved)} unit(s) assigned", data=None)


@router.delete("/{user_id}/church-units/{unit_id}", response_model=APIResponse,
               dependencies=[require_permission("user:write")])
async def remove_church_unit(
    user_id: UUID,
    unit_id: int,
    session: SessionDep,
    current_user: CurrentUser,
    unit_scope: ChurchUnitScope,
) -> Any:
    """Remove a single church unit from a user."""
    user = _get_user_or_404(session, user_id)
    if unit_scope is not None and unit_id != unit_scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only remove users from your own church unit.",
        )
    membership = session.query(UserChurchUnit).filter(
        UserChurchUnit.user_id == user_id,
        UserChurchUnit.church_unit_id == unit_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="This user is not assigned to that church unit")
    session.delete(membership)
    session.commit()
    return APIResponse(message="Church unit removed from user", data=None)

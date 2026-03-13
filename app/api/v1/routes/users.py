import logging
import secrets
from typing import Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser
from app.core.config import settings
from app.core.security import get_password_hash
from app.schemas.common import APIResponse
from app.schemas.user import User, UserCreate, UserUpdate
from app.models.user import User as UserModel, UserRole, UserStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/users/{user_id}", response_model=APIResponse)
async def get_user(
    user_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    user = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return APIResponse(message="User retrieved successfully", data=User.model_validate(user))


@router.get("/users", response_model=APIResponse)
async def get_users(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    users = session.query(UserModel).offset(skip).limit(limit).all()
    return APIResponse(
        message="Users retrieved successfully",
        data=[User.model_validate(user) for user in users],
    )


@router.put("/users/{user_id}", response_model=APIResponse)
async def update_user(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    user_id: UUID,
    user_in: UserUpdate,
) -> Any:
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Only super admins can update users.",
        )

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

    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    try:
        session.add(user)
        session.commit()
        session.refresh(user)
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating user")

    return APIResponse(message="User updated successfully", data=User.model_validate(user))


@router.delete("/users/{user_id}", response_model=APIResponse)
async def delete_user(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    user_id: UUID,
) -> Any:
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

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

    session.delete(user)
    session.commit()
    return APIResponse(message="User deleted successfully", data=User.model_validate(user))


@router.post("/users", response_model=APIResponse)
async def create_user(
    *,
    session: SessionDep,
    user_in: UserCreate,
    current_user: CurrentUser,
) -> Any:
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    try:
        temp_password = secrets.token_urlsafe(12)

        user = UserModel(
            email=user_in.email,
            full_name=user_in.full_name,
            role=user_in.role or UserRole.USER,
            hashed_password=get_password_hash(temp_password),
            status=user_in.status or UserStatus.RESET_REQUIRED,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        from app.services.email.service import email_service
        email_sent = await email_service.send_welcome_email(
            email=user.email,
            full_name=user.full_name,
            temp_password=temp_password,
        )

        if not email_sent:
            logger.warning(f"Failed to send welcome email to {user.email}")

        return APIResponse(
            message="User created successfully" + (" and welcome email sent" if email_sent else " but email sending failed"),
            data=User.model_validate(user),
        )

    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating user")

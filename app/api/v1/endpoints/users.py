from typing import Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import SessionDep, CurrentUser

from app.core.security import get_password_hash
from app.schemas.user import User, UserCreate, UserUpdate
from app.models.user import User as UserModel

class APIResponse(BaseModel):
    message: str
    user: User

router = APIRouter()

@router.get("/users", response_model=list[User])
async def get_users(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get all users with pagination.
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    users = session.query(UserModel)\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return [User.model_validate(user) for user in users]


@router.put("/users/{user_id}", response_model=APIResponse)
async def update_user(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    user_id: int,
    user_in: UserUpdate,
) -> Any:
    """
    Update existing user. Only super_admin can update users.
    Updatable fields: full_name, is_active, and role
    """
    # Only super_admin can update users
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Get existing user
    user = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update allowed fields if provided
    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    if user_in.role is not None:
        user.role = user_in.role
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return {
        "message": "User Updated successfully",
        "user": User.model_validate(user)
    }

@router.delete("/users/{user_id}", response_model=APIResponse)
async def delete_user(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    user_id: int,
) -> Any:
    """
    Delete existing user.
    """
    # Only super_admin can delete users
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Get user to delete
    user = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own user account"
        )
    
    # Delete user
    session.delete(user)
    session.commit()
    
    return {
        "message": "User deleted successfully",
        "user": User.model_validate(user)
    }


@router.get("/users/{user_id}", response_model=APIResponse)
async def get_user(
    user_id: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Get user by ID.
    """
    user = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return User.model_validate(user)

@router.post("/users", response_model=APIResponse)
async def create_user(
    *,
    session: SessionDep,
    user_in: UserCreate,
    current_user: CurrentUser,
) -> Any:
    """
    Create new user.
    """
    # Check if the current user has permission to create users
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if user with this email exists
    user = session.query(UserModel).filter(UserModel.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = UserModel(
        email=user_in.email,
        full_name=user_in.full_name,
        role=user_in.role,
        hashed_password=get_password_hash(user_in.password),
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return {
        "message": "User created succeffully",
        "user" : User.model_validate(user)
    }
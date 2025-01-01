import logging
from typing import Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.deps import SessionDep, CurrentUser

from app.core.security import get_password_hash
from app.schemas.user import User, UserCreate, UserUpdate
from app.models.user import User as UserModel, UserRole, UserStatus

class APIResponse(BaseModel):
    message: str
    user: User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter()

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
    Updatable fields: full_name, status, and role
    """
    # Only super_admin can update users
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Only super admins can update users."
        )
    
    # Get existing user
    user = session.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Prevent updating the main super admin account
    if user.email == "database.sfoacc@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify the main super admin account"
        )
    
    # Prevent users from updating their own profile through this endpoint
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update your own profile through this endpoint. Please use the profile update endpoint"
        )
     # Update only provided fields
    update_data = user_in.model_dump(exclude_unset=True)
    
    # Apply updates
    for field, value in update_data.items():
        setattr(user, field, value)
    
    try:
        session.add(user)
        session.commit()
        session.refresh(user)
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating user: {str(e)}"
        )
    
    return APIResponse(
        message="User updated successfully",
        user=User.model_validate(user)
    )
    
    # # Update allowed fields if provided
    # if user_in.full_name is not None:
    #     user.full_name = user_in.full_name
    # if user_in.status is not None:
    #     user.status = user_in.status
    # if user_in.role is not None:
    #     user.role = user_in.role
    
    # session.add(user)
    # session.commit()
    # session.refresh(user)
    
    # return {
    #     "message": "User Updated successfully",
    #     "user": User.model_validate(user)
    # }

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
    
    # Prevent deleting the main super admin account
    if user.email == "database.sfoacc@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify the main super admin account"
        )
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete your own user account"
        )
    
    # Delete user
    session.delete(user)
    session.commit()
    
    return {
        "message": "User deleted successfully",
        "user": User.model_validate(user)
    }

@router.post("/users", response_model=APIResponse)
async def create_user(
    *,
    session: SessionDep,
    user_in: UserCreate,
    current_user: CurrentUser,
) -> Any:
    """
    Create new user.
    Only email and full_name are required.
    Optional fields:
    - role (defaults to USER)
    - status (defaults to RESET_REQUIRED)
    - password (auto-generated (set to "password") if not provided)
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
    
    try:
        # Generate or use provided temporary password
        temp_password = "password123"
        
        # Create new user with default or provided values
        user = UserModel(
            email=user_in.email,
            full_name=user_in.full_name,
            role=user_in.role or UserRole.USER,
            hashed_password=get_password_hash(temp_password),
            status=user_in.status or UserStatus.ACTIVE #change to resetrequired after you implmement it
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        
        # Send welcome email with credentials
        from app.services.email.service import email_service
        email_sent = await email_service.send_welcome_email(
            email=user.email,
            full_name=user.full_name,
            temp_password=temp_password
        )
        
        if not email_sent:
            # logger.warning(f"Failed to send welcome email to {user.email}")
            print(F"Failed to send welcome email to {user.email}")
        
        return {
            "message": "User created successfully" + 
                      (" and welcome email sent" if email_sent else " but email sending failed"),
            "user": User.model_validate(user)
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )
    

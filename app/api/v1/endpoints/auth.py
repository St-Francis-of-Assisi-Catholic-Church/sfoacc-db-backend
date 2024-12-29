# app/api/auth.py
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.api.deps import SessionDep, CurrentUser

from app.schemas.user import LoginResponse, User, UserCreate
from app.models.user import User as UserModel

router = APIRouter()
    
@router.post("/login", response_model=LoginResponse)
async def login(
    session: SessionDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = session.query(UserModel).filter(
        UserModel.email == form_data.username
    ).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user.id,
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": User.model_validate(user)
    }

@router.get("/me", response_model=User)
async def read_users_me(
    current_user: CurrentUser,
) -> Any:
    """
    Get current user.
    """
    return User.model_validate(current_user)

@router.post("/test-token", response_model=User)
async def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token.
    """
    return User.model_validate(current_user)

# @router.get("/user/{user_id}", response_model=User)
# async def get_user(
#     user_id: int,
#     session: SessionDep,
#     current_user: CurrentUser,
# ) -> Any:
#     """
#     Get user by ID.
#     """
#     user = session.query(UserModel).filter(UserModel.id == user_id).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
#     return User.model_validate(user)

# @router.post("/users", response_model=User)
# async def create_user(
#     *,
#     session: SessionDep,
#     user_in: UserCreate,
#     current_user: CurrentUser,
# ) -> Any:
#     """
#     Create new user.
#     """
#     # Check if the current user has permission to create users
#     if current_user.role != "super_admin":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not enough permissions"
#         )
    
#     # Check if user with this email exists
#     user = session.query(UserModel).filter(UserModel.email == user_in.email).first()
#     if user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Email already registered"
#         )
    
#     # Create new user
#     user = UserModel(
#         email=user_in.email,
#         full_name=user_in.full_name,
#         role=user_in.role,
#         hashed_password=get_password_hash(user_in.password),
#         is_active=True
#     )
#     session.add(user)
#     session.commit()
#     session.refresh(user)
    
#     return User.model_validate(user)
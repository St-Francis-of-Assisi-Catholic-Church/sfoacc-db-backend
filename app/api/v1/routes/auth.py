from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.api.deps import SessionDep, CurrentUser, check_user_status

from app.schemas.user import LoginResponse, User
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
            #  headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check user status using centralized function
    check_user_status(user)

    # Generate access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user.id,
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=User.model_validate(user)
    )

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


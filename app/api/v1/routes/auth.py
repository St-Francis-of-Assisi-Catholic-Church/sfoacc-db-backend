import time
from collections import defaultdict
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.api.deps import SessionDep, CurrentUser, check_user_status

from app.schemas.user import LoginResponse, PasswordResetRequest, PasswordResetResponse, User
from app.models.user import User as UserModel, UserStatus

router = APIRouter()

# Simple in-memory rate limiter: ip -> [timestamp, ...]
_login_attempts: dict = defaultdict(list)
_RATE_LIMIT_WINDOW = 60   # seconds
_RATE_LIMIT_MAX = 10      # max attempts per window per IP


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


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    session: SessionDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    user = session.query(UserModel).filter(
        UserModel.email == form_data.username
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
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



@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(
    reset_data: PasswordResetRequest,
    session: SessionDep,
) -> Any:
    """
    Reset password for users with RESET_REQUIRED status.
    Validates temp password and sets new password, then auto-logs in the user.
    """
    # Find user by email
    user = session.query(UserModel).filter(
        UserModel.email == reset_data.email
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check if user status is RESET_REQUIRED
    if user.status != UserStatus.RESET_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset not required for this user",
        )
    
    # Verify temp password
    if not verify_password(reset_data.temp_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid temporary password",
        )
    
    # Update user with new password and set status to ACTIVE
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.status = UserStatus.ACTIVE
    
    # Commit the changes
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Generate access token for auto-login
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user.id,
        expires_delta=access_token_expires
    )
    
    return PasswordResetResponse(
        message="Password reset successful. You are now logged in.",
        access_token=access_token,
        token_type="bearer",
        user=User.model_validate(user)
    )
    


from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, verify_password, decode_access_token
from app.core.database import db
from app.schemas.user import User, UserInDB
from app.models.user import User as UserModel, UserRole

router = APIRouter()

# OAuth2 scheme for token handling
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# Authentication schemas extending your user schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginResponse(Token):
    user: UserInDB

@router.post("/login", response_model=LoginResponse)
async def login(email: str, password: str) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    try:
        with db.session() as session:
            # Find user
            user = session.query(UserModel).filter(UserModel.email == email).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                )

            # Verify password
            if not verify_password(password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password -> verify password failed",
                )

            # Check if user is active
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inactive user"
                )

            # Generate access token
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                user.id, expires_delta=access_token_expires
            )

            # Return token and user info
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": user
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserModel:
    """
    Dependency to get current user from JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        with db.session() as session:
            user = session.query(UserModel).filter(UserModel.id == user_id).first()
            if user is None:
                raise credentials_exception
            return user

    except Exception:
        raise credentials_exception

async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    Dependency to get current active user.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

async def get_current_active_superuser(
    current_user: UserModel = Depends(get_current_active_user)
) -> UserModel:
    """
    Dependency to get current active superuser.
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

@router.get("/me", response_model=User)
async def read_users_me(
    current_user: UserModel = Depends(get_current_active_user)
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.post("/verify-token", response_model=User)
async def verify_token(
    current_user: UserModel = Depends(get_current_active_user)
) -> Any:
    """
    Verify access token and return user info.
    """
    return current_user
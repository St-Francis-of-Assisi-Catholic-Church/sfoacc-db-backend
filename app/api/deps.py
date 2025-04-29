from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
# from jose import JWTError, jwt # type: ignore

from jwt import api_jwt
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.core.database import db
from app.models.user import User as UserModel, UserStatus



class TokenPayload(BaseModel):
    sub: str | None = None

# OAuth2 scheme setup
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_db() -> Generator[Session, None, None]:
    with db.session() as session:
        yield session

# Type dependencies
SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def check_user_status(user: UserModel) -> None:
    """
    Centralized user status checking logic to ensure consistent error handling
    Raises appropriate HTTPException based on user status
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.status == UserStatus.DISABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled. Please contact support for assistance."
        )
    elif user.status == UserStatus.RESET_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password reset required. Please reset your password before continuing."
        )
    elif user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not active. Please verify your account or contact support."
        )


def get_current_user(
    session: SessionDep,
    token: TokenDep,
) -> UserModel:
    """
    Validate the access token and return the current active user.
    Handles all token validation and user status checks.
    """
    try:
        payload = api_jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
    except (api_jwt.InvalidIssuerError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    # new checks
    if token_data.sub is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token payload"
        )
    
    try:
        user_id = UUID(token_data.sub)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Invalud userID format")

    user = session.query(UserModel).filter(UserModel.id == user_id).first()
    
    # Centralized status checking
    check_user_status(user)

    return user

# Current user dependency
CurrentUser = Annotated[UserModel, Depends(get_current_user)]

def get_current_active_superuser(
    current_user: CurrentUser,
) -> UserModel:
    """
    Verify the current user has superadmin privileges
    """
    if not current_user.role == "super_admin":
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges. This action requires super admin access."
        )
    return current_user

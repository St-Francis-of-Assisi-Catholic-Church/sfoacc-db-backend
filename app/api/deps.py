from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError, api_jwt
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.core.database import db
from app.models.user import User as UserModel, UserStatus


class TokenPayload(BaseModel):
    sub: str | None = None


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
    return user


CurrentUser = Annotated[UserModel, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> UserModel:
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges. This action requires super admin access.",
        )
    return current_user

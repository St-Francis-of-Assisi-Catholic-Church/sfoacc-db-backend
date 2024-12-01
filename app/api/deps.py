from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
# from jose import JWTError, jwt # type: ignore

from jwt import api_jwt
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.core.database import db
from app.models.user import User as UserModel



class TokenPayload(BaseModel):
    sub: int | None = None

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

def get_current_user(
    session: SessionDep,
    token: TokenDep,
) -> UserModel:
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
    
    user = session.query(UserModel).filter(UserModel.id == token_data.sub).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return user

# Current user dependency
CurrentUser = Annotated[UserModel, Depends(get_current_user)]

def get_current_active_superuser(
    current_user: CurrentUser,
) -> UserModel:
    if not current_user.role == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

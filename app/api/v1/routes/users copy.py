from collections.abc import Generator
from typing import Annotated, Any
from datetime import timedelta
import enum

from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import api_jwt
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM, verify_password, create_access_token
from app.core.database import db
from app.models.user import User as UserModel
from app.schemas.user import User

router = APIRouter()

class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    RESET_REQUIRED = "reset_required"

class TokenPayload(BaseModel):
    sub: int | None = None

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: User

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
            detail="Could not validate credentials. Please log in again."
        )
    
    if token_data.sub is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token payload"
        )
    
    user = session.query(UserModel).filter(UserModel.id == token_data.sub).first()
    
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

@router.post("/login", response_model=LoginResponse)
async def login(
    session: SessionDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login with comprehensive status checking
    Returns an access token for future requests
    """
    # First verify the user exists and credentials are correct
    user = session.query(UserModel).filter(
        UserModel.email == form_data.username
    ).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
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
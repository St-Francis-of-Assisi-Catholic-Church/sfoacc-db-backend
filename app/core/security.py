from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID
from fastapi import HTTPException, status
from jwt import api_jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7




def create_access_token(subject: str | UUID | Any, expires_delta: timedelta) -> str:
    """
    Create JWT access token with support for UUID objects
    
    Args:
        subject: The subject for the token (user ID) - can be UUID, str or other
        expires_delta: How long the token should be valid
        
    Returns:
        str: The encoded JWT token
    """
    expire = datetime.now(timezone.utc) + expires_delta
    
    # Ensure UUID is converted to string if that's what was passed
    subject_str = str(subject)
    
    to_encode = {"exp": expire, "sub": subject_str}
    encoded_jwt = api_jwt.encode(payload=to_encode, key=settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        dict: The decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = api_jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload
    except api_jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # except api_jwt.JWTError:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Could not validate credentials",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )

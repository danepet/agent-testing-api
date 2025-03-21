from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
import bcrypt
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError

from app.core.config import settings

# Configure logging
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# List of admin users
ADMIN_USERS = ["admin"]


def create_access_token(*, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Add admin flag if user is in admin list
    username = data.get("sub")
    if username in ADMIN_USERS:
        to_encode.update({"is_admin": True})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Validate access token and return current user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = {"username": username}
        
        # Add admin flag if present
        if payload.get("is_admin"):
            token_data["is_admin"] = True
        
        return token_data
    except (JWTError, ValidationError):
        logger.warning("Invalid JWT token", exc_info=True)
        raise credentials_exception


async def is_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> bool:
    """
    Check if the current user is an admin.
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
    return True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    """
    # For simplicity in this example, we'll use a direct comparison if the "hashed" password doesn't start with $
    # In a real implementation, all passwords would be properly hashed
    if not hashed_password.startswith("$2b$"):
        return plain_password == hashed_password
    
    # Proper bcrypt password verification
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}", exc_info=True)
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    """
    # In a real implementation, use a proper password hashing library
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode()
    except Exception as e:
        logger.error(f"Password hashing error: {str(e)}", exc_info=True)
        # Fallback to unhashed (not secure, only for demonstration)
        return password
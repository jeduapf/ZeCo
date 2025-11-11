"""
Security utilities: JWT, password hashing, authentication (ASYNC VERSION)
"""
from typing import Annotated, Optional
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from config import (
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, 
    TOKEN_REFRESH_THRESHOLD_MINUTES, DEBUG
)
from src.database.session import get_db
from src.database.models.user import User, UserRole
from src.schemas.user import LoginResponse, UserPublicResponse
from src.core.i18n_logger import get_i18n_logger
from config import LANG
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

if not SECRET_KEY or not ALGORITHM:
    raise RuntimeError("SECRET_KEY and ALGORITHM must be set in environment variables")

# Initialize password hashing and OAuth2
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

logger = get_i18n_logger(__name__)

# === Password Utilities ===

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: The password to verify
        hashed_password: The hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def validate_password(password: str) -> str:
    """
    Validate password meets security requirements.
    
    Requirements:
    - 8-72 characters (bcrypt limit)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - No spaces
    
    Args:
        password: Password to validate
        
    Returns:
        The validated password
        
    Raises:
        HTTPException: If password doesn't meet requirements
    """
    if len(password.encode('utf-8')) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be less than 72 bytes long"
        )
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    if " " in password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must not contain spaces"
        )
    if not any(char.isupper() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter"
        )
    if not any(char.islower() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter"
        )
    if not any(char.isdigit() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one digit"
        )
    if not any(char in "!@#$%^&*()-+_=[]{}|;:,.<>?" for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one special character (!@#$%^&*()-+_=[]{}|;:,.<>?)"
        )
    return password


def get_password_hash(password: str) -> str:
    """
    Hash a password after validation.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    validate_password(password)
    return pwd_context.hash(password)


# === JWT Token Utilities ===

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in token (typically {"sub": username})
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),  # Issued at
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        JWTError: If token is invalid
        ExpiredSignatureError: If token has expired
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def should_refresh_token(token: str) -> bool:
    """
    Check if token should be refreshed based on remaining time.
    
    Tokens are refreshed if they have less than TOKEN_REFRESH_THRESHOLD_MINUTES
    remaining before expiration.
    
    Args:
        token: JWT token to check
        
    Returns:
        True if token should be refreshed, False otherwise
    """
    try:
        payload = decode_token(token)
        exp_timestamp = payload.get("exp")
        
        if exp_timestamp is None:
            return False
        
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        time_remaining = exp_datetime - datetime.now(timezone.utc)
        
        return time_remaining.total_seconds() < (TOKEN_REFRESH_THRESHOLD_MINUTES * 60)
    
    except (JWTError, ExpiredSignatureError):
        # If token is invalid or expired, don't try to refresh
        return False


# === Authentication Dependencies ===

def get_token_remaining_minutes(payload: dict) -> float:
    """
    Returns the remaining time of a JWT token in minutes.
    """
    exp_timestamp = payload.get("exp")
    if exp_timestamp is None:
        return 0.0
    
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    remaining = exp_datetime - datetime.now(timezone.utc)
    
    # Return remaining time in minutes
    return remaining.total_seconds() / 60


def get_token_remaining_duration(token: str) -> timedelta:
    """
    Get the remaining duration for a token as a timedelta object.
    Used for token refresh to maintain the original session time.
    """
    try:
        payload = decode_token(token)
        exp_timestamp = payload.get("exp")
        
        if exp_timestamp is None:
            return timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        remaining = exp_datetime - datetime.now(timezone.utc)
        
        # Return remaining duration, but ensure it's at least 1 minute
        return max(remaining, timedelta(minutes=1))
    
    except (JWTError, ExpiredSignatureError):
        return timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response
) -> User:
    """
    Get current authenticated user from JWT token (ASYNC VERSION).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token has expired. Please login again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = decode_token(token)
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
        
    except ExpiredSignatureError:
        raise expired_exception
    
    except JWTError as e:
        if DEBUG:
            print(f"JWT Error: {e}")
        raise credentials_exception
    
    # Fetch user from database (ASYNC)
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    # Auto-refresh if needed - FIX: Use remaining duration from original token
    if should_refresh_token(token):
        # Get the remaining duration from the original token
        remaining_duration = get_token_remaining_duration(token)
        # Create new token with the SAME remaining duration
        new_access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=remaining_duration
        )
        response.headers["X-New-Token"] = new_access_token
        logger.info(
            "auth.token.refreshed",
            language=LANG,
            username=user.username
        )

    logger.debug(
        "security.token.time",
        language=LANG,
        username= user.username,
        time= round(get_token_remaining_minutes(payload), 2)
    )
    
    return user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Verify current user is an admin (ASYNC VERSION).
    
    Use this dependency when an endpoint requires admin privileges:
    
    @router.delete("/users/{user_id}")
    async def delete_user(
        user_id: int,
        admin: User = Depends(get_current_admin_user)
    ):
        # Only admins can reach here
        ...
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        User model (same as input, but verified as admin)
        
    Raises:
        HTTPException 403: If user is not an admin
    """

    if current_user.role != UserRole.ADMIN:
        logger.warning(
            "auth.unauthorized.access",
            language=LANG,
            username=current_user.username
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires administrator privileges"
        )
    
    return current_user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get current user and verify they are active (not disabled).
    
    Use this if you add an 'is_active' field to User model in the future.
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        User model
        
    Raises:
        HTTPException 400: If user is inactive
    """
    # If you add an 'is_active' field to User model, uncomment this:
    # if not current_user.is_active:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Inactive user"
    #     )
    
    return current_user


async def get_current_staff_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Verify current user is any type of staff member.
    
    Use when an endpoint should be accessible to any staff
    (admin, kitchen, waiter) but not clients.
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        User model
        
    Raises:
        HTTPException 403: If user is not staff
    """
    if not current_user.is_staff():
        logger.warning(
            "auth.unauthorized.access",
            language=LANG,
            username=current_user.username
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires staff privileges"
        )
    
    return current_user


async def get_current_kitchen_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Verify current user is kitchen staff or admin.
    
    Use for kitchen-specific operations like inventory management.
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        User model
        
    Raises:
        HTTPException 403: If user is not kitchen or admin
    """
    if current_user.role not in (UserRole.KITCHEN, UserRole.ADMIN):
        logger.warning(
            "auth.unauthorized.access",
            language=LANG,
            username=current_user.username
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires kitchen staff privileges"
        )
    
    return current_user


async def get_current_waiter_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Verify current user is waiter or admin.
    
    Use for waiter-specific operations like managing tables.
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        User model
        
    Raises:
        HTTPException 403: If user is not waiter or admin
    """
    if current_user.role not in (UserRole.WAITER, UserRole.ADMIN):
        logger.warning(
            "auth.unauthorized.access",
            language=LANG,
            username=current_user.username
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires waiter privileges"
        )
    
    return current_user


# === Optional: For WebSocket Authentication ===

async def get_user_from_token(token: str, db: AsyncSession) -> User:
    """
    Authenticate user from JWT token without using Depends.
    
    This is specifically for WebSocket connections where you can't use
    FastAPI's dependency injection system in the same way.
    
    Args:
        token: JWT access token (from query parameter)
        db: Async database session
        
    Returns:
        User model from database
        
    Raises:
        Exception: If authentication fails
    """
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        
        if username is None:
            raise Exception("Invalid token: no username in payload")
        
        # Get user from database
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            raise Exception(f"User not found: {username}")
        
        return user
        
    except ExpiredSignatureError:
        raise Exception("Token has expired")
    
    except JWTError as e:
        raise Exception(f"Invalid token: {str(e)}")


# === Helper Functions for Authentication Responses ===

def create_token_response(user: User) -> dict:
    """
    Create a complete token response with user info.
    
    Use this in your login endpoint to return token + user info.
    
    Args:
        user: User model
        
    Returns:
        Dictionary with access_token, token_type, expires_in, and user info
    """
    access_token = create_access_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # In seconds
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "age": user.age,
            "gender": user.gender,
            "table_id": user.table_id
        }
    }
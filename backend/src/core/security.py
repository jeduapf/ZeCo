"""
Security utilities: JWT, password hashing, authentication
"""
from typing import Annotated
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, TOKEN_REFRESH_THRESHOLD_MINUTES, DEBUG
from database.session import get_db
from database.models.user import User, UserRole
from slowapi import Limiter
from slowapi.util import get_remote_address

Limiter = Limiter(key_func=get_remote_address)

if not SECRET_KEY or not ALGORITHM:
    raise RuntimeError("SECRET_KEY and ALGORITHM must be set")

# Initialize password hashing and OAuth2
pwd_context = CryptContext(schemes=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)

def validate_password(password: str) -> str:
    """Validate password meets requirements"""
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
    if not any(char in "!@#$%^&*()-+" for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one special character (!@#$%^&*()-+)"
        )
    return password

def get_password_hash(password: str) -> str:
    """Hash password with validation"""
    return pwd_context.hash(validate_password(password))

def create_access_token(data: dict) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def should_refresh_token(token: str) -> bool:
    """Check if token should be refreshed"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        if exp_timestamp is None:
            return False
        
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        time_remaining = exp_datetime - datetime.now(timezone.utc)
        
        return time_remaining.total_seconds() < (TOKEN_REFRESH_THRESHOLD_MINUTES * 60)
    except (JWTError, ExpiredSignatureError):
        return False

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], 
    db: Annotated[Session, Depends(get_db)],
    response: Response = None
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token has expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        username_str: str = str(username)
    except ExpiredSignatureError:
        raise expired_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username_str).first()
    if user is None:
        raise credentials_exception
    
    # Auto-refresh token if needed
    if response is not None and should_refresh_token(token):
        new_token = create_access_token(data={"sub": user.username})
        response.headers["X-New-Token"] = new_token
        if DEBUG:
            print(f"Token refreshed for user: {user.username}")
    
    return user

async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Verify current user is an admin"""
    if DEBUG:
        print(f"Admin check - User: {current_user.username}, Role: {current_user.role.value}")
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
    return current_user
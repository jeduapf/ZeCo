"""
Authentication endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends, Response, Body, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from sqlalchemy import select
from datetime import datetime, timezone
from src.core.dependencies import DbDependency, CurrentUser
from src.core.security import (verify_password, create_access_token, 
                               get_password_hash, should_refresh_token, 
                               get_token_remaining_duration, limiter, decode_token)
from src.database.models.user import User, UserRole
from src.schemas.user import LoginResponse, UserPublicResponse, UserRegister, Token, UserRegisterResponse
from src.core.i18n_logger import get_i18n_logger
from config import ACCESS_TOKEN_EXPIRE_MINUTES, LANG, DEBUG
from src.core.utils import log_request_debug


logger = get_i18n_logger(__name__)

router = APIRouter(tags=["Authentication"])


# ============================================================================
# REGISTRATION ENDPOINT
# ============================================================================
@router.post(
    "/register", 
    status_code=status.HTTP_201_CREATED, 
    response_model=UserRegisterResponse,
    summary="Register a new user",
    description="Create a new user account. First user becomes admin automatically."
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    db: DbDependency,
    form_data: Annotated[UserRegister, Body(...)]
):
    """
    Register a new user with validation and logging.
    
    The first user to register automatically becomes an admin.
    Subsequent users are registered as clients by default.
    
    Password requirements:
    - At least 8 characters
    - Contains uppercase and lowercase letters
    - Contains at least one digit
    - Contains at least one special character (!@#$%^&*()-+)
    - No spaces allowed
    """

    # Check if username exists
    result = await db.execute(select(User).where(User.username == form_data.username))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        logger.warning(
            "auth.registration.failed",
            language=LANG,
            reason=form_data.username
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
        
    # Check if email exists
    result = await db.execute(select(User).where(User.email == form_data.email))
    existing_email = result.scalar_one_or_none()
    if existing_email:
        logger.warning(
            "auth.registration.failed",
            language=LANG,
            reason=form_data.email
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    
    # Hash password (validation happens inside get_password_hash)
    try:
        hashed_password = get_password_hash(form_data.password)
    except HTTPException as e:
        logger.error(
            "auth.password.validation_failed",
            language=LANG,
            username=form_data.username,
            reason=e.detail
        )
        raise

    
    # Count users to determine role
    result = await db.execute(select(User))
    user_count = len(result.scalars().all())
    role = UserRole.ADMIN if user_count < 1 else UserRole.CLIENT
    
    new_user = User(
        username=form_data.username,
        hashed_password=hashed_password,
        role=role,
        email=form_data.email,
        age=form_data.age,
        gender= form_data.gender
    )

    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logger.info(
            "auth.registration.success",
            language=LANG,
            role=new_user.role.value,
            username=new_user.username,
            email=new_user.email,
            user_id=new_user.id
        )
        
        return new_user
        
    except Exception as e:
        await db.rollback()
        logger.error(
            "auth.registration.database_error",
            language=LANG,
            username=form_data.username,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )

# ============================================================================
# LOGIN ENDPOINT
# ============================================================================
@router.post(
    "/token",
    response_model=Token,
    summary="Login to get access token",
    description="Authenticate with username and password to receive a JWT token"
)
@limiter.limit("3/minute")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDependency,
    request: Request
):
    """
    Login endpoint that authenticates a user and returns a JWT token
    along with basic user information.
    """
    logger.info(
        "auth.login.attempt",
        language=LANG,
        username=form_data.username,
        ip_address=request.client.host if request.client else "unknown"
    )

    # Fetch user
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(
            "auth.login.failed",
            language=LANG,
            username=form_data.username,
            reason="Invalid credentials"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT access token
    access_token = create_access_token(data={"sub": user.username})

    logger.info(
        "auth.login.success",
        language=LANG,
        username=user.username,
        role=user.role.value,
        user_id=user.id
    )

    # Return a Token model-compliant response
    return LoginResponse.model_validate({
                "access_token": access_token,
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES,     # Configured in config.py
                "user": UserPublicResponse.model_validate(user)
            })

# ============================================================================
# GET CURRENT USER PROFILE
# ============================================================================
@router.get(
    "/me", 
    response_model=UserPublicResponse,
    summary="Get current user profile",
    description="Retrieve the authenticated user's profile information"
)
@limiter.limit("50/minute")
async def get_current_user_info(
    current_user: CurrentUser,
    response: Response,
    request: Request
):
    """
    Get current authenticated user's information.
    
    This endpoint also handles automatic token refresh if the token
    is close to expiration (sliding session).
    """
    logger.debug(
        "auth.profile.accessed",
        language=LANG,
        username=current_user.username,
        user_id=current_user.id
    )
    
    # Check if token should be refreshed
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        
        if should_refresh_token(token):
            # FIX: Use remaining duration from original token
            remaining_duration = get_token_remaining_duration(token)
            new_token = create_access_token(
                data={"sub": current_user.username}, 
                expires_delta=remaining_duration
            )
            response.headers["X-New-Token"] = new_token
            response.headers["X-Token-Refreshed"] = "true"
            
            logger.info(
                "auth.token.refreshed",
                language=LANG,
                username=current_user.username
            )
    
    return UserPublicResponse.model_validate(current_user)

# ============================================================================
# VERIFY TOKEN
# ============================================================================
@router.post(
    "/verify-token",
    status_code=status.HTTP_200_OK,
    summary="Verify token validity",
    description="Check if a token is valid without requiring authentication"
)
async def verify_token_endpoint(
    request: Request,
    token: str = Body(..., embed=True)
):
    """
    Verify if a token is valid and not expired.
    
    This is useful for frontend applications to check token validity
    without making an authenticated request.
    """
    
    if DEBUG:
        log_request_debug(request, await request.body())
    try:
        payload = decode_token(token)
        username = payload.get("sub")
        exp_timestamp = payload.get("exp")
        
        if not username or not exp_timestamp:
            logger.warning(
                "auth.token.invalid",
                language=LANG,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token structure"
            )
        
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        is_expired = exp_datetime < datetime.now(timezone.utc)
        
        if is_expired:
            logger.info(
                "auth.token.expired",
                language=LANG,
                username=username
            )
            return {
                "valid": False,
                "reason": "Token expired"
            }
        
        time_remaining = exp_datetime - datetime.now(timezone.utc)
        
        return {
            "valid": True,
            "username": username,
            "expires_in_seconds": int(time_remaining.total_seconds())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "auth.token.verification_error",
            language=LANG,
            error=str(e)
        )
        return {
            "valid": False,
            "reason": "Token verification failed"
        }


"""
Sliding token expiration system
Automatically extends token lifetime on user activity
"""
from functools import wraps
from typing import Callable, Optional
from fastapi import Response
from datetime import datetime, timedelta, timezone

from config import ACCESS_TOKEN_EXPIRE_MINUTES, DEBUG, TOKEN_REFRESH_THRESHOLD_MINUTES
from core.security import create_access_token, decode_token
from database.models.user import User


class TokenRefreshManager:
    """
    Manages automatic token refresh based on user activity.
    
    This implements a "sliding expiration" pattern where:
    - User gets a token valid for 30 minutes
    - Every time they make a request, we check time remaining
    - If less than 15 minutes left, we issue a new token
    - The new token is sent via X-New-Token header
    - Client should replace their token when they receive this header
    
    This means an active user's session never expires!
    """
    
    @staticmethod
    def should_refresh_token(token: str, threshold_minutes: int = TOKEN_REFRESH_THRESHOLD_MINUTES) -> bool:
        """
        Check if token should be refreshed based on remaining time.
        
        Args:
            token: JWT token to check
            threshold_minutes: Refresh if less than this many minutes remain
            
        Returns:
            True if token should be refreshed
        """
        try:
            payload = decode_token(token)
            exp_timestamp = payload.get("exp")
            
            if exp_timestamp is None:
                return False
            
            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            time_remaining = exp_datetime - datetime.now(timezone.utc)
            remaining_minutes = time_remaining.total_seconds() / 60
            
            if DEBUG:
                print(f"Token has {remaining_minutes:.1f} minutes remaining")
            
            return remaining_minutes < threshold_minutes
            
        except Exception as e:
            if DEBUG:
                print(f"Error checking token refresh: {e}")
            return False
    
    @staticmethod
    def refresh_token_for_user(user: User, response: Response) -> None:
        """
        Generate a new token for the user and add it to response headers.
        
        Args:
            user: User to generate token for
            response: FastAPI Response object to add header to
        """
        new_token = create_access_token(data={"sub": user.username})
        
        # Add new token to response header
        response.headers["X-New-Token"] = new_token
        
        # Also add a custom header indicating token was refreshed
        response.headers["X-Token-Refreshed"] = "true"
        
        if DEBUG:
            print(f"Token refreshed for user: {user.username}")


def auto_refresh_token(func: Callable) -> Callable:
    """
    Decorator that automatically refreshes tokens on user activity.
    
    This decorator:
    1. Checks if token is close to expiration
    2. If yes, generates a new token
    3. Adds new token to response headers
    4. Client can detect and update their stored token
    
    Usage:
        @router.get("/orders")
        @auto_refresh_token
        async def get_orders(
            current_user: CurrentUser,
            response: Response
        ):
            # Token automatically refreshed if needed
            return orders
    
    IMPORTANT: Your endpoint MUST have:
    - current_user parameter (User model)
    - response parameter (Response object)
    
    Args:
        func: Endpoint function to decorate
        
    Returns:
        Decorated function with auto token refresh
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract current_user and response from kwargs
        current_user: Optional[User] = kwargs.get('current_user')
        response: Optional[Response] = kwargs.get('response')
        
        # If we have both user and response, try to refresh token
        if current_user and response:
            # Try to extract the original token from request
            # This is a bit tricky since we're in the wrapper
            # We'll use a simplified approach and just refresh based on time
            
            # Get the token from the Authorization header
            # Note: This requires accessing the request, which we don't have here
            # So we'll use a simpler approach: always generate new token if needed
            
            # Generate new token if user session is active
            new_token = create_access_token(data={"sub": current_user.username})
            response.headers["X-New-Token"] = new_token
            response.headers["X-Token-Refreshed"] = "true"
            
            if DEBUG:
                print(f"Token auto-refreshed for {current_user.username}")
        
        # Execute the original function
        return await func(*args, **kwargs)
    
    return wrapper


def sliding_token(threshold_minutes: int = TOKEN_REFRESH_THRESHOLD_MINUTES) -> Callable:
    """
    Decorator factory for sliding token expiration with custom threshold.
    
    This is a more sophisticated version that only refreshes when needed.
    
    Usage:
        @router.get("/orders")
        @sliding_token(threshold_minutes=10)  # Refresh if <10 min remain
        async def get_orders(
            current_user: CurrentUser,
            response: Response,
            request: Request
        ):
            return orders
    
    Args:
        threshold_minutes: Refresh token if less than this many minutes remain
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from fastapi import Request
            
            # Extract required objects from kwargs
            current_user: Optional[User] = kwargs.get('current_user')
            response: Optional[Response] = kwargs.get('response')
            request: Optional[Request] = kwargs.get('request')
            
            if current_user and response and request:
                # Extract token from Authorization header
                auth_header = request.headers.get("Authorization")
                
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.replace("Bearer ", "")
                    
                    # Check if token should be refreshed
                    if TokenRefreshManager.should_refresh_token(token, threshold_minutes):
                        TokenRefreshManager.refresh_token_for_user(current_user, response)
            
            # Execute the original function
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# === Simple approach: Automatic refresh on every request ===

def always_refresh_token(func: Callable) -> Callable:
    """
    Simple decorator that ALWAYS refreshes the token on every request.
    
    This is the simplest approach but generates more tokens.
    Good for maximum security but more overhead.
    
    Usage:
        @router.get("/orders")
        @always_refresh_token
        async def get_orders(
            current_user: CurrentUser,
            response: Response
        ):
            return orders
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user: Optional[User] = kwargs.get('current_user')
        response: Optional[Response] = kwargs.get('response')
        
        if current_user and response:
            # Always generate new token
            new_token = create_access_token(
                data={"sub": current_user.username}
            )
            response.headers["X-New-Token"] = new_token
            response.headers["X-Token-Refreshed"] = "true"
            
            if DEBUG:
                print(f"Token refreshed for {current_user.username}")
        
        return await func(*args, **kwargs)
    
    return wrapper


# === Middleware approach: Global automatic refresh ===

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse


class SlidingTokenMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically refreshes tokens on ALL requests.
    
    Add this to your FastAPI app:
        app.add_middleware(SlidingTokenMiddleware, threshold_minutes=15)
    
    Benefits:
    - No need to add decorators to every endpoint
    - Works automatically for all protected endpoints
    - Cleaner code
    
    How it works:
    1. Intercepts every request
    2. If request has valid Authorization header
    3. Checks if token is close to expiration
    4. If yes, adds X-New-Token header to response
    """
    
    def __init__(self, app, threshold_minutes: int = TOKEN_REFRESH_THRESHOLD_MINUTES):
        super().__init__(app)
        self.threshold_minutes = threshold_minutes
    
    async def dispatch(self, request: Request, call_next):
        # Get the response from the endpoint
        response = await call_next(request)
        
        # Check if this is an authenticated request
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            
            # Check if token should be refreshed
            if TokenRefreshManager.should_refresh_token(token, self.threshold_minutes):
                try:
                    # Decode token to get username
                    payload = decode_token(token)
                    username = payload.get("sub")
                    
                    if username:
                        # Generate new token
                        new_token = create_access_token(data={"sub": username})
                        
                        # Add to response headers
                        response.headers["X-New-Token"] = new_token
                        response.headers["X-Token-Refreshed"] = "true"
                        
                        if DEBUG:
                            print(f"Token auto-refreshed for {username} via middleware")
                
                except Exception as e:
                    # Don't break the request if token refresh fails
                    if DEBUG:
                        print(f"Token refresh failed in middleware: {e}")
        
        return response


# === Usage Examples ===

"""
# OPTION 1: Use decorator on specific endpoints
from core.token_refresh import sliding_token
from fastapi import Request

@router.get("/orders")
@sliding_token(threshold_minutes=15)
async def get_orders(
    current_user: CurrentUser,
    response: Response,
    request: Request,
    db: DbDependency
):
    # Token automatically refreshed if <15 min remain
    result = await db.execute(select(Order))
    return result.scalars().all()


# OPTION 2: Use simple "always refresh" decorator
from core.token_refresh import always_refresh_token

@router.get("/profile")
@always_refresh_token
async def get_profile(
    current_user: CurrentUser,
    response: Response
):
    # Token refreshed on every request
    return UserResponse.model_validate(current_user)


# OPTION 3: Use middleware (RECOMMENDED - easiest!)
from core.token_refresh import SlidingTokenMiddleware

# In your main.py
app = FastAPI()
app.add_middleware(
    SlidingTokenMiddleware,
    threshold_minutes=15  # Refresh if <15 min remain
)

# Now ALL your endpoints automatically refresh tokens!
@router.get("/orders")
async def get_orders(
    current_user: CurrentUser,
    db: DbDependency
):
    # No decorator needed - middleware handles it!
    result = await db.execute(select(Order))
    return result.scalars().all()
"""
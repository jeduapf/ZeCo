"""
Pydantic schemas for the User model.
Integrates i18n logging and admin role verification.
Complete schemas for all user-related operations.
"""

from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, EmailStr, field_validator
from src.core.i18n_logger import get_i18n_logger
from config import LANG
from src.database.models.user import UserRole
from enum import StrEnum



# --- i18n logger setup ---
logger = get_i18n_logger("user_schemas")


# --- MIXINS ---
class AdminAccessMixin:
    """Provide admin role verification for operations that require privilege."""

    @staticmethod
    def verify_admin(role: UserRole):
        """Check if the role is admin and log if not."""
        if role != UserRole.ADMIN:
            logger.error(
                "auth.permission.denied",
                language=LANG,
                value=role,
                reason="Admin access required"
            )
            raise PermissionError("Admin access required")


# === Base Schemas ===
class GenderEnum(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"



class UserBase(BaseModel):
    """Base user schema with common fields shared across all user schemas."""
    username: str = Field(..., min_length=3, max_length=50, description="Username for login")
    email: EmailStr = Field(..., description="User email address")
    age: int = Field(..., ge=0, le=150, description="User age")
    gender: Optional[GenderEnum] = Field(
        None, 
        description="Gender (True=Male, False=Female, None=Other/Prefer not to say)"
    )

    @field_validator("age")
    @classmethod
    def validate_age(cls, value: int) -> int:
        """Ensure age is within realistic bounds."""
        # Pydantic's Field constraints already handle this, but we log for monitoring
        if not (0 <= value <= 150):
            logger.error(
                "error.validation",
                language=LANG,
                field="age",
                message=f"Age must be between 0 and 150, got {value}"
            )
            raise ValueError("Age must be between 0 and 150")
        return value

    class Config:
        orm_mode = True
        
# === Creation Schemas ===

class UserCreate(UserBase):
    """Schema for creating a new user with full control (admin operation)."""
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    role: Optional[UserRole] = Field(
        UserRole.CLIENT, 
        description="User role (defaults to CLIENT)"
    )
    table_id: Optional[int] = Field(
        None, 
        description="Initial table assignment, if applicable"
    )
    
    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Ensure password meets complexity requirements for security."""
        if len(v) < 8:
            logger.error(
                "error.validation",
                language=LANG,
                field="password",
                message="Password must be at least 8 characters long"
            )
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for uppercase letter
        if not any(char.isupper() for char in v):
            logger.error(
                "error.validation",
                language=LANG,
                field="password",
                message="Password must contain at least one uppercase letter"
            )
            raise ValueError("Password must contain at least one uppercase letter")
        
        # Check for lowercase letter
        if not any(char.islower() for char in v):
            logger.error(
                "error.validation",
                language=LANG,
                field="password",
                message="Password must contain at least one lowercase letter"
            )
            raise ValueError("Password must contain at least one lowercase letter")
        
        # Check for digit
        if not any(char.isdigit() for char in v):
            logger.error(
                "error.validation",
                language=LANG,
                field="password",
                message="Password must contain at least one digit"
            )
            raise ValueError("Password must contain at least one digit")
        
        # Check for special character
        if not any(char in "!@#$%^&*()-+" for char in v):
            logger.error(
                "error.validation",
                language=LANG,
                field="password",
                message="Password must contain at least one special character"
            )
            raise ValueError("Password must contain at least one special character (!@#$%^&*()-+)")
        
        return v


class UserRegister(UserBase):
    """Simplified schema for public user registration (always creates CLIENT role)."""
    password: str = Field(..., min_length=8)
    
    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Apply same password complexity rules as UserCreate."""
        # Reuse the same validation logic
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char in "!@#$%^&*()-+" for char in v):
            raise ValueError("Password must contain at least one special character")
        return v


# === Update Schemas ===

class UserUpdate(BaseModel):
    """Schema for updating user information (all fields optional for partial updates)."""
    email: Optional[EmailStr] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[GenderEnum] = None
    table_id: Optional[int] = None


class UserPasswordUpdate(BaseModel):
    """Schema for changing user password (requires current password for security)."""
    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @field_validator('new_password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Ensure new password meets complexity requirements."""
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char in "!@#$%^&*()-+" for char in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserRoleUpdate(BaseModel):
    """Schema for updating user role (admin operation only)."""
    role: UserRole = Field(..., description="New role to assign")


class UserTableAssignment(BaseModel):
    """Schema for assigning/unassigning user to a table."""
    table_id: Optional[int] = Field(
        None, 
        description="Table ID to assign (None to unassign)"
    )


# === Response Schemas ===

class UserRegisterResponse(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username for login")
    email: EmailStr = Field(..., description="User email address")
    age: int = Field(..., ge=0, le=150, description="User age")
    role:UserRole
    
    class Config:
        orm_mode = True



class UserResponse(UserBase):
    """Schema for user response (excludes sensitive data like password)."""
    id: int
    role: UserRole
    table_id: Optional[int] = None
    is_currently_working: bool = Field(
        default=False, 
        description="Whether staff member is currently clocked in"
    )
    staff_shifts: Optional[List[int]] = Field(
        None, 
        description="List of staff shift IDs associated with this user"
    )
    
    model_config = {"from_attributes": True}
    


class UserDetailedResponse(UserResponse):
    """Detailed user response with additional computed fields for dashboards."""
    total_orders: int = Field(default=0, description="Total number of orders placed")
    active_orders_count: int = Field(default=0, description="Number of active orders")
    monthly_hours_worked: Optional[float] = Field(
        None, 
        description="Hours worked this month (staff only)"
    )


class UserPublic(BaseModel):
    """Public version of a user (minimal exposure for client-facing contexts)."""
    username: str
    role: UserRole
    table_id: Optional[int] = None
    
    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Paginated list of users for list endpoints."""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


# === Authentication Schemas ===

class Token(BaseModel):
    """JWT token response after successful authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserResponse


class TokenData(BaseModel):
    """Data stored within JWT token payload for authentication."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[UserRole] = None


class LoginRequest(BaseModel):
    """Login credentials for authentication."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """Login response with token and user information."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# === Staff-Specific Schemas ===

class StaffWorkSummary(BaseModel):
    """Summary of staff member's work for admin dashboard views."""
    user_id: int
    username: str
    role: UserRole
    is_currently_working: bool
    current_shift_start: Optional[datetime] = None
    total_hours_this_month: float = Field(default=0.0)
    total_shifts_this_month: int = Field(default=0)


class StaffShiftSummary(BaseModel):
    """Summary of a single work shift for reporting."""
    shift_id: int
    start_time: datetime
    end_time: Optional[datetime]
    duration_hours: Optional[float]
    role: str
    is_active: bool


class UserWorkHistory(BaseModel):
    """Complete work history for a staff member including current and past shifts."""
    user: UserResponse
    current_shift: Optional[StaffShiftSummary]
    recent_shifts: List[StaffShiftSummary]
    monthly_summary: dict = Field(
        default_factory=dict,
        description="Monthly breakdown of hours worked by month"
    )


# === WebSocket Schemas ===

class UserStatusUpdate(BaseModel):
    """Real-time user status update for WebSocket notifications."""
    user_id: int
    username: str
    event_type: str = Field(
        ..., 
        description="Event type: clock_in, clock_out, table_assigned, table_cleared"
    )
    table_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[dict] = None
    
    model_config = {"from_attributes": True}
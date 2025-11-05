"""
User Pydantic schemas for API requests/responses
"""
from pydantic import BaseModel, Field
from database.models.user import UserRole

class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    """Schema for creating a user"""
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    role: UserRole
    
    class Config:
        from_attributes = True

class UserRoleUpdate(BaseModel):
    """Schema for updating user role"""
    role: UserRole

class Token(BaseModel):
    """Schema for token response"""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Schema for token data"""
    username: str | None = None
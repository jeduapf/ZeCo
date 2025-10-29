"""
User database model
"""
from database.base import Base
from sqlalchemy import Column, Integer, String, Enum as SQLAlchemyEnum
from enum import Enum
from pydantic import BaseModel

class UserRole(str, Enum):
    ADMIN = "admin"
    KITCHEN = "kitchen"
    CLIENT = "client"
    WAITER = "waiter"

class UserRoleUpdate(BaseModel):
    role: UserRole

# Database configuration
class User(Base):
    """
    User Model for storing user related details in database
    Attributes:
        id: Unique identifier for the user
        username: Unique username for authentication
        hashed_password: Securely hashed password using bcrypt
        role: User role defining access level
    """
    __tablename__ = "users" # Table name in the database 

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    role = Column(SQLAlchemyEnum(UserRole), nullable=False, default=UserRole.CLIENT)
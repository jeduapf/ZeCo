"""
User database model with i18n logging integration
"""
from database.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLAlchemyEnum, Boolean
from sqlalchemy.orm import relationship, validates
from enum import StrEnum
from pydantic import BaseModel
from typing import Optional, List
from core.i18n_logger import get_i18n_logger
from config import LANG

# Initialize logger for this module
logger = get_i18n_logger("user_model")


class UserRole(StrEnum):
    """User roles in the restaurant system"""
    ADMIN = "admin"
    KITCHEN = "kitchen"
    CLIENT = "client"
    WAITER = "waiter"


class UserRoleUpdate(BaseModel):
    """Pydantic schema for updating user roles"""
    role: UserRole


class User(Base):
    """
    User Model representing all types of users in the system.
    
    This includes:
    - Clients who sit at tables and place orders
    - Staff (waiters, kitchen staff, admins) who manage operations
    - The role field determines what permissions the user has
    
    Relationships explained:
    - table: The physical table where a client is currently seated (nullable for staff)
    - orders: All orders this user has created or is responsible for
    - basic_items_updated: Items this user has modified (for audit trail)
    - inventory_logs: Stock changes this user has made
    """
    __tablename__ = "users"
    
    # === Core Identity ===
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(100), nullable=False)
    
    # === Role and Permissions ===
    role = Column(
        SQLAlchemyEnum(UserRole), 
        nullable=False, 
        default=UserRole.CLIENT,
        index=True
    )
    
    # === Personal Information ===
    email = Column(String(255), unique=True, nullable=False, index=True)
    age = Column(Integer, nullable=False)
    gender = Column(Boolean, nullable=True)
    
    # === Table Assignment ===
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    
    # === Relationships ===
    table = relationship("Table", back_populates="users")
    orders = relationship("Order", back_populates="user")
    basic_items_updated = relationship("BasicItem", back_populates="updater")
    inventory_logs = relationship("InventoryLog", back_populates="user")
    
    # === Helper Methods ===
    
    def is_staff(self) -> bool:
        """Check if user is any type of staff member"""
        return self.role in (UserRole.ADMIN, UserRole.KITCHEN, UserRole.WAITER)
    
    def is_admin(self) -> bool:
        """Check if user has admin privileges"""
        return self.role == UserRole.ADMIN
    
    def can_modify_inventory(self) -> bool:
        """Check if user can modify basic item inventory"""
        return self.role in (UserRole.ADMIN, UserRole.KITCHEN)
    
    def can_manage_orders(self) -> bool:
        """Check if user can view and manage all orders"""
        return self.role in (UserRole.ADMIN, UserRole.WAITER, UserRole.KITCHEN)
    
    def get_active_orders(self, db_session) -> List['Order']:
        """
        Get all active (non-completed) orders for this user.
        Useful for client's current order tracking.
        """
        from database.models.order import OrderStatus
        return [
            order for order in self.orders 
            if order.status not in (OrderStatus.COMPLETED, OrderStatus.CANCELLED)
        ]
    
    def has_table_assigned(self) -> bool:
        """Check if user is currently seated at a table"""
        return self.table_id is not None
    
    @validates('age')
    def validate_age(self, key, value):
        """Ensure age is reasonable"""
        if value < 0 or value > 150:
            logger.error(
                "error.validation",
                language=LANG,
                field="age",
                message=f"Age must be between 0 and 150, got {value}"
            )
            raise ValueError("Age must be between 0 and 150")
        return value
    
    @validates('email')
    def validate_email(self, key, value):
        """Basic email validation"""
        if '@' not in value or '.' not in value:
            logger.error(
                "error.validation",
                language=LANG,
                field="email",
                message=f"Invalid email format: {value}"
            )
            raise ValueError("Invalid email format")
        return value.lower()
    
    def __repr__(self):
        table_info = f" at Table {self.table_id}" if self.table_id else ""
        return f"<User {self.username} ({self.role.value}){table_info}>"
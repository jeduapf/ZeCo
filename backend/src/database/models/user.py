"""
User database model with i18n logging integration (UPDATED with staff_shifts relationship)
"""
from src.database.base import Base
from src.database.models.order import Order, OrderStatus
from src.database.models.staff_shift import StaffShift
from datetime import date
from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLAlchemyEnum, Boolean
from sqlalchemy.orm import relationship, validates
from enum import StrEnum
from typing import List
from src.core.i18n_logger import get_i18n_logger
from config import LANG

# Initialize logger for this module
logger = get_i18n_logger("user_model")


class UserRole(StrEnum):
    """User roles in the restaurant system"""
    ADMIN = "admin"
    KITCHEN = "kitchen"
    CLIENT = "client"
    WAITER = "waiter"

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
    - staff_shifts: Work shifts for this user (for staff members only)
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
    
    # NEW RELATIONSHIP: Track staff work shifts
    staff_shifts = relationship(
        "StaffShift", 
        back_populates="user",
        order_by="StaffShift.shift_start.desc()"  # Most recent first
    )
    
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
        return [
            order for order in self.orders 
            if order.status not in (OrderStatus.COMPLETED, OrderStatus.CANCELLED)
        ]
    
    def has_table_assigned(self) -> bool:
        """Check if user is currently seated at a table"""
        return self.table_id is not None
    
    def get_current_shift(self, db_session):
        """
        Get the user's currently active shift (if they're clocked in).
        
        Returns:
            StaffShift object if user is currently working, None otherwise
        """
        
        active_shifts = [shift for shift in self.staff_shifts if shift.is_active()]
        return active_shifts[0] if active_shifts else None
    
    def is_currently_working(self) -> bool:
        """
        Check if this staff member is currently clocked in.
        
        Returns:
            True if user has an active shift
        """
        return any(shift.is_active() for shift in self.staff_shifts)
    
    def get_monthly_hours(self, db_session, year: int, month: int) -> float:
        """
        Calculate total hours worked by this user in a specific month.
        
        Useful for payroll calculations.
        
        Args:
            db_session: Active database session
            year: Year
            month: Month number (1-12)
            
        Returns:
            Total hours worked
        """
        
        month_start = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        
        shifts = db_session.query(StaffShift).filter(
            StaffShift.user_id == self.id,
            StaffShift.shift_start >= month_start,
            StaffShift.shift_start < next_month
        ).all()
        
        return StaffShift.calculate_total_hours(shifts)
    
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
        work_status = " (WORKING)" if self.is_currently_working() else ""
        return f"<User {self.username} ({self.role.value}){table_info}{work_status}>"
"""
Table database model with i18n logging integration
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone
from database.base import Base
from enum import StrEnum
from typing import List, Optional
from core.i18n_logger import get_i18n_logger
from config import LANG

# Initialize logger for this module
logger = get_i18n_logger("table_model")


class TableStatus(StrEnum):
    """Status of a table in the restaurant"""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    CLEANING = "cleaning"


class LocationZone(StrEnum):
    """Different zones/sections in the restaurant"""
    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    TERRACE = "terrace"
    BAR = "bar"
    VIP = "vip"


class Table(Base):
    """
    Table model representing physical tables in the restaurant.
    Each table has a QR code that encodes its ID for customer ordering.
    """
    __tablename__ = "tables"
    
    # === Core Identity ===
    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False, index=True)
    
    # === Table Characteristics ===
    capacity = Column(Integer, nullable=False)
    location_zone = Column(
        SQLAlchemyEnum(LocationZone), 
        nullable=False, 
        default=LocationZone.INDOOR,
        index=True
    )
    
    # === Current Status ===
    status = Column(
        SQLAlchemyEnum(TableStatus), 
        nullable=False, 
        default=TableStatus.AVAILABLE,
        index=True
    )
    
    # === Reservation Tracking ===
    reservation_start = Column(DateTime(timezone=True), nullable=True)
    
    # === Relationships ===
    users = relationship("User", back_populates="table")
    orders = relationship("Order", back_populates="table", order_by="Order.created_at.desc()")
    
    # === Helper Methods ===
    
    def is_available(self) -> bool:
        """Check if table can accept new customers right now"""
        return self.status == TableStatus.AVAILABLE
    
    def is_occupied(self) -> bool:
        """Check if customers are currently seated"""
        return self.status == TableStatus.OCCUPIED
    
    def get_active_orders(self) -> List['Order']:
        """Get all orders for this table that are not yet completed"""
        from database.models.order import OrderStatus
        
        return [
            order for order in self.orders
            if order.status not in (OrderStatus.COMPLETED, OrderStatus.CANCELLED)
        ]
    
    def get_current_bill_total(self) -> float:
        """Calculate the total bill for all active orders at this table"""
        active_orders = self.get_active_orders()
        total = sum(order.total_amount for order in active_orders)
        
        if total > 0:
            logger.debug(
                "table.bill_calculated",
                language=LANG,
                table_number=self.number,
                total_amount=total,
                order_count=len(active_orders)
            )
        
        return total
    
    def get_seated_customers(self) -> List['User']:
        """Get all users (customers) currently assigned to this table"""
        return self.users
    
    def has_capacity_for(self, party_size: int) -> bool:
        """Check if table can accommodate a group of given size"""
        return self.capacity >= party_size
    
    def assign_customer(self, user: 'User', db_session) -> bool:
        """Assign a customer to this table and update status"""
        if not self.is_available():
            logger.warning(
                "table.assignment_failed",
                language=LANG,
                table_number=self.number,
                current_status=self.status.value,
                username=user.username
            )
            return False
        
        user.table_id = self.id
        self.status = TableStatus.OCCUPIED
        
        logger.info(
            "table.assigned",
            language=LANG,
            table_number=self.number,
            username=user.username
        )
        
        db_session.commit()
        return True
    
    def clear_table(self, db_session):
        """Clear all customers from table and set to cleaning status"""
        customer_count = len(self.users)
        
        for user in self.users:
            user.table_id = None
        
        self.status = TableStatus.CLEANING
        
        logger.info(
            "table.cleared",
            language=LANG,
            table_number=self.number,
            customer_count=customer_count
        )
        
        db_session.commit()
    
    def mark_available(self, db_session):
        """Mark table as available for new customers after cleaning"""
        old_status = self.status
        self.status = TableStatus.AVAILABLE
        self.reservation_start = None
        
        logger.info(
            "table.status.changed",
            language=LANG,
            table_number=self.number,
            status="available"
        )
        
        db_session.commit()
    
    def reserve_table(self, start_time: datetime, db_session) -> bool:
        """Reserve this table for a future time"""
        if self.status != TableStatus.AVAILABLE:
            logger.warning(
                "table.reservation_failed",
                language=LANG,
                table_number=self.number,
                current_status=self.status.value,
                requested_time=start_time.isoformat()
            )
            return False
        
        self.status = TableStatus.RESERVED
        self.reservation_start = start_time
        
        logger.info(
            "table.reserved",
            language=LANG,
            table_number=self.number,
            reservation_time=start_time.isoformat()
        )
        
        db_session.commit()
        return True
    
    def cancel_reservation(self, db_session):
        """Cancel an existing reservation and mark table available"""
        if self.status == TableStatus.RESERVED:
            self.status = TableStatus.AVAILABLE
            self.reservation_start = None
            
            logger.info(
                "table.reservation_cancelled",
                language=LANG,
                table_number=self.number
            )
            
            db_session.commit()
    
    def is_reservation_active(self) -> bool:
        """Check if a reservation time has arrived (customer should be here)"""
        if self.status != TableStatus.RESERVED or not self.reservation_start:
            return False
        
        now = datetime.now(timezone.utc)
        time_diff = abs((now - self.reservation_start).total_seconds() / 60)
        return time_diff <= 15
    
    def get_qr_code_data(self) -> dict:
        """Generate data to be encoded in the QR code for this table"""
        return {
            'table_id': self.id,
            'table_number': self.number,
            'capacity': self.capacity,
            'zone': self.location_zone.value
        }
    
    @validates('capacity')
    def validate_capacity(self, key, value):
        """Ensure capacity is reasonable"""
        if value < 1 or value > 50:
            logger.error(
                "error.validation",
                language=LANG,
                field="capacity",
                message=f"Capacity must be between 1 and 50, got {value}"
            )
            raise ValueError("Capacity must be between 1 and 50")
        return value
    
    @validates('number')
    def validate_number(self, key, value):
        """Ensure table number is positive"""
        if value < 1:
            logger.error(
                "error.validation",
                language=LANG,
                field="table_number",
                message=f"Table number must be positive, got {value}"
            )
            raise ValueError("Table number must be positive")
        return value
    
    def __repr__(self):
        customer_count = len(self.users)
        customer_info = f" ({customer_count} guests)" if customer_count > 0 else ""
        return f"<Table {self.number} ({self.location_zone.value}) - {self.status.value}{customer_info}>"
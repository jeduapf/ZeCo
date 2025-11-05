"""
Order database model
Manages customer orders from creation to completion
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.base import Base
from enum import StrEnum


class OrderStatus(StrEnum):
    """Lifecycle of an order through the restaurant"""
    PENDING = "pending"           # Just created, not yet sent to kitchen
    CONFIRMED = "confirmed"       # Confirmed by waiter/system
    PREPARING = "preparing"       # Kitchen is working on it
    READY = "ready"              # Ready to be served
    SERVED = "served"            # Delivered to customer
    COMPLETED = "completed"      # Finished, payment done
    CANCELLED = "cancelled"      # Order was cancelled


class PaymentMethod(StrEnum):
    """Available payment options"""
    CASH = "cash"
    CARD = "card"
    MOBILE = "mobile"            # Apple Pay, Google Pay, etc.
    VOUCHER = "voucher"
    PENDING = "pending"          # Not yet paid


class Order(Base):
    """
    Order model representing a customer's order.
    This is the central entity connecting users, tables, items, and payments.
    """
    __tablename__ = "orders"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys - who ordered and where
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for guest orders
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)  # Must know which table
    
    # Order lifecycle
    status = Column(
        SQLAlchemyEnum(OrderStatus), 
        nullable=False, 
        default=OrderStatus.PENDING,
        index=True  # Fast queries for "all preparing orders" etc.
    )
    
    # Timestamps - crucial for analytics and kitchen timing
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)  # Set when order completed
    
    # Customer specifications and notes
    specifications = Column(Text, nullable=True)  # "No onions", "Extra spicy", etc.
    
    # Financial tracking
    total_amount = Column(Float, nullable=False, default=0.0)
    discount_applied = Column(Float, nullable=False, default=0.0)  # Amount discounted
    payment_method = Column(
        SQLAlchemyEnum(PaymentMethod), 
        nullable=False, 
        default=PaymentMethod.PENDING
    )
    
    # Promotional tracking
    promo_code = Column(String(50), ForeignKey("promotions.code"), nullable=True)
    
    # Relationships - this is where SQLAlchemy's ORM shines
    user = relationship("User", back_populates="orders")
    table = relationship("Table", back_populates="orders")
    
    # Many-to-many with items through order_items junction table
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    # Link to promotion if used
    promotion = relationship("Promotion", back_populates="orders")
    
    def calculate_total(self):
        """Calculate total from items, then apply discount"""
        subtotal = sum(item.item_price * item.quantity for item in self.order_items)
        self.total_amount = subtotal - self.discount_applied
        return self.total_amount
    
    def __repr__(self):
        return f"<Order {self.id} - Table {self.table_id} - {self.status.value}>"
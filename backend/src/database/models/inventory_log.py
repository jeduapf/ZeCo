"""
Inventory Log model - Complete audit trail for all stock changes
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.base import Base
from enum import StrEnum
from typing import Optional


class StockChangeReason(StrEnum):
    """Why stock changed - crucial for inventory analysis and identifying problems"""
    INITIAL_STOCK = "initial_stock"      # Setting up initial inventory when adding new item
    RESTOCK = "restock"                  # Received new delivery from supplier
    SALE = "sale"                        # Item was sold/used to make a dish (most common)
    WASTE = "waste"                      # Item expired, spoiled, or damaged
    THEFT = "theft"                      # Item was stolen
    CORRECTION = "correction"            # Manual correction/audit adjustment
    RETURN = "return"                    # Customer returned item or supplier credit
    SAMPLE = "sample"                    # Used for tasting, testing, or quality control


class InventoryLog(Base):
    """
    Immutable audit log for all inventory changes.
    
    Why this table is critical:
    - Accountability: Every stock change is tracked with who did it and why
    - Analytics: Understand waste patterns, theft issues, popular items
    - Debugging: If stock numbers look wrong, we can trace every single change
    - Compliance: Some jurisdictions require food inventory tracking for health/tax purposes
    - Financial tracking: Helps calculate actual food costs and loss
    
    Design principle: This table is APPEND-ONLY. We NEVER update or delete logs.
    This ensures complete audit trail integrity - every entry is permanent history.
    
    Example entries:
    - "+50.0 kg flour - RESTOCK - Delivery from Miller's Supply"
    - "-2.5 kg chicken - SALE - Used for 5x Chicken Caesar orders"
    - "-0.8 kg lettuce - WASTE - Expired batch from June 1st"
    """
    __tablename__ = "inventory_logs"
    
    # === Primary Identification ===
    id = Column(Integer, primary_key=True, index=True)
    
    # === Foreign Keys ===
    # Who made the change and what item was affected
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("basic_items.id"), nullable=False)  # FIXED: was items.id
    
    # === When Did This Happen? ===
    timestamp = Column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True  # Indexed for time-range queries like "show all changes this month"
    )
    
    # === The Actual Change ===
    stock_change = Column(
        Float, 
        nullable=False
    )  # Positive for adding stock (restock), negative for removing (sale, waste)
    
    # === Why Did This Happen? ===
    reason = Column(
        SQLAlchemyEnum(StockChangeReason),
        nullable=False,
        index=True  # Indexed for queries like "show all waste this month"
    )
    
    # === Optional Additional Context ===
    notes = Column(
        String(500), 
        nullable=True
    )  # Free-form text like "Delivery from Supplier X" or "Batch #12345 expired"
    
    # === Relationships ===
    user = relationship("User", back_populates="inventory_logs")  # Who made this change
    item = relationship("BasicItem", back_populates="inventory_logs")  # Which item was affected
    
    # === Helper Methods ===
    
    def is_increase(self) -> bool:
        """Check if this log entry represents an increase in stock"""
        return self.stock_change > 0
    
    def is_decrease(self) -> bool:
        """Check if this log entry represents a decrease in stock"""
        return self.stock_change < 0
    
    def get_absolute_amount(self) -> float:
        """Get the absolute value of stock change (without sign)"""
        return abs(self.stock_change)
    
    def is_recent(self, hours: int = 24) -> bool:
        """
        Check if this log entry was created within the last N hours.
        
        Args:
            hours: Time window to check (default 24 hours)
            
        Returns:
            True if log entry is within the time window
        """
        now = datetime.now(timezone.utc)
        time_diff = (now - self.timestamp).total_seconds() / 3600  # Convert to hours
        return time_diff <= hours
    
    def format_change_description(self) -> str:
        """
        Create a human-readable description of this stock change.
        
        Returns:
            Formatted string like "+10.5 kg (RESTOCK)" or "-2.0 liters (SALE)"
        """
        sign = "+" if self.stock_change >= 0 else ""
        return (
            f"{sign}{self.stock_change:.2f} {self.item.unit} "
            f"({self.reason.value.upper()})"
        )
    
    def get_cost_impact(self) -> float:
        """
        Calculate the financial impact of this stock change.
        
        For increases (RESTOCK): positive cost (we spent money)
        For decreases (SALE, WASTE): negative cost (we lost/used inventory)
        
        Returns:
            Cost impact in currency units
        """
        # Cost per unit of the item
        unit_cost = self.item.base_cost
        
        # Total cost impact (positive for restocks, negative for usage/waste)
        return self.stock_change * unit_cost
    
    @classmethod
    def get_logs_for_item(cls, item_id: int, db_session, limit: int = 50):
        """
        Get recent logs for a specific item.
        Useful for auditing a particular ingredient's history.
        
        Args:
            item_id: The BasicItem id to query
            db_session: Active database session
            limit: Maximum number of logs to return
            
        Returns:
            List of InventoryLog entries, most recent first
        """
        return (
            db_session.query(cls)
            .filter(cls.item_id == item_id)
            .order_by(cls.timestamp.desc())
            .limit(limit)
            .all()
        )
    
    @classmethod
    def get_logs_by_reason(cls, reason: StockChangeReason, db_session, days: int = 30):
        """
        Get all logs with a specific reason within the last N days.
        Perfect for analyzing waste, theft, or sales patterns.
        
        Args:
            reason: The StockChangeReason to filter by
            db_session: Active database session
            days: How many days back to look
            
        Returns:
            List of matching InventoryLog entries
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        return (
            db_session.query(cls)
            .filter(cls.reason == reason)
            .filter(cls.timestamp >= cutoff_date)
            .order_by(cls.timestamp.desc())
            .all()
        )
    
    @classmethod
    def calculate_waste_total(cls, db_session, days: int = 30) -> float:
        """
        Calculate total monetary value of wasted inventory over a period.
        Critical for understanding food cost problems and improving ordering.
        
        Args:
            db_session: Active database session
            days: Period to calculate over
            
        Returns:
            Total cost of wasted items
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        waste_logs = (
            db_session.query(cls)
            .filter(cls.reason == StockChangeReason.WASTE)
            .filter(cls.timestamp >= cutoff_date)
            .all()
        )
        
        return sum(abs(log.get_cost_impact()) for log in waste_logs)
    
    def __repr__(self):
        sign = "+" if self.stock_change >= 0 else ""
        return (
            f"<InventoryLog #{self.id} - "
            f"{self.item.name if self.item else 'Unknown'} "
            f"{sign}{self.stock_change:.2f} - "
            f"{self.reason.value}>"
        )


# Import timedelta for helper methods
from datetime import timedelta
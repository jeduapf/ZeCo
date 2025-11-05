"""
BasicItem database model with i18n logging integration
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone, timedelta
from database.base import Base
from typing import Optional
from core.i18n_logger import get_i18n_logger
from config import LANG

# Initialize logger for this module
logger = get_i18n_logger("basic_item_model")


class BasicItem(Base):
    """
    BasicItem represents raw ingredients and supplies used to make menu items.
    
    Examples: flour, tomatoes, olive oil, chicken breast, milk, etc.
    These are the building blocks that get combined into dishes (MenuItem).
    """
    __tablename__ = "basic_items"
    
    # === Core Identity ===
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    
    # === Stock Management ===
    stock = Column(Float, default=0.0)
    unit = Column(String(50), nullable=False)
    
    # === Cost Tracking ===
    base_cost = Column(Float, nullable=False)
    tax_rate = Column(Float, default=0.0)
    
    # === Expiration and Freshness ===
    expiration_date = Column(DateTime(timezone=True), nullable=False)
    
    # === Audit Trail ===
    last_updated = Column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    last_updated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # === Additional Information ===
    description = Column(Text, nullable=True)
    
    # === Relationships ===
    updater = relationship("User", foreign_keys=[last_updated_by], back_populates="basic_items_updated")
    menu_item_components = relationship("MenuItemComponent", back_populates="basic_item")
    inventory_logs = relationship("InventoryLog", back_populates="item", order_by="InventoryLog.timestamp.desc()")
    
    # === Helper Methods ===
    
    def is_expired(self) -> bool:
        """Check if this item has passed its expiration date"""
        return datetime.now(timezone.utc) >= self.expiration_date
    
    def days_until_expiration(self) -> int:
        """
        Calculate how many days until expiration.
        Returns negative number if already expired.
        """
        delta = self.expiration_date - datetime.now(timezone.utc)
        return delta.days
    
    def is_expiring_soon(self, warning_days: int = 3) -> bool:
        """
        Check if item is expiring within the warning period.
        Default is 3 days, but can be customized per item type.
        """
        days_left = self.days_until_expiration()
        is_expiring = 0 <= days_left <= warning_days
        
        if is_expiring:
            logger.warning(
                "inventory.expiring_soon",
                language=LANG,
                item_name=self.name,
                days_remaining=days_left,
                expiration_date=self.expiration_date.isoformat()
            )
        
        return is_expiring
    
    def is_low_stock(self, threshold: float = 10.0) -> bool:
        """
        Check if stock is below threshold.
        Threshold can be customized based on item type and usage frequency.
        """
        is_low = self.stock < threshold
        
        if is_low:
            logger.warning(
                "inventory.low_stock",
                language=LANG,
                item_name=self.name,
                current_stock=self.stock,
                unit=self.unit,
                threshold=threshold
            )
        
        return is_low
    
    def is_out_of_stock(self) -> bool:
        """Check if completely out of stock"""
        is_out = self.stock <= 0.0
        
        if is_out:
            logger.error(
                "inventory.out_of_stock",
                language=LANG,
                item_name=self.name
            )
        
        return is_out
    
    def adjust_stock(
        self, 
        amount: float, 
        reason: str, 
        user_id: int, 
        db_session, 
        notes: Optional[str] = None
    ):
        """
        Adjust stock and create an inventory log entry.
        
        Args:
            amount: Positive for adding stock, negative for removing
            reason: One of StockChangeReason values
            user_id: Who is making this change
            db_session: Active database session
            notes: Optional additional information
        """
        from database.models.inventory_log import InventoryLog, StockChangeReason
        
        old_stock = self.stock
        self.stock += amount
        
        # Prevent negative stock
        if self.stock < 0:
            logger.warning(
                "inventory.negative_stock_prevented",
                language=LANG,
                item_name=self.name,
                attempted_stock=self.stock,
                old_stock=old_stock
            )
            self.stock = 0
        
        # Create audit log entry
        log_entry = InventoryLog(
            user_id=user_id,
            item_id=self.id,
            stock_change=amount,
            reason=StockChangeReason(reason),
            notes=notes or f"Stock adjusted from {old_stock:.2f} to {self.stock:.2f}"
        )
        db_session.add(log_entry)
        
        # Log the adjustment based on reason
        log_key = f"inventory.{reason}"
        logger.info(
            log_key,
            language=LANG,
            item_name=self.name,
            quantity=abs(amount),
            unit=self.unit,
            old_stock=old_stock,
            new_stock=self.stock,
            username=f"user_{user_id}"  # In service layer, you'd pass actual username
        )
        
        self.last_updated_by = user_id
    
    def get_total_cost(self) -> float:
        """Calculate total cost including tax"""
        return self.base_cost * (1 + self.tax_rate)
    
    def can_make_menu_item(self, menu_item_id: int, quantity: int = 1) -> bool:
        """
        Check if we have enough of this ingredient to make the specified quantity
        of a particular menu item.
        """
        component = next(
            (c for c in self.menu_item_components if c.menu_item_id == menu_item_id),
            None
        )
        
        if not component:
            return True
        
        required_amount = component.quantity_required * quantity
        return self.stock >= required_amount
    
    @validates('stock')
    def validate_stock(self, key, value):
        """Ensure stock is never negative"""
        if value < 0:
            logger.error(
                "error.validation",
                language=LANG,
                field="stock",
                message=f"Stock cannot be negative, got {value}"
            )
            raise ValueError("Stock cannot be negative")
        return value
    
    @validates('base_cost')
    def validate_cost(self, key, value):
        """Ensure cost is positive"""
        if value < 0:
            logger.error(
                "error.validation",
                language=LANG,
                field="base_cost",
                message=f"Cost cannot be negative, got {value}"
            )
            raise ValueError("Cost cannot be negative")
        return value
    
    @validates('tax_rate')
    def validate_tax_rate(self, key, value):
        """Ensure tax rate is between 0 and 1 (0% to 100%)"""
        if not 0 <= value <= 1:
            logger.error(
                "database.value.error",
                language=LANG,
                value=value,
                reason="0 <= tax_rate <= 1"
            )
            raise ValueError("Tax rate must be between 0 and 1")
        return value
    
    @validates('expiration_date')
    def validate_expiration(self, key, value):
        """Warn if expiration date is in the past"""
        if value < datetime.now(timezone.utc):
            logger.warning(
                "inventory.expired_date_set",
                language=LANG,
                item_name=self.name if hasattr(self, 'name') else 'Unknown',
                expiration_date=value.isoformat()
            )
        return value
    
    def __repr__(self):
        status = "EXPIRED" if self.is_expired() else f"{self.stock:.2f} {self.unit}"
        return f"<BasicItem {self.name} - {status}>"
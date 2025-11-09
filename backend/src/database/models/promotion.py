"""
Promotion database model
Manages discount codes and promotional campaigns
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone
from src.database.base import Base
from src.core.i18n_logger import get_i18n_logger
from config import LANG
from src.database.models.menu_item import Category

logger = get_i18n_logger("promotion_logger")

class Promotion(Base):
    """
    Promotion model for managing discount codes and campaigns.
    
    Design decisions:
    - Promotions can target specific categories (e.g., "20% off desserts")
    - They have time windows (valid from X to Y date)
    - The code is the primary identifier customers will use
    - We track which orders used this promotion for analytics
    """
    __tablename__ = "promotions"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    
    # The actual promo code customers will enter
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "SUMMER2024"
    
    # Human-readable description
    description = Column(Text, nullable=False)  # "20% off all beverages during summer"
    
    # Discount mechanics
    discount_percentage = Column(Float, nullable=False)  # Store as 0.20 for 20%
    
    # Target filtering - if None, applies to entire order
    target_category = Column(SQLAlchemyEnum(Category), nullable=True)  # e.g., "dessert", "beverage"
    target_menu_item = Column(Integer, nullable=True)  # Specific menu item ID if applicable
    
    # Time validity window
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    orders = relationship("Order", back_populates="promotion")
    
    @validates('discount_percentage')
    def validate_discount(self, key, value):
        """Ensure discount is between 0 and 1 (0% to 100%)"""
        if not 0 <= value <= 1:
            logger.error(
                "src.database.value.error", 
                language=LANG,  
                value=value, 
                reason="0 <= value <= 1"
            )
            raise ValueError("Discount must be between 0 and 1 (representing 0% to 100%)")
        return value
    
    @validates('end_date')
    def validate_dates(self, key, end_date):
        """Ensure end date is after start date"""
        if hasattr(self, 'start_date') and self.start_date and end_date <= self.start_date:
            logger.error(
                "src.database.enddate.error", 
                language=LANG,  
                value=end_date,
            )
            raise ValueError("End date must be after start date")
        return end_date
    
    def is_active(self):
        """Check if promotion is currently valid"""
        now = datetime.now(timezone.utc)
        return self.start_date <= now <= self.end_date
    
    def applies_to_category(self, category: str) -> bool:
        """Check if promotion applies to given category"""
        if not self.target_category:
            return True  # Applies to all categories
        return self.target_category.lower() == category.lower()
    
    def __repr__(self):
        return f"<Promotion {self.code} - {self.discount_percentage * 100}% off for {self.target_category or self.target_menu_item or 'all items'}>"

"""
MenuItem database model with i18n logging integration
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone
from database.base import Base
from enum import StrEnum
from config import MIN_STOCK, LANG
from typing import Optional, List
from core.i18n_logger import get_i18n_logger

# Initialize logger for this module
logger = get_i18n_logger("menu_item_model")


class Category(StrEnum):
    """Menu categories for organizing dishes"""
    ENTRY = "entry"
    MAIN_COURSE = "main_course"
    DESSERT = "dessert"
    BEVERAGE = "beverage"


class MenuItem(Base):
    """
    MenuItem represents finished dishes that appear on the customer-facing menu.
    
    Examples: "Margherita Pizza", "Caesar Salad", "Tiramisu", "Espresso"
    
    Key differences from BasicItem:
    - MenuItems are what customers order (finished products)
    - BasicItems are ingredients used to make MenuItems
    - MenuItems have prices (customer-facing)
    - BasicItems have costs (internal tracking)
    
    The relationship:
        MenuItem (Caesar Salad) 
        └── composed of multiple BasicItems via MenuItemComponent
            ├── Lettuce (100g)
            ├── Parmesan (50g)
            └── Croutons (20g)
    """
    __tablename__ = "menu_items"
    
    # === Core Identity ===
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True, unique=True)
    
    # === Pricing ===
    price = Column(Float, nullable=False)
    
    # === Stock Management ===
    stock = Column(Integer, default=0)
    
    # === Menu Organization ===
    category = Column(SQLAlchemyEnum(Category), nullable=False, index=True)
    
    # === Availability ===
    available = Column(Boolean, default=True)
    
    # === Metadata ===
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    description = Column(Text, nullable=True)
    
    # === Relationships ===
    components = relationship(
        "MenuItemComponent", 
        back_populates="menu_item",
        cascade="all, delete-orphan"
    )
    order_items = relationship("OrderItem", back_populates="item")
    
    # === Helper Methods ===
    
    def calculate_base_cost(self) -> float:
        """Calculate the total cost to make this dish based on ingredient costs"""
        return sum(component.get_total_cost() for component in self.components)
    
    def calculate_profit_margin(self) -> float:
        """Calculate profit margin as a percentage"""
        cost = self.calculate_base_cost()
        if cost == 0:
            return 1.0
        return (self.price - cost) / self.price
    
    def update_stock_from_ingredients(self) -> int:
        """
        Calculate how many servings we can make based on current ingredient stock.
        """
        if not self.components:
            logger.warning(
                "item.no_ingredients",
                language=LANG,
                item_name=self.name
            )
            return 0
        
        old_stock = self.stock
        max_servings = min(
            component.max_servings_possible() 
            for component in self.components
        )
        
        self.stock = int(max_servings)
        
        if old_stock != self.stock:
            logger.info(
                "item.stock_updated",
                language=LANG,
                item_name=self.name,
                old_stock=old_stock,
                new_stock=self.stock
            )
        
        if self.stock == 0:
            logger.warning(
                "inventory.out_of_stock",
                language=LANG,
                item_name=self.name
            )
            self.available = False
        
        return self.stock
    
    def is_available_for_order(self, quantity: int = 1, min_stock: int = MIN_STOCK) -> bool:
        """Check if this dish can be ordered right now"""
        is_available = (
            self.available and
            self.stock >= (min_stock + quantity)
        )
        
        if not is_available:
            logger.debug(
                "item.not_available",
                language=LANG,
                item_name=self.name,
                current_stock=self.stock,
                requested_quantity=quantity,
                min_stock_threshold=min_stock
            )
        
        return is_available
    
    def can_fulfill_order(self, quantity: int) -> tuple[bool, Optional[str]]:
        """
        Check if we can make the requested quantity and return helpful feedback.
        """
        if not self.available:
            return False, "Dish is temporarily unavailable"
        
        if self.stock < quantity:
            logger.warning(
                "item.insufficient_stock",
                language=LANG,
                item_name=self.name,
                available=self.stock,
                requested=quantity
            )
            return False, f"Only {self.stock} servings available"
        
        for component in self.components:
            if not component.can_make_quantity(quantity):
                ingredient_name = component.basic_item.name
                logger.warning(
                    "item.missing_ingredient",
                    language=LANG,
                    item_name=self.name,
                    ingredient=ingredient_name,
                    quantity=quantity
                )
                return False, f"Not enough {ingredient_name}"
        
        return True, None
    
    def deduct_ingredients_for_order(self, quantity: int, user_id: int, db_session):
        """
        Deduct all required ingredients from stock when an order is placed.
        """
        logger.info(
            "item.deducting_ingredients",
            language=LANG,
            item_name=self.name,
            quantity=quantity,
            username=f"user_{user_id}"
        )
        
        for component in self.components:
            component.deduct_stock_for_servings(
                servings=quantity,
                user_id=user_id,
                db_session=db_session
            )
        
        self.update_stock_from_ingredients()
    
    def adjust_stock(self, amount: int, min_quantity: int = MIN_STOCK) -> None:
        """Manually adjust stock by given amount"""
        old_stock = self.stock
        self.stock += amount
        
        if self.stock < 0:
            self.stock = 0
        
        if self.stock < min_quantity:
            self.available = False
            logger.warning(
                "item.availability.changed",
                language=LANG,
                item_name=self.name,
                available=False,
                current_stock=self.stock
            )
        
        logger.info(
            "item.stock_adjusted",
            language=LANG,
            item_name=self.name,
            old_stock=old_stock,
            new_stock=self.stock,
            change=amount
        )
    
    def get_missing_ingredients(self, quantity: int = 1) -> List[dict]:
        """Get a list of ingredients that are insufficient for making the dish"""
        missing = []
        
        for component in self.components:
            needed = component.quantity_required * quantity
            available = component.basic_item.stock
            
            if available < needed:
                missing.append({
                    'name': component.basic_item.name,
                    'unit': component.basic_item.unit,
                    'needed': needed,
                    'available': available,
                    'shortage': needed - available
                })
        
        if missing:
            logger.warning(
                "item.multiple_missing_ingredients",
                language=LANG,
                item_name=self.name,
                missing_count=len(missing)
            )
        
        return missing
    
    def has_expiring_ingredients(self, warning_days: int = 3) -> List[str]:
        """Check if any ingredients for this dish are expiring soon"""
        expiring = []
        
        for component in self.components:
            if component.basic_item.is_expiring_soon(warning_days):
                days_left = component.basic_item.days_until_expiration()
                expiring.append(
                    f"{component.basic_item.name} (expires in {days_left} days)"
                )
        
        if expiring:
            logger.info(
                "item.has_expiring_ingredients",
                language=LANG,
                item_name=self.name,
                expiring_count=len(expiring)
            )
        
        return expiring
    
    @validates('price')
    def validate_price(self, key, value):
        """Ensure price is positive"""
        if value < 0:
            logger.error(
                "error.validation",
                language=LANG,
                field="price",
                message=f"Price cannot be negative, got {value}"
            )
            raise ValueError("Price cannot be negative")
        return value
    
    @validates('stock')
    def validate_stock(self, key, value):
        """Ensure stock is non-negative"""
        if value < 0:
            logger.error(
                "error.validation",
                language=LANG,
                field="stock",
                message=f"Stock cannot be negative, got {value}"
            )
            raise ValueError("Stock cannot be negative")
        return value
    
    def __repr__(self):
        availability = "Available" if self.available and self.stock > 0 else "Unavailable"
        return f"<MenuItem {self.name} ({self.category.value}) - ${self.price:.2f} - {availability}>"
        availability = "Available" if self.available and self.stock > 0 else "Unavailable"
        return f"<MenuItem {self.name} ({self.category.value}) - ${self.price:.2f} - {availability}>"
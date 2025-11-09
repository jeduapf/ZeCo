"""
MenuItemComponent junction table with i18n logging integration
"""
from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, validates
from src.database.base import Base
from src.core.i18n_logger import get_i18n_logger
from config import LANG

# Initialize logger for this module
logger = get_i18n_logger("menu_item_component_model")

class MenuItemComponent(Base):
    """
    Junction table connecting MenuItem (finished dishes) to BasicItem (ingredients).
    This represents the recipe: "To make 1 Margherita Pizza, you need 200g flour, 50ml tomato sauce, etc."
    
    Why we need this table:
    - A menu item (dish) needs multiple ingredients
    - An ingredient is used in multiple dishes
    - We need to track the exact quantity of each ingredient per dish
    - This enables automatic stock calculation and cost tracking
    
    Example:
        MenuItem: "Caesar Salad" is composed of:
        - 100g Lettuce (BasicItem)
        - 50g Parmesan (BasicItem)  
        - 30ml Caesar Dressing (BasicItem)
        - 20g Croutons (BasicItem)
    """
    __tablename__ = "menu_item_components"
    
    # === Composite Primary Key ===
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), primary_key=True)
    basic_item_id = Column(Integer, ForeignKey("basic_items.id"), primary_key=True)
    
    # === Recipe Specification ===
    quantity_required = Column(Float, nullable=False)
    
    # === Relationships ===
    menu_item = relationship("MenuItem", back_populates="components")
    basic_item = relationship("BasicItem", back_populates="menu_item_components")
    
    # === Constraints ===
    __table_args__ = (
        UniqueConstraint('menu_item_id', 'basic_item_id', name='unique_menu_item_component'),
    )
    
    # === Helper Methods ===
    
    def get_total_cost(self) -> float:
        """Calculate the cost of this ingredient portion for one serving of the dish"""
        return self.basic_item.base_cost * self.quantity_required
    
    def is_available(self) -> bool:
        """Check if we have enough of this ingredient in stock to make the dish"""
        return self.basic_item.stock >= self.quantity_required
    
    def can_make_quantity(self, servings: int) -> bool:
        """Check if we have enough stock to make the specified number of servings"""
        required_amount = self.quantity_required * servings
        can_make = self.basic_item.stock >= required_amount
        
        if not can_make:
            logger.debug(
                "component.insufficient_ingredient",
                language=LANG,
                menu_item=self.menu_item.name if self.menu_item else "Unknown",
                ingredient=self.basic_item.name if self.basic_item else "Unknown",
                required=required_amount,
                available=self.basic_item.stock if self.basic_item else 0,
                unit=self.basic_item.unit if self.basic_item else "units"
            )
        
        return can_make
    
    def max_servings_possible(self) -> int:
        """Calculate the maximum number of servings we can make based on current stock"""
        if self.quantity_required == 0:
            logger.warning(
                "component.zero_quantity",
                language=LANG,
                menu_item=self.menu_item.name if self.menu_item else "Unknown",
                ingredient=self.basic_item.name if self.basic_item else "Unknown"
            )
            return float('inf')
        
        return int(self.basic_item.stock / self.quantity_required)
    
    def deduct_stock_for_servings(self, servings: int, user_id: int, db_session):
        """
        Deduct the required amount of this ingredient from stock when making servings.
        This creates an inventory log entry for audit purposes.
        """
        amount_needed = self.quantity_required * servings
        
        logger.info(
            "component.deducting_ingredient",
            language=LANG,
            menu_item=self.menu_item.name if self.menu_item else "Unknown",
            ingredient=self.basic_item.name if self.basic_item else "Unknown",
            amount=amount_needed,
            unit=self.basic_item.unit if self.basic_item else "units",
            servings=servings
        )
        
        self.basic_item.adjust_stock(
            amount=-amount_needed,
            reason="sale",
            user_id=user_id,
            db_session=db_session,
            notes=f"Used {amount_needed:.2f} {self.basic_item.unit} for {servings}x {self.menu_item.name}"
        )
    
    @validates('quantity_required')
    def validate_quantity(self, key, value):
        """Ensure quantity is positive"""
        if value <= 0:
            logger.error(
                "error.validation",
                language=LANG,
                field="quantity_required",
                message=f"Quantity must be greater than 0, got {value}"
            )
            raise ValueError("Quantity required must be greater than 0")
        return value
    
    def __repr__(self):
        return (
            f"<MenuItemComponent "
            f"{self.menu_item.name if self.menu_item else 'Unknown'} needs "
            f"{self.quantity_required:.2f} {self.basic_item.unit if self.basic_item else 'units'} "
            f"of {self.basic_item.name if self.basic_item else 'Unknown'}>"
        )
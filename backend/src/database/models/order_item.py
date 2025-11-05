"""
OrderItem junction table - Links orders to menu items with quantity and pricing snapshot
"""
from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, validates
from database.base import Base


class OrderItem(Base):
    """
    Junction table linking Orders and MenuItems with quantity and price information.
    
    Why we need this table:
    - Orders contain multiple menu items (one order can include pizza, salad, and drink)
    - Menu items appear in many different orders (pizza is ordered by multiple customers)
    - We need to track quantity per order (someone might order 3 pizzas)
    - We snapshot prices at order time (menu prices change, but past orders stay fixed)
    
    This is a classic many-to-many relationship with additional data.
    
    Important design decision - Price Snapshotting:
    When an order is placed, we capture the current price and cost from MenuItem.
    This means if you change your menu prices tomorrow, yesterday's orders still 
    show what was actually charged. This is crucial for:
    - Accurate financial records
    - Customer dispute resolution  
    - Historical profit analysis
    """
    __tablename__ = "order_items"
    
    # === Composite Primary Key ===
    # The combination of order_id and item_id uniquely identifies each line item
    order_id = Column(Integer, ForeignKey("orders.id"), primary_key=True)
    item_id = Column(Integer, ForeignKey("menu_items.id"), primary_key=True)  # FIXED: was items.id
    
    # === Order-Specific Data ===
    quantity = Column(Integer, nullable=False, default=1)  # How many of this item
    
    # === Price Snapshotting ===
    # CRITICAL: These are copied from MenuItem at order creation time
    # They never change, even if MenuItem.price changes later
    item_price = Column(Float, nullable=False)  # Price per unit when ordered (from MenuItem.price)
    item_cost = Column(Float, nullable=False)   # Cost per unit for profit analysis (from MenuItem.calculate_base_cost())
    
    # === Relationships ===
    order = relationship("Order", back_populates="order_items")
    item = relationship("MenuItem", back_populates="order_items")
    
    # === Constraints ===
    __table_args__ = (
        UniqueConstraint('order_id', 'item_id', name='unique_order_item'),
    )
    
    # === Helper Methods ===
    
    @property
    def subtotal(self) -> float:
        """
        Calculate the line item total (price × quantity).
        This is what the customer pays for this specific item in the order.
        
        Example: 3 pizzas at $15 each = $45 subtotal
        """
        return self.item_price * self.quantity
    
    @property
    def total_cost(self) -> float:
        """
        Calculate the total cost to make this line item (cost × quantity).
        This is what it cost the restaurant to make these items.
        
        Example: 3 pizzas that cost $5 each to make = $15 total cost
        """
        return self.item_cost * self.quantity
    
    @property
    def profit(self) -> float:
        """
        Calculate gross profit for this line item.
        Profit = Revenue - Cost = (item_price - item_cost) × quantity
        
        Example: 3 pizzas sold at $15, cost $5 each = ($15-$5) × 3 = $30 profit
        """
        return (self.item_price - self.item_cost) * self.quantity
    
    @property
    def profit_margin(self) -> float:
        """
        Calculate profit margin as a percentage.
        
        Returns:
            Profit margin as decimal (0.40 = 40% margin)
        """
        if self.subtotal == 0:
            return 0.0
        return self.profit / self.subtotal
    
    def apply_discount(self, discount_amount: float) -> float:
        """
        Apply a discount to this line item and return new subtotal.
        Note: This modifies the item_price, not a separate discount field.
        
        Args:
            discount_amount: Absolute amount to discount (not percentage)
            
        Returns:
            New subtotal after discount
        """
        discount_per_item = discount_amount / self.quantity
        self.item_price = max(0, self.item_price - discount_per_item)
        return self.subtotal
    
    def can_fulfill(self) -> tuple[bool, str]:
        """
        Check if this order item can currently be fulfilled based on menu item availability.
        
        Returns:
            (can_fulfill, message)
        """
        return self.item.can_fulfill_order(self.quantity)
    
    @validates('quantity')
    def validate_quantity(self, key, value):
        """Ensure quantity is positive"""
        if value < 1:
            raise ValueError("Quantity must be at least 1")
        return value
    
    @validates('item_price', 'item_cost')
    def validate_money(self, key, value):
        """Ensure prices and costs are non-negative"""
        if value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value
    
    @classmethod
    def create_from_menu_item(cls, order_id: int, menu_item: 'MenuItem', quantity: int) -> 'OrderItem':
        """
        Factory method to create an OrderItem with current prices from MenuItem.
        This ensures we snapshot the prices correctly at order time.
        
        Args:
            order_id: The order this belongs to
            menu_item: The MenuItem being ordered
            quantity: How many to order
            
        Returns:
            New OrderItem instance (not yet added to database)
        """
        return cls(
            order_id=order_id,
            item_id=menu_item.id,
            quantity=quantity,
            item_price=menu_item.price,  # Snapshot current price
            item_cost=menu_item.calculate_base_cost()  # Snapshot current cost
        )
    
    def __repr__(self):
        item_name = self.item.name if self.item else f"Item#{self.item_id}"
        return (
            f"<OrderItem Order:{self.order_id} - "
            f"{self.quantity}x {item_name} @ ${self.item_price:.2f} = ${self.subtotal:.2f}>"
        )
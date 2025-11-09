"""
MenuItem and BasicItem Pydantic schemas for API requests/responses
"""
from pydantic import BaseModel, Field, field_validator
from database.models.menu_item import Category
from typing import Optional, List
from datetime import datetime


# === BasicItem Schemas ===

class BasicItemBase(BaseModel):
    """Base schema for ingredients"""
    name: str = Field(..., min_length=1, max_length=255)
    unit: str = Field(..., description="Unit of measurement (kg, liters, pieces, etc.)")
    base_cost: float = Field(..., ge=0, description="Cost per unit")
    tax_rate: float = Field(0.0, ge=0, le=1, description="Tax rate as decimal (0.2 = 20%)")
    description: Optional[str] = None


class BasicItemCreate(BasicItemBase):
    """Schema for creating a new ingredient"""
    stock: float = Field(0.0, ge=0, description="Initial stock quantity")
    expiration_date: datetime = Field(..., description="When this batch expires")
    
    @field_validator('expiration_date')
    @classmethod
    def validate_expiration_future(cls, v: datetime) -> datetime:
        """Warn if expiration date is in the past"""
        if v < datetime.utcnow():
            # Allow past dates but could log a warning
            pass
        return v


class BasicItemUpdate(BaseModel):
    """Schema for updating ingredient information"""
    base_cost: Optional[float] = Field(None, ge=0)
    tax_rate: Optional[float] = Field(None, ge=0, le=1)
    description: Optional[str] = None


class BasicItemStockAdjust(BaseModel):
    """Schema for adjusting ingredient stock"""
    amount: float = Field(..., description="Amount to add (positive) or remove (negative)")
    reason: str = Field(
        ..., 
        description="Reason: initial_stock, restock, sale, waste, theft, correction, return, sample"
    )
    notes: Optional[str] = Field(None, description="Additional context about this adjustment")


class BasicItemRestock(BaseModel):
    """Schema for restocking an ingredient"""
    quantity: float = Field(..., gt=0, description="Quantity to add")
    expiration_date: datetime = Field(..., description="Expiration date of new batch")
    supplier: Optional[str] = Field(None, description="Supplier name")
    unit_cost: Optional[float] = Field(None, ge=0, description="Cost for this batch (if different)")


class BasicItemResponse(BasicItemBase):
    """Response schema for ingredient"""
    id: int
    stock: float
    expiration_date: datetime
    last_updated: datetime
    last_updated_by: int
    is_expired: bool = Field(..., description="Whether item has passed expiration date")
    days_until_expiration: int = Field(..., description="Days remaining (negative if expired)")
    is_low_stock: bool = Field(..., description="Whether stock is below threshold")
    
    model_config = {"from_attributes": True}


class BasicItemDetailedResponse(BasicItemResponse):
    """Detailed ingredient response with usage info"""
    total_cost_with_tax: float = Field(..., description="Total cost including tax")
    used_in_menu_items: List[str] = Field(default_factory=list, description="Menu items using this ingredient")
    recent_logs_count: int = Field(default=0, description="Number of recent inventory changes")


# === MenuItemComponent Schemas ===

class MenuItemComponentBase(BaseModel):
    """Recipe component linking menu item to ingredient"""
    basic_item_id: int = Field(..., description="Ingredient ID")
    quantity_required: float = Field(..., gt=0, description="Amount needed per serving")


class MenuItemComponentCreate(MenuItemComponentBase):
    """Schema for adding ingredient to a recipe"""
    pass


class MenuItemComponentResponse(MenuItemComponentBase):
    """Response schema for recipe component"""
    basic_item_name: str
    basic_item_unit: str
    total_cost: float = Field(..., description="Cost of this ingredient per serving")
    is_available: bool = Field(..., description="Whether we have enough stock")
    
    model_config = {"from_attributes": True}


# === MenuItem Schemas ===

class MenuItemBase(BaseModel):
    """Base schema for menu items (dishes)"""
    name: str = Field(..., min_length=1, max_length=255)
    price: float = Field(..., gt=0, description="Customer-facing price")
    category: Category = Field(..., description="Menu category")
    description: Optional[str] = None


class MenuItemCreate(MenuItemBase):
    """Schema for creating a new menu item"""
    components: List[MenuItemComponentCreate] = Field(
        default_factory=list,
        description="Recipe: list of ingredients and quantities"
    )
    
    @field_validator('components')
    @classmethod
    def validate_has_components(cls, v: List[MenuItemComponentCreate]) -> List[MenuItemComponentCreate]:
        """Ensure menu item has at least one ingredient"""
        if not v:
            raise ValueError("Menu item must have at least one ingredient")
        return v


class MenuItemUpdate(BaseModel):
    """Schema for updating menu item information"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[float] = Field(None, gt=0)
    category: Optional[Category] = None
    description: Optional[str] = None
    available: Optional[bool] = Field(None, description="Whether item can be ordered")


class MenuItemRecipeUpdate(BaseModel):
    """Schema for updating a menu item's recipe"""
    components: List[MenuItemComponentCreate] = Field(
        ...,
        description="Complete new recipe (replaces existing)"
    )


class MenuItemResponse(MenuItemBase):
    """Response schema for menu item"""
    id: int
    stock: int = Field(..., description="Estimated servings we can make")
    available: bool = Field(..., description="Whether item can be ordered")
    created_at: datetime
    base_cost: float = Field(..., description="Cost to make one serving")
    profit_margin: float = Field(..., description="Profit margin as percentage (0.3 = 30%)")
    
    model_config = {"from_attributes": True}


class MenuItemDetailedResponse(MenuItemResponse):
    """Detailed menu item response with recipe"""
    components: List[MenuItemComponentResponse] = []
    can_be_made: bool = Field(..., description="Whether we have all ingredients in stock")
    missing_ingredients: List[str] = Field(
        default_factory=list,
        description="List of ingredients we're out of"
    )
    expiring_ingredients: List[str] = Field(
        default_factory=list,
        description="Ingredients expiring soon"
    )


class MenuItemWithAvailability(MenuItemResponse):
    """Menu item with real-time availability info"""
    max_quantity_available: int = Field(..., description="Maximum servings we can make now")
    estimated_prep_time: Optional[int] = Field(None, description="Estimated minutes to prepare")


class MenuItemListResponse(BaseModel):
    """Paginated list of menu items"""
    items: List[MenuItemResponse]
    total: int
    page: int
    page_size: int
    category_filter: Optional[Category] = None


# === Menu Display Schemas (Customer-Facing) ===

class PublicMenuItem(BaseModel):
    """Public menu item (no cost/stock info)"""
    id: int
    name: str
    price: float
    category: Category
    description: Optional[str]
    available: bool
    estimated_prep_time: Optional[int] = None
    allergens: Optional[List[str]] = Field(default_factory=list)
    dietary_info: Optional[List[str]] = Field(
        default_factory=list,
        description="vegetarian, vegan, gluten-free, etc."
    )


class PublicMenuCategory(BaseModel):
    """Menu organized by category (customer-facing)"""
    category: Category
    items: List[PublicMenuItem]


class PublicMenu(BaseModel):
    """Complete customer-facing menu"""
    categories: List[PublicMenuCategory]
    restaurant_name: str = "Restaurant"
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# === Inventory Management Schemas ===

class LowStockAlert(BaseModel):
    """Alert for ingredients running low"""
    basic_item_id: int
    name: str
    current_stock: float
    unit: str
    threshold: float
    affects_menu_items: List[str] = Field(
        default_factory=list,
        description="Menu items that will be unavailable"
    )


class ExpiringItemAlert(BaseModel):
    """Alert for expiring ingredients"""
    basic_item_id: int
    name: str
    stock: float
    unit: str
    expiration_date: datetime
    days_remaining: int
    used_in_menu_items: List[str]


class InventoryDashboard(BaseModel):
    """Dashboard overview of inventory status"""
    low_stock_items: List[LowStockAlert]
    expiring_items: List[ExpiringItemAlert]
    out_of_stock_items: List[str]
    total_inventory_value: float
    total_waste_this_month: float
    unavailable_menu_items: List[str]


# === WebSocket Schemas ===

class MenuItemAvailabilityUpdate(BaseModel):
    """Real-time menu item availability update"""
    menu_item_id: int
    name: str
    event_type: str = Field(..., description="stock_updated, became_available, became_unavailable")
    new_stock: int
    is_available: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class InventoryUpdate(BaseModel):
    """Real-time inventory change notification"""
    basic_item_id: int
    name: str
    event_type: str = Field(..., description="restocked, low_stock, out_of_stock, expiring_soon")
    current_stock: float
    unit: str
    affected_menu_items: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)
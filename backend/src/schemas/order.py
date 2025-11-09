"""
Order Pydantic schemas for API requests/responses
Complete schemas for the order lifecycle from creation to payment
"""
from pydantic import BaseModel, Field, field_validator
from src.database.models.order import OrderStatus, PaymentMethod
from typing import Optional, List
from datetime import datetime, timezone


# === OrderItem Schemas ===

class OrderItemBase(BaseModel):
    """Base schema for items in an order"""
    menu_item_id: int = Field(..., description="Menu item ID", alias="item_id")
    quantity: int = Field(..., ge=1, description="Quantity to order")


class OrderItemCreate(OrderItemBase):
    """Schema for adding item to order"""
    special_instructions: Optional[str] = Field(None, max_length=500, description="Special requests")


class OrderItemUpdate(BaseModel):
    """Schema for updating an order item"""
    quantity: Optional[int] = Field(None, ge=1)
    special_instructions: Optional[str] = Field(None, max_length=500)


class OrderItemResponse(BaseModel):
    """Response schema for order item"""
    menu_item_id: int
    menu_item_name: str
    quantity: int
    item_price: float = Field(..., description="Price per unit when ordered")
    item_cost: float = Field(..., description="Cost per unit (for analytics)")
    subtotal: float = Field(..., description="Total for this line item")
    profit: float = Field(..., description="Profit for this line item")
    special_instructions: Optional[str] = None
    
    model_config = {"from_attributes": True}


# === Order Schemas ===

class OrderBase(BaseModel):
    """Base order schema"""
    table_id: int = Field(..., description="Table number where order is placed")
    specifications: Optional[str] = Field(None, max_length=1000, description="General order notes")
    num_customers: int = Field(1, ge=1, le=50, description="Number of people at the table")


class OrderCreate(OrderBase):
    """Schema for creating a new order"""
    items: List[OrderItemCreate] = Field(..., min_length=1, description="Items to order")
    promo_code: Optional[str] = Field(None, description="Promotional code to apply")
    
    @field_validator('items')
    @classmethod
    def validate_has_items(cls, v: List[OrderItemCreate]) -> List[OrderItemCreate]:
        """Ensure order has at least one item"""
        if not v:
            raise ValueError("Order must contain at least one item")
        return v


class OrderAddItems(BaseModel):
    """Schema for adding more items to existing order"""
    items: List[OrderItemCreate] = Field(..., min_length=1, description="Additional items")


class OrderRemoveItem(BaseModel):
    """Schema for removing an item from order"""
    menu_item_id: int = Field(..., description="Item to remove")


class OrderUpdateStatus(BaseModel):
    """Schema for updating order status (kitchen/waiter)"""
    new_status: OrderStatus = Field(..., description="New order status")
    notes: Optional[str] = Field(None, description="Notes about status change")


class OrderCancel(BaseModel):
    """Schema for cancelling an order"""
    reason: str = Field(..., min_length=1, max_length=500, description="Cancellation reason")


class OrderPayment(BaseModel):
    """Schema for processing payment"""
    payment_method: PaymentMethod = Field(..., description="How customer is paying")
    amount_paid: float = Field(..., gt=0, description="Amount customer is paying")
    tip_amount: Optional[float] = Field(0.0, ge=0, description="Tip amount")


class OrderSplitPayment(BaseModel):
    """Schema for split payment between multiple people"""
    num_splits: int = Field(..., ge=2, le=10, description="Number of ways to split")
    split_type: str = Field("equal", description="equal or custom")
    custom_amounts: Optional[List[float]] = Field(None, description="Custom amounts if not equal")
    
    @field_validator('custom_amounts')
    @classmethod
    def validate_custom_amounts(cls, v: Optional[List[float]], info) -> Optional[List[float]]:
        """Validate custom amounts match num_splits"""
        if v is not None:
            num_splits = info.data.get('num_splits')
            if len(v) != num_splits:
                raise ValueError(f"Must provide exactly {num_splits} amounts")
        return v


# === Order Response Schemas ===

class OrderResponse(BaseModel):
    """Basic order response"""
    id: int
    table_id: int
    user_id: Optional[int]
    status: OrderStatus
    created_at: datetime
    finished_at: Optional[datetime]
    total_amount: float
    discount_applied: float
    payment_method: PaymentMethod
    num_customers: int
    specifications: Optional[str]
    promo_code: Optional[str]
    
    model_config = {"from_attributes": True}


class OrderDetailedResponse(OrderResponse):
    """Detailed order response with items"""
    items: List[OrderItemResponse] = []
    per_person_cost: float = Field(..., description="Average cost per customer")
    subtotal: float = Field(..., description="Total before discounts")
    
    # Kitchen timing info
    estimated_prep_time: Optional[int] = Field(None, description="Estimated minutes to prepare")
    time_since_created: Optional[int] = Field(None, description="Minutes since order was placed")


class OrderWithCustomer(OrderDetailedResponse):
    """Order response including customer information"""
    customer_name: Optional[str] = None
    table_number: int
    table_zone: str


class OrderListResponse(BaseModel):
    """Paginated list of orders"""
    orders: List[OrderResponse]
    total: int
    page: int
    page_size: int
    status_filter: Optional[OrderStatus] = None


# === Kitchen Display Schemas ===

class KitchenOrderItem(BaseModel):
    """Simplified item view for kitchen display"""
    name: str
    quantity: int
    special_instructions: Optional[str]
    category: str


class KitchenOrder(BaseModel):
    """Order formatted for kitchen display"""
    order_id: int
    table_number: int
    items: List[KitchenOrderItem]
    status: OrderStatus
    created_at: datetime
    time_elapsed_minutes: int
    priority: str = Field(..., description="normal, urgent, late")
    specifications: Optional[str]


class KitchenDashboard(BaseModel):
    """Complete kitchen dashboard"""
    pending_orders: List[KitchenOrder]
    preparing_orders: List[KitchenOrder]
    ready_orders: List[KitchenOrder]
    total_pending: int
    total_preparing: int
    average_prep_time: float = Field(..., description="Average minutes to prepare")
    longest_waiting: Optional[KitchenOrder] = None


# === Waiter Dashboard Schemas ===

class WaiterOrderSummary(BaseModel):
    """Simplified order for waiter view"""
    order_id: int
    table_number: int
    status: OrderStatus
    total_amount: float
    num_customers: int
    created_at: datetime
    is_ready_to_serve: bool


class WaiterTable(BaseModel):
    """Table status for waiter"""
    table_id: int
    table_number: int
    status: str
    seated_customers: int
    active_orders: List[WaiterOrderSummary]
    total_bill: float
    needs_attention: bool = Field(..., description="Whether table needs waiter attention")


class WaiterDashboard(BaseModel):
    """Complete waiter dashboard"""
    my_tables: List[WaiterTable]
    orders_ready_to_serve: List[WaiterOrderSummary]
    pending_payments: List[WaiterOrderSummary]
    total_tables_assigned: int
    total_active_orders: int


# === Bill and Payment Schemas ===

class BillItem(BaseModel):
    """Line item on the bill"""
    name: str
    quantity: int
    unit_price: float
    subtotal: float


class Bill(BaseModel):
    """Complete bill for a table"""
    order_ids: List[int]
    items: List[BillItem]
    subtotal: float
    discount: float
    tax: float
    tip: float
    total: float
    num_customers: int
    per_person: float
    payment_method: Optional[PaymentMethod] = None


class PaymentReceipt(BaseModel):
    """Payment confirmation receipt"""
    order_ids: List[int]
    table_number: int
    total_paid: float
    payment_method: PaymentMethod
    tip_amount: float
    timestamp: datetime
    receipt_number: str


# === Analytics Schemas ===

class OrderStatistics(BaseModel):
    """Order statistics for a period"""
    total_orders: int
    total_revenue: float
    average_order_value: float
    total_customers_served: int
    average_party_size: float
    orders_by_status: dict[OrderStatus, int]
    popular_items: List[dict] = Field(default_factory=list)
    revenue_by_category: dict[str, float]


class PeakHoursAnalysis(BaseModel):
    """Analysis of busy times"""
    hour: int
    order_count: int
    revenue: float
    average_wait_time: float


class DailyOrderSummary(BaseModel):
    """Summary of orders for a day"""
    date: datetime
    total_orders: int
    total_revenue: float
    total_customers: int
    average_order_value: float
    peak_hours: List[PeakHoursAnalysis]
    cancelled_orders: int
    cancellation_rate: float


# === WebSocket Schemas ===

class OrderStatusUpdate(BaseModel):
    """Real-time order status update"""
    order_id: int
    table_id: int
    table_number: int
    event_type: str = Field(
        ...,
        description="created, status_changed, item_added, ready, completed, cancelled"
    )
    old_status: Optional[OrderStatus] = None
    new_status: OrderStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    affected_items: List[str] = Field(default_factory=list)
    notify_roles: List[str] = Field(
        default_factory=list,
        description="Which roles should be notified: kitchen, waiter, admin"
    )
    message: Optional[str] = None


class TableOrderUpdate(BaseModel):
    """Real-time update about table's orders"""
    table_id: int
    table_number: int
    event_type: str = Field(..., description="new_order, order_ready, bill_requested, payment_completed")
    order_id: Optional[int] = None
    current_bill_total: float
    active_orders_count: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Validation Schemas ===

class OrderValidation(BaseModel):
    """Validation result before creating order"""
    is_valid: bool
    can_fulfill: bool
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    estimated_total: float
    estimated_prep_time: int
    unavailable_items: List[str] = Field(default_factory=list)


class OrderAvailabilityCheck(BaseModel):
    """Check if order items are currently available"""
    items: List[OrderItemCreate]
"""
Table Pydantic schemas for API requests/responses
"""
from pydantic import BaseModel, Field, field_validator
from database.models.table import TableStatus, LocationZone
from typing import Optional, List
from datetime import datetime, timezone


# === Base Schemas ===

class TableBase(BaseModel):
    """Base table schema"""
    number: int = Field(..., gt=0, description="Physical table number")
    capacity: int = Field(..., ge=1, le=50, description="Maximum number of guests")
    location_zone: LocationZone = Field(..., description="Restaurant zone")


# === Creation Schemas ===

class TableCreate(TableBase):
    """Schema for creating a new table"""
    pass


# === Update Schemas ===

class TableUpdate(BaseModel):
    """Schema for updating table information (all fields optional)"""
    capacity: Optional[int] = Field(None, ge=1, le=50)
    location_zone: Optional[LocationZone] = None


class TableStatusUpdate(BaseModel):
    """Schema for manually updating table status"""
    status: TableStatus = Field(..., description="New table status")


class TableReservation(BaseModel):
    """Schema for creating a table reservation"""
    reservation_time: datetime = Field(..., description="When the reservation starts")
    party_size: int = Field(..., ge=1, description="Number of guests")
    customer_name: Optional[str] = Field(None, description="Name for the reservation")
    customer_contact: Optional[str] = Field(None, description="Phone or email")
    
    @field_validator('reservation_time')
    @classmethod
    def validate_future_time(cls, v: datetime) -> datetime:
        """Ensure reservation is in the future"""
        if v <= datetime.now(timezone.utc):
            raise ValueError("Reservation time must be in the future")
        return v


# === Response Schemas ===

class TableResponse(TableBase):
    """Basic table response"""
    id: int
    status: TableStatus
    reservation_start: Optional[datetime] = None
    
    model_config = {"from_attributes": True}


class TableDetailedResponse(TableResponse):
    """Detailed table response with current occupancy"""
    seated_customers_count: int = Field(default=0, description="Number of currently seated customers")
    active_orders_count: int = Field(default=0, description="Number of active orders")
    current_bill_total: float = Field(default=0.0, description="Total amount of active orders")
    is_available: bool = Field(default=True, description="Whether table can accept new customers")


class CustomerInfo(BaseModel):
    """Simplified customer info for table response"""
    user_id: int
    username: str


class OrderSummary(BaseModel):
    """Simplified order info for table response"""
    order_id: int
    status: str
    total_amount: float
    created_at: datetime


class TableWithDetails(TableDetailedResponse):
    """Complete table information including customers and orders"""
    seated_customers: List[CustomerInfo] = []
    active_orders: List[OrderSummary] = []


class TableListResponse(BaseModel):
    """Paginated list of tables"""
    tables: List[TableResponse]
    total: int
    page: int
    page_size: int


class TableAvailability(BaseModel):
    """Table availability for a specific time/party size"""
    table_id: int
    table_number: int
    capacity: int
    location_zone: LocationZone
    is_available: bool
    current_status: TableStatus
    can_accommodate: bool = Field(..., description="Whether table can fit the party size")


class TableAvailabilityResponse(BaseModel):
    """List of available tables"""
    available_tables: List[TableAvailability]
    requested_time: datetime
    party_size: int


# === QR Code Schema ===

class TableQRCode(BaseModel):
    """Data encoded in table QR code"""
    table_id: int
    table_number: int
    capacity: int
    zone: str
    restaurant_id: Optional[str] = Field(None, description="Restaurant identifier for multi-location")
    

class TableQRCodeResponse(BaseModel):
    """QR code generation response"""
    table_id: int
    table_number: int
    qr_code_data: TableQRCode
    qr_code_url: Optional[str] = Field(None, description="URL to generated QR code image")


# === WebSocket Schemas ===

class TableStatusUpdate(BaseModel):
    """Real-time table status update for WebSocket"""
    table_id: int
    table_number: int
    event_type: str = Field(
        ..., 
        description="status_changed, customer_seated, customer_left, order_placed, bill_updated"
    )
    new_status: Optional[TableStatus] = None
    seated_count: int = 0
    current_bill: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[dict] = None


# === Operational Schemas ===

class TableClearRequest(BaseModel):
    """Request to clear a table after customers leave"""
    mark_for_cleaning: bool = Field(True, description="Set status to CLEANING vs AVAILABLE")


class TableAssignmentRequest(BaseModel):
    """Request to assign a customer to a table"""
    user_id: int = Field(..., description="Customer user ID to assign")
    force: bool = Field(False, description="Force assignment even if table is not available")


class BulkTableStatusUpdate(BaseModel):
    """Update multiple tables at once (for closing/opening sections)"""
    table_ids: List[int] = Field(..., description="List of table IDs to update")
    new_status: TableStatus = Field(..., description="Status to set for all tables")
    reason: Optional[str] = Field(None, description="Reason for bulk update")


class TableStatistics(BaseModel):
    """Statistics for a table over a time period"""
    table_id: int
    table_number: int
    total_orders: int
    total_revenue: float
    average_party_size: float
    average_order_value: float
    total_customers_served: int
    turnover_rate: float = Field(..., description="How many times the table turned over")
    occupancy_percentage: float = Field(..., description="Percentage of time table was occupied")


class RestaurantFloorPlan(BaseModel):
    """Complete floor plan with all tables"""
    zones: dict[LocationZone, List[TableDetailedResponse]] = Field(
        ...,
        description="Tables grouped by location zone"
    )
    total_tables: int
    available_tables: int
    occupied_tables: int
    reserved_tables: int
    cleaning_tables: int
    total_capacity: int
    current_occupancy: int
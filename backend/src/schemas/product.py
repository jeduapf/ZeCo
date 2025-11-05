"""
Product Pydantic schemas for API requests/responses
"""
from pydantic import BaseModel, Field
from datetime import datetime

class ProductBase(BaseModel):
    """Base product schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)
    is_active: bool = True

class ProductCreate(ProductBase):
    """Schema for creating a product"""
    pass

class ProductUpdate(BaseModel):
    """Schema for updating a product (all fields optional)"""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    price: float | None = Field(None, gt=0)
    stock: int | None = Field(None, ge=0)
    is_active: bool | None = None

class ProductResponse(ProductBase):
    """Schema for product response"""
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: int
    
    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    """Schema for paginated product list"""
    products: list[ProductResponse]
    total: int
    page: int
    page_size: int
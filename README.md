# Complete Modular FastAPI Project Guide

## 📁 Final Project Structure

```
project_root/
│
├── main.py                              # Application entry point
├── config.py                            # Configuration settings
├── requirements.txt                     # Dependencies
├── .env                                # Environment variables
├── .gitignore
│
├── core/                               # Core functionality
│   ├── __init__.py
│   ├── security.py                     # JWT, hashing, auth
│   └── dependencies.py                 # Shared dependencies
│
├── database/                           # Database layer
│   ├── __init__.py
│   ├── base.py                         # Base setup & model imports
│   ├── session.py                      # Session management
│   └── models/                         # ORM models
│       ├── __init__.py
│       ├── user.py                     # User model
│       └── product.py                  # Product model
│
├── schemas/                            # Pydantic schemas
│   ├── __init__.py
│   ├── user.py                         # User schemas
│   └── product.py                      # Product schemas
│
├── services/                           # Business logic
│   ├── __init__.py
│   ├── user_service.py                 # User operations
│   └── product_service.py              # Product operations
│
├── api/                                # API routes
│   ├── __init__.py
│   └── v1/                             # API version 1
│       ├── __init__.py
│       ├── router.py                   # Main v1 router
│       └── endpoints/                  # Endpoint modules
│           ├── __init__.py
│           ├── auth.py                 # Auth endpoints
│           ├── users.py                # User endpoints
│           └── products.py             # Product endpoints
│
└── tests/                              # Test suite
    ├── __init__.py
    ├── test_auth.py
    └── test_products.py
```

## 🔧 Configuration Files

### `config.py`
```python
from dotenv import load_dotenv
import os
from typing import Final # So that my variables are immutable

# Load environment variables from .env file
load_dotenv(dotenv_path=".env")

# Database configuration
DATABASE_URL: Final[str] = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# JWT configuration
SECRET_KEY: Final[str] = os.getenv("SECRET_KEY", "your-secret-key-here")  # Change in production!
ALGORITHM: Final[str] = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
TOKEN_REFRESH_THRESHOLD_MINUTES: Final[int] = int(os.getenv("TOKEN_REFRESH_THRESHOLD_MINUTES", "15"))
DEBUG: Final[bool] = os.getenv("DEBUG", "False").lower() in ("true", "1", "t", "True", "TRUE")  # Convert to boolean
```

### `.env`
```env
DATABASE_URL=sqlite:///./DATABASE.db
SECRET_KEY=sexysecret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
TOKEN_REFRESH_THRESHOLD_MINUTES = 15
DEBUG=True
```

### `requirements.txt`
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
python-dotenv==1.0.0
pydantic==2.5.0
bcrypt==3.2.2
```

## 📝 __init__.py Files

### `database/__init__.py`
```python
from database.base import Base
from database.session import engine, SessionLocal, get_db
from database.models.user import User, UserRole
from database.models.product import Product

__all__ = [
    'Base', 'engine', 'SessionLocal', 'get_db',
    'User', 'UserRole', 'Product'
]
```

### `database/models/__init__.py`
```python
from database.models.user import User, UserRole
from database.models.product import Product

__all__ = ['User', 'UserRole', 'Product']
```

### `schemas/__init__.py`
```python
from schemas.user import (
    UserBase, UserCreate, UserResponse, 
    UserRoleUpdate, Token, TokenData
)
from schemas.product import (
    ProductBase, ProductCreate, ProductUpdate,
    ProductResponse, ProductListResponse
)

__all__ = [
    'UserBase', 'UserCreate', 'UserResponse',
    'UserRoleUpdate', 'Token', 'TokenData',
    'ProductBase', 'ProductCreate', 'ProductUpdate',
    'ProductResponse', 'ProductListResponse'
]
```

### `services/__init__.py`
```python
from services.product_service import ProductService

__all__ = ['ProductService']
```

### `api/v1/endpoints/__init__.py`
```python
from api.v1.endpoints import auth, users, products

__all__ = ['auth', 'users', 'products']
```

### `core/__init__.py`
```python
from core.security import (
    verify_password, get_password_hash,
    create_access_token, get_current_user,
    get_current_admin_user
)
from core.dependencies import DbDependency, CurrentUser, AdminUser

__all__ = [
    'verify_password', 'get_password_hash',
    'create_access_token', 'get_current_user',
    'get_current_admin_user', 'DbDependency',
    'CurrentUser', 'AdminUser'
]
```

## 🚀 How to Add New Features

### Adding a New Model (e.g., Order)

1. **Create model**: `database/models/order.py`
```python
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database.base import Base
from enum import Enum as PyEnum

class OrderStatus(PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")
    product = relationship("Product")
```

2. **Update**: `database/base.py` - add import
```python
from database.models.order import Order
```

3. **Create schemas**: `schemas/order.py`
```python
from pydantic import BaseModel
from datetime import datetime

class OrderCreate(BaseModel):
    product_id: int
    quantity: int

class OrderResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    quantity: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True
```

4. **Create service**: `services/order_service.py`
```python
from sqlalchemy.orm import Session
from database.models.order import Order
from schemas.order import OrderCreate

class OrderService:
    @staticmethod
    def create_order(db: Session, order: OrderCreate, user_id: int):
        new_order = Order(
            user_id=user_id,
            product_id=order.product_id,
            quantity=order.quantity
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        return new_order
```

5. **Create endpoints**: `api/v1/endpoints/orders.py`
```python
from fastapi import APIRouter
from core.dependencies import DbDependency, CurrentUser
from schemas.order import OrderCreate, OrderResponse
from services.order_service import OrderService

router = APIRouter(tags=["Orders"])

@router.post("/", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    current_user: CurrentUser,
    db: DbDependency
):
    return OrderService.create_order(db, order, current_user.id)
```

6. **Register router**: `api/v1/router.py`
```python
from api.v1.endpoints import orders
api_router.include_router(orders.router, prefix="/orders")
```

## 🎯 Key Benefits of This Structure

1. **Clear Separation**:
   - Models = Database structure
   - Schemas = API contracts
   - Services = Business logic
   - Endpoints = HTTP layer

2. **Easy Testing**:
   - Test services independently
   - Mock database easily
   - Test endpoints separately

3. **Scalability**:
   - Add new features without touching existing code
   - Easy to add API versioning (v2, v3)
   - Can split into microservices later

4. **Maintainability**:
   - Each file has a single responsibility
   - Easy to find and fix bugs
   - Clear dependencies

## 📚 API Endpoints

Once running, your API will have:

- `POST /api/v1/auth/token` - Login
- `POST /api/v1/auth/register` - Register
- `GET /api/v1/auth/me` - Get current user
- `GET /api/v1/users/` - List users (admin)
- `PUT /api/v1/users/{id}/role` - Update role (admin)
- `POST /api/v1/products/` - Create product
- `GET /api/v1/products/` - List products
- `GET /api/v1/products/{id}` - Get product
- `PUT /api/v1/products/{id}` - Update product
- `DELETE /api/v1/products/{id}` - Delete product

## 🏃 Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload

# Access documentation
# http://localhost:8000/docs
```

## 🔒 Security Notes

- Change `SECRET_KEY` in production
- Use environment variables for sensitive data
- Consider using PostgreSQL in production
- Add rate limiting for production
- Implement proper CORS settings
- Add input validation
- Use HTTPS in production

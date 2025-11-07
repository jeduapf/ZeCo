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

## 🧩 Database Schema (ER Diagram)

Below is the complete **Entity–Relationship Diagram** showing how users, orders, and items connect — including analytical extensions like costs, promotions, and inventory logs.

```mermaid
erDiagram
erDiagram
    %% === USERS ===
    USERS {
        int id PK
        string username UK
        string hashed_password
        string email UK
        int age
        bool gender "nullable"
        enum role "admin, kitchen, client, waiter"
        int table_id FK "nullable"
    }

    %% === TABLES ===
    TABLES {
        int id PK
        int number UK "physical table number"
        int capacity
        enum status "available, occupied, reserved, cleaning"
        enum location_zone "indoor, outdoor, terrace, bar, vip"
        datetime reservation_start "nullable"
    }

    %% === BASIC ITEMS ===
    BASIC_ITEMS {
        int id PK
        string name
        float stock
        string unit "kg, liters, pieces"
        float base_cost
        float tax_rate
        datetime expiration_date
        datetime last_updated
        int last_updated_by FK
        text description "nullable"
    }

    %% === MENU ITEMS ===
    MENU_ITEMS {
        int id PK
        string name UK
        float price
        int stock
        enum category "entry, main_course, dessert, beverage"
        bool available
        datetime created_at
        text description "nullable"
    }

    %% === MENU ITEM COMPONENTS ===
    MENU_ITEM_COMPONENTS {
        int menu_item_id PK,FK
        int basic_item_id PK,FK
        float quantity_required
    }

    %% === ORDERS ===
    ORDERS {
        int id PK
        int user_id FK "nullable for guest orders"
        int table_id FK
        enum status "pending, confirmed, preparing, ready, served, completed, cancelled"
        datetime created_at
        datetime finished_at "nullable"
        text specifications "nullable"
        float total_amount
        float discount_applied
        enum payment_method "cash, card, mobile, voucher, pending"
        string promo_code FK "nullable"
        int num_customers "number of people for this order"
    }

    %% === ORDER ITEMS ===
    ORDER_ITEMS {
        int order_id PK,FK
        int item_id PK,FK
        int quantity
        float item_price
        float item_cost
    }

    %% === PROMOTIONS ===
    PROMOTIONS {
        int id PK
        string code UK
        text description
        float discount_percentage
        enum target_category "nullable"
        int target_menu_item "nullable"
        datetime start_date
        datetime end_date
    }

    %% === INVENTORY LOGS ===
    INVENTORY_LOGS {
        int id PK
        int user_id FK
        int item_id FK
        datetime timestamp
        float stock_change
        enum reason "initial_stock, restock, sale, waste, theft, correction, return, sample"
        string notes "nullable"
    }

    %% === STAFF SHIFTS ===
    STAFF_SHIFTS {
        int id PK
        int user_id FK
        datetime shift_start
        datetime shift_end
        enum role "waiter, kitchen"
    }

    %% === DAILY LOGS ===
    DAILY_LOGS {
        int id PK
        date log_date UK
        int total_customers
        float total_revenue
        float total_expenses
        float worked_time
    }

    %% === MONTHLY OVERVIEW ===
    MONTHLY_OVERVIEW {
        int id PK
        date month_start "e.g., 2025-11-01"
        string category "revenue, food_cost, staff_cost, electricity, rent, taxes, etc."
        float amount "positive for income, negative for expense"
        text notes "optional"
    }

    %% === MONTHLY ITEM STATS ===
    MONTHLY_ITEM_STATS {
        int id PK
        int menu_item_id FK
        date month_start
        int quantity_sold
        float revenue_generated
        float total_item_cost
        float avg_margin
    }

    %% === RELATIONSHIPS ===
    USERS ||--o{ ORDERS : "places/manages"
    TABLES ||--o{ USERS : "seats"
    TABLES ||--o{ ORDERS : "serves at"

    ORDERS ||--|{ ORDER_ITEMS : "contains"
    MENU_ITEMS ||--o{ ORDER_ITEMS : "ordered as"

    MENU_ITEMS ||--|{ MENU_ITEM_COMPONENTS : "composed of"
    BASIC_ITEMS ||--o{ MENU_ITEM_COMPONENTS : "ingredient in"

    USERS ||--o{ BASIC_ITEMS : "last updated by"
    USERS ||--o{ INVENTORY_LOGS : "performs change"
    BASIC_ITEMS ||--o{ INVENTORY_LOGS : "tracked in"

    PROMOTIONS ||--o{ ORDERS : "applied to"

    DAILY_LOGS ||--o{ STAFF_SHIFTS : "includes staff shifts"
    DAILY_LOGS ||--o{ ORDERS : "summarizes orders of the day"

    MONTHLY_ITEM_STATS ||--|| MENU_ITEMS : "analyzes"
    MONTHLY_ITEM_STATS ||--|| MONTHLY_OVERVIEW : "belongs to month"
    DAILY_LOGS ||--o{ MONTHLY_OVERVIEW : "aggregated into"
```

---


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
SECRET_KEY=secret
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

## 🏃 Running the Application Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload

# Access documentation
# http://localhost:8000/docs
```

## 🏃 Running the Application with Docker

```bash
docker build -t backend_api .

docker run --rm -p 8000:8000 backend_api
```

OR just click in the bat file which contains the following inside

```bash
@echo off
SET IMAGE_NAME=backend_api
SET PORT=8000

echo Building Docker image...
docker build -t %IMAGE_NAME% .

IF %ERRORLEVEL% NEQ 0 (
    echo Docker build failed. Exiting.
    exit /b 1
)

echo Running Docker container...
docker run --rm -p %PORT%:%PORT% %IMAGE_NAME%

pause
```

## 🔒 Security Notes

- Change `SECRET_KEY` in production
- Use environment variables for sensitive data
- Consider using PostgreSQL in production if the place is too big
- Add rate limiting for production 
- Implement proper CORS settings
- Add input validation
- Use HTTPS in production

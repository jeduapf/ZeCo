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
│       └── item.py                     # Item model
|             ...
│
├── schemas/                            # Pydantic schemas
│   ├── __init__.py
│   ├── user.py                         # User schemas
│   └── item.py                         # Item schemas
|          ...
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
│           └── items.py                # Items endpoints
|                 ...
│
└── tests/                              # Test suite
    ├── __init__.py
    ├── test_auth.py
    ├── test_products.py
    └── ...

```
---

## Database structure

```mermaid
erDiagram
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

    TABLES {
        int id PK
        int number UK "physical table number"
        int capacity
        enum status "available, occupied, reserved, cleaning"
        enum location_zone "indoor, outdoor, terrace, bar, vip"
        datetime reservation_start "nullable"
    }

    BASIC_ITEMS {
        int id PK
        string name
        float stock "current quantity"
        string unit "kg, liters, pieces"
        float base_cost "cost per unit"
        float tax_rate "0.0 to 1.0"
        datetime expiration_date
        datetime last_updated
        int last_updated_by FK
        text description "nullable"
    }

    MENU_ITEMS {
        int id PK
        string name UK "dish name"
        float price "customer price"
        int stock "estimated servings"
        enum category "entry, main_course, dessert, beverage"
        bool available "can be ordered"
        datetime created_at
        text description "nullable"
    }

    MENU_ITEM_COMPONENTS {
        int menu_item_id PK,FK
        int basic_item_id PK,FK
        float quantity_required "amount needed per serving (unit in basic_items)"
    }

    ORDERS {
        int id PK
        int user_id FK "nullable for guest orders"
        int table_id FK
        enum status "pending, confirmed, preparing, ready, served, completed, cancelled"
        datetime created_at
        datetime finished_at "nullable"
        text specifications "nullable - special requests"
        float total_amount
        float discount_applied
        enum payment_method "cash, card, mobile, voucher, pending"
        string promo_code FK "nullable"
    }

    ORDER_ITEMS {
        int order_id PK,FK
        int item_id PK,FK
        int quantity
        float item_price "price snapshot at order time"
        float item_cost "cost snapshot for profit calculation"
    }

    PROMOTIONS {
        int id PK
        string code UK "promo code customers enter"
        text description
        float discount_percentage "0.0 to 1.0"
        enum target_category "nullable - if applies to specific category"
        int target_menu_item "nullable - if applies to specific item"
        datetime start_date
        datetime end_date
    }

    INVENTORY_LOGS {
        int id PK
        int user_id FK
        int item_id FK "references basic_items"
        datetime timestamp
        float stock_change "positive or negative"
        enum reason "initial_stock, restock, sale, waste, theft, correction, return, sample"
        string notes "nullable - additional context"
    }

    %% Core Relationships
    USERS ||--o{ ORDERS : "places/manages"
    TABLES ||--o{ USERS : "seats"
    TABLES ||--o{ ORDERS : "serves at"
    
    %% Order Structure
    ORDERS ||--|{ ORDER_ITEMS : "contains"
    MENU_ITEMS ||--o{ ORDER_ITEMS : "ordered as"
    
    %% Menu Composition (Recipe)
    MENU_ITEMS ||--|{ MENU_ITEM_COMPONENTS : "composed of"
    BASIC_ITEMS ||--o{ MENU_ITEM_COMPONENTS : "ingredient in"
    
    %% Inventory Management
    USERS ||--o{ BASIC_ITEMS : "last updated by"
    USERS ||--o{ INVENTORY_LOGS : "performs change"
    BASIC_ITEMS ||--o{ INVENTORY_LOGS : "tracked in"
    
    %% Promotions
    PROMOTIONS ||--o{ ORDERS : "applied to"
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

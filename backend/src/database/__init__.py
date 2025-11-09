"""
Database package initialization
Centralized imports for all database components
"""
from database.base import Base
from database.session import engine, AsyncSessionLocal, get_db
"""
Database models package initialization (COMPLETE UPDATE)
Centralized imports for all database models
"""
from database.models.user import User, UserRole
from database.models.basic_item import BasicItem
from database.models.menu_item import MenuItem, Category
from database.models.menu_item_component import MenuItemComponent
from database.models.table import Table, TableStatus, LocationZone
from database.models.order import Order, OrderStatus, PaymentMethod
from database.models.order_item import OrderItem
from database.models.promotion import Promotion
from database.models.inventory_log import InventoryLog, StockChangeReason

# NEW MODELS:
from database.models.staff_shift import StaffShift, ShiftRole
from database.models.daily_log import DailyLog
from database.models.monthly_overview import MonthlyOverview, FinancialCategory
from database.models.monthly_item_stats import MonthlyItemStats

__all__ = [
    # Base components
    'Base', 
    'engine', 
    'AsyncSessionLocal', 
    'get_db',
    
    # User and Authentication
    'User', 
    'UserRole',
    
    # Inventory Management
    'BasicItem',
    'MenuItem',
    'MenuItemComponent',
    'Category',
    'InventoryLog',
    'StockChangeReason',
    
    # Table Management
    'Table',
    'TableStatus',
    'LocationZone',
    
    # Order Management
    'Order',
    'OrderStatus',
    'PaymentMethod',
    'OrderItem',
    
    # Promotions
    'Promotion',
    
    # Analytics and Reporting (NEW)
    'StaffShift',
    'ShiftRole',
    'DailyLog',
    'MonthlyOverview',
    'FinancialCategory',
    'MonthlyItemStats',
]
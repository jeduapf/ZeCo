"""
Database models package initialization (COMPLETE UPDATE)
Centralized imports for all database models
"""
from src.database.models.user import User, UserRole
from src.database.models.basic_item import BasicItem
from src.database.models.menu_item import MenuItem, Category
from src.database.models.menu_item_component import MenuItemComponent
from src.database.models.table import Table, TableStatus, LocationZone
from src.database.models.order import Order, OrderStatus, PaymentMethod
from src.database.models.order_item import OrderItem
from src.database.models.promotion import Promotion
from src.database.models.inventory_log import InventoryLog, StockChangeReason

# NEW MODELS:
from src.database.models.staff_shift import StaffShift, ShiftRole
from src.database.models.daily_log import DailyLog
from src.database.models.monthly_overview import MonthlyOverview, FinancialCategory
from src.database.models.monthly_item_stats import MonthlyItemStats

__all__ = [
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
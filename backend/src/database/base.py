"""
Database base configuration and model imports
Import all models here to ensure they're registered with SQLAlchemy
"""
from sqlalchemy.ext.declarative import declarative_base
from config import DATABASE_URL

# Create base class for all models
Base = declarative_base() 

# Import all models here so they're registered
# This ensures all models are available when creating tables
from database.models.user import User
from src.database.models.basic_item import Item  # When you create it

__all__ = ['Base', 'User', 'Item']




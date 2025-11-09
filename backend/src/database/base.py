"""
Database base configuration and model imports
Import all models here to ensure they're registered with SQLAlchemy
"""
from sqlalchemy.ext.declarative import declarative_base
# Import all models here so they're registered
# This ensures all models are available when creating tables
# from src.database.models import *  # Import all models to register them

# Create base class for all models
Base = declarative_base() 
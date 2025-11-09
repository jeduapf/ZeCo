"""
Database base configuration and model imports
Import all models here to ensure they're registered with SQLAlchemy
"""
from sqlalchemy.ext.declarative import declarative_base
from config import DATABASE_URL

# Create base class for all models
Base = declarative_base() 
"""
License-related Pydantic schemas.

This module defines data validation models for license activation and management.
"""
from pydantic import BaseModel, Field


class LicenseInput(BaseModel):
    """
    Schema for license key input during activation.
    
    Attributes:
        key (str): The JWT-encoded license key to activate
    
    Example:
        {
            "key": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
    """
    key: str = Field(
        ...,
        description="JWT-encoded license key",
        min_length=1
    )

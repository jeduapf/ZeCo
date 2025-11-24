"""
License Management Endpoints

This module provides REST API endpoints for license activation and status checking.
All endpoints use the LicenseManager from src.core.license_manager for validation.
"""
from fastapi import APIRouter, status, HTTPException
from fastapi.responses import JSONResponse
from src.schemas.license import LicenseInput
from src.core.license_manager import LicenseManager


# Initialize router for license-related endpoints
router = APIRouter(
    prefix="/license",
    tags=["license"]
)

# Initialize License Manager (singleton pattern - same instance across requests)
license_manager = LicenseManager()


@router.post("", status_code=status.HTTP_200_OK)
async def activate_license(license_data: LicenseInput):
    """
    Activate or update the application license key.
    
    This endpoint validates and stores a JWT-encoded license key.
    The license must be signed with the corresponding private key to the
    server's public key (public_key.pem).
    
    Args:
        license_data: LicenseInput schema containing the license key
        
    Returns:
        dict: Success message if license is valid
        
    Raises:
        HTTPException 402: If license is invalid or expired
        HTTPException 500: If license verification fails due to server error
        
    Example:
        POST /api/v1/license
        {
            "key": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
        
        Response 200:
        {
            "message": "License activated successfully"
        }
    """
    try:
        # LicenseManager.set_license() internally calls verify_license()
        # This ensures we only store valid licenses
        license_manager.set_license(license_data.key)
        return {"message": "License activated successfully"}
    except HTTPException as e:
        # Re-raise HTTP exceptions (402 for invalid/expired license)
        raise e
    except Exception as e:
        # Catch any unexpected errors and return 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/status", status_code=status.HTTP_200_OK)
async def get_license_status():
    """
    Check the current license activation status.
    
    This endpoint verifies:
    1. A license key exists
    2. The license signature is valid
    3. The license has not expired
    4. System time has not been tampered with
    
    Returns:
        dict: License status (active or inactive)
        
    Example:
        GET /api/v1/license/status
        
        Response 200 (valid license):
        {
            "status": "active",
            "message": "License is valid"
        }
        
        Response 402 (invalid/missing license):
        {
            "status": "inactive",
            "detail": "No license key found. Please activate your application."
        }
    """
    try:
        # is_active() checks tampering, existence, and validity
        license_manager.is_active()
        return {
            "status": "active",
            "message": "License is valid"
        }
    except HTTPException as e:
        # Return 402 with inactive status for license issues
        return JSONResponse(
            status_code=e.status_code,
            content={
                "status": "inactive",
                "detail": e.detail
            }
        )

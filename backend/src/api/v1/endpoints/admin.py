from fastapi import APIRouter, Depends
from src.core.security import get_current_admin_user

router = APIRouter()


@router.get("/only")
async def admin_only(admin = Depends(get_current_admin_user)):
    """Simple admin-only endpoint for testing."""
    return {"msg": "admin access granted", "username": admin.username, "role": admin.role.value}

"""
User management endpoints (Admin only)
"""
from fastapi import APIRouter, HTTPException, status, Response
from core.dependencies import DbDependency, AdminUser
from database.models.user import User, UserRole
from schemas.user import UserResponse, UserRoleUpdate

router = APIRouter(tags=["User Management"])

@router.get("/", response_model=list[UserResponse])
async def get_all_users(
    admin: AdminUser,
    db: DbDependency,
    response: Response
):
    """Get all users (Admin only)"""
    users = db.query(User).all()
    return users

@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    admin: AdminUser,
    db: DbDependency,
    response: Response
):
    """Update a user's role (Admin only)"""
    user_to_update = db.query(User).filter(User.id == user_id).first()
    if not user_to_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user_to_update.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    # Prevent removing last admin
    if (user_to_update.role == UserRole.ADMIN and 
        role_update.role != UserRole.ADMIN):
        admin_count = db.query(User).filter(User.role == UserRole.ADMIN).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last admin user"
            )
    
    user_to_update.role = role_update.role
    db.commit()
    db.refresh(user_to_update)
    
    return user_to_update
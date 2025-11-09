"""
Shared dependencies across the application (ASYNC VERSION)

This module provides type-annotated dependencies that you can use in your
FastAPI endpoints to make them cleaner and more readable.

Usage example:
    @router.get("/orders")
    async def get_orders(
        db: DbDependency,
        current_user: CurrentUser
    ):
        # db is AsyncSession
        # current_user is User model
        ...
"""
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.database.models.user import User
from src.core.security import (
    get_current_user,
    get_current_admin_user,
    get_current_staff_user,
    get_current_kitchen_user,
    get_current_waiter_user
)


# === Database Dependency ===

DbDependency = Annotated[AsyncSession, Depends(get_db)]
"""
Async database session dependency.

Use this instead of manually adding `db: AsyncSession = Depends(get_db)`.

Example:
    async def my_endpoint(db: DbDependency):
        result = await db.execute(select(User))
        ...
"""


# === User Authentication Dependencies ===

CurrentUser = Annotated[User, Depends(get_current_user)]
"""
Current authenticated user (any role).

The user is already authenticated and their JWT token has been validated.
Returns the SQLAlchemy User model, not a Pydantic schema.

Example:
    async def my_endpoint(current_user: CurrentUser):
        print(f"User {current_user.username} is accessing endpoint")
        orders = current_user.orders  # Access relationships
        is_admin = current_user.is_admin()  # Call methods
"""


AdminUser = Annotated[User, Depends(get_current_admin_user)]
"""
Current user verified as ADMIN.

Only admins can access endpoints using this dependency.

Example:
    async def delete_user(user_id: int, admin: AdminUser):
        # Only admins reach here
        ...
"""


StaffUser = Annotated[User, Depends(get_current_staff_user)]
"""
Current user verified as staff (admin, kitchen, or waiter).

Clients are blocked from endpoints using this dependency.

Example:
    async def get_all_orders(staff: StaffUser):
        # Staff can see all orders, clients cannot
        ...
"""


KitchenUser = Annotated[User, Depends(get_current_kitchen_user)]
"""
Current user verified as KITCHEN or ADMIN.

Example:
    async def adjust_inventory(item_id: int, kitchen: KitchenUser):
        # Only kitchen staff and admins can modify inventory
        ...
"""


WaiterUser = Annotated[User, Depends(get_current_waiter_user)]
"""
Current user verified as WAITER or ADMIN.

Example:
    async def assign_table(table_id: int, waiter: WaiterUser):
        # Only waiters and admins can assign tables
        ...
"""


# === Optional: Custom Dependencies ===

def get_pagination_params(
    page: int = 1,
    page_size: int = 20
):
    """
    Dependency for pagination parameters with validation.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Tuple of (skip, limit) for SQLAlchemy queries
        
    Example:
        async def list_items(
            db: DbDependency,
            pagination: Annotated[tuple, Depends(get_pagination_params)]
        ):
            skip, limit = pagination
            result = await db.execute(
                select(Item).offset(skip).limit(limit)
            )
    """
    # Validate inputs
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100
    
    skip = (page - 1) * page_size
    return skip, page_size


PaginationDependency = Annotated[tuple[int, int], Depends(get_pagination_params)]
"""
Pagination parameters (skip, limit).

Example:
    async def list_items(
        db: DbDependency,
        pagination: PaginationDependency
    ):
        skip, limit = pagination
        ...
"""


# === Example Usage in Endpoints ===

"""
# Example 1: Basic endpoint with authentication
@router.get("/profile")
async def get_profile(current_user: CurrentUser):
    return {
        "username": current_user.username,
        "email": current_user.email
    }

# Example 2: Admin-only endpoint
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: AdminUser,
    db: DbDependency
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    # ... delete logic

# Example 3: Staff endpoint with database access
@router.get("/orders/pending")
async def get_pending_orders(
    staff: StaffUser,
    db: DbDependency
):
    result = await db.execute(
        select(Order).where(Order.status == OrderStatus.PENDING)
    )
    orders = result.scalars().all()
    return orders

# Example 4: Kitchen-specific endpoint
@router.post("/inventory/{item_id}/adjust")
async def adjust_inventory(
    item_id: int,
    adjustment: InventoryAdjustment,
    kitchen: KitchenUser,
    db: DbDependency
):
    # Only kitchen staff can adjust inventory
    ...

# Example 5: Using pagination
@router.get("/menu-items")
async def list_menu_items(
    db: DbDependency,
    pagination: PaginationDependency
):
    skip, limit = pagination
    result = await db.execute(
        select(MenuItem).offset(skip).limit(limit)
    )
    return result.scalars().all()

# Example 6: Multiple dependencies
@router.post("/orders")
async def create_order(
    order_data: OrderCreate,
    current_user: CurrentUser,
    db: DbDependency
):
    # current_user is the authenticated User model
    # db is the async database session
    # order_data is the validated Pydantic schema
    
    new_order = Order(
        user_id=current_user.id,
        table_id=current_user.table_id,
        ...
    )
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)
    
    return OrderResponse.model_validate(new_order)
"""
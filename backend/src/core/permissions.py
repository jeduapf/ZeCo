"""
Model-level permission system for database access control (ASYNC VERSION)
This provides the first layer of security, ensuring only authorized users can access certain data
"""
from functools import wraps
from typing import Callable, List, Optional
import asyncio
from fastapi import HTTPException, status

from src.database.models.user import User, UserRole
from src.core.i18n_logger import get_i18n_logger
from config import LANG

logger = get_i18n_logger("permissions")


class PermissionDeniedError(Exception):
    """Raised when a user doesn't have permission to perform an operation"""
    pass


class ModelPermissions:
    """
    Central permission definitions for each model/table.
    
    This class acts as a single source of truth for who can access what.
    Each model has defined roles that can READ, WRITE, or DELETE data.
    
    Think of this as the building's security policy document - it defines
    which keycards (roles) can access which rooms (models).
    """
    
    # Define which roles can access each model
    # Format: 'model_name': {'read': [roles], 'write': [roles], 'delete': [roles]}
    
    PERMISSIONS = {
        'orders': {
            'read': [UserRole.ADMIN, UserRole.WAITER, UserRole.KITCHEN, UserRole.CLIENT],
            'write': [UserRole.ADMIN, UserRole.WAITER, UserRole.CLIENT],
            'delete': [UserRole.ADMIN, UserRole.WAITER]
        },
        'order_items': {
            'read': [UserRole.ADMIN, UserRole.WAITER, UserRole.KITCHEN],
            'write': [UserRole.ADMIN, UserRole.WAITER],
            'delete': [UserRole.ADMIN, UserRole.WAITER]
        },
        'menu_items': {
            'read': [UserRole.ADMIN, UserRole.WAITER, UserRole.KITCHEN, UserRole.CLIENT],
            'write': [UserRole.ADMIN],
            'delete': [UserRole.ADMIN]
        },
        'basic_items': {
            'read': [UserRole.ADMIN, UserRole.KITCHEN],
            'write': [UserRole.ADMIN, UserRole.KITCHEN],
            'delete': [UserRole.ADMIN]
        },
        'inventory_logs': {
            'read': [UserRole.ADMIN, UserRole.KITCHEN],
            'write': [UserRole.ADMIN, UserRole.KITCHEN],
            'delete': [UserRole.ADMIN]  # Logs should rarely be deleted
        },
        'tables': {
            'read': [UserRole.ADMIN, UserRole.WAITER, UserRole.CLIENT],
            'write': [UserRole.ADMIN, UserRole.WAITER],
            'delete': [UserRole.ADMIN]
        },
        'promotions': {
            'read': [UserRole.ADMIN, UserRole.WAITER],
            'write': [UserRole.ADMIN],
            'delete': [UserRole.ADMIN]
        },
        'staff_shifts': {
            'read': [UserRole.ADMIN],  # Only admins can view shift data
            'write': [UserRole.ADMIN],
            'delete': [UserRole.ADMIN]
        },
        'daily_logs': {
            'read': [UserRole.ADMIN],  # Only admins see daily summaries
            'write': [UserRole.ADMIN],  # System auto-generates, admin can correct
            'delete': [UserRole.ADMIN]
        },
        'monthly_overview': {
            'read': [UserRole.ADMIN],  # Financial data is admin-only
            'write': [UserRole.ADMIN],
            'delete': [UserRole.ADMIN]
        },
        'monthly_item_stats': {
            'read': [UserRole.ADMIN],  # Analytics are admin-only
            'write': [UserRole.ADMIN],  # System auto-generates
            'delete': [UserRole.ADMIN]
        },
        'users': {
            'read': [UserRole.ADMIN],
            'write': [UserRole.ADMIN],
            'delete': [UserRole.ADMIN]
        }
    }
    
    @classmethod
    def check_permission(
        cls, 
        user: Optional[User], 
        model_name: str, 
        operation: str = 'read'
    ) -> bool:
        """
        Check if a user has permission to perform an operation on a model.
        
        Args:
            user: The user attempting the operation (can be None)
            model_name: Name of the model/table (e.g., 'orders', 'staff_shifts')
            operation: Type of operation ('read', 'write', 'delete')
            
        Returns:
            True if user has permission, False otherwise
        """
        if not user:
            logger.warning(
                "auth.unauthorized",
                language=LANG,
                resource=f"{model_name}.{operation}"
            )
            return False
        
        # Get permission rules for this model
        model_perms = cls.PERMISSIONS.get(model_name.lower(), {})
        allowed_roles = model_perms.get(operation, [])
        
        # Check if user's role is in the allowed list
        has_permission = user.role in allowed_roles
        
        if not has_permission:
            logger.warning(
                "error.permission",
                language=LANG,
                username=user.username,
                action=f"{operation} on {model_name}"
            )
        
        return has_permission
    
    @classmethod
    def require_permission(
        cls,
        model_name: str,
        operation: str = 'read'
    ) -> Callable:
        """
        Decorator to enforce permissions on service methods (ASYNC VERSION).
        
        This decorator now supports both sync and async functions.
        
        Usage:
            @ModelPermissions.require_permission('staff_shifts', 'read')
            async def get_all_shifts(db: AsyncSession, user: User):
                # This method will only execute if user has permission
                result = await db.execute(select(StaffShift))
                return result.scalars().all()
        
        Args:
            model_name: The model being accessed
            operation: The type of operation ('read', 'write', 'delete')
            
        Returns:
            Decorated function that checks permissions before executing
        """
        def decorator(func: Callable) -> Callable:
            # Check if function is async
            if asyncio.iscoroutinefunction(func):
                # Async version
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    # Extract user from function arguments
                    user = kwargs.get('user')
                    if not user and len(args) > 1:
                        # Try to find User object in positional args
                        for arg in args:
                            if isinstance(arg, User):
                                user = arg
                                break
                    
                    if not user:
                        logger.error(
                            "error.permission",
                            language=LANG,
                            username="unknown",
                            action=f"No user provided for {operation} on {model_name}"
                        )
                        raise PermissionDeniedError(
                            f"No user provided for permission check on {model_name}"
                        )
                    
                    # Check permission
                    if not cls.check_permission(user, model_name, operation):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"You don't have permission to {operation} {model_name}"
                        )
                    
                    # Permission granted, execute the async function
                    return await func(*args, **kwargs)
                
                return async_wrapper
            
            else:
                # Sync version (for backwards compatibility)
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    user = kwargs.get('user')
                    if not user and len(args) > 1:
                        for arg in args:
                            if isinstance(arg, User):
                                user = arg
                                break
                    
                    if not user:
                        logger.error(
                            "error.permission",
                            language=LANG,
                            username="unknown",
                            action=f"No user provided for {operation} on {model_name}"
                        )
                        raise PermissionDeniedError(
                            f"No user provided for permission check on {model_name}"
                        )
                    
                    if not cls.check_permission(user, model_name, operation):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"You don't have permission to {operation} {model_name}"
                        )
                    
                    return func(*args, **kwargs)
                
                return sync_wrapper
        
        return decorator


# Convenience decorators for common operations

def require_read(model_name: str):
    """
    Decorator to require read permission.
    
    Example:
        @require_read('orders')
        async def get_orders(db: AsyncSession, user: User):
            ...
    """
    return ModelPermissions.require_permission(model_name, 'read')


def require_write(model_name: str):
    """
    Decorator to require write permission.
    
    Example:
        @require_write('menu_items')
        async def create_menu_item(db: AsyncSession, item_data: dict, user: User):
            ...
    """
    return ModelPermissions.require_permission(model_name, 'write')


def require_delete(model_name: str):
    """
    Decorator to require delete permission.
    
    Example:
        @require_delete('users')
        async def delete_user(db: AsyncSession, user_id: int, admin: User):
            ...
    """
    return ModelPermissions.require_permission(model_name, 'delete')


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require admin role for any operation (ASYNC VERSION).
    
    This decorator now supports both sync and async functions.
    
    Example:
        @require_admin
        async def sensitive_operation(db: AsyncSession, user: User):
            # Only admins can execute this
            ...
    """
    # Check if function is async
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            user = kwargs.get('user')
            if not user and len(args) > 1:
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                        break
            
            if not user:
                logger.warning(
                    "error.permission",
                    language=LANG,
                    username="unknown",
                    action="admin-only operation (no user provided)"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This operation requires administrator privileges"
                )
            
            if not user.is_admin():
                logger.warning(
                    "error.permission",
                    language=LANG,
                    username=user.username,
                    action="admin-only operation"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This operation requires administrator privileges"
                )
            
            return await func(*args, **kwargs)
        
        return async_wrapper
    
    else:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            user = kwargs.get('user')
            if not user and len(args) > 1:
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                        break
            
            if not user or not user.is_admin():
                logger.warning(
                    "error.permission",
                    language=LANG,
                    username=user.username if user else "unknown",
                    action="admin-only operation"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This operation requires administrator privileges"
                )
            
            return func(*args, **kwargs)
        
        return sync_wrapper


# === Usage Examples ===

"""
# Example 1: Using in a service function
from core.permissions import require_read

class OrderService:
    @staticmethod
    @require_read('orders')
    async def get_all_orders(db: AsyncSession, user: User):
        # Permission checked automatically
        result = await db.execute(select(Order))
        return result.scalars().all()

# Example 2: Using admin decorator
from core.permissions import require_admin

class StaffShiftService:
    @staticmethod
    @require_admin
    async def get_payroll_data(db: AsyncSession, user: User):
        # Only admins can access this
        ...

# Example 3: Manual permission check
from core.permissions import ModelPermissions

async def some_function(user: User):
    if ModelPermissions.check_permission(user, 'staff_shifts', 'read'):
        # User has permission
        ...
    else:
        # User does not have permission
        raise HTTPException(403, "Access denied")

# Example 4: Using in an endpoint (usually you'd use dependency injection instead)
@router.get("/orders")
@require_read('orders')
async def get_orders(
    db: DbDependency,
    user: CurrentUser  # User is passed and checked by decorator
):
    result = await db.execute(select(Order))
    return result.scalars().all()
"""
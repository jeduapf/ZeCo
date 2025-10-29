"""
Shared dependencies across the application
"""
from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from database.session import get_db
from database.models.user import User
from core.security import get_current_user, get_current_admin_user

# Type hints for common dependencies
DbDependency = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_current_admin_user)]
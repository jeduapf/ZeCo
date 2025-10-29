"""
Authentication endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from core.dependencies import DbDependency, CurrentUser, AdminUser
from core.security import verify_password, create_access_token, get_password_hash
from database.models.user import User, UserRole
from schemas.user import UserResponse, UserRoleUpdate, Token

router = APIRouter(tags=["Authentication"])

@router.post("/token", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDependency
):
    """Login endpoint to get JWT token"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDependency
):
    """Register a new user"""
    if db.query(User).filter(User.username == form_data.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(form_data.password)
    user_count = db.query(User).count()
    role = UserRole.ADMIN if user_count < 1 else UserRole.CLIENT
    
    new_user = User(
        username=form_data.username,
        hashed_password=hashed_password,
        role=role
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
    response: Response
):
    """Get current user information"""
    return current_user

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: CurrentUser):
    """Refresh access token"""
    new_token = create_access_token(data={"sub": current_user.username})
    return {"access_token": new_token, "token_type": "bearer"}
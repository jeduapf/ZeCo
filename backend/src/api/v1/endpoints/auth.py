"""
Authentication endpoints
"""
from fastapi import APIRouter, HTTPException, status, Depends, Response, Body
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from sqlalchemy import select
from src.core.dependencies import DbDependency, CurrentUser, AdminUser
from src.core.security import verify_password, create_access_token, get_password_hash
from src.database.models.user import User, UserRole
from src.schemas.user import UserResponse, UserRegister, Token, UserRegisterResponse, UserBase, GenderEnum

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

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserRegisterResponse)
async def register(
    db: DbDependency,
    form_data: Annotated[UserRegister, Body(...)]
):
    """Register a new user"""

    # Check if username exists
    result = await db.execute(select(User).where(User.username == form_data.username))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Check if email exists
    result = await db.execute(select(User).where(User.email == form_data.email))
    existing_email = result.scalar_one_or_none()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(form_data.password)

    # Count users to determine role
    result = await db.execute(select(User))
    user_count = len(result.scalars().all())
    role = UserRole.ADMIN if user_count < 1 else UserRole.CLIENT
    
    new_user = User(
        username=form_data.username,
        hashed_password=hashed_password,
        role=role,
        email=form_data.email,
        age=form_data.age,
        gender= True if form_data.gender == GenderEnum.MALE.value else False if form_data.gender == GenderEnum.FEMALE.value else None
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# @router.get("/me", response_model=UserResponse)
# async def get_current_user_info(
#     current_user: CurrentUser,
# ):
#     """Get current user information"""
#     return current_user

# @router.post("/refresh", response_model=Token)
# async def refresh_token(current_user: CurrentUser):
#     """Refresh access token"""
#     new_token = create_access_token(data={"sub": current_user.username})
#     return {"access_token": new_token, "token_type": "bearer"}
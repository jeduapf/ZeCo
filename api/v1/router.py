"""
API v1 router - combines all v1 endpoints
"""
from fastapi import APIRouter
from api.v1.endpoints import auth, users, products

# Create main v1 router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(users.router, prefix="/users")
api_router.include_router(products.router, prefix="/products")

# You can add more routers here as you build new features:
# api_router.include_router(orders.router, prefix="/orders")
# api_router.include_router(categories.router, prefix="/categories")
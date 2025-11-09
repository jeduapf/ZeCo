"""
Product management endpoints
"""
from fastapi import APIRouter, Query, status, Response
from src.core.dependencies import DbDependency, CurrentUser, AdminUser

router = APIRouter(tags=["Products"])

# @router.post("/", status_code=status.HTTP_201_CREATED, response_model=ProductResponse)
# async def create_product(
#     product: ProductCreate,
#     current_user: CurrentUser,
#     admin: AdminUser,
#     db: DbDependency
# ):
#     """Create a new product (authenticated users)"""
#     return ProductService.create_product(db, product, current_user)

# @router.get("/", response_model=ProductListResponse)
# async def get_products(
#     db: DbDependency,
#     page: int = Query(1, ge=1),
#     page_size: int = Query(10, ge=1, le=100),
#     active_only: bool = Query(True)
# ):
#     """Get all products with pagination (public endpoint)"""
#     skip = (page - 1) * page_size
#     products, total = ProductService.get_products(db, skip, page_size, active_only)
    
#     return {
#         "products": products,
#         "total": total,
#         "page": page,
#         "page_size": page_size
#     }

# @router.get("/{product_id}", response_model=ProductResponse)
# async def get_product(product_id: int, db: DbDependency):
#     """Get a specific product by ID (public endpoint)"""
#     return ProductService.get_product(db, product_id)

# @router.put("/{product_id}", response_model=ProductResponse)
# async def update_product(
#     product_id: int,
#     product: ProductUpdate,
#     current_user: CurrentUser,
#     admin: AdminUser,
#     db: DbDependency
# ):
#     """Update a product (authenticated users)"""
#     return ProductService.update_product(db, product_id, product, current_user)

# @router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_product(
#     product_id: int,
#     current_user: CurrentUser,
#     admin: AdminUser,
#     db: DbDependency
# ):
#     """Soft delete a product (authenticated users)"""
#     ProductService.delete_product(db, product_id, current_user)

# @router.delete("/{product_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
# async def hard_delete_product(
#     product_id: int,
#     admin: AdminUser,
#     db: DbDependency
# ):
#     """Permanently delete a product (admin only)"""
#     ProductService.hard_delete_product(db, product_id, admin)
"""
Product business logic service
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from database.models.product import Product
from database.models.user import User
from schemas.product import ProductCreate, ProductUpdate

class ProductService:
    """Service for product business logic"""
    
    @staticmethod
    def create_product(db: Session, product_data: ProductCreate, user: User) -> Product:
        """Create a new product"""
        new_product = Product(
            name=product_data.name,
            description=product_data.description,
            price=product_data.price,
            stock=product_data.stock,
            is_active=product_data.is_active,
            created_by=user.id
        )
        db.add(new_product)
        db.commit()
        db.refresh(new_product)
        return new_product
    
    @staticmethod
    def get_product(db: Session, product_id: int) -> Product:
        """Get a product by ID"""
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        return product
    
    @staticmethod
    def get_products(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False
    ) -> tuple[list[Product], int]:
        """Get all products with pagination"""
        query = db.query(Product)
        
        if active_only:
            query = query.filter(Product.is_active == True)
        
        total = query.count()
        products = query.offset(skip).limit(limit).all()
        
        return products, total
    
    @staticmethod
    def update_product(
        db: Session,
        product_id: int,
        product_data: ProductUpdate,
        user: User
    ) -> Product:
        """Update a product"""
        product = ProductService.get_product(db, product_id)
        
        # Update only provided fields
        update_data = product_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        
        db.commit()
        db.refresh(product)
        return product
    
    @staticmethod
    def delete_product(db: Session, product_id: int, user: User) -> None:
        """Delete a product (soft delete by setting is_active=False)"""
        product = ProductService.get_product(db, product_id)
        product.is_active = False
        db.commit()
    
    @staticmethod
    def hard_delete_product(db: Session, product_id: int, user: User) -> None:
        """Permanently delete a product (admin only)"""
        product = ProductService.get_product(db, product_id)
        db.delete(product)
        db.commit()
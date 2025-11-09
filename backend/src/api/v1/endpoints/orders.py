"""
Order management endpoints with async support and WebSocket notifications
"""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime, timezone

from src.core.dependencies import get_current_user, get_db, DbDependency, StaffUser, CurrentUser
from src.database.models.user import User, UserRole
from src.database.models.order import Order, OrderStatus, PaymentMethod
from src.database.models.order_item import OrderItem
from src.database.models.menu_item import MenuItem
from src.database.models.table import Table
from src.schemas.order import (
    OrderCreate, OrderResponse, OrderDetailedResponse, OrderListResponse,
    OrderAddItems, OrderUpdateStatus, OrderPayment, KitchenDashboard,
    WaiterDashboard, OrderStatusUpdate
)
from src.core.websocket_manager import (
    notify_order_created, notify_order_ready, notify_table_status_change
)

# Import necessary for the count query
from sqlalchemy import func
from src.core.websocket_manager import manager

router = APIRouter(tags=["Orders"])


# # === Customer/Client Endpoints ===

# @router.post("/", status_code=status.HTTP_201_CREATED, response_model=OrderDetailedResponse)
# async def create_order(
#     order_data: OrderCreate,
#     current_user: CurrentUser,
#     db: DbDependency
# ):
#     """
#     Create a new order.
    
#     Process:
#     1. Validate table exists and user is seated there (or is staff)
#     2. Validate all menu items exist and are available
#     3. Create order with PENDING status
#     4. Add order items with price snapshot
#     5. Calculate total
#     6. Notify kitchen and waiters via WebSocket
    
#     Permissions: Any authenticated user
#     """
#     # Verify table exists
#     table_result = await db.execute(
#         select(Table).where(Table.id == order_data.table_id)
#     )
#     table = table_result.scalar_one_or_none()
    
#     if not table:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Table {order_data.table_id} not found"
#         )
    
#     # Verify user is seated at this table (or is staff who can order for any table)
#     if current_user.role == UserRole.CLIENT and current_user.table_id != order_data.table_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You can only create orders for your assigned table"
#         )
    
#     # Validate all menu items exist and are available
#     menu_item_ids = [item.menu_item_id for item in order_data.items]
#     menu_items_result = await db.execute(
#         select(MenuItem).where(MenuItem.id.in_(menu_item_ids))
#     )
#     menu_items = {item.id: item for item in menu_items_result.scalars().all()}
    
#     # Check availability
#     unavailable_items = []
#     for item_data in order_data.items:
#         menu_item = menu_items.get(item_data.menu_item_id)
#         if not menu_item:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Menu item {item_data.menu_item_id} not found"
#             )
        
#         if not menu_item.is_available_for_order(item_data.quantity):
#             unavailable_items.append(menu_item.name)
    
#     if unavailable_items:
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail=f"Items not available: {', '.join(unavailable_items)}"
#         )
    
#     # Create the order
#     new_order = Order(
#         user_id=current_user.id,
#         table_id=order_data.table_id,
#         status=OrderStatus.PENDING,
#         specifications=order_data.specifications,
#         num_customers=order_data.num_customers,
#         promo_code=order_data.promo_code,
#         created_at=datetime.now(timezone.utc)
#     )
    
#     db.add(new_order)
#     await db.flush()  # Get order ID
    
#     # Add order items with price snapshot
#     total_amount = 0.0
#     for item_data in order_data.items:
#         menu_item = menu_items[item_data.menu_item_id]
        
#         order_item = OrderItem(
#             order_id=new_order.id,
#             item_id=menu_item.id,
#             quantity=item_data.quantity,
#             item_price=menu_item.price,  # Snapshot current price
#             item_cost=menu_item.calculate_base_cost()  # Snapshot current cost
#         )
        
#         db.add(order_item)
#         total_amount += order_item.subtotal
        
#         # Deduct ingredients from stock
#         menu_item.deduct_ingredients_for_order(
#             quantity=item_data.quantity,
#             user_id=current_user.id,
#             db_session=db
#         )
    
#     # Set total amount
#     new_order.total_amount = total_amount
    
#     await db.commit()
#     await db.refresh(new_order)
    
#     # Prepare response
#     order_items_result = await db.execute(
#         select(OrderItem).where(OrderItem.order_id == new_order.id)
#     )
#     order_items = order_items_result.scalars().all()
    
#     response_data = {
#         **OrderResponse.model_validate(new_order).model_dump(),
#         "items": [
#             {
#                 "menu_item_id": oi.item_id,
#                 "menu_item_name": menu_items[oi.item_id].name,
#                 "quantity": oi.quantity,
#                 "item_price": oi.item_price,
#                 "item_cost": oi.item_cost,
#                 "subtotal": oi.subtotal,
#                 "profit": oi.profit
#             }
#             for oi in order_items
#         ],
#         "per_person_cost": new_order.calculate_per_person_cost(),
#         "subtotal": total_amount
#     }
    
#     # Notify kitchen and waiters via WebSocket
#     await notify_order_created({
#         "order_id": new_order.id,
#         "table_id": new_order.table_id,
#         "table_number": table.number,
#         "status": new_order.status.value,
#         "item_count": len(order_items),
#         "total_amount": new_order.total_amount
#     })
    
#     return response_data


# @router.get("/{order_id}", response_model=OrderDetailedResponse)
# async def get_order(
#     order_id: int,
#     current_user: CurrentUser,
#     db: DbDependency
# ):
#     """
#     Get details of a specific order.
    
#     Permissions:
#     - Clients can only view their own orders
#     - Staff can view any order
#     """
#     result = await db.execute(
#         select(Order).where(Order.id == order_id)
#     )
#     order = result.scalar_one_or_none()
    
#     if not order:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Order {order_id} not found"
#         )
    
#     # Permission check
#     if current_user.role == UserRole.CLIENT and order.user_id != current_user.id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You can only view your own orders"
#         )
    
#     # Get order items
#     items_result = await db.execute(
#         select(OrderItem, MenuItem)
#         .join(MenuItem, OrderItem.item_id == MenuItem.id)
#         .where(OrderItem.order_id == order_id)
#     )
#     items_data = items_result.all()
    
#     return {
#         **OrderResponse.model_validate(order).model_dump(),
#         "items": [
#             {
#                 "menu_item_id": oi.item_id,
#                 "menu_item_name": mi.name,
#                 "quantity": oi.quantity,
#                 "item_price": oi.item_price,
#                 "item_cost": oi.item_cost,
#                 "subtotal": oi.subtotal,
#                 "profit": oi.profit
#             }
#             for oi, mi in items_data
#         ],
#         "per_person_cost": order.calculate_per_person_cost(),
#         "subtotal": order.total_amount + order.discount_applied,
#         "time_since_created": int((datetime.now(timezone.utc) - order.created_at).total_seconds() / 60)
#     }


# @router.get("/", response_model=OrderListResponse)
# async def list_orders(
#     db: DbDependency,
#     current_user: CurrentUser,
#     status_filter: Optional[OrderStatus] = None,
#     table_id: Optional[int] = None,
#     page: int = Query(1, ge=1),
#     page_size: int = Query(20, ge=1, le=100)
# ):
#     """
#     List orders with filtering and pagination.
    
#     Permissions:
#     - Clients see only their orders
#     - Staff see all orders
    
#     Filters:
#     - status: Filter by order status
#     - table_id: Filter by table
#     """
#     # Build query
#     query = select(Order)
    
#     # Permission-based filtering
#     if current_user.role == UserRole.CLIENT:
#         query = query.where(Order.user_id == current_user.id)
    
#     # Apply filters
#     if status_filter:
#         query = query.where(Order.status == status_filter)
    
#     if table_id:
#         query = query.where(Order.table_id == table_id)
    
#     # Get total count
#     count_result = await db.execute(
#         select(func.count()).select_from(query.subquery())
#     )
#     total = count_result.scalar()
    
#     # Apply pagination
#     query = query.order_by(Order.created_at.desc())
#     query = query.offset((page - 1) * page_size).limit(page_size)
    
#     # Execute query
#     result = await db.execute(query)
#     orders = result.scalars().all()
    
#     return {
#         "orders": [OrderResponse.model_validate(o) for o in orders],
#         "total": total,
#         "page": page,
#         "page_size": page_size,
#         "status_filter": status_filter
#     }


# # === Kitchen Endpoints ===

# @router.patch("/{order_id}/status", response_model=OrderResponse)
# async def update_order_status(
#     order_id: int,
#     status_update: OrderUpdateStatus,
#     current_user: StaffUser,
#     db: DbDependency
# ):
#     """
#     Update order status (kitchen/waiter workflow).
    
#     Typical workflow:
#     - Kitchen: PENDING → CONFIRMED → PREPARING → READY
#     - Waiter: READY → SERVED → COMPLETED
    
#     Permissions: KITCHEN, WAITER, ADMIN
#     """
#     # Permission check
#     if current_user.role not in (UserRole.KITCHEN, UserRole.WAITER, UserRole.ADMIN):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Only kitchen staff and waiters can update order status"
#         )
    
#     # Get order
#     result = await db.execute(
#         select(Order).where(Order.id == order_id)
#     )
#     order = result.scalar_one_or_none()
    
#     if not order:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Order {order_id} not found"
#         )
    
#     # Validate status transition
#     old_status = order.status
#     new_status = status_update.new_status
    
#     # Basic validation (you might want more complex state machine logic)
#     if old_status == OrderStatus.COMPLETED:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Cannot modify completed orders"
#         )
    
#     if old_status == OrderStatus.CANCELLED:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Cannot modify cancelled orders"
#         )
    
#     # Update status
#     order.status = new_status
    
#     # Set finished_at if completed
#     if new_status == OrderStatus.COMPLETED:
#         order.finished_at = datetime.now(timezone.utc)
    
#     await db.commit()
#     await db.refresh(order)
    
#     # Get table info for notification
#     table_result = await db.execute(
#         select(Table).where(Table.id == order.table_id)
#     )
#     table = table_result.scalar_one()
    
#     # Notify via WebSocket
#     if new_status == OrderStatus.READY:
#         await notify_order_ready({
#             "order_id": order.id,
#             "table_id": order.table_id,
#             "table_number": table.number,
#             "status": new_status.value
#         })
    
#     # Broadcast status change
#     await manager.broadcast_to_roles(
#         {
#             "type": "order_status_changed",
#             "data": {
#                 "order_id": order.id,
#                 "table_number": table.number,
#                 "old_status": old_status.value,
#                 "new_status": new_status.value,
#                 "updated_by": current_user.username
#             },
#             "timestamp": datetime.now(timezone.utc).isoformat()
#         },
#         [UserRole.KITCHEN, UserRole.WAITER, UserRole.ADMIN]
#     )
    
#     return OrderResponse.model_validate(order)


# @router.get("/kitchen/dashboard", response_model=KitchenDashboard)
# async def get_kitchen_dashboard(
#     current_user: StaffUser,
#     db: DbDependency
# ):
#     """
#     Get kitchen dashboard with all active orders organized by status.
    
#     Shows:
#     - Pending orders (need to start)
#     - Preparing orders (currently working on)
#     - Ready orders (waiting to be served)
    
#     Permissions: KITCHEN, ADMIN
#     """
#     if current_user.role not in (UserRole.KITCHEN, UserRole.ADMIN):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Kitchen dashboard is for kitchen staff only"
#         )
    
#     # Get all active orders
#     result = await db.execute(
#         select(Order, Table)
#         .join(Table, Order.table_id == Table.id)
#         .where(Order.status.in_([
#             OrderStatus.PENDING,
#             OrderStatus.CONFIRMED,
#             OrderStatus.PREPARING,
#             OrderStatus.READY
#         ]))
#         .order_by(Order.created_at)
#     )
#     orders_data = result.all()
    
#     # Organize by status
#     pending = []
#     preparing = []
#     ready = []
    
#     for order, table in orders_data:
#         # Get order items
#         items_result = await db.execute(
#             select(OrderItem, MenuItem)
#             .join(MenuItem, OrderItem.item_id == MenuItem.id)
#             .where(OrderItem.order_id == order.id)
#         )
#         items = items_result.all()
        
#         kitchen_order = {
#             "order_id": order.id,
#             "table_number": table.number,
#             "items": [
#                 {
#                     "name": mi.name,
#                     "quantity": oi.quantity,
#                     "special_instructions": None,  # Add if you store this
#                     "category": mi.category.value
#                 }
#                 for oi, mi in items
#             ],
#             "status": order.status,
#             "created_at": order.created_at,
#             "time_elapsed_minutes": int((datetime.now(timezone.utc) - order.created_at).total_seconds() / 60),
#             "priority": "urgent" if (datetime.now(timezone.utc) - order.created_at).total_seconds() > 900 else "normal",
#             "specifications": order.specifications
#         }
        
#         if order.status in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
#             pending.append(kitchen_order)
#         elif order.status == OrderStatus.PREPARING:
#             preparing.append(kitchen_order)
#         elif order.status == OrderStatus.READY:
#             ready.append(kitchen_order)
    
#     # Calculate average prep time (simplified)
#     avg_prep_time = sum(o["time_elapsed_minutes"] for o in preparing) / len(preparing) if preparing else 0.0
    
#     # Find longest waiting order
#     all_orders = pending + preparing
#     longest_waiting = max(all_orders, key=lambda x: x["time_elapsed_minutes"]) if all_orders else None
    
#     return {
#         "pending_orders": pending,
#         "preparing_orders": preparing,
#         "ready_orders": ready,
#         "total_pending": len(pending),
#         "total_preparing": len(preparing),
#         "average_prep_time": avg_prep_time,
#         "longest_waiting": longest_waiting
#     }



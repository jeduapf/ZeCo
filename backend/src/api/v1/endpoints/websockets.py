"""
WebSocket endpoints for real-time updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from core.websocket_manager import manager
from core.dependencies import get_db
from database.models.user import User
from config import SECRET_KEY, ALGORITHM

router = APIRouter(tags=["WebSocket"])
security = HTTPBearer()
logger = logging.getLogger(__name__)


async def get_user_from_token(token: str, db: AsyncSession) -> User:
    """
    Authenticate user from JWT token for WebSocket connection.
    
    Args:
        token: JWT access token
        db: Database session
        
    Returns:
        Authenticated User object
        
    Raises:
        Exception if authentication fails
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        
        if username is None:
            raise Exception("Invalid token: no username")
        
        # Get user from database
        result = await db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            raise Exception("User not found")
        
        return user
        
    except JWTError:
        raise Exception("Invalid token")


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token for authentication"),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time updates.
    
    Connection URL: ws://localhost:8000/api/v1/ws?token=YOUR_JWT_TOKEN
    
    After connecting, clients receive updates based on their role:
    - KITCHEN: New orders, order status changes
    - WAITER: Order ready notifications, table status changes
    - ADMIN: All updates
    - CLIENT: Updates about their own orders
    
    Message format (from server to client):
    {
        "type": "order_created" | "order_status_changed" | "table_status_changed" | ...,
        "data": { ... specific data for the event ... },
        "timestamp": "2024-11-09T12:34:56Z"
    }
    
    Clients can also send messages (client to server):
    {
        "action": "ping" | "subscribe" | "unsubscribe",
        "data": { ... }
    }
    """
    user = None
    
    try:
        # Authenticate user
        user = await get_user_from_token(token, db)
        
        # Connect to WebSocket manager
        await manager.connect(
            websocket=websocket,
            user_id=user.id,
            user_role=user.role,
            username=user.username
        )
        
        logger.info(f"WebSocket connection established for user {user.username}")
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_json()
                
                # Handle different client actions
                action = data.get("action")
                
                if action == "ping":
                    # Respond to ping with pong
                    await manager.send_personal_message(
                        {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        websocket
                    )
                
                elif action == "get_stats":
                    # Send connection statistics (admin only)
                    if user.is_admin():
                        stats = manager.get_connection_stats()
                        await manager.send_personal_message(
                            {
                                "type": "stats",
                                "data": stats,
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            websocket
                        )
                
                elif action == "get_connected_users":
                    # Get list of connected users (admin only)
                    if user.is_admin():
                        users = manager.get_connected_users()
                        await manager.send_personal_message(
                            {
                                "type": "connected_users",
                                "data": {"users": users},
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            websocket
                        )
                
                else:
                    # Unknown action
                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "message": f"Unknown action: {action}",
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        websocket
                    )
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user.username}")
                break
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Error processing your request",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    websocket
                )
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        # Try to send error message before closing
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Authentication failed or connection error",
                "timestamp": datetime.utcnow().isoformat()
            })
        except:
            pass
        
        # Close connection if not already closed
        try:
            await websocket.close()
        except:
            pass
    
    finally:
        # Clean up connection
        if user:
            manager.disconnect(websocket)


from datetime import datetime
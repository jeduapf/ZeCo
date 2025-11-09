"""
WebSocket Connection Manager for Real-Time Updates
Handles connections from waiters, kitchen staff, and admin dashboards
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set, Optional
from src.database.models.user import UserRole
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections organized by role and user.
    
    This allows targeted broadcasting:
    - Send kitchen orders only to kitchen staff
    - Send table updates only to waiters
    - Send all updates to admins
    
    Architecture:
    - connections: all active websocket connections
    - connections_by_role: connections grouped by user role
    - connections_by_user: connections for specific users
    """
    
    def __init__(self):
        # All active connections
        self.active_connections: List[WebSocket] = []
        
        # Connections grouped by role
        self.connections_by_role: Dict[UserRole, Set[WebSocket]] = {
            UserRole.ADMIN: set(),
            UserRole.WAITER: set(),
            UserRole.KITCHEN: set(),
            UserRole.CLIENT: set()
        }
        
        # Connections mapped to specific users
        self.connections_by_user: Dict[int, Set[WebSocket]] = {}
        
        # Connection metadata (store user info per connection)
        self.connection_metadata: Dict[WebSocket, dict] = {}
    
    async def connect(
        self, 
        websocket: WebSocket, 
        user_id: int, 
        user_role: UserRole,
        username: str
    ):
        """
        Accept a new WebSocket connection and register it.
        
        Args:
            websocket: The WebSocket connection
            user_id: User's ID
            user_role: User's role (determines what updates they receive)
            username: User's username (for logging)
        """
        await websocket.accept()
        
        # Add to active connections
        self.active_connections.append(websocket)
        
        # Add to role-based group
        self.connections_by_role[user_role].add(websocket)
        
        # Add to user-specific set
        if user_id not in self.connections_by_user:
            self.connections_by_user[user_id] = set()
        self.connections_by_user[user_id].add(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            'user_id': user_id,
            'username': username,
            'role': user_role,
            'connected_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(
            f"WebSocket connected: user_id={user_id}, username={username}, "
            f"role={user_role.value}, total_connections={len(self.active_connections)}"
        )
        
        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection_established",
                "message": f"Welcome {username}! You're connected to real-time updates.",
                "role": user_role.value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            websocket
        )
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection when client disconnects.
        
        Args:
            websocket: The WebSocket connection to remove
        """
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            user_id = metadata['user_id']
            user_role = metadata['role']
            username = metadata['username']
            
            # Remove from all tracking structures
            self.active_connections.remove(websocket)
            self.connections_by_role[user_role].discard(websocket)
            
            if user_id in self.connections_by_user:
                self.connections_by_user[user_id].discard(websocket)
                if not self.connections_by_user[user_id]:
                    del self.connections_by_user[user_id]
            
            del self.connection_metadata[websocket]
            
            logger.info(
                f"WebSocket disconnected: user_id={user_id}, username={username}, "
                f"remaining_connections={len(self.active_connections)}"
            )
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific connection.
        
        Args:
            message: Dictionary to send (will be JSON encoded)
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def send_to_user(self, message: dict, user_id: int):
        """
        Send a message to all connections of a specific user.
        
        Useful when a user is connected from multiple devices.
        
        Args:
            message: Dictionary to send
            user_id: Target user ID
        """
        if user_id in self.connections_by_user:
            disconnected = []
            for connection in self.connections_by_user[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")
                    disconnected.append(connection)
            
            # Clean up failed connections
            for conn in disconnected:
                self.disconnect(conn)
    
    async def broadcast_to_role(self, message: dict, role: UserRole):
        """
        Send a message to all connections with a specific role.
        
        Examples:
        - Broadcast new order to all KITCHEN staff
        - Broadcast table assignment to all WAITERS
        - Broadcast system alert to all ADMINS
        
        Args:
            message: Dictionary to send
            role: Target role
        """
        disconnected = []
        connections = self.connections_by_role.get(role, set())
        
        logger.debug(f"Broadcasting to role {role.value}: {len(connections)} connections")
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {role.value}: {e}")
                disconnected.append(connection)
        
        # Clean up failed connections
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_to_roles(self, message: dict, roles: List[UserRole]):
        """
        Send a message to multiple roles at once.
        
        Example: Broadcast order update to both KITCHEN and WAITER
        
        Args:
            message: Dictionary to send
            roles: List of target roles
        """
        for role in roles:
            await self.broadcast_to_role(message, role)
    
    async def broadcast_to_all(self, message: dict):
        """
        Send a message to all connected clients.
        
        Use sparingly! Usually you want targeted broadcasts.
        
        Args:
            message: Dictionary to send
        """
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to all: {e}")
                disconnected.append(connection)
        
        # Clean up failed connections
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_to_admins(self, message: dict):
        """Convenience method to broadcast to admins only"""
        await self.broadcast_to_role(message, UserRole.ADMIN)
    
    async def broadcast_to_kitchen(self, message: dict):
        """Convenience method to broadcast to kitchen only"""
        await self.broadcast_to_role(message, UserRole.KITCHEN)
    
    async def broadcast_to_waiters(self, message: dict):
        """Convenience method to broadcast to waiters only"""
        await self.broadcast_to_role(message, UserRole.WAITER)
    
    def get_connection_stats(self) -> dict:
        """
        Get statistics about current connections.
        
        Useful for admin dashboard.
        
        Returns:
            Dictionary with connection statistics
        """
        return {
            'total_connections': len(self.active_connections),
            'connections_by_role': {
                role.value: len(connections)
                for role, connections in self.connections_by_role.items()
            },
            'unique_users': len(self.connections_by_user),
            'average_connections_per_user': (
                len(self.active_connections) / len(self.connections_by_user)
                if self.connections_by_user else 0
            )
        }
    
    def get_connected_users(self, role: Optional[UserRole] = None) -> List[dict]:
        """
        Get list of currently connected users.
        
        Args:
            role: Filter by role (None = all users)
            
        Returns:
            List of user info dictionaries
        """
        users = []
        seen_users = set()
        
        for conn, metadata in self.connection_metadata.items():
            user_id = metadata['user_id']
            
            # Skip if we've already added this user
            if user_id in seen_users:
                continue
            
            # Skip if role filter doesn't match
            if role and metadata['role'] != role:
                continue
            
            users.append({
                'user_id': user_id,
                'username': metadata['username'],
                'role': metadata['role'].value,
                'connected_at': metadata['connected_at'],
                'connection_count': len(self.connections_by_user.get(user_id, []))
            })
            
            seen_users.add(user_id)
        
        return users


# Global connection manager instance
manager = ConnectionManager()


# Helper functions for common broadcast patterns

async def notify_order_created(order_data: dict):
    """Notify kitchen and waiters about new order"""
    message = {
        "type": "order_created",
        "data": order_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await manager.broadcast_to_roles(
        message,
        [UserRole.KITCHEN, UserRole.WAITER, UserRole.ADMIN]
    )


async def notify_order_ready(order_data: dict):
    """Notify waiters when order is ready to serve"""
    message = {
        "type": "order_ready",
        "data": order_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await manager.broadcast_to_roles(
        message,
        [UserRole.WAITER, UserRole.ADMIN]
    )


async def notify_table_status_change(table_data: dict):
    """Notify waiters about table status changes"""
    message = {
        "type": "table_status_changed",
        "data": table_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await manager.broadcast_to_roles(
        message,
        [UserRole.WAITER, UserRole.ADMIN]
    )


async def notify_inventory_alert(alert_data: dict):
    """Notify kitchen and admins about inventory issues"""
    message = {
        "type": "inventory_alert",
        "data": alert_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await manager.broadcast_to_roles(
        message,
        [UserRole.KITCHEN, UserRole.ADMIN]
    )


async def notify_user_action(user_id: int, action_data: dict):
    """Notify specific user about action result"""
    message = {
        "type": "action_result",
        "data": action_data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await manager.send_to_user(message, user_id)
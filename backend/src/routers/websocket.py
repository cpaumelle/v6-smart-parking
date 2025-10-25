# src/routers/websocket.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from typing import Dict, Set, Optional
import json
import logging
import os
from datetime import datetime
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

router = APIRouter()

# Connection manager to handle WebSocket connections
class ConnectionManager:
    def __init__(self):
        # tenant_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> {tenant_id, user_id, channels}
        self.connection_info: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str, user_id: str):
        """Accept and store WebSocket connection"""
        await websocket.accept()

        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = set()

        self.active_connections[tenant_id].add(websocket)
        self.connection_info[websocket] = {
            'tenant_id': tenant_id,
            'user_id': user_id,
            'channels': set(),
            'connected_at': datetime.utcnow()
        }

        logger.info(f"WebSocket connected: user={user_id}, tenant={tenant_id}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.connection_info:
            info = self.connection_info[websocket]
            tenant_id = info['tenant_id']

            if tenant_id in self.active_connections:
                self.active_connections[tenant_id].discard(websocket)
                if not self.active_connections[tenant_id]:
                    del self.active_connections[tenant_id]

            logger.info(f"WebSocket disconnected: user={info['user_id']}, tenant={tenant_id}")
            del self.connection_info[websocket]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message to websocket: {e}")

    async def broadcast_to_tenant(self, message: dict, tenant_id: str, channel: Optional[str] = None):
        """Broadcast message to all connections in a tenant"""
        if tenant_id not in self.active_connections:
            return

        disconnected = []
        for websocket in self.active_connections[tenant_id]:
            # If channel specified, check if connection is subscribed
            if channel and websocket in self.connection_info:
                if channel not in self.connection_info[websocket]['channels']:
                    continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to websocket: {e}")
                disconnected.append(websocket)

        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast_to_all(self, message: dict, channel: Optional[str] = None):
        """Broadcast message to all connected clients"""
        for tenant_id in list(self.active_connections.keys()):
            await self.broadcast_to_tenant(message, tenant_id, channel)

    def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe connection to a channel"""
        if websocket in self.connection_info:
            self.connection_info[websocket]['channels'].add(channel)
            logger.info(f"WebSocket subscribed to channel: {channel}")

    def unsubscribe(self, websocket: WebSocket, channel: str):
        """Unsubscribe connection from a channel"""
        if websocket in self.connection_info:
            self.connection_info[websocket]['channels'].discard(channel)
            logger.info(f"WebSocket unsubscribed from channel: {channel}")

# Global connection manager instance
manager = ConnectionManager()


def verify_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        # Get JWT configuration from environment (same as in security.py)
        JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token")
):
    """
    WebSocket endpoint for real-time updates

    Authentication via query parameter: /ws?token=<jwt_token>

    Message format:
    {
        "type": "subscribe" | "unsubscribe" | "ping",
        "channel": "spaces" | "devices" | "alerts" | "metrics",
        "data": {...}
    }
    """

    # Verify authentication
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")

        if not user_id or not tenant_id:
            await websocket.close(code=1008, reason="Invalid token payload")
            return

    except HTTPException:
        await websocket.close(code=1008, reason="Authentication failed")
        return

    # Connect
    await manager.connect(websocket, tenant_id, user_id)

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established",
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Listen for messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                message_type = message.get("type")
                channel = message.get("channel")

                # Handle different message types
                if message_type == "subscribe" and channel:
                    manager.subscribe(websocket, channel)
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": channel,
                        "message": f"Subscribed to {channel}"
                    })

                elif message_type == "unsubscribe" and channel:
                    manager.unsubscribe(websocket, channel)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "channel": channel,
                        "message": f"Unsubscribed from {channel}"
                    })

                elif message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON message"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Helper function to broadcast updates from other parts of the application
async def broadcast_space_update(tenant_id: str, space_data: dict):
    """Broadcast space status update to all subscribers"""
    await manager.broadcast_to_tenant(
        {
            "type": "space:update",
            "channel": "spaces",
            "data": space_data,
            "timestamp": datetime.utcnow().isoformat()
        },
        tenant_id,
        channel="spaces"
    )


async def broadcast_device_status(tenant_id: str, device_data: dict):
    """Broadcast device status update to all subscribers"""
    await manager.broadcast_to_tenant(
        {
            "type": "device:status",
            "channel": "devices",
            "data": device_data,
            "timestamp": datetime.utcnow().isoformat()
        },
        tenant_id,
        channel="devices"
    )


async def broadcast_alert(tenant_id: str, alert_data: dict):
    """Broadcast alert to all subscribers"""
    await manager.broadcast_to_tenant(
        {
            "type": "alert",
            "channel": "alerts",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        },
        tenant_id,
        channel="alerts"
    )


async def broadcast_metrics(tenant_id: str, metrics_data: dict):
    """Broadcast metrics update to all subscribers"""
    await manager.broadcast_to_tenant(
        {
            "type": "metrics",
            "channel": "metrics",
            "data": metrics_data,
            "timestamp": datetime.utcnow().isoformat()
        },
        tenant_id,
        channel="metrics"
    )

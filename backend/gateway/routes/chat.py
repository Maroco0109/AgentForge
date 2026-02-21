"""WebSocket chat endpoint with role-based limits."""

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException, status

from backend.gateway.auth import decode_token
from backend.gateway.rate_limiter import (
    get_redis,
    ws_release_connection,
    ws_track_connection,
)
from backend.gateway.rbac import get_permission, is_unlimited
from backend.shared.models import UserRole

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: str, client_id: str) -> None:
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected clients."""
        for connection in list(self.active_connections.values()):
            await connection.send_text(message)


# Global connection manager
manager = ConnectionManager()


def _authenticate_ws(websocket: WebSocket) -> tuple[str, UserRole]:
    """Authenticate a WebSocket connection via query parameter token.

    Args:
        websocket: The WebSocket connection.

    Returns:
        Tuple of (user_id, role).

    Raises:
        WebSocketException: If authentication fails.
    """
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing authentication token",
        )

    try:
        payload = decode_token(token)
    except Exception:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired token",
        )

    if payload.get("type") != "access":
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid token type",
        )

    user_id = payload.get("sub")
    role_str = payload.get("role", "free")

    try:
        role = UserRole(role_str)
    except ValueError:
        role = UserRole.FREE

    return user_id, role


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_endpoint(websocket: WebSocket, conversation_id: uuid.UUID) -> None:
    """WebSocket endpoint for chat conversations.

    Authentication: Pass JWT token as query parameter `?token=<access_token>`.
    Enforces per-role message size limits and connection count limits.
    """
    # Authenticate
    user_id, role = _authenticate_ws(websocket)

    # Check connection limit
    max_connections = get_permission(role, "ws_max_connections")
    redis = get_redis()
    allowed = await ws_track_connection(redis, user_id, max_connections)
    if not allowed:
        await websocket.close(
            code=status.WS_1013_TRY_AGAIN_LATER,
            reason="Too many concurrent connections",
        )
        return

    max_message_size = get_permission(role, "ws_max_message_size")
    client_id = str(uuid.uuid4())

    try:
        await manager.connect(websocket, client_id)

        while True:
            # Receive message from client
            data = await websocket.receive_text()

            # Check message size
            if not is_unlimited(max_message_size) and len(data.encode("utf-8")) > max_message_size:
                await websocket.close(
                    code=1009,  # Message Too Big
                    reason=f"Message exceeds maximum size of {max_message_size} bytes",
                )
                break

            try:
                message_data = json.loads(data)
                user_message = message_data.get("content", "")

                # Echo back user message confirmation
                await manager.send_personal_message(
                    json.dumps(
                        {
                            "type": "user_message_received",
                            "content": user_message,
                            "conversation_id": str(conversation_id),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    ),
                    client_id,
                )

                # Placeholder: Echo back as assistant response
                # In later phases, this will call the LLM/agent pipeline
                assistant_response = f"Assistant echo: {user_message}"
                await manager.send_personal_message(
                    json.dumps(
                        {
                            "type": "assistant_message",
                            "content": assistant_response,
                            "conversation_id": str(conversation_id),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    ),
                    client_id,
                )

            except json.JSONDecodeError:
                # Handle invalid JSON
                await manager.send_personal_message(
                    json.dumps(
                        {
                            "type": "error",
                            "content": "Invalid message format",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    ),
                    client_id,
                )

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(client_id)
        await ws_release_connection(redis, user_id)

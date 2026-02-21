"""WebSocket chat endpoint."""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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
        for connection in self.active_connections.values():
            await connection.send_text(message)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_endpoint(websocket: WebSocket, conversation_id: uuid.UUID) -> None:
    """WebSocket endpoint for chat conversations."""
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

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
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ),
                    client_id,
                )

                # Placeholder: Echo back as assistant response
                # In Phase 2, this will call the LLM/agent pipeline
                assistant_response = f"Assistant echo: {user_message}"
                await manager.send_personal_message(
                    json.dumps(
                        {
                            "type": "assistant_message",
                            "content": assistant_response,
                            "conversation_id": str(conversation_id),
                            "timestamp": datetime.utcnow().isoformat(),
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
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ),
                    client_id,
                )

    except WebSocketDisconnect:
        manager.disconnect(client_id)

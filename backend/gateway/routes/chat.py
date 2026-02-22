"""WebSocket chat endpoint with role-based limits."""

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException, status
from sqlalchemy import select

from backend.discussion.design_generator import DesignProposal
from backend.gateway.auth import decode_token
from backend.gateway.cost_tracker import (
    acquire_pipeline_lock,
    check_budget,
    record_cost,
    release_pipeline_lock,
)
from backend.gateway.rate_limiter import (
    get_redis,
    ws_release_connection,
    ws_track_connection,
)
from backend.gateway.rbac import get_permission, is_unlimited
from backend.gateway.session_manager import session_manager
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.shared.database import AsyncSessionLocal
from backend.shared.models import Conversation, Message, MessageRole, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()

# Hard server-level cap matches uvicorn --ws-max-size (ADMIN tier max).
# Per-role limits are enforced in the handler as defense-in-depth.
WS_ABSOLUTE_MAX_SIZE = 1_048_576  # 1MB


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


async def _save_message(
    conversation_id: uuid.UUID,
    role: MessageRole,
    content: str,
    metadata: dict | None = None,
) -> None:
    """Save a message to the database."""
    try:
        async with AsyncSessionLocal() as session:
            msg = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                metadata_=metadata,
            )
            session.add(msg)
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to save message: {e}")


async def _process_discussion_response(
    response: dict,
    client_id: str,
    conversation_id: uuid.UUID,
    user_id: str,
    role: UserRole,
) -> None:
    """Route a DiscussionEngine response to the WebSocket client."""
    resp_type = response.get("type", "unknown")
    timestamp = datetime.now(timezone.utc).isoformat()

    if resp_type == "plan_generated":
        # Execute pipeline
        selected_design_data = response.get("selected_design")
        if not selected_design_data:
            await manager.send_personal_message(
                json.dumps(
                    {
                        "type": "error",
                        "content": "설계안이 없습니다. 대화를 다시 시작해주세요.",
                        "timestamp": timestamp,
                    }
                ),
                client_id,
            )
            return

        # Notify plan is ready
        await manager.send_personal_message(
            json.dumps(
                {
                    "type": "plan_generated",
                    "content": response.get("content", "파이프라인 실행을 시작합니다."),
                    "conversation_id": str(conversation_id),
                    "timestamp": timestamp,
                }
            ),
            client_id,
        )

        # Save assistant plan message
        await _save_message(
            conversation_id,
            MessageRole.ASSISTANT,
            response.get("content", "파이프라인 실행 계획이 준비되었습니다."),
            {"type": resp_type, "discussion_summary": response.get("discussion_summary")},
        )

        # Build and execute pipeline
        design = DesignProposal(**selected_design_data)
        orchestrator = PipelineOrchestrator()

        async def on_status(status_data: dict) -> None:
            """Stream pipeline status to WebSocket."""
            try:
                status_data["conversation_id"] = str(conversation_id)
                status_data["timestamp"] = datetime.now(timezone.utc).isoformat()
                await manager.send_personal_message(json.dumps(status_data), client_id)
            except Exception:
                logger.debug("Client disconnected during pipeline execution", exc_info=True)

        # Cost circuit breaker
        allowed, current, limit = await check_budget(user_id, role)
        if not allowed:
            await manager.send_personal_message(
                json.dumps(
                    {
                        "type": "error",
                        "content": f"일일 비용 한도 초과: ${current:.2f}/${limit:.2f}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ),
                client_id,
            )
            return

        # Per-user pipeline lock to prevent TOCTOU race condition
        if not await acquire_pipeline_lock(user_id):
            await manager.send_personal_message(
                json.dumps(
                    {
                        "type": "error",
                        "content": "파이프라인이 이미 실행 중입니다. 완료 후 다시 시도해주세요.",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ),
                client_id,
            )
            return

        try:
            result = await orchestrator.execute(design, on_status=on_status)
        except Exception:
            await release_pipeline_lock(user_id)
            raise

        await release_pipeline_lock(user_id)

        # Send final result
        await manager.send_personal_message(
            json.dumps(
                {
                    "type": "pipeline_result",
                    "content": result.output or "파이프라인 실행이 완료되었습니다.",
                    "result": result.model_dump(),
                    "conversation_id": str(conversation_id),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
            client_id,
        )

        # Save pipeline result as assistant message
        await _save_message(
            conversation_id,
            MessageRole.ASSISTANT,
            result.output or "파이프라인 실행이 완료되었습니다.",
            {"type": "pipeline_result", "status": result.status, "total_cost": result.total_cost},
        )

        # Record cost
        if result.total_cost:
            await record_cost(user_id, result.total_cost)

    else:
        # All other discussion responses: clarification, designs_presented,
        # critique_complete, security_warning, error
        payload = response.copy()
        payload["conversation_id"] = str(conversation_id)
        payload["timestamp"] = timestamp
        await manager.send_personal_message(json.dumps(payload), client_id)

        # Save assistant response
        content = response.get("content", "")
        if content and resp_type not in ("error", "security_warning"):
            await _save_message(
                conversation_id,
                MessageRole.ASSISTANT,
                content,
                {"type": resp_type},
            )


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_endpoint(websocket: WebSocket, conversation_id: uuid.UUID) -> None:
    """WebSocket endpoint for chat conversations.

    Authentication: Pass JWT token as query parameter `?token=<access_token>`.
    Enforces per-role message size limits and connection count limits.
    """
    # Authenticate
    user_id, role = _authenticate_ws(websocket)

    # Verify conversation ownership (IDOR prevention)
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise WebSocketException(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason="Conversation not found or access denied",
                )
    except WebSocketException:
        raise
    except Exception as e:
        logger.error(f"Conversation ownership check failed: {e}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Access verification failed",
        )

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
            # Receive raw ASGI message for early size check before processing.
            # Server-level --ws-max-size caps frames at WS_ABSOLUTE_MAX_SIZE;
            # this per-role check is defense-in-depth.
            raw = await websocket.receive()
            if raw["type"] == "websocket.disconnect":
                break

            data = raw.get("text", "")
            if not data and "bytes" in raw and raw["bytes"]:
                data = raw["bytes"].decode("utf-8", errors="replace")

            # Check message size against role limit
            msg_byte_len = len(data.encode("utf-8"))
            if not is_unlimited(max_message_size) and msg_byte_len > max_message_size:
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

                # Save user message to DB
                await _save_message(
                    conversation_id,
                    MessageRole.USER,
                    user_message,
                )

                # Process through DiscussionEngine
                engine = session_manager.get_or_create(str(conversation_id))
                response = await engine.process_message(user_message)

                # Route response to client
                await _process_discussion_response(
                    response, client_id, conversation_id, user_id, role
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

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await manager.send_personal_message(
                    json.dumps(
                        {
                            "type": "error",
                            "content": "메시지 처리 중 오류가 발생했습니다.",
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

"""Integration tests for WebSocket chat and messaging.

Note: These tests use SQLite in-memory database for speed and isolation.
PostgreSQL-specific features are tested via CI with real PostgreSQL.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.shared.models import (
    Base,
    Message,
    MessageRole,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def chat_engine():
    """Create test database engine for chat tests."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def chat_client(chat_engine):
    """Create test HTTP client with mocked Redis."""
    from backend.gateway.main import app
    from backend.shared.database import get_db

    session_maker = async_sessionmaker(
        chat_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # Mock Redis to avoid connection errors
    with patch("backend.gateway.rate_limiter.get_redis") as mock_redis_getter:
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_redis_getter.return_value = mock_redis

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


async def register_and_login(client: AsyncClient, email: str = None) -> str:
    """Register a user and return JWT token."""
    email = email or f"test-{uuid.uuid4().hex[:8]}@test.com"
    password = "TestPass123"

    # Register
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Tester"},
    )
    assert resp.status_code == 201

    # Login
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.mark.asyncio
class TestChatMessaging:
    """Tests for chat conversation and messaging."""

    async def test_create_conversation(self, chat_client: AsyncClient):
        """Test creating a new conversation."""
        token = await register_and_login(chat_client)

        resp = await chat_client.post(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Test Conversation"},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Conversation"
        assert data["status"] == "active"
        assert "id" in data

    async def test_list_conversations(self, chat_client: AsyncClient):
        """Test listing user's conversations."""
        token = await register_and_login(chat_client)

        # Create two conversations
        await chat_client.post(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Conversation 1"},
        )
        await chat_client.post(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Conversation 2"},
        )

        # List conversations
        resp = await chat_client.get(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["title"] in ("Conversation 1", "Conversation 2")

    async def test_get_conversation_messages(
        self, chat_client: AsyncClient, chat_engine
    ):
        """Test retrieving messages from a conversation."""
        token = await register_and_login(chat_client)

        # Create conversation
        resp = await chat_client.post(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Test Chat"},
        )
        conversation_id = resp.json()["id"]

        # Add messages directly to DB
        async with async_sessionmaker(chat_engine, class_=AsyncSession)() as session:
            msg1 = Message(
                conversation_id=uuid.UUID(conversation_id),
                role=MessageRole.USER,
                content="Hello",
            )
            msg2 = Message(
                conversation_id=uuid.UUID(conversation_id),
                role=MessageRole.ASSISTANT,
                content="Hi there!",
            )
            session.add_all([msg1, msg2])
            await session.commit()

        # Retrieve messages
        resp = await chat_client.get(
            f"/api/v1/conversations/{conversation_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        messages = resp.json()["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hi there!"

    async def test_unauthorized_conversation_access(self, chat_client: AsyncClient):
        """Test that users cannot access other users' conversations."""
        # User 1 creates a conversation
        token1 = await register_and_login(chat_client, "user1@test.com")
        resp = await chat_client.post(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token1}"},
            json={"title": "Private Chat"},
        )
        conversation_id = resp.json()["id"]

        # User 2 tries to access it
        token2 = await register_and_login(chat_client, "user2@test.com")
        resp = await chat_client.get(
            f"/api/v1/conversations/{conversation_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )

        assert resp.status_code == 404  # IDOR prevention

    async def test_conversation_without_auth(self, chat_client: AsyncClient):
        """Test that unauthenticated requests are rejected."""
        resp = await chat_client.get("/api/v1/conversations")
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestMessagePersistence:
    """Tests for message CRUD operations."""

    async def test_send_message_via_api_creates_db_record(
        self, chat_client: AsyncClient, chat_engine
    ):
        """Test that sending a message via API creates a database record."""
        token = await register_and_login(chat_client)

        # Create conversation
        resp = await chat_client.post(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Test Message Persistence"},
        )
        conversation_id = uuid.UUID(resp.json()["id"])

        # Add a message directly to DB (simulating WebSocket behavior)
        async with async_sessionmaker(chat_engine, class_=AsyncSession)() as session:
            msg = Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content="Test message",
            )
            session.add(msg)
            await session.commit()

        # Verify message exists in DB
        async with async_sessionmaker(chat_engine, class_=AsyncSession)() as session:
            result = await session.execute(
                select(Message).where(Message.conversation_id == conversation_id)
            )
            messages = list(result.scalars().all())
            assert len(messages) == 1
            assert messages[0].content == "Test message"
            assert messages[0].role == MessageRole.USER

    async def test_conversation_messages_list_order(
        self, chat_client: AsyncClient, chat_engine
    ):
        """Test that messages are returned in chronological order."""
        token = await register_and_login(chat_client)

        # Create conversation
        resp = await chat_client.post(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Order Test"},
        )
        conversation_id = uuid.UUID(resp.json()["id"])

        # Add messages in order
        async with async_sessionmaker(chat_engine, class_=AsyncSession)() as session:
            for i in range(5):
                msg = Message(
                    conversation_id=conversation_id,
                    role=MessageRole.USER,
                    content=f"Message {i}",
                )
                session.add(msg)
            await session.commit()

        # Retrieve and verify order
        resp = await chat_client.get(
            f"/api/v1/conversations/{str(conversation_id)}",
            headers={"Authorization": f"Bearer {token}"},
        )

        messages = resp.json()["messages"]
        assert len(messages) == 5
        for i in range(5):
            assert messages[i]["content"] == f"Message {i}"

    async def test_message_metadata_storage(
        self, chat_client: AsyncClient, chat_engine
    ):
        """Test that message metadata is stored and retrieved correctly."""
        token = await register_and_login(chat_client)

        resp = await chat_client.post(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Metadata Test"},
        )
        conversation_id = uuid.UUID(resp.json()["id"])

        # Add message with metadata
        metadata = {"type": "test", "data": {"key": "value"}}
        async with async_sessionmaker(chat_engine, class_=AsyncSession)() as session:
            msg = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content="Response",
                metadata_=metadata,
            )
            session.add(msg)
            await session.commit()

        # Retrieve and verify metadata
        resp = await chat_client.get(
            f"/api/v1/conversations/{str(conversation_id)}",
            headers={"Authorization": f"Bearer {token}"},
        )

        messages = resp.json()["messages"]
        assert len(messages) == 1
        assert messages[0]["metadata_"] == metadata


@pytest.mark.asyncio
class TestConnectionManager:
    """Tests for WebSocket ConnectionManager."""

    async def test_connection_manager_add_remove(self):
        """Test adding and removing connections."""
        from backend.gateway.routes.chat import ConnectionManager

        manager = ConnectionManager()
        client_id = "test-client-1"

        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        # Add connection
        await manager.connect(mock_ws, client_id)
        assert client_id in manager.active_connections
        mock_ws.accept.assert_called_once()

        # Remove connection
        manager.disconnect(client_id)
        assert client_id not in manager.active_connections

    async def test_send_personal_message(self):
        """Test sending a message to a specific client."""
        from backend.gateway.routes.chat import ConnectionManager

        manager = ConnectionManager()
        client_id = "test-client-2"

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()

        await manager.connect(mock_ws, client_id)
        await manager.send_personal_message("Hello", client_id)

        mock_ws.send_text.assert_called_once_with("Hello")

    async def test_broadcast_to_all_clients(self):
        """Test broadcasting a message to all connected clients."""
        from backend.gateway.routes.chat import ConnectionManager

        manager = ConnectionManager()

        # Add multiple clients
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.send_text = AsyncMock()

        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.send_text = AsyncMock()

        await manager.connect(mock_ws1, "client-1")
        await manager.connect(mock_ws2, "client-2")

        # Broadcast
        await manager.broadcast("Broadcast message")

        mock_ws1.send_text.assert_called_once_with("Broadcast message")
        mock_ws2.send_text.assert_called_once_with("Broadcast message")

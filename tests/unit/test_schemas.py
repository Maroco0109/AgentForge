"""Tests for Pydantic schemas."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.shared.schemas import (
    ChatMessage,
    ConversationCreate,
    HealthResponse,
    MessageCreate,
    UserCreate,
)
from backend.shared.models import MessageRole


def test_user_create_valid():
    """Test valid UserCreate schema."""
    user = UserCreate(email="test@example.com", password="secret", display_name="Test")
    assert user.email == "test@example.com"


def test_user_create_invalid_email():
    """Test UserCreate with invalid email fails."""
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="secret", display_name="Test")


def test_conversation_create():
    """Test ConversationCreate schema."""
    conv = ConversationCreate(title="Test")
    assert conv.title == "Test"
    assert conv.user_id is None


def test_conversation_create_with_user():
    """Test ConversationCreate with user_id."""
    uid = uuid.uuid4()
    conv = ConversationCreate(title="Test", user_id=uid)
    assert conv.user_id == uid


def test_health_response():
    """Test HealthResponse schema."""
    resp = HealthResponse(
        status="healthy", version="0.1.0", timestamp=datetime.now(timezone.utc)
    )
    assert resp.status == "healthy"


def test_chat_message():
    """Test ChatMessage schema."""
    msg = ChatMessage(type="user_message", content="Hello")
    assert msg.type == "user_message"
    assert msg.conversation_id is None


def test_message_create():
    """Test MessageCreate schema."""
    msg = MessageCreate(
        conversation_id=uuid.uuid4(),
        role=MessageRole.USER,
        content="Hello",
    )
    assert msg.content == "Hello"

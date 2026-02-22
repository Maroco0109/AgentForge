"""Tests for database models."""

import uuid


from backend.shared.models import (
    Conversation,
    ConversationStatus,
    Message,
    MessageRole,
    User,
    UserRole,
)


def test_user_role_enum():
    """Test UserRole enum values."""
    assert UserRole.FREE == "free"
    assert UserRole.PRO == "pro"
    assert UserRole.ADMIN == "admin"


def test_conversation_status_enum():
    """Test ConversationStatus enum values."""
    assert ConversationStatus.ACTIVE == "active"
    assert ConversationStatus.ARCHIVED == "archived"


def test_message_role_enum():
    """Test MessageRole enum values."""
    assert MessageRole.USER == "user"
    assert MessageRole.ASSISTANT == "assistant"
    assert MessageRole.SYSTEM == "system"


def test_user_model_creation():
    """Test User model can be instantiated."""
    user = User(
        email="test@example.com",
        hashed_password="hash",
        display_name="Test",
    )
    assert user.email == "test@example.com"
    assert user.display_name == "Test"


def test_conversation_model_creation():
    """Test Conversation model can be instantiated."""
    conv = Conversation(
        user_id=uuid.uuid4(),
        title="Test",
    )
    assert conv.title == "Test"


def test_message_model_creation():
    """Test Message model can be instantiated."""
    msg = Message(
        conversation_id=uuid.uuid4(),
        role=MessageRole.USER,
        content="Hello",
    )
    assert msg.content == "Hello"
    assert msg.role == MessageRole.USER

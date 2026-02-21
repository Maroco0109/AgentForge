"""Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from .models import ConversationStatus, MessageRole, UserRole


# User schemas
class UserCreate(BaseModel):
    """Schema for creating a user."""

    email: EmailStr
    password: str
    display_name: str


class UserResponse(BaseModel):
    """Schema for user response."""

    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


# Conversation schemas
class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""

    title: str
    user_id: uuid.UUID | None = None  # Optional for now, will be from auth in Phase 2


class ConversationResponse(BaseModel):
    """Schema for conversation response."""

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


# Message schemas
class MessageCreate(BaseModel):
    """Schema for creating a message."""

    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    metadata_: dict | None = None


class MessageResponse(BaseModel):
    """Schema for message response."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    metadata_: dict | None
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


# WebSocket schemas
class ChatMessage(BaseModel):
    """Schema for WebSocket chat messages."""

    type: str  # "user_message", "assistant_message", "status", etc.
    content: str
    conversation_id: uuid.UUID | None = None
    timestamp: datetime | None = None


# Health check schema
class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    version: str
    timestamp: datetime

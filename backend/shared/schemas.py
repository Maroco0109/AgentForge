"""Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

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


class ConversationDetailResponse(ConversationResponse):
    """Schema for conversation detail response with messages."""

    messages: list["MessageResponse"]

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


# API Key schemas
class APIKeyCreate(BaseModel):
    """Schema for creating an API key."""

    name: str = Field(min_length=1, max_length=100)


class APIKeyResponse(BaseModel):
    """Schema for API key response (masked)."""

    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class APIKeyCreateResponse(APIKeyResponse):
    """Schema for API key creation response (includes plaintext key once)."""

    key: str


# Usage schemas
class UsageResponse(BaseModel):
    """Schema for user daily usage response."""

    daily_cost: float
    daily_limit: float
    remaining: float
    is_unlimited: bool


# Health check schema
class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    version: str
    timestamp: datetime

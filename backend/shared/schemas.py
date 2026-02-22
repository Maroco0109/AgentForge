"""Pydantic schemas for request/response validation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from .models import ConversationStatus, MessageRole, UserRole

MAX_JSON_SIZE_BYTES = 512 * 1024  # 512KB


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


# Pipeline Template schemas
def _check_json_size(v: dict, field_name: str) -> dict:
    """Validate JSON dict does not exceed 512KB when serialized."""
    import json

    size = len(json.dumps(v, default=str).encode())
    if size > MAX_JSON_SIZE_BYTES:
        max_kb = MAX_JSON_SIZE_BYTES // 1024
        raise ValueError(f"{field_name} exceeds {max_kb}KB limit")
    return v


class TemplateCreate(BaseModel):
    """Schema for creating a pipeline template."""

    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    graph_data: dict
    design_data: dict

    @field_validator("graph_data")
    @classmethod
    def validate_graph_data_size(cls, v: dict) -> dict:
        """Ensure graph_data does not exceed size limit."""
        return _check_json_size(v, "graph_data")

    @field_validator("design_data")
    @classmethod
    def validate_design_data_size(cls, v: dict) -> dict:
        """Ensure design_data does not exceed size limit."""
        return _check_json_size(v, "design_data")


class TemplateUpdate(BaseModel):
    """Schema for updating a pipeline template."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    graph_data: dict | None = None
    design_data: dict | None = None

    @field_validator("graph_data")
    @classmethod
    def validate_graph_data_size(cls, v: dict | None) -> dict | None:
        """Ensure graph_data does not exceed size limit."""
        if v is not None:
            return _check_json_size(v, "graph_data")
        return v

    @field_validator("design_data")
    @classmethod
    def validate_design_data_size(cls, v: dict | None) -> dict | None:
        """Ensure design_data does not exceed size limit."""
        if v is not None:
            return _check_json_size(v, "design_data")
        return v


class TemplateResponse(BaseModel):
    """Schema for pipeline template response."""

    id: uuid.UUID
    name: str
    description: str | None
    graph_data: dict
    design_data: dict
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


class TemplateListResponse(BaseModel):
    """Schema for pipeline template list response (summary)."""

    id: uuid.UUID
    name: str
    description: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True


# Health check schema
class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    version: str
    timestamp: datetime

"""REST endpoints for conversation management."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.shared.database import get_db
from backend.shared.models import Conversation
from backend.shared.schemas import ConversationCreate, ConversationResponse, MessageResponse

router = APIRouter()


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    """Create a new conversation."""
    # For Phase 1, use provided user_id or create a dummy UUID
    # In Phase 2, this will come from authenticated user
    user_id = conversation.user_id or uuid.uuid4()

    new_conversation = Conversation(
        user_id=user_id,
        title=conversation.title,
    )

    db.add(new_conversation)
    await db.commit()
    await db.refresh(new_conversation)

    return new_conversation


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
) -> list[Conversation]:
    """List all conversations for the current user."""
    # For Phase 1, return all conversations
    # In Phase 2, filter by authenticated user_id
    result = await db.execute(select(Conversation).order_by(Conversation.updated_at.desc()))
    conversations = result.scalars().all()

    return list(conversations)


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a conversation with its messages."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Convert to response format
    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "title": conversation.title,
        "status": conversation.status,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": [
            MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                role=msg.role,
                content=msg.content,
                metadata_=msg.metadata_,
                created_at=msg.created_at,
            )
            for msg in sorted(conversation.messages, key=lambda m: m.created_at)
        ],
    }

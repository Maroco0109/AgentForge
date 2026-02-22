import hashlib
import logging
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from backend.gateway.auth import get_current_user
from backend.shared.database import get_db
from backend.shared.models import APIKey, User
from backend.shared.schemas import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

# Maximum API keys per user
_MAX_API_KEYS_PER_USER = 20


@router.post(
    "",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    request: APIKeyCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> APIKeyCreateResponse:
    """Create a new API key for the current user.

    Returns the plaintext key only once - it cannot be retrieved later.
    """
    # Check per-user API key count limit
    key_count = await db.scalar(
        select(func.count()).select_from(APIKey).where(APIKey.user_id == current_user.id)
    )
    if key_count >= _MAX_API_KEYS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API key limit reached (max {_MAX_API_KEYS_PER_USER} per user)",
        )

    # Generate raw key: sk- + 32 hex chars = 35 chars total
    raw_key = "sk-" + secrets.token_hex(16)

    # Hash for storage
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    # Store first 11 chars as prefix for display
    key_prefix = raw_key[:11]

    # Create API key record
    api_key = APIKey(
        user_id=current_user.id,
        name=request.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        is_active=True,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    logger.info(
        "API key created: id=%s, user_id=%s, name=%s",
        api_key.id,
        current_user.id,
        request.name,
    )

    # Return with plaintext key (one-time only)
    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        key=raw_key,
    )


@router.get("", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[APIKeyResponse]:
    """List all API keys for the current user."""
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id).order_by(APIKey.created_at.desc())
    )
    api_keys = result.scalars().all()

    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            is_active=key.is_active,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
        )
        for key in api_keys
    ]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Delete an API key by ID.

    Only the owner can delete their API keys.
    """
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == current_user.id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await db.delete(api_key)
    await db.commit()

    logger.info("API key deleted: id=%s, user_id=%s", key_id, current_user.id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)

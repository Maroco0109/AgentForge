"""LLM API key management routes for BYOK."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.gateway.auth import get_current_user
from backend.pipeline.key_validator import validate_provider_key
from backend.pipeline.user_router_factory import invalidate_user_cache
from backend.shared.database import get_db
from backend.shared.encryption import decrypt_api_key, encrypt_api_key
from backend.shared.models import LLMProviderType, User, UserLLMKey
from backend.shared.schemas import LLMKeyCreate, LLMKeyResponse, LLMKeyValidationResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm-keys", tags=["llm-keys"])


@router.post("", response_model=LLMKeyResponse, status_code=status.HTTP_201_CREATED)
async def register_llm_key(
    request: LLMKeyCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LLMKeyResponse:
    """Register or update an LLM API key.

    Encrypts the key, validates it, and upserts (one key per provider per user).
    """
    # Validate provider
    try:
        provider_enum = LLMProviderType(request.provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported provider: {request.provider}. Supported: openai, anthropic, google"
            ),
        )

    # Validate the key
    try:
        is_valid, message, models = await validate_provider_key(request.provider, request.api_key)
    except Exception as e:
        logger.warning("Key validation error during registration: %s", e)
        is_valid, message, models = False, "Key validation failed. Please try again.", []

    # Encrypt the key
    encrypted_key, nonce = encrypt_api_key(request.api_key)

    # Key prefix for display (first 12 chars)
    key_prefix = request.api_key[:12] + "..."

    now = datetime.now(timezone.utc)

    # Check for existing key (upsert)
    result = await db.execute(
        select(UserLLMKey).where(
            UserLLMKey.user_id == current_user.id,
            UserLLMKey.provider == provider_enum,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.encrypted_key = encrypted_key
        existing.nonce = nonce
        existing.key_prefix = key_prefix
        existing.is_valid = is_valid
        existing.last_validated_at = now
        existing.updated_at = now
        llm_key = existing
    else:
        llm_key = UserLLMKey(
            user_id=current_user.id,
            provider=provider_enum,
            encrypted_key=encrypted_key,
            nonce=nonce,
            key_prefix=key_prefix,
            is_active=True,
            is_valid=is_valid,
            last_validated_at=now,
        )
        db.add(llm_key)

    await db.commit()
    await db.refresh(llm_key)

    # Invalidate user router cache
    invalidate_user_cache(str(current_user.id))

    logger.info(
        "LLM key registered: user_id=%s, provider=%s, valid=%s",
        current_user.id,
        provider_enum.value,
        is_valid,
    )

    return LLMKeyResponse(
        id=llm_key.id,
        provider=llm_key.provider.value,
        key_prefix=llm_key.key_prefix,
        is_active=llm_key.is_active,
        is_valid=llm_key.is_valid,
        last_used_at=llm_key.last_used_at,
        last_validated_at=llm_key.last_validated_at,
        created_at=llm_key.created_at,
        updated_at=llm_key.updated_at,
    )


@router.get("", response_model=list[LLMKeyResponse])
async def list_llm_keys(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[LLMKeyResponse]:
    """List all LLM keys for the current user (masked)."""
    result = await db.execute(
        select(UserLLMKey)
        .where(UserLLMKey.user_id == current_user.id)
        .order_by(UserLLMKey.created_at.desc())
    )
    keys = result.scalars().all()

    return [
        LLMKeyResponse(
            id=key.id,
            provider=key.provider.value,
            key_prefix=key.key_prefix,
            is_active=key.is_active,
            is_valid=key.is_valid,
            last_used_at=key.last_used_at,
            last_validated_at=key.last_validated_at,
            created_at=key.created_at,
            updated_at=key.updated_at,
        )
        for key in keys
    ]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_key(
    key_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Delete an LLM key. IDOR prevention: returns 404 for non-owner."""
    result = await db.execute(
        select(UserLLMKey).where(
            UserLLMKey.id == key_id,
            UserLLMKey.user_id == current_user.id,
        )
    )
    llm_key = result.scalar_one_or_none()

    if not llm_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM key not found",
        )

    await db.delete(llm_key)
    await db.commit()

    # Invalidate user router cache
    invalidate_user_cache(str(current_user.id))

    logger.info("LLM key deleted: id=%s, user_id=%s", key_id, current_user.id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{key_id}/validate", response_model=LLMKeyValidationResponse)
async def validate_llm_key(
    key_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LLMKeyValidationResponse:
    """Re-validate an existing LLM key."""
    result = await db.execute(
        select(UserLLMKey).where(
            UserLLMKey.id == key_id,
            UserLLMKey.user_id == current_user.id,
        )
    )
    llm_key = result.scalar_one_or_none()

    if not llm_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM key not found",
        )

    # Decrypt and validate
    try:
        plaintext = decrypt_api_key(llm_key.encrypted_key, llm_key.nonce)
    except RuntimeError:
        llm_key.is_valid = False
        llm_key.updated_at = datetime.now(timezone.utc)
        await db.commit()
        invalidate_user_cache(str(current_user.id))
        return LLMKeyValidationResponse(
            provider=llm_key.provider.value,
            is_valid=False,
            message="Failed to decrypt key. Please re-register.",
        )

    is_valid, message, models = await validate_provider_key(llm_key.provider.value, plaintext)

    now = datetime.now(timezone.utc)
    llm_key.is_valid = is_valid
    llm_key.last_validated_at = now
    llm_key.updated_at = now
    await db.commit()

    # Invalidate cache on validation status change
    invalidate_user_cache(str(current_user.id))

    return LLMKeyValidationResponse(
        provider=llm_key.provider.value,
        is_valid=is_valid,
        message=message,
        models_available=models,
    )

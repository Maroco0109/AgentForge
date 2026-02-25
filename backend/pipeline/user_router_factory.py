"""User-specific LLM Router factory with TTL cache."""

from __future__ import annotations

import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.pipeline.llm_router import LLMProvider, LLMRouter

logger = logging.getLogger(__name__)

# Cache: user_id -> (router, created_at)
_cache: dict[str, tuple[LLMRouter, float]] = {}
_CACHE_TTL = 300  # 5 minutes
_CACHE_MAX_SIZE = 200

# Module-level imports for Phase 8-1 dependencies (patchable in tests).
# These modules are added by Phase 8-1; import gracefully if not merged yet.
try:
    from backend.shared.encryption import decrypt_api_key
    from backend.shared.models import LLMProviderType, UserLLMKey
except ImportError:  # pragma: no cover
    decrypt_api_key = None  # type: ignore[assignment]
    LLMProviderType = None  # type: ignore[assignment]
    UserLLMKey = None  # type: ignore[assignment]


def _get_provider_map() -> dict:
    """Build a mapping from DB LLMProviderType values to router LLMProvider values."""
    if LLMProviderType is None:  # pragma: no cover
        return {}
    provider_map: dict = {}
    for attr_name in ("OPENAI", "ANTHROPIC", "GOOGLE"):
        try:
            db_provider = getattr(LLMProviderType, attr_name)
            router_provider = LLMProvider(db_provider.value)
            provider_map[db_provider] = router_provider
        except (AttributeError, ValueError):
            pass
    return provider_map


async def get_user_router(user_id: str, db: AsyncSession) -> LLMRouter:
    """Get or create a user-specific LLM Router.

    Raises:
        ValueError: If no active/valid LLM keys are registered.
    """
    # Check cache
    cached = _cache.get(user_id)
    if cached:
        router, created_at = cached
        if time.time() - created_at < _CACHE_TTL:
            return router
        # Expired
        del _cache[user_id]

    # Query DB for active, valid keys
    stmt = select(UserLLMKey).where(
        UserLLMKey.user_id == user_id,
        UserLLMKey.is_active.is_(True),
        UserLLMKey.is_valid.is_(True),
    )
    result = await db.execute(stmt)
    keys = result.scalars().all()

    if not keys:
        raise ValueError("LLM API 키가 등록되지 않았습니다. 설정에서 API 키를 등록해주세요.")

    provider_map = _get_provider_map()

    # Decrypt and build user_keys dict
    user_keys: dict[LLMProvider, str] = {}
    for key_record in keys:
        router_provider = provider_map.get(key_record.provider)
        if router_provider:
            try:
                plaintext = decrypt_api_key(key_record.encrypted_key, key_record.nonce)
                user_keys[router_provider] = plaintext
            except RuntimeError:
                logger.warning(
                    f"Failed to decrypt key for user={user_id} provider={key_record.provider.value}"
                )

    if not user_keys:
        raise ValueError("등록된 API 키를 복호화할 수 없습니다. 키를 다시 등록해주세요.")

    # Create router and cache
    router = LLMRouter(user_keys=user_keys)

    # Evict oldest if at capacity
    if len(_cache) >= _CACHE_MAX_SIZE:
        oldest_key = min(_cache, key=lambda k: _cache[k][1])
        del _cache[oldest_key]

    _cache[user_id] = (router, time.time())
    return router


def invalidate_user_cache(user_id: str) -> None:
    """Invalidate cached router for a user (call after key CRUD)."""
    _cache.pop(user_id, None)


def clear_cache() -> None:
    """Clear all cached routers (for testing)."""
    _cache.clear()

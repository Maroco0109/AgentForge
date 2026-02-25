"""Tests for user router factory."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.pipeline.llm_router import LLMProvider, LLMRouter
from backend.pipeline.user_router_factory import (
    _CACHE_TTL,
    _cache,
    clear_cache,
    get_user_router,
    invalidate_user_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


def _make_provider_enum(value: str):
    """Create a mock provider enum value matching LLMProviderType."""
    p = MagicMock()
    p.value = value
    return p


def _make_mock_key(
    provider_value: str = "openai", encrypted_key=b"enc", nonce=b"123456789012"
):
    """Create a mock UserLLMKey record."""
    key = MagicMock()
    key.provider = _make_provider_enum(provider_value)
    key.encrypted_key = encrypted_key
    key.nonce = nonce
    key.is_active = True
    key.is_valid = True
    return key


def _make_db_mock(keys: list) -> AsyncMock:
    """Create a mock AsyncSession that returns the given keys."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = keys
    mock_db.execute.return_value = mock_result
    return mock_db


def _make_provider_map(*provider_values: str) -> dict:
    """Build a provider_map dict mapping mock provider enums to LLMProvider."""
    provider_map = {}
    for value in provider_values:
        try:
            router_provider = LLMProvider(value)
        except ValueError:
            continue
        enum_mock = _make_provider_enum(value)
        provider_map[enum_mock] = router_provider
    return provider_map


@pytest.mark.asyncio
class TestGetUserRouter:
    """Test get_user_router function."""

    async def test_creates_router_from_db_keys(self):
        openai_key = _make_mock_key("openai")
        openai_enum = openai_key.provider
        provider_map = {openai_enum: LLMProvider.OPENAI}
        mock_db = _make_db_mock([openai_key])

        mock_router = MagicMock(spec=LLMRouter)
        mock_router._clients = {LLMProvider.OPENAI: MagicMock()}

        with (
            patch(
                "backend.pipeline.user_router_factory.select", return_value=MagicMock()
            ),
            patch(
                "backend.pipeline.user_router_factory.decrypt_api_key",
                return_value="sk-dec",
            ),
            patch("backend.pipeline.user_router_factory.UserLLMKey", MagicMock()),
            patch(
                "backend.pipeline.user_router_factory._get_provider_map",
                return_value=provider_map,
            ),
            patch(
                "backend.pipeline.user_router_factory.LLMRouter",
                return_value=mock_router,
            ),
        ):
            router = await get_user_router("user-123", mock_db)

        assert router is mock_router
        assert LLMProvider.OPENAI in router._clients

    async def test_cache_hit(self):
        openai_key = _make_mock_key("openai")
        openai_enum = openai_key.provider
        provider_map = {openai_enum: LLMProvider.OPENAI}
        mock_db = _make_db_mock([openai_key])

        mock_router = MagicMock(spec=LLMRouter)
        mock_router._clients = {LLMProvider.OPENAI: MagicMock()}

        with (
            patch(
                "backend.pipeline.user_router_factory.select", return_value=MagicMock()
            ),
            patch(
                "backend.pipeline.user_router_factory.decrypt_api_key",
                return_value="sk-dec",
            ),
            patch("backend.pipeline.user_router_factory.UserLLMKey", MagicMock()),
            patch(
                "backend.pipeline.user_router_factory._get_provider_map",
                return_value=provider_map,
            ),
            patch(
                "backend.pipeline.user_router_factory.LLMRouter",
                return_value=mock_router,
            ),
        ):
            router1 = await get_user_router("user-123", mock_db)
            router2 = await get_user_router("user-123", mock_db)

        assert router1 is router2
        # DB should only be called once (second call is cache hit)
        assert mock_db.execute.call_count == 1

    async def test_cache_expired(self):
        openai_key = _make_mock_key("openai")
        openai_enum = openai_key.provider
        provider_map = {openai_enum: LLMProvider.OPENAI}
        mock_db = _make_db_mock([openai_key])

        call_count = 0

        def make_router(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            r = MagicMock(spec=LLMRouter)
            r._clients = {LLMProvider.OPENAI: MagicMock()}
            r._call_count = call_count
            return r

        with (
            patch(
                "backend.pipeline.user_router_factory.select", return_value=MagicMock()
            ),
            patch(
                "backend.pipeline.user_router_factory.decrypt_api_key",
                return_value="sk-dec",
            ),
            patch("backend.pipeline.user_router_factory.UserLLMKey", MagicMock()),
            patch(
                "backend.pipeline.user_router_factory._get_provider_map",
                return_value=provider_map,
            ),
            patch(
                "backend.pipeline.user_router_factory.LLMRouter",
                side_effect=make_router,
            ),
        ):
            router1 = await get_user_router("user-123", mock_db)

            # Manually expire cache
            _cache["user-123"] = (_cache["user-123"][0], time.time() - _CACHE_TTL - 1)

            router2 = await get_user_router("user-123", mock_db)

        assert router1 is not router2
        assert mock_db.execute.call_count == 2

    async def test_no_keys_raises_value_error(self):
        mock_db = _make_db_mock([])

        with (
            patch(
                "backend.pipeline.user_router_factory.select", return_value=MagicMock()
            ),
            patch("backend.pipeline.user_router_factory.UserLLMKey", MagicMock()),
            patch(
                "backend.pipeline.user_router_factory._get_provider_map",
                return_value={},
            ),
        ):
            with pytest.raises(ValueError, match="LLM API 키가 등록되지 않았습니다"):
                await get_user_router("user-123", mock_db)

    async def test_multiple_providers(self):
        openai_key = _make_mock_key("openai")
        anthropic_key = _make_mock_key("anthropic")
        openai_enum = openai_key.provider
        anthropic_enum = anthropic_key.provider
        provider_map = {
            openai_enum: LLMProvider.OPENAI,
            anthropic_enum: LLMProvider.ANTHROPIC,
        }
        mock_db = _make_db_mock([openai_key, anthropic_key])

        mock_router = MagicMock(spec=LLMRouter)
        mock_router._clients = {
            LLMProvider.OPENAI: MagicMock(),
            LLMProvider.ANTHROPIC: MagicMock(),
        }

        with (
            patch(
                "backend.pipeline.user_router_factory.select", return_value=MagicMock()
            ),
            patch(
                "backend.pipeline.user_router_factory.decrypt_api_key",
                return_value="sk-dec",
            ),
            patch("backend.pipeline.user_router_factory.UserLLMKey", MagicMock()),
            patch(
                "backend.pipeline.user_router_factory._get_provider_map",
                return_value=provider_map,
            ),
            patch(
                "backend.pipeline.user_router_factory.LLMRouter",
                return_value=mock_router,
            ),
        ):
            router = await get_user_router("user-123", mock_db)

        assert LLMProvider.OPENAI in router._clients
        assert LLMProvider.ANTHROPIC in router._clients


@pytest.mark.asyncio
class TestInvalidateCache:
    """Test cache invalidation."""

    async def test_invalidate_clears_user(self):
        openai_key = _make_mock_key("openai")
        openai_enum = openai_key.provider
        provider_map = {openai_enum: LLMProvider.OPENAI}
        mock_db = _make_db_mock([openai_key])

        mock_router = MagicMock(spec=LLMRouter)
        mock_router._clients = {LLMProvider.OPENAI: MagicMock()}

        with (
            patch(
                "backend.pipeline.user_router_factory.select", return_value=MagicMock()
            ),
            patch(
                "backend.pipeline.user_router_factory.decrypt_api_key",
                return_value="sk-dec",
            ),
            patch("backend.pipeline.user_router_factory.UserLLMKey", MagicMock()),
            patch(
                "backend.pipeline.user_router_factory._get_provider_map",
                return_value=provider_map,
            ),
            patch(
                "backend.pipeline.user_router_factory.LLMRouter",
                return_value=mock_router,
            ),
        ):
            await get_user_router("user-123", mock_db)

        assert "user-123" in _cache

        invalidate_user_cache("user-123")
        assert "user-123" not in _cache

    async def test_invalidate_nonexistent_user(self):
        # Should not raise
        invalidate_user_cache("nonexistent")

    async def test_clear_cache(self):
        _cache["a"] = (MagicMock(), time.time())
        _cache["b"] = (MagicMock(), time.time())
        clear_cache()
        assert len(_cache) == 0

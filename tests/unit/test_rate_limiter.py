"""Unit tests for Redis-based rate limiter."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.gateway.rate_limiter import (
    RateLimiter,
    check_rate_limit,
    close_redis,
    get_redis,
    init_redis,
    ws_release_connection,
    ws_track_connection,
)
from backend.shared.models import UserRole


class TestInitRedis:
    """Tests for Redis initialization."""

    @pytest.mark.asyncio
    async def test_init_redis_success(self):
        """Test successful Redis initialization."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        with patch(
            "backend.gateway.rate_limiter.Redis.from_url",
            return_value=mock_redis,
        ):
            result = await init_redis()
            assert result is mock_redis
            mock_redis.ping.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_init_redis_failure_returns_none(self):
        """Test that Redis connection failure returns None (graceful degradation)."""
        with patch(
            "backend.gateway.rate_limiter.Redis.from_url",
            side_effect=ConnectionError("Connection refused"),
        ):
            result = await init_redis()
            assert result is None

    @pytest.mark.asyncio
    async def test_init_redis_ping_failure_returns_none(self):
        """Test that Redis ping failure returns None."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=ConnectionError("ping failed"))

        with patch(
            "backend.gateway.rate_limiter.Redis.from_url",
            return_value=mock_redis,
        ):
            result = await init_redis()
            assert result is None


class TestCloseRedis:
    """Tests for Redis connection cleanup."""

    @pytest.mark.asyncio
    async def test_close_redis_when_connected(self):
        """Test closing an active Redis connection."""
        mock_redis = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with patch("backend.gateway.rate_limiter._redis_client", mock_redis):
            await close_redis()
            mock_redis.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_redis_when_none(self):
        """Test closing Redis when no connection exists (no error)."""
        with patch("backend.gateway.rate_limiter._redis_client", None):
            await close_redis()  # Should not raise


class TestGetRedis:
    """Tests for get_redis helper."""

    def test_get_redis_returns_client(self):
        """Test get_redis returns the module-level client."""
        mock_redis = MagicMock()
        with patch("backend.gateway.rate_limiter._redis_client", mock_redis):
            result = get_redis()
            assert result is mock_redis

    def test_get_redis_returns_none_when_not_initialized(self):
        """Test get_redis returns None when Redis is not initialized."""
        with patch("backend.gateway.rate_limiter._redis_client", None):
            result = get_redis()
            assert result is None


class TestCheckRateLimit:
    """Tests for check_rate_limit sliding window logic."""

    @pytest.mark.asyncio
    async def test_allowed_when_under_limit(self):
        """Test that requests under the limit are allowed."""
        mock_pipe = AsyncMock()
        mock_pipe.zremrangebyscore = MagicMock()
        mock_pipe.zcard = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 5, True])  # 5 requests

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        allowed, remaining, retry_after = await check_rate_limit(
            mock_redis, "rate_limit:test", limit=10, window_seconds=60
        )

        assert allowed is True
        assert remaining == 4  # 10 - 5 - 1 (current request)
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_denied_when_over_limit(self):
        """Test that requests over the limit are denied."""
        mock_pipe = AsyncMock()
        mock_pipe.zremrangebyscore = MagicMock()
        mock_pipe.zcard = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 11, True])  # 11 requests

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        # Mock zrange for oldest entry
        import time

        mock_redis.zrange = AsyncMock(return_value=[("entry", time.time() - 30)])

        allowed, remaining, retry_after = await check_rate_limit(
            mock_redis, "rate_limit:test", limit=10, window_seconds=60
        )

        assert allowed is False
        assert remaining == 0
        assert retry_after >= 1

    @pytest.mark.asyncio
    async def test_denied_with_no_oldest_entry(self):
        """Test denied response when no oldest entry found."""
        mock_pipe = AsyncMock()
        mock_pipe.zremrangebyscore = MagicMock()
        mock_pipe.zcard = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 11, True])

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_redis.zrange = AsyncMock(return_value=[])

        allowed, remaining, retry_after = await check_rate_limit(
            mock_redis, "rate_limit:test", limit=10, window_seconds=60
        )

        assert allowed is False
        assert remaining == 0
        assert retry_after == 60  # Falls back to full window

    @pytest.mark.asyncio
    async def test_exactly_at_limit_is_denied(self):
        """Test that request count at limit is denied (>= check)."""
        mock_pipe = AsyncMock()
        mock_pipe.zremrangebyscore = MagicMock()
        mock_pipe.zcard = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 10, True])

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_redis.zrange = AsyncMock(return_value=[])

        allowed, remaining, retry_after = await check_rate_limit(
            mock_redis, "rate_limit:test", limit=10, window_seconds=60
        )

        assert allowed is False
        assert remaining == 0
        assert retry_after == 60

    @pytest.mark.asyncio
    async def test_custom_window_seconds(self):
        """Test rate limit with custom window duration."""
        mock_pipe = AsyncMock()
        mock_pipe.zremrangebyscore = MagicMock()
        mock_pipe.zcard = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[0, 3, True])

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        allowed, remaining, retry_after = await check_rate_limit(
            mock_redis, "rate_limit:test", limit=5, window_seconds=120
        )

        assert allowed is True
        assert remaining == 1  # 5 - 3 - 1


class TestRateLimiterClass:
    """Tests for RateLimiter FastAPI dependency class."""

    def test_init_default_window(self):
        """Test RateLimiter default window_seconds."""
        limiter = RateLimiter()
        assert limiter.window_seconds == 60

    def test_init_custom_window(self):
        """Test RateLimiter custom window_seconds."""
        limiter = RateLimiter(window_seconds=120)
        assert limiter.window_seconds == 120

    @pytest.mark.asyncio
    async def test_allows_when_redis_unavailable(self):
        """Test graceful degradation: allows request when Redis is down."""
        limiter = RateLimiter()
        mock_request = MagicMock()

        with patch("backend.gateway.rate_limiter.get_redis", return_value=None):
            # Should not raise
            await limiter(mock_request)

    @pytest.mark.asyncio
    async def test_allows_unlimited_role(self):
        """Test that unlimited role (admin) skips rate limiting."""
        limiter = RateLimiter()

        mock_user = MagicMock()
        mock_user.role = UserRole.ADMIN
        mock_user.id = uuid.uuid4()

        mock_request = MagicMock()
        mock_request.state.current_user = mock_user

        mock_redis = AsyncMock()

        with patch("backend.gateway.rate_limiter.get_redis", return_value=mock_redis):
            await limiter(mock_request)
            # Should return without calling check_rate_limit

    @pytest.mark.asyncio
    async def test_raises_429_when_rate_exceeded(self):
        """Test that 429 is raised when rate limit is exceeded."""
        from fastapi import HTTPException

        limiter = RateLimiter()

        mock_user = MagicMock()
        mock_user.role = UserRole.FREE
        mock_user.id = uuid.uuid4()

        mock_request = MagicMock()
        mock_request.state.current_user = mock_user

        mock_redis = AsyncMock()

        with (
            patch("backend.gateway.rate_limiter.get_redis", return_value=mock_redis),
            patch(
                "backend.gateway.rate_limiter.check_rate_limit",
                new_callable=AsyncMock,
                return_value=(False, 0, 30),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await limiter(mock_request)

            assert exc_info.value.status_code == 429
            assert exc_info.value.detail == "Rate limit exceeded"
            assert exc_info.value.headers["Retry-After"] == "30"

    @pytest.mark.asyncio
    async def test_sets_rate_limit_headers_on_success(self):
        """Test that remaining/limit are set on request state on success."""
        limiter = RateLimiter()

        mock_user = MagicMock()
        mock_user.role = UserRole.FREE
        mock_user.id = uuid.uuid4()

        mock_request = MagicMock()
        mock_request.state.current_user = mock_user

        mock_redis = AsyncMock()

        with (
            patch("backend.gateway.rate_limiter.get_redis", return_value=mock_redis),
            patch(
                "backend.gateway.rate_limiter.check_rate_limit",
                new_callable=AsyncMock,
                return_value=(True, 7, 0),
            ),
        ):
            await limiter(mock_request)

            assert mock_request.state.rate_limit_remaining == 7
            assert mock_request.state.rate_limit_limit == 10

    @pytest.mark.asyncio
    async def test_allows_when_check_raises_exception(self):
        """Test graceful degradation: allows request when rate check fails."""
        limiter = RateLimiter()

        mock_user = MagicMock()
        mock_user.role = UserRole.FREE
        mock_user.id = uuid.uuid4()

        mock_request = MagicMock()
        mock_request.state.current_user = mock_user

        mock_redis = AsyncMock()

        with (
            patch("backend.gateway.rate_limiter.get_redis", return_value=mock_redis),
            patch(
                "backend.gateway.rate_limiter.check_rate_limit",
                new_callable=AsyncMock,
                side_effect=ConnectionError("Redis error"),
            ),
        ):
            # Should not raise -- graceful degradation
            await limiter(mock_request)


class TestWsTrackConnection:
    """Tests for WebSocket connection tracking."""

    @pytest.mark.asyncio
    async def test_allows_when_redis_none(self):
        """Test that connection is allowed when Redis is unavailable."""
        result = await ws_track_connection(None, "user-1", max_connections=2)
        assert result is True

    @pytest.mark.asyncio
    async def test_allows_when_unlimited(self):
        """Test that connection is allowed when max_connections is unlimited."""
        mock_redis = AsyncMock()
        result = await ws_track_connection(mock_redis, "user-1", max_connections=-1)
        assert result is True

    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        """Test that connection is allowed when under the limit."""
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        result = await ws_track_connection(mock_redis, "user-1", max_connections=2)
        assert result is True
        mock_redis.incr.assert_awaited_once_with("ws_connections:user-1")

    @pytest.mark.asyncio
    async def test_denies_over_limit(self):
        """Test that connection is denied when over the limit."""
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=3)
        mock_redis.decr = AsyncMock()
        mock_redis.expire = AsyncMock()

        result = await ws_track_connection(mock_redis, "user-1", max_connections=2)
        assert result is False
        mock_redis.decr.assert_awaited_once_with("ws_connections:user-1")

    @pytest.mark.asyncio
    async def test_allows_on_redis_error(self):
        """Test graceful degradation on Redis error."""
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=ConnectionError("Redis error"))

        result = await ws_track_connection(mock_redis, "user-1", max_connections=2)
        assert result is True


class TestWsReleaseConnection:
    """Tests for WebSocket connection release."""

    @pytest.mark.asyncio
    async def test_release_when_redis_none(self):
        """Test release does nothing when Redis is unavailable."""
        await ws_release_connection(None, "user-1")  # Should not raise

    @pytest.mark.asyncio
    async def test_release_decrements_count(self):
        """Test that release decrements connection count."""
        mock_redis = AsyncMock()
        mock_redis.decr = AsyncMock(return_value=1)

        await ws_release_connection(mock_redis, "user-1")
        mock_redis.decr.assert_awaited_once_with("ws_connections:user-1")

    @pytest.mark.asyncio
    async def test_release_deletes_key_at_zero(self):
        """Test that key is deleted when count reaches zero."""
        mock_redis = AsyncMock()
        mock_redis.decr = AsyncMock(return_value=0)
        mock_redis.delete = AsyncMock()

        await ws_release_connection(mock_redis, "user-1")
        mock_redis.delete.assert_awaited_once_with("ws_connections:user-1")

    @pytest.mark.asyncio
    async def test_release_deletes_key_below_zero(self):
        """Test that key is deleted when count goes below zero."""
        mock_redis = AsyncMock()
        mock_redis.decr = AsyncMock(return_value=-1)
        mock_redis.delete = AsyncMock()

        await ws_release_connection(mock_redis, "user-1")
        mock_redis.delete.assert_awaited_once_with("ws_connections:user-1")

    @pytest.mark.asyncio
    async def test_release_handles_redis_error(self):
        """Test graceful degradation on Redis error during release."""
        mock_redis = AsyncMock()
        mock_redis.decr = AsyncMock(side_effect=ConnectionError("Redis error"))

        await ws_release_connection(mock_redis, "user-1")  # Should not raise

"""Unit tests for Redis-based cost tracker."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from backend.gateway.cost_tracker import (
    _today_key,
    check_budget,
    get_daily_cost,
    record_cost,
)
from backend.shared.models import User, UserRole


@pytest.fixture
def mock_redis():
    """Create mock Redis client with pipeline support."""
    from unittest.mock import MagicMock

    redis = AsyncMock()
    mock_pipe = MagicMock()
    mock_pipe.incrbyfloat = MagicMock(return_value=mock_pipe)
    mock_pipe.expire = MagicMock(return_value=mock_pipe)
    mock_pipe.execute = AsyncMock(return_value=[0.75, True])
    redis.pipeline = MagicMock(return_value=mock_pipe)
    return redis


class TestTodayKey:
    """Tests for _today_key helper."""

    def test_today_key_format(self):
        """Test that _today_key returns correct format."""
        user_id = "test-user-123"
        key = _today_key(user_id)
        assert key.startswith("cost_budget:test-user-123:")
        # Should end with YYYY-MM-DD format
        date_part = key.split(":")[-1]
        assert len(date_part) == 10  # YYYY-MM-DD
        assert date_part[4] == "-"
        assert date_part[7] == "-"


class TestGetDailyCost:
    """Tests for get_daily_cost function."""

    @pytest.mark.asyncio
    async def test_get_daily_cost_returns_value(self, mock_redis):
        """Test get_daily_cost returns value from Redis."""
        mock_redis.get.return_value = "0.5"

        with patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis):
            result = await get_daily_cost("user-1")

        assert result == 0.5
        mock_redis.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_daily_cost_no_value(self, mock_redis):
        """Test get_daily_cost returns 0.0 when Redis returns None."""
        mock_redis.get.return_value = None

        with patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis):
            result = await get_daily_cost("user-1")

        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_daily_cost_redis_unavailable(self):
        """Test get_daily_cost returns 0.0 when get_redis returns None."""
        with patch("backend.gateway.cost_tracker.get_redis", return_value=None):
            result = await get_daily_cost("user-1")

        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_daily_cost_redis_error(self, mock_redis):
        """Test get_daily_cost returns 0.0 when Redis raises exception."""
        mock_redis.get.side_effect = ConnectionError("Redis error")

        with patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis):
            result = await get_daily_cost("user-1")

        assert result == 0.0


class TestCheckBudget:
    """Tests for check_budget function."""

    @pytest.mark.asyncio
    async def test_check_budget_free_under_limit(self, mock_redis):
        """Test FREE user under limit is allowed."""
        mock_redis.get.return_value = "0.5"

        with patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis):
            allowed, current, limit = await check_budget("user-1", UserRole.FREE)

        assert allowed is True
        assert current == 0.5
        assert limit == 1.0

    @pytest.mark.asyncio
    async def test_check_budget_free_over_limit(self, mock_redis):
        """Test FREE user over limit is denied."""
        mock_redis.get.return_value = "1.5"

        with patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis):
            allowed, current, limit = await check_budget("user-1", UserRole.FREE)

        assert allowed is False
        assert current == 1.5
        assert limit == 1.0

    @pytest.mark.asyncio
    async def test_check_budget_pro_under_limit(self, mock_redis):
        """Test PRO user under limit is allowed."""
        mock_redis.get.return_value = "10.0"

        with patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis):
            allowed, current, limit = await check_budget("user-1", UserRole.PRO)

        assert allowed is True
        assert current == 10.0
        assert limit == 50.0

    @pytest.mark.asyncio
    async def test_check_budget_admin_unlimited(self, mock_redis):
        """Test ADMIN user has unlimited budget."""
        mock_redis.get.return_value = "999.99"

        with patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis):
            allowed, current, limit = await check_budget("user-1", UserRole.ADMIN)

        assert allowed is True
        assert current == 999.99
        assert limit == -1

    @pytest.mark.asyncio
    async def test_check_budget_at_exact_limit(self, mock_redis):
        """Test user at exact limit is denied (not less than)."""
        mock_redis.get.return_value = "1.0"

        with patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis):
            allowed, current, limit = await check_budget("user-1", UserRole.FREE)

        assert allowed is False
        assert current == 1.0
        assert limit == 1.0


class TestRecordCost:
    """Tests for record_cost function."""

    @pytest.mark.asyncio
    async def test_record_cost_increments(self, mock_redis):
        """Test record_cost increments Redis counter with correct TTL via pipeline."""
        mock_pipe = mock_redis.pipeline.return_value

        with (
            patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis),
            patch(
                "backend.gateway.cost_tracker._persist_daily_cost",
                new_callable=AsyncMock,
            ),
        ):
            result = await record_cost("user-1", 0.25)

        assert result == 0.75
        mock_redis.pipeline.assert_called_once()
        mock_pipe.incrbyfloat.assert_called_once()
        args = mock_pipe.incrbyfloat.call_args[0]
        assert args[1] == 0.25  # cost value
        mock_pipe.expire.assert_called_once()
        expire_args = mock_pipe.expire.call_args[0]
        assert expire_args[1] == 172800  # 48 hours TTL
        mock_pipe.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_record_cost_zero_skipped(self, mock_redis):
        """Test cost=0 doesn't call Redis."""
        mock_redis.get.return_value = "1.0"

        with (
            patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis),
            patch(
                "backend.gateway.cost_tracker._persist_daily_cost",
                new_callable=AsyncMock,
            ),
        ):
            result = await record_cost("user-1", 0)

        assert result == 1.0
        mock_redis.incrbyfloat.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_cost_negative_skipped(self, mock_redis):
        """Test cost=-1 doesn't call Redis."""
        mock_redis.get.return_value = "1.0"

        with (
            patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis),
            patch(
                "backend.gateway.cost_tracker._persist_daily_cost",
                new_callable=AsyncMock,
            ),
        ):
            result = await record_cost("user-1", -1)

        assert result == 1.0
        mock_redis.incrbyfloat.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_cost_redis_unavailable(self):
        """Test record_cost skips tracking when Redis unavailable."""
        mock_persist = AsyncMock()

        with (
            patch("backend.gateway.cost_tracker.get_redis", return_value=None),
            patch("backend.gateway.cost_tracker._persist_daily_cost", mock_persist),
        ):
            result = await record_cost("user-1", 0.5)

        assert result == 0.0  # No Redis, returns 0
        mock_persist.assert_not_awaited()  # No persist without Redis

    @pytest.mark.asyncio
    async def test_record_cost_redis_error(self, mock_redis):
        """Test record_cost falls back gracefully on Redis error."""
        mock_redis.pipeline.return_value.execute = AsyncMock(
            side_effect=ConnectionError("Redis error")
        )
        mock_persist = AsyncMock()

        with (
            patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis),
            patch("backend.gateway.cost_tracker._persist_daily_cost", mock_persist),
        ):
            result = await record_cost("user-1", 0.5)

        assert result == 0.5  # Falls back to cost value
        mock_persist.assert_not_awaited()  # No persist on error


class TestPersistDailyCost:
    """Tests for _persist_daily_cost function."""

    @pytest.mark.asyncio
    async def test_persist_called_on_record_cost(self, mock_redis):
        """Test _persist_daily_cost is called when recording cost."""
        mock_persist = AsyncMock()

        with (
            patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis),
            patch("backend.gateway.cost_tracker._persist_daily_cost", mock_persist),
        ):
            await record_cost("user-1", 0.25)

        # Verify persist was called with correct args
        mock_persist.assert_awaited_once()
        args = mock_persist.call_args[0]
        assert args[0] == "user-1"  # user_id
        assert args[2] == 0.75  # total cost

    @pytest.mark.asyncio
    async def test_persist_not_called_when_cost_zero(self, mock_redis):
        """Test _persist_daily_cost not called when cost is zero."""
        mock_redis.get.return_value = "1.0"
        mock_persist = AsyncMock()

        with (
            patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis),
            patch("backend.gateway.cost_tracker._persist_daily_cost", mock_persist),
        ):
            result = await record_cost("user-1", 0)

        # Persist should not be called for zero cost
        mock_persist.assert_not_called()
        assert result == 1.0


class TestUsageEndpoint:
    """Tests for /api/v1/auth/me/usage endpoint."""

    @pytest_asyncio.fixture
    async def auth_headers(self, client, test_session):
        """Create authenticated user and return auth headers."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "usage@example.com",
                "password": "SecurePass123!",
                "display_name": "Usage Test",
            },
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_usage_endpoint(self, client, auth_headers, mock_redis):
        """Test GET /api/v1/auth/me/usage returns cost usage."""
        mock_redis.get.return_value = "0.35"

        with patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis):
            response = await client.get("/api/v1/auth/me/usage", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["daily_cost"] == 0.35
        assert data["daily_limit"] == 1.0  # FREE user
        assert data["remaining"] == 0.65
        assert data["is_unlimited"] is False

    @pytest.mark.asyncio
    async def test_usage_endpoint_admin(self, client, test_session, mock_redis):
        """Test admin user sees is_unlimited=True."""
        from backend.gateway.auth import create_access_token, hash_password

        # Create admin user
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            hashed_password=hash_password("AdminPass123!"),
            display_name="Admin User",
            role=UserRole.ADMIN,
        )
        test_session.add(admin_user)
        await test_session.commit()

        # Create token
        token = create_access_token(str(admin_user.id), admin_user.role.value)
        headers = {"Authorization": f"Bearer {token}"}

        mock_redis.get.return_value = "999.99"

        with patch("backend.gateway.cost_tracker.get_redis", return_value=mock_redis):
            response = await client.get("/api/v1/auth/me/usage", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["daily_cost"] == 999.99
        assert data["daily_limit"] == -1
        assert data["remaining"] == -1
        assert data["is_unlimited"] is True

    @pytest.mark.asyncio
    async def test_usage_endpoint_redis_unavailable(self, client, auth_headers):
        """Test usage endpoint works when Redis is unavailable."""
        with patch("backend.gateway.cost_tracker.get_redis", return_value=None):
            response = await client.get("/api/v1/auth/me/usage", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["daily_cost"] == 0.0  # Graceful fallback
        assert data["daily_limit"] == 1.0
        assert data["remaining"] == 1.0

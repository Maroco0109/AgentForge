"""Tests for auth endpoint rate limiter."""

from unittest.mock import MagicMock, patch

import pytest

from backend.gateway.auth_rate_limiter import (
    AUTH_RATE_LIMIT,
    AUTH_RATE_WINDOW_SECONDS,
    _get_client_ip,
    check_auth_rate_limit,
)


class TestGetClientIp:
    """Tests for _get_client_ip function."""

    def _make_request(self, client_host="127.0.0.1", forwarded_for=None):
        """Create a mock request."""
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = client_host
        request.headers = {}
        if forwarded_for is not None:
            request.headers["x-forwarded-for"] = forwarded_for
        return request

    @patch("backend.gateway.auth_rate_limiter.settings")
    def test_no_proxy_returns_client_host(self, mock_settings):
        """TRUSTED_PROXY_COUNT=0 should return request.client.host."""
        mock_settings.TRUSTED_PROXY_COUNT = 0
        request = self._make_request(client_host="192.168.1.100")
        assert _get_client_ip(request) == "192.168.1.100"

    @patch("backend.gateway.auth_rate_limiter.settings")
    def test_one_proxy_extracts_correct_ip(self, mock_settings):
        """TRUSTED_PROXY_COUNT=1 should extract client IP from X-Forwarded-For."""
        mock_settings.TRUSTED_PROXY_COUNT = 1
        request = self._make_request(forwarded_for="203.0.113.50, 10.0.0.1")
        assert _get_client_ip(request) == "203.0.113.50"

    @patch("backend.gateway.auth_rate_limiter.settings")
    def test_two_proxies_extracts_correct_ip(self, mock_settings):
        """TRUSTED_PROXY_COUNT=2 should skip 2 rightmost IPs."""
        mock_settings.TRUSTED_PROXY_COUNT = 2
        request = self._make_request(forwarded_for="203.0.113.50, 10.0.0.1, 10.0.0.2")
        assert _get_client_ip(request) == "203.0.113.50"

    @patch("backend.gateway.auth_rate_limiter.settings")
    def test_proxy_count_exceeds_ips_fallback(self, mock_settings):
        """When proxy count exceeds available IPs, fallback to leftmost."""
        mock_settings.TRUSTED_PROXY_COUNT = 5
        request = self._make_request(forwarded_for="203.0.113.50, 10.0.0.1")
        assert _get_client_ip(request) == "203.0.113.50"

    @patch("backend.gateway.auth_rate_limiter.settings")
    def test_no_forwarded_for_with_proxy(self, mock_settings):
        """Missing X-Forwarded-For with proxy should fallback to client.host."""
        mock_settings.TRUSTED_PROXY_COUNT = 1
        request = self._make_request(client_host="10.0.0.5")
        assert _get_client_ip(request) == "10.0.0.5"


class TestCheckAuthRateLimit:
    """Tests for check_auth_rate_limit dependency."""

    def _make_request(self):
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        return request

    @pytest.mark.anyio
    @patch("backend.gateway.auth_rate_limiter.get_redis", return_value=None)
    async def test_redis_unavailable_allows_request(self, mock_get_redis):
        """When Redis is down, requests should be allowed."""
        request = self._make_request()
        await check_auth_rate_limit(request)

    @pytest.mark.anyio
    @patch("backend.gateway.auth_rate_limiter.settings")
    @patch("backend.gateway.auth_rate_limiter.check_rate_limit")
    @patch("backend.gateway.auth_rate_limiter.get_redis")
    async def test_under_limit_allows_request(
        self, mock_get_redis, mock_check, mock_settings
    ):
        """Requests under limit should be allowed."""
        mock_settings.TRUSTED_PROXY_COUNT = 0
        mock_get_redis.return_value = MagicMock()
        mock_check.return_value = (True, 4, 0)
        request = self._make_request()
        await check_auth_rate_limit(request)

    @pytest.mark.anyio
    @patch("backend.gateway.auth_rate_limiter.settings")
    @patch("backend.gateway.auth_rate_limiter.check_rate_limit")
    @patch("backend.gateway.auth_rate_limiter.get_redis")
    async def test_over_limit_returns_429(
        self, mock_get_redis, mock_check, mock_settings
    ):
        """Requests over limit should raise 429."""
        mock_settings.TRUSTED_PROXY_COUNT = 0
        mock_get_redis.return_value = MagicMock()
        mock_check.return_value = (False, 0, 600)
        request = self._make_request()
        with pytest.raises(Exception) as exc_info:
            await check_auth_rate_limit(request)
        assert exc_info.value.status_code == 429
        assert exc_info.value.headers["Retry-After"] == "600"

    @pytest.mark.anyio
    @patch("backend.gateway.auth_rate_limiter.settings")
    @patch("backend.gateway.auth_rate_limiter.check_rate_limit")
    @patch("backend.gateway.auth_rate_limiter.get_redis")
    async def test_redis_error_allows_request(
        self, mock_get_redis, mock_check, mock_settings
    ):
        """Redis errors should gracefully allow the request."""
        mock_settings.TRUSTED_PROXY_COUNT = 0
        mock_get_redis.return_value = MagicMock()
        mock_check.side_effect = Exception("Redis connection lost")
        request = self._make_request()
        await check_auth_rate_limit(request)

    def test_constants(self):
        """Verify rate limit constants."""
        assert AUTH_RATE_LIMIT == 5
        assert AUTH_RATE_WINDOW_SECONDS == 900

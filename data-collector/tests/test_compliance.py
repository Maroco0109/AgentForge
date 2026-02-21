"""Tests for compliance module: robots.txt, PII detection, rate limiting."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import httpx
from data_collector.compliance.pii_detector import PIIDetector
from data_collector.compliance.rate_limiter import SiteRateLimiter
from data_collector.compliance.robots_checker import RobotsChecker


class TestRobotsChecker:
    """Test robots.txt checker."""

    async def test_robots_txt_allow(self):
        """Test URL allowed by robots.txt."""
        checker = RobotsChecker()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = """User-agent: *
Disallow: /admin
Allow: /
"""

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            allowed, reason = await checker.is_allowed("https://example.com/page")
            assert allowed is True
            assert "Allowed" in reason

    async def test_robots_txt_disallow(self):
        """Test URL blocked by robots.txt."""
        checker = RobotsChecker()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = """User-agent: *
Disallow: /admin
"""

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            allowed, reason = await checker.is_allowed("https://example.com/admin")
            assert allowed is False
            assert "Blocked" in reason

    async def test_robots_txt_not_found(self):
        """Test robots.txt not found - assume allowed."""
        checker = RobotsChecker()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            allowed, reason = await checker.is_allowed("https://example.com/page")
            assert allowed is True
            assert "not found" in reason

    async def test_robots_txt_crawl_delay(self):
        """Test crawl delay extraction."""
        checker = RobotsChecker()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = """User-agent: *
Crawl-delay: 5
Disallow: /admin
"""

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            delay = await checker.get_crawl_delay("https://example.com/page")
            assert delay == 5.0

    async def test_robots_txt_cache(self):
        """Test robots.txt caching."""
        checker = RobotsChecker()
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nAllow: /"

        with patch("httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.get = mock_get

            # First call
            await checker.is_allowed("https://example.com/page1")
            # Second call - should use cache
            await checker.is_allowed("https://example.com/page2")

            # Should only fetch robots.txt once
            assert mock_get.call_count == 1

    async def test_robots_txt_request_error(self):
        """Test handling network error."""
        checker = RobotsChecker()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Network error")
            )

            allowed, reason = await checker.is_allowed("https://example.com/page")
            assert allowed is True
            assert "failed" in reason


class TestPIIDetector:
    """Test PII detection."""

    def test_detect_phone_number(self):
        """Test Korean phone number detection."""
        detector = PIIDetector()
        text = "연락처: 010-1234-5678입니다."

        result = detector.detect(text)
        assert result.has_pii is True
        assert "phone" in result.pii_types
        assert len(result.found) == 1
        assert result.found[0]["value"] == "010-1234-5678"

    def test_detect_email(self):
        """Test email detection."""
        detector = PIIDetector()
        text = "이메일은 test@example.com입니다."

        result = detector.detect(text)
        assert result.has_pii is True
        assert "email" in result.pii_types
        assert result.found[0]["value"] == "test@example.com"

    def test_detect_ssn(self):
        """Test Korean SSN detection."""
        detector = PIIDetector()
        text = "주민번호: 990101-1234567"

        result = detector.detect(text)
        assert result.has_pii is True
        assert "ssn" in result.pii_types

    def test_detect_card_number(self):
        """Test credit card number detection."""
        detector = PIIDetector()
        text = "카드번호: 1234-5678-9012-3456"

        result = detector.detect(text)
        assert result.has_pii is True
        assert "card_number" in result.pii_types

    def test_detect_korean_name(self):
        """Test Korean name pattern detection."""
        detector = PIIDetector()
        text = "홍길동 님께서 말씀하셨습니다."

        result = detector.detect(text)
        assert result.has_pii is True
        assert "name_pattern" in result.pii_types

    def test_detect_address(self):
        """Test Korean address detection."""
        detector = PIIDetector()
        text = "주소는 서울시 강남구 테헤란로 123입니다."

        result = detector.detect(text)
        assert result.has_pii is True
        assert "address" in result.pii_types

    def test_detect_multiple_pii(self):
        """Test multiple PII types in one text."""
        detector = PIIDetector()
        text = "홍길동 님 010-1234-5678, test@example.com"

        result = detector.detect(text)
        assert result.has_pii is True
        assert len(result.pii_types) == 3
        assert "name_pattern" in result.pii_types
        assert "phone" in result.pii_types
        assert "email" in result.pii_types

    def test_no_pii(self):
        """Test clean text with no PII."""
        detector = PIIDetector()
        text = "This is a clean text with no personal information."

        result = detector.detect(text)
        assert result.has_pii is False
        assert len(result.found) == 0

    def test_has_pii_quick_check(self):
        """Test quick PII check."""
        detector = PIIDetector()

        assert detector.has_pii("010-1234-5678") is True
        assert detector.has_pii("clean text") is False

    def test_pii_result_to_dict(self):
        """Test PII result serialization."""
        detector = PIIDetector()
        text = "010-1234-5678"

        result = detector.detect(text)
        result_dict = result.to_dict()

        assert result_dict["has_pii"] is True
        assert result_dict["pii_count"] == 1
        assert "phone" in result_dict["pii_types"]
        assert len(result_dict["details"]) == 1


class TestRateLimiter:
    """Test per-site rate limiter."""

    async def test_set_and_get_delay(self):
        """Test setting and getting delay for a domain."""
        limiter = SiteRateLimiter(default_delay=2.0)

        limiter.set_delay("example.com", 5.0)
        assert limiter.get_delay("example.com") == 5.0
        assert limiter.get_delay("unknown.com") == 2.0

    async def test_minimum_delay_enforced(self):
        """Test minimum delay of 0.5s is enforced."""
        limiter = SiteRateLimiter()
        limiter.set_delay("example.com", 0.1)

        assert limiter.get_delay("example.com") == 0.5

    async def test_rate_limiting_waits(self):
        """Test that rate limiting actually waits."""
        limiter = SiteRateLimiter(default_delay=0.5)

        start = time.time()
        await limiter.wait("example.com")
        await limiter.wait("example.com")
        elapsed = time.time() - start

        # Should wait at least 0.5 seconds between calls
        assert elapsed >= 0.5

    async def test_different_domains_no_wait(self):
        """Test different domains don't affect each other."""
        limiter = SiteRateLimiter(default_delay=1.0)

        start = time.time()
        await limiter.wait("example.com")
        await limiter.wait("other.com")
        elapsed = time.time() - start

        # Should not wait since different domains
        assert elapsed < 0.5

    async def test_concurrent_wait_same_domain(self):
        """Test concurrent requests to same domain are serialized."""
        limiter = SiteRateLimiter(default_delay=0.5)

        async def request():
            await limiter.wait("example.com")
            return time.time()

        start = time.time()
        _results = await asyncio.gather(request(), request(), request())
        total_time = time.time() - start

        # Three requests with 0.5s delay should take at least 1.0s
        assert total_time >= 1.0

    async def test_elapsed_time_reduces_wait(self):
        """Test that time already passed reduces wait time."""
        limiter = SiteRateLimiter(default_delay=1.0)

        await limiter.wait("example.com")
        await asyncio.sleep(0.8)  # Wait 0.8s

        start = time.time()
        await limiter.wait("example.com")
        elapsed = time.time() - start

        # Should only wait ~0.2s since 0.8s already passed
        assert elapsed < 0.5

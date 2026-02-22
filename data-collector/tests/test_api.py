"""Tests for FastAPI endpoints."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from data_collector.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_collections():
    """Reset in-memory collections before each test."""
    from data_collector.main import _collections

    _collections.clear()
    yield
    _collections.clear()


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_returns_200(self, client):
        """Test health endpoint returns 200."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "data-collector"
        assert data["version"] == "0.1.0"


class TestCreateCollection:
    """Test create collection endpoint."""

    def test_create_collection_returns_201(self, client):
        """Test creating a collection returns 201."""
        request_data = {"url": "https://example.com", "source_type": "web", "options": {}}

        response = client.post("/api/v1/collections", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert data["source_type"] == "web"
        assert data["url"] == "https://example.com"

    def test_create_collection_generates_unique_id(self, client):
        """Test that each collection gets unique ID."""
        request_data = {"url": "https://example.com", "source_type": "web"}

        response1 = client.post("/api/v1/collections", json=request_data)
        response2 = client.post("/api/v1/collections", json=request_data)

        data1 = response1.json()
        data2 = response2.json()

        assert data1["id"] != data2["id"]

    def test_create_collection_with_api_source(self, client):
        """Test creating API source collection."""
        request_data = {"url": "https://api.example.com/data", "source_type": "api"}

        response = client.post("/api/v1/collections", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["source_type"] == "api"

    def test_create_collection_default_source_type(self, client):
        """Test default source type is web."""
        request_data = {"url": "https://example.com"}

        response = client.post("/api/v1/collections", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["source_type"] == "web"

    def test_create_collection_with_options(self, client):
        """Test creating collection with custom options."""
        request_data = {
            "url": "https://example.com",
            "source_type": "web",
            "options": {"max_depth": 2, "follow_links": True},
        }

        response = client.post("/api/v1/collections", json=request_data)

        assert response.status_code == 201


class TestCheckCompliance:
    """Test compliance check endpoint."""

    @pytest.mark.asyncio
    async def test_check_compliance_allowed(self, client):
        """Test compliance check for allowed URL."""
        # Create collection first
        create_response = client.post(
            "/api/v1/collections", json={"url": "https://example.com", "source_type": "web"}
        )
        collection_id = create_response.json()["id"]

        # Mock robots checker
        mock_is_allowed = AsyncMock(return_value=(True, "Allowed by robots.txt"))
        mock_get_crawl_delay = AsyncMock(return_value=None)

        with patch("data_collector.main.robots_checker.is_allowed", mock_is_allowed):
            with patch("data_collector.main.robots_checker.get_crawl_delay", mock_get_crawl_delay):
                response = client.get(f"/api/v1/collections/{collection_id}/compliance")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "allowed"
        assert data["robots_allowed"] is True
        assert data["rate_limit_seconds"] == 2.0

    @pytest.mark.asyncio
    async def test_check_compliance_blocked(self, client):
        """Test compliance check for blocked URL."""
        create_response = client.post(
            "/api/v1/collections", json={"url": "https://example.com/admin", "source_type": "web"}
        )
        collection_id = create_response.json()["id"]

        mock_is_allowed = AsyncMock(return_value=(False, "Blocked by robots.txt"))

        with patch("data_collector.main.robots_checker.is_allowed", mock_is_allowed):
            response = client.get(f"/api/v1/collections/{collection_id}/compliance")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "blocked"
        assert data["robots_allowed"] is False

    @pytest.mark.asyncio
    async def test_check_compliance_with_crawl_delay(self, client):
        """Test compliance check extracts crawl delay."""
        create_response = client.post(
            "/api/v1/collections", json={"url": "https://example.com", "source_type": "web"}
        )
        collection_id = create_response.json()["id"]

        mock_is_allowed = AsyncMock(return_value=(True, "Allowed"))
        mock_get_crawl_delay = AsyncMock(return_value=5.0)

        with patch("data_collector.main.robots_checker.is_allowed", mock_is_allowed):
            with patch("data_collector.main.robots_checker.get_crawl_delay", mock_get_crawl_delay):
                response = client.get(f"/api/v1/collections/{collection_id}/compliance")

        assert response.status_code == 200
        data = response.json()
        assert data["rate_limit_seconds"] == 5.0

    def test_check_compliance_not_found(self, client):
        """Test compliance check for non-existent collection."""
        response = client.get("/api/v1/collections/nonexistent-id/compliance")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_check_compliance_no_url(self, client):
        """Test compliance check when no URL provided."""
        create_response = client.post(
            "/api/v1/collections", json={"source_type": "file", "options": {}}
        )
        collection_id = create_response.json()["id"]

        response = client.get(f"/api/v1/collections/{collection_id}/compliance")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "allowed"
        assert "No URL" in data["robots_reason"]


class TestGetCollectionStatus:
    """Test get collection status endpoint."""

    def test_get_collection_status(self, client):
        """Test getting collection status."""
        create_response = client.post(
            "/api/v1/collections", json={"url": "https://example.com", "source_type": "web"}
        )
        collection_id = create_response.json()["id"]

        response = client.get(f"/api/v1/collections/{collection_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == collection_id
        assert data["status"] == "pending"
        assert data["url"] == "https://example.com"

    def test_get_collection_status_not_found(self, client):
        """Test getting status for non-existent collection."""
        response = client.get("/api/v1/collections/nonexistent-id/status")

        assert response.status_code == 404


class TestRunCollection:
    """Test run collection endpoint."""

    @pytest.mark.asyncio
    async def test_run_collection_success(self, client):
        """Test successful collection execution."""
        # Create and check compliance first
        create_response = client.post(
            "/api/v1/collections", json={"url": "https://example.com", "source_type": "web"}
        )
        collection_id = create_response.json()["id"]

        # Mock compliance check
        mock_is_allowed = AsyncMock(return_value=(True, "Allowed"))
        mock_get_crawl_delay = AsyncMock(return_value=None)

        with patch("data_collector.main.robots_checker.is_allowed", mock_is_allowed):
            with patch("data_collector.main.robots_checker.get_crawl_delay", mock_get_crawl_delay):
                client.get(f"/api/v1/collections/{collection_id}/compliance")

        # Mock crawler
        from data_collector.collectors.web_crawler import CrawlResult

        mock_crawl_result = CrawlResult(
            url="https://example.com",
            status_code=200,
            title="Test Page",
            text_content="This is test content for the page.",
            html_content="<html>Test</html>",
            links=["https://example.com/page1"],
            success=True,
        )

        with patch("data_collector.main.WebCrawler") as mock_crawler_class:
            mock_crawler = Mock()
            mock_crawler.crawl = AsyncMock(return_value=mock_crawl_result)
            mock_crawler_class.return_value = mock_crawler

            response = client.post(f"/api/v1/collections/{collection_id}/collect")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_collection_without_compliance_check(self, client):
        """Test running collection without compliance check fails."""
        create_response = client.post(
            "/api/v1/collections", json={"url": "https://example.com", "source_type": "web"}
        )
        collection_id = create_response.json()["id"]

        response = client.post(f"/api/v1/collections/{collection_id}/collect")

        assert response.status_code == 400
        assert "compliance check" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_run_collection_blocked_by_compliance(self, client):
        """Test running collection that's blocked by compliance."""
        create_response = client.post(
            "/api/v1/collections", json={"url": "https://example.com", "source_type": "web"}
        )
        collection_id = create_response.json()["id"]

        # Mock blocked compliance
        mock_is_allowed = AsyncMock(return_value=(False, "Blocked"))

        with patch("data_collector.main.robots_checker.is_allowed", mock_is_allowed):
            client.get(f"/api/v1/collections/{collection_id}/compliance")

        response = client.post(f"/api/v1/collections/{collection_id}/collect")

        assert response.status_code == 403
        assert "blocked" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_run_collection_crawl_failure(self, client):
        """Test collection with crawl failure."""
        create_response = client.post(
            "/api/v1/collections", json={"url": "https://example.com", "source_type": "web"}
        )
        collection_id = create_response.json()["id"]

        # Mock compliance
        mock_is_allowed = AsyncMock(return_value=(True, "Allowed"))
        mock_get_crawl_delay = AsyncMock(return_value=None)

        with patch("data_collector.main.robots_checker.is_allowed", mock_is_allowed):
            with patch("data_collector.main.robots_checker.get_crawl_delay", mock_get_crawl_delay):
                client.get(f"/api/v1/collections/{collection_id}/compliance")

        # Mock failed crawl
        from data_collector.collectors.web_crawler import CrawlResult

        mock_crawl_result = CrawlResult(
            url="https://example.com", status_code=500, error="Server error", success=False
        )

        with patch("data_collector.main.WebCrawler") as mock_crawler_class:
            mock_crawler = Mock()
            mock_crawler.crawl = AsyncMock(return_value=mock_crawl_result)
            mock_crawler_class.return_value = mock_crawler

            response = client.post(f"/api/v1/collections/{collection_id}/collect")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Server error"

    def test_run_collection_not_found(self, client):
        """Test running non-existent collection."""
        response = client.post("/api/v1/collections/nonexistent-id/collect")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_run_collection_no_url(self, client):
        """Test running collection without URL."""
        create_response = client.post("/api/v1/collections", json={"source_type": "file"})
        collection_id = create_response.json()["id"]

        # Mock compliance
        mock_is_allowed = AsyncMock(return_value=(True, "Allowed"))
        with patch("data_collector.main.robots_checker.is_allowed", mock_is_allowed):
            client.get(f"/api/v1/collections/{collection_id}/compliance")

        response = client.post(f"/api/v1/collections/{collection_id}/collect")

        assert response.status_code == 400
        assert "No URL" in response.json()["detail"]


class TestGetCollectionData:
    """Test get collection data endpoint."""

    @pytest.mark.asyncio
    async def test_get_collection_data(self, client):
        """Test getting collected data."""
        # Create, check compliance, and run collection
        create_response = client.post(
            "/api/v1/collections", json={"url": "https://example.com", "source_type": "web"}
        )
        collection_id = create_response.json()["id"]

        # Mock compliance
        mock_is_allowed = AsyncMock(return_value=(True, "Allowed"))
        mock_get_crawl_delay = AsyncMock(return_value=None)

        with patch("data_collector.main.robots_checker.is_allowed", mock_is_allowed):
            with patch("data_collector.main.robots_checker.get_crawl_delay", mock_get_crawl_delay):
                client.get(f"/api/v1/collections/{collection_id}/compliance")

        # Mock successful collection
        from data_collector.collectors.web_crawler import CrawlResult

        mock_crawl_result = CrawlResult(
            url="https://example.com",
            status_code=200,
            title="Test Page",
            text_content="This is test content.",
            html_content="<html>Test</html>",
            links=[],
            success=True,
        )

        with patch("data_collector.main.WebCrawler") as mock_crawler_class:
            mock_crawler = Mock()
            mock_crawler.crawl = AsyncMock(return_value=mock_crawl_result)
            mock_crawler_class.return_value = mock_crawler

            client.post(f"/api/v1/collections/{collection_id}/collect")

        # Get data
        response = client.get(f"/api/v1/collections/{collection_id}/data")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == collection_id
        assert data["status"] == "completed"
        assert "data" in data
        assert data["total_items"] > 0

    def test_get_collection_data_not_found(self, client):
        """Test getting data for non-existent collection."""
        response = client.get("/api/v1/collections/nonexistent-id/data")

        assert response.status_code == 404

    def test_get_collection_data_before_collection(self, client):
        """Test getting data before collection runs."""
        create_response = client.post(
            "/api/v1/collections", json={"url": "https://example.com", "source_type": "web"}
        )
        collection_id = create_response.json()["id"]

        response = client.get(f"/api/v1/collections/{collection_id}/data")

        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 0
        assert data["data"] == []

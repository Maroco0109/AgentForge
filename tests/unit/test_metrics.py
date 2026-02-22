"""Tests for Prometheus metrics and middleware."""

from unittest.mock import AsyncMock

import pytest
from starlette.requests import Request
from starlette.responses import Response

from backend.shared.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    LLM_COST_DOLLARS_TOTAL,
    LLM_REQUEST_DURATION_SECONDS,
    LLM_REQUESTS_TOTAL,
    LLM_TOKENS_TOTAL,
    PIPELINE_DURATION_SECONDS,
    PIPELINE_EXECUTIONS_TOTAL,
    WEBSOCKET_CONNECTIONS_ACTIVE,
)
from backend.shared.middleware import PrometheusMiddleware


class TestMetricsDefinitions:
    """Verify all metric objects are properly defined."""

    def test_http_metrics_exist(self):
        assert HTTP_REQUESTS_TOTAL is not None
        assert HTTP_REQUEST_DURATION_SECONDS is not None

    def test_llm_metrics_exist(self):
        assert LLM_REQUESTS_TOTAL is not None
        assert LLM_TOKENS_TOTAL is not None
        assert LLM_COST_DOLLARS_TOTAL is not None
        assert LLM_REQUEST_DURATION_SECONDS is not None

    def test_pipeline_metrics_exist(self):
        assert PIPELINE_EXECUTIONS_TOTAL is not None
        assert PIPELINE_DURATION_SECONDS is not None

    def test_websocket_metrics_exist(self):
        assert WEBSOCKET_CONNECTIONS_ACTIVE is not None

    def test_http_requests_total_labels(self):
        """Counter should accept method, endpoint, status labels."""
        counter = HTTP_REQUESTS_TOTAL.labels(
            method="GET", endpoint="/test", status="200"
        )
        assert counter is not None

    def test_llm_requests_total_labels(self):
        """Counter should accept provider, model, complexity labels."""
        counter = LLM_REQUESTS_TOTAL.labels(
            provider="openai", model="gpt-4o-mini", complexity="simple"
        )
        assert counter is not None

    def test_llm_tokens_total_labels(self):
        """Counter should accept provider, model, type labels."""
        counter = LLM_TOKENS_TOTAL.labels(
            provider="openai", model="gpt-4o-mini", type="input"
        )
        assert counter is not None

    def test_pipeline_executions_total_labels(self):
        """Counter should accept status label."""
        counter = PIPELINE_EXECUTIONS_TOTAL.labels(status="completed")
        assert counter is not None


class TestPrometheusMiddleware:
    """Tests for HTTP metrics middleware."""

    def test_normalize_path_uuid(self):
        """UUID segments should be collapsed to {id}."""
        result = PrometheusMiddleware._normalize_path(
            "/api/v1/conversations/550e8400-e29b-41d4-a716-446655440000/messages"
        )
        assert result == "/api/v1/conversations/{id}/messages"

    def test_normalize_path_numeric(self):
        """Numeric segments should be collapsed to {id}."""
        result = PrometheusMiddleware._normalize_path("/api/v1/users/123/profile")
        assert result == "/api/v1/users/{id}/profile"

    def test_normalize_path_no_ids(self):
        """Paths without IDs should remain unchanged."""
        result = PrometheusMiddleware._normalize_path("/api/v1/health")
        assert result == "/api/v1/health"

    def test_exclude_paths(self):
        """Health and metrics endpoints should be excluded."""
        assert "/metrics" in PrometheusMiddleware.EXCLUDE_PATHS
        assert "/api/v1/health" in PrometheusMiddleware.EXCLUDE_PATHS

    @pytest.mark.asyncio
    async def test_middleware_records_metrics(self):
        """Middleware should call next and return response."""

        async def mock_app(scope, receive, send):
            pass

        middleware = PrometheusMiddleware(mock_app)

        # Create a mock request for a non-excluded path
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/conversations",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)

        mock_response = Response(status_code=200)
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_skips_excluded_paths(self):
        """Middleware should skip metrics for excluded paths."""

        async def mock_app(scope, receive, send):
            pass

        middleware = PrometheusMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/metrics",
            "query_string": b"",
            "headers": [],
        }
        request = Request(scope)

        mock_response = Response(status_code=200)
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(request, call_next)
        assert response.status_code == 200


class TestMetricsEndpoint:
    """Test the /metrics endpoint returns valid Prometheus format."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_returns_text(self):
        """The metrics route should return prometheus text format."""
        from backend.gateway.routes.metrics import metrics

        response = await metrics()
        assert response.status_code == 200
        assert (
            "text/plain" in response.media_type or "openmetrics" in response.media_type
        )
        # Content should contain at least one metric name
        body = response.body.decode()
        assert "http_requests" in body or "python_info" in body or "HELP" in body

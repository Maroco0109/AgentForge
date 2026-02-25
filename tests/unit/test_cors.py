"""Tests for CORS configuration."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.gateway.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_cors_allows_get_method(client):
    """GET method should be allowed."""
    response = await client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    allowed = response.headers.get("access-control-allow-methods", "")
    assert "GET" in allowed


@pytest.mark.anyio
async def test_cors_allows_post_method(client):
    """POST method should be allowed."""
    response = await client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    allowed = response.headers.get("access-control-allow-methods", "")
    assert "POST" in allowed


@pytest.mark.anyio
async def test_cors_allows_delete_method(client):
    """DELETE method should be allowed."""
    response = await client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "DELETE",
        },
    )
    allowed = response.headers.get("access-control-allow-methods", "")
    assert "DELETE" in allowed


@pytest.mark.anyio
async def test_cors_allows_required_headers(client):
    """Authorization and X-API-Key headers should be allowed."""
    response = await client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization, X-API-Key",
        },
    )
    allowed = response.headers.get("access-control-allow-headers", "")
    assert "Authorization" in allowed or "authorization" in allowed


@pytest.mark.anyio
async def test_cors_exposes_retry_after(client):
    """Retry-After header should be exposed to the browser."""
    response = await client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:3000"},
    )
    exposed = response.headers.get("access-control-expose-headers", "")
    assert "Retry-After" in exposed or "retry-after" in exposed.lower()

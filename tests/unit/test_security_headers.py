"""Tests for security headers middleware and exception handlers."""

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
async def test_x_frame_options_header(client):
    """X-Frame-Options should be DENY."""
    response = await client.get("/api/v1/health")
    assert response.headers["x-frame-options"] == "DENY"


@pytest.mark.anyio
async def test_x_content_type_options_header(client):
    """X-Content-Type-Options should be nosniff."""
    response = await client.get("/api/v1/health")
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.anyio
async def test_x_xss_protection_header(client):
    """X-XSS-Protection should be set."""
    response = await client.get("/api/v1/health")
    assert response.headers["x-xss-protection"] == "1; mode=block"


@pytest.mark.anyio
async def test_referrer_policy_header(client):
    """Referrer-Policy should be strict-origin-when-cross-origin."""
    response = await client.get("/api/v1/health")
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"


@pytest.mark.anyio
async def test_permissions_policy_header(client):
    """Permissions-Policy should restrict camera, mic, geo."""
    response = await client.get("/api/v1/health")
    assert (
        response.headers["permissions-policy"]
        == "camera=(), microphone=(), geolocation=()"
    )


@pytest.mark.anyio
async def test_csp_header_present(client):
    """Content-Security-Policy should be present."""
    response = await client.get("/api/v1/health")
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


@pytest.mark.anyio
async def test_hsts_absent_in_debug_mode(client):
    """HSTS should NOT be present when DEBUG=True (default in tests)."""
    response = await client.get("/api/v1/health")
    assert "strict-transport-security" not in response.headers


@pytest.mark.anyio
async def test_health_endpoint_still_works(client):
    """Health endpoint should return 200 with security headers."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.anyio
async def test_validation_error_format(client):
    """422 errors should not expose stack traces."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "x", "display_name": ""},
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert isinstance(data["detail"], list)
    for error in data["detail"]:
        assert "field" in error
        assert "msg" in error
        assert "traceback" not in str(error).lower()


@pytest.mark.anyio
async def test_exception_handlers_registered(client):
    """Verify all 3 exception handlers are registered."""
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    handlers = app.exception_handlers
    assert StarletteHTTPException in handlers
    assert RequestValidationError in handlers
    assert Exception in handlers

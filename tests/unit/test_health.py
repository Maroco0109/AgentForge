"""Tests for health check endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check returns healthy status."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_check_response_format(client):
    """Test health check response has correct format."""
    response = await client.get("/api/v1/health")
    data = response.json()
    assert isinstance(data["status"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["timestamp"], str)

"""Pytest configuration and shared fixtures."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a FastAPI test client."""
    from data_collector.main import app

    return TestClient(app)

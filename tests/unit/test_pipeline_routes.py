"""Tests for pipeline API routes."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.gateway.auth import get_current_user
from backend.gateway.main import app
from backend.pipeline.result import PipelineResult
from backend.shared.models import User, UserRole


def _mock_current_user() -> User:
    """Create a mock authenticated user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        display_name="Test User",
        role=UserRole.FREE,
    )
    return user


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = _mock_current_user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _make_design_dict() -> dict:
    """Create a test design dict for API requests."""
    return {
        "name": "Test Pipeline",
        "description": "A test pipeline",
        "agents": [
            {
                "name": "analyzer",
                "role": "analyzer",
                "llm_model": "gpt-4o-mini",
                "description": "Analyzes",
            },
        ],
        "pros": ["fast"],
        "cons": ["simple"],
        "estimated_cost": "~$0.01",
        "complexity": "low",
        "recommended": False,
    }


class TestPipelineRoutes:
    """Tests for pipeline API endpoints."""

    @patch("backend.gateway.routes.pipeline.PipelineOrchestrator")
    def test_execute_pipeline(self, mock_orch_class, client):
        mock_result = PipelineResult(
            design_name="Test Pipeline",
            status="completed",
            agent_results=[],
            total_cost=0.01,
            total_duration=5.0,
            total_tokens=500,
            output="Final output",
        )
        mock_orch = AsyncMock()
        mock_orch.execute = AsyncMock(return_value=mock_result)
        mock_orch_class.return_value = mock_orch

        response = client.post(
            "/api/v1/pipelines/execute",
            json={"design": _make_design_dict()},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["design_name"] == "Test Pipeline"
        assert data["result"]["output"] == "Final output"

    def test_get_nonexistent_pipeline_status(self, client):
        response = client.get("/api/v1/pipelines/nonexistent-id/status")
        assert response.status_code == 404

    def test_get_nonexistent_pipeline_result(self, client):
        response = client.get("/api/v1/pipelines/nonexistent-id/result")
        assert response.status_code == 404

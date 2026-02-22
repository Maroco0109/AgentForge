"""Tests for pipeline execute-direct API endpoint."""

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


class TestExecuteDirect:
    """Tests for POST /api/v1/pipelines/execute-direct."""

    @patch("backend.gateway.routes.pipeline.PipelineOrchestrator")
    def test_execute_direct_success(self, mock_orch_class, client):
        mock_result = PipelineResult(
            design_name="Test Pipeline",
            status="completed",
            agent_results=[],
            total_cost=0.01,
            total_duration=5.0,
            total_tokens=500,
            output="Final output from direct execution",
        )
        mock_orch = AsyncMock()
        mock_orch.execute = AsyncMock(return_value=mock_result)
        mock_orch_class.return_value = mock_orch

        response = client.post(
            "/api/v1/pipelines/execute-direct",
            json={"design": _make_design_dict()},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["design_name"] == "Test Pipeline"
        assert data["result"]["output"] == "Final output from direct execution"

    def test_execute_direct_invalid_design(self, client):
        response = client.post(
            "/api/v1/pipelines/execute-direct",
            json={"design": {"invalid": "data"}},
        )
        assert response.status_code == 422

    def test_execute_direct_no_design(self, client):
        response = client.post(
            "/api/v1/pipelines/execute-direct",
            json={},
        )
        assert response.status_code == 422

    @patch("backend.gateway.routes.pipeline.PipelineOrchestrator")
    def test_execute_direct_shares_logic_with_execute(self, mock_orch_class, client):
        """Both endpoints should produce similar responses for the same input."""
        mock_result = PipelineResult(
            design_name="Test Pipeline",
            status="completed",
            agent_results=[],
            total_cost=0.02,
            total_duration=3.0,
            total_tokens=300,
            output="Shared logic output",
        )
        mock_orch = AsyncMock()
        mock_orch.execute = AsyncMock(return_value=mock_result)
        mock_orch_class.return_value = mock_orch

        design = _make_design_dict()

        resp1 = client.post("/api/v1/pipelines/execute", json={"design": design})
        resp2 = client.post("/api/v1/pipelines/execute-direct", json={"design": design})

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        # Both should return the same structure
        assert resp1.json()["status"] == resp2.json()["status"]
        assert resp1.json()["design_name"] == resp2.json()["design_name"]

    @patch("backend.gateway.routes.pipeline.check_budget")
    def test_execute_direct_budget_exceeded(self, mock_budget, client):
        mock_budget.return_value = (False, 10.0, 5.0)

        response = client.post(
            "/api/v1/pipelines/execute-direct",
            json={"design": _make_design_dict()},
        )
        assert response.status_code == 402
        assert "cost limit" in response.json()["detail"].lower()

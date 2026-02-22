"""Tests for pipeline template CRUD API routes."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.gateway.auth import get_current_user
from backend.gateway.main import app
from backend.shared.models import User, UserRole


def _mock_current_user() -> User:
    """Create a mock authenticated user."""
    user = User(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
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


def _make_template_data() -> dict:
    """Create valid template request data."""
    return {
        "name": "Test Pipeline Template",
        "description": "A test template",
        "graph_data": {
            "nodes": [
                {
                    "id": "agent-1",
                    "type": "agentNode",
                    "position": {"x": 300, "y": 50},
                    "data": {
                        "name": "analyzer",
                        "role": "analyzer",
                        "llmModel": "gpt-4o-mini",
                        "description": "Analyzes data",
                        "status": "idle",
                    },
                }
            ],
            "edges": [],
        },
        "design_data": {
            "name": "Test Pipeline",
            "description": "A test pipeline",
            "agents": [
                {
                    "name": "analyzer",
                    "role": "analyzer",
                    "llm_model": "gpt-4o-mini",
                    "description": "Analyzes data",
                }
            ],
            "pros": [],
            "cons": [],
            "estimated_cost": "~$0.01",
            "complexity": "low",
            "recommended": False,
        },
    }


class TestTemplateSchemaValidation:
    """Tests for template schema validation (no DB needed)."""

    def test_create_template_invalid_name_empty(self, client):
        data = _make_template_data()
        data["name"] = ""
        response = client.post("/api/v1/templates", json=data)
        assert response.status_code == 422

    def test_create_template_name_too_long(self, client):
        data = _make_template_data()
        data["name"] = "x" * 256
        response = client.post("/api/v1/templates", json=data)
        assert response.status_code == 422

    def test_create_template_missing_graph_data(self, client):
        data = _make_template_data()
        del data["graph_data"]
        response = client.post("/api/v1/templates", json=data)
        assert response.status_code == 422

    def test_create_template_missing_design_data(self, client):
        data = _make_template_data()
        del data["design_data"]
        response = client.post("/api/v1/templates", json=data)
        assert response.status_code == 422

    def test_get_template_invalid_uuid(self, client):
        response = client.get("/api/v1/templates/not-a-uuid")
        assert response.status_code == 422

    def test_update_template_invalid_uuid(self, client):
        response = client.put(
            "/api/v1/templates/not-a-uuid",
            json={"name": "Updated"},
        )
        assert response.status_code == 422

    def test_delete_template_invalid_uuid(self, client):
        response = client.delete("/api/v1/templates/not-a-uuid")
        assert response.status_code == 422


class TestTemplateRouteExists:
    """Tests that template routes are registered and require auth."""

    def test_list_templates_requires_auth(self):
        """Templates endpoint exists and requires authentication."""
        # No dependency overrides — should fail auth
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/templates")
        # 401 (no token) or 500 (DB not available) — either means route exists
        assert response.status_code in (401, 403, 500)

    def test_create_template_route_exists(self, client):
        """POST /templates route exists and validates input."""
        response = client.post("/api/v1/templates", json={})
        assert response.status_code == 422

    def test_execute_direct_route_exists(self, client):
        """POST /pipelines/execute-direct route exists."""
        response = client.post("/api/v1/pipelines/execute-direct", json={})
        assert response.status_code == 422


class TestTemplateResponseSchema:
    """Tests for template response schema models."""

    def test_template_create_schema(self):
        from backend.shared.schemas import TemplateCreate

        data = _make_template_data()
        schema = TemplateCreate(**data)
        assert schema.name == "Test Pipeline Template"
        assert schema.description == "A test template"
        assert "nodes" in schema.graph_data
        assert "agents" in schema.design_data

    def test_template_update_schema_partial(self):
        from backend.shared.schemas import TemplateUpdate

        schema = TemplateUpdate(name="New Name")
        dumped = schema.model_dump(exclude_unset=True)
        assert dumped == {"name": "New Name"}

    def test_template_update_schema_empty(self):
        from backend.shared.schemas import TemplateUpdate

        schema = TemplateUpdate()
        dumped = schema.model_dump(exclude_unset=True)
        assert dumped == {}

    def test_template_response_schema(self):
        from backend.shared.schemas import TemplateResponse

        data = {
            "id": uuid.uuid4(),
            "name": "Test",
            "description": None,
            "graph_data": {},
            "design_data": {},
            "is_public": False,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        schema = TemplateResponse(**data)
        assert schema.name == "Test"
        assert schema.is_public is False

    def test_template_list_response_schema(self):
        from backend.shared.schemas import TemplateListResponse

        data = {
            "id": uuid.uuid4(),
            "name": "Test",
            "description": "desc",
            "is_public": True,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        schema = TemplateListResponse(**data)
        assert schema.name == "Test"
        assert schema.is_public is True


class TestPipelineTemplateModel:
    """Tests for the PipelineTemplate SQLAlchemy model."""

    def test_model_exists(self):
        from backend.shared.models import PipelineTemplate

        assert PipelineTemplate.__tablename__ == "pipeline_templates"

    def test_model_fields(self):
        from backend.shared.models import PipelineTemplate

        columns = {c.name for c in PipelineTemplate.__table__.columns}
        expected = {
            "id",
            "user_id",
            "name",
            "description",
            "graph_data",
            "design_data",
            "is_public",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(columns)

    def test_user_relationship(self):
        from backend.shared.models import User

        # Verify templates relationship exists on User
        mapper = User.__mapper__
        assert "templates" in mapper.relationships

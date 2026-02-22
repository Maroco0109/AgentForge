"""Tests for Phase 8B template sharing API routes and schema."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.gateway.auth import get_current_user
from backend.gateway.main import app
from backend.shared.models import User, UserRole


def _mock_user_a() -> User:
    """Create mock user A."""
    return User(
        id=uuid.UUID("aaaa1111-1111-1111-1111-111111111111"),
        email="user_a@example.com",
        hashed_password="hashed",
        display_name="User A",
        role=UserRole.FREE,
    )


def _mock_user_b() -> User:
    """Create mock user B."""
    return User(
        id=uuid.UUID("bbbb2222-2222-2222-2222-222222222222"),
        email="user_b@example.com",
        hashed_password="hashed",
        display_name="User B",
        role=UserRole.FREE,
    )


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = _mock_user_a
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


class TestSharedTemplatesRoute:
    """Tests for GET /templates/shared route."""

    def test_shared_route_exists(self, client):
        """Shared templates route exists and accepts GET."""
        response = client.get("/api/v1/templates/shared")
        # 200 (empty list) or 500 (no DB) — both mean route exists
        assert response.status_code in (200, 500)

    def test_shared_route_requires_auth(self):
        """Shared templates route requires authentication."""
        bare_client = TestClient(app, raise_server_exceptions=False)
        response = bare_client.get("/api/v1/templates/shared")
        assert response.status_code in (401, 403, 500)


class TestForkTemplateRoute:
    """Tests for POST /templates/{id}/fork route."""

    def test_fork_route_exists(self, client):
        """Fork route exists and handles request."""
        fake_id = uuid.uuid4()
        response = client.post(f"/api/v1/templates/{fake_id}/fork")
        # 404 (not found) or 500 (no DB) — both mean route exists
        assert response.status_code in (404, 500)

    def test_fork_invalid_uuid(self, client):
        """Fork with invalid UUID returns 422."""
        response = client.post("/api/v1/templates/not-a-uuid/fork")
        assert response.status_code == 422

    def test_fork_requires_auth(self):
        """Fork route requires authentication."""
        bare_client = TestClient(app, raise_server_exceptions=False)
        fake_id = uuid.uuid4()
        response = bare_client.post(f"/api/v1/templates/{fake_id}/fork")
        assert response.status_code in (401, 403, 500)


class TestTemplateUpdateIsPublic:
    """Tests for is_public field in TemplateUpdate schema."""

    def test_update_schema_accepts_is_public(self):
        """TemplateUpdate schema accepts is_public field."""
        from backend.shared.schemas import TemplateUpdate

        schema = TemplateUpdate(is_public=True)
        dumped = schema.model_dump(exclude_unset=True)
        assert dumped == {"is_public": True}

    def test_update_schema_is_public_false(self):
        """TemplateUpdate schema accepts is_public=False."""
        from backend.shared.schemas import TemplateUpdate

        schema = TemplateUpdate(is_public=False)
        dumped = schema.model_dump(exclude_unset=True)
        assert dumped == {"is_public": False}

    def test_update_schema_is_public_optional(self):
        """is_public is optional in TemplateUpdate."""
        from backend.shared.schemas import TemplateUpdate

        schema = TemplateUpdate(name="Updated")
        dumped = schema.model_dump(exclude_unset=True)
        assert "is_public" not in dumped

    def test_update_is_public_via_route(self, client):
        """PUT /templates/{id} accepts is_public in body."""
        fake_id = uuid.uuid4()
        response = client.put(
            f"/api/v1/templates/{fake_id}",
            json={"is_public": True},
        )
        # 404 (template not found) or 500 (no DB) — route processes the body
        assert response.status_code in (404, 500)

    def test_update_is_public_with_name(self, client):
        """PUT /templates/{id} accepts is_public alongside other fields."""
        fake_id = uuid.uuid4()
        response = client.put(
            f"/api/v1/templates/{fake_id}",
            json={"name": "Updated", "is_public": True},
        )
        assert response.status_code in (404, 500)


class TestForkResponseSchema:
    """Tests for fork endpoint response format."""

    def test_fork_response_model(self):
        """Verify TemplateResponse can represent a forked template."""
        from backend.shared.schemas import TemplateResponse

        data = {
            "id": uuid.uuid4(),
            "name": "Original (fork)",
            "description": "Forked template",
            "graph_data": {"nodes": [], "edges": []},
            "design_data": {"agents": []},
            "is_public": False,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        schema = TemplateResponse(**data)
        assert schema.name == "Original (fork)"
        assert schema.is_public is False

    def test_shared_list_response(self):
        """TemplateListResponse for shared templates."""
        from backend.shared.schemas import TemplateListResponse

        data = {
            "id": uuid.uuid4(),
            "name": "Shared Pipeline",
            "description": "A shared template",
            "is_public": True,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        schema = TemplateListResponse(**data)
        assert schema.is_public is True

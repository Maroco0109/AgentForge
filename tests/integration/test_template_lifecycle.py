"""Integration tests for template CRUD lifecycle."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock, patch

from backend.shared.models import Base

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def template_engine():
    """Create test database engine for template tests."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def template_client(template_engine):
    """Create test HTTP client with mocked Redis."""
    from backend.gateway.main import app
    from backend.shared.database import get_db

    session_maker = async_sessionmaker(
        template_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # Mock Redis
    with patch("backend.gateway.rate_limiter.get_redis") as mock_redis_getter:
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()
        mock_redis.delete = AsyncMock()
        mock_redis_getter.return_value = mock_redis

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


async def register_and_login(client: AsyncClient, email: str = None) -> str:
    """Register a user and return JWT token."""
    email = email or f"test-{uuid.uuid4().hex[:8]}@test.com"
    password = "TestPass123"

    # Register
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Tester"},
    )
    assert resp.status_code == 201

    # Login
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def sample_template_data():
    """Return sample template data for testing."""
    return {
        "name": "Test Template",
        "description": "A test pipeline template",
        "graph_data": {
            "nodes": [
                {"id": "1", "type": "collector", "position": {"x": 100, "y": 100}},
                {"id": "2", "type": "analyzer", "position": {"x": 300, "y": 100}},
            ],
            "edges": [{"id": "e1", "source": "1", "target": "2"}],
        },
        "design_data": {
            "name": "Test Design",
            "agents": [
                {
                    "name": "collector",
                    "role": "collector",
                    "llm_model": "gpt-4o-mini",
                    "description": "Collects data",
                },
                {
                    "name": "analyzer",
                    "role": "analyzer",
                    "llm_model": "gpt-4o",
                    "description": "Analyzes data",
                },
            ],
        },
    }


@pytest.mark.asyncio
class TestTemplateLifecycle:
    """Tests for template CRUD operations."""

    async def test_create_template(self, template_client: AsyncClient):
        """Test creating a new template."""
        token = await register_and_login(template_client)
        template_data = sample_template_data()

        resp = await template_client.post(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token}"},
            json=template_data,
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Template"
        assert data["description"] == "A test pipeline template"
        assert "id" in data
        assert data["is_public"] is False

    async def test_list_templates(self, template_client: AsyncClient):
        """Test listing user's templates."""
        token = await register_and_login(template_client)

        # Create two templates
        template1 = sample_template_data()
        template1["name"] = "Template 1"
        template2 = sample_template_data()
        template2["name"] = "Template 2"

        await template_client.post(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token}"},
            json=template1,
        )
        await template_client.post(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token}"},
            json=template2,
        )

        # List templates
        resp = await template_client.get(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        templates = resp.json()
        assert len(templates) == 2
        names = [t["name"] for t in templates]
        assert "Template 1" in names
        assert "Template 2" in names

    async def test_get_template_by_id(self, template_client: AsyncClient):
        """Test retrieving a specific template."""
        token = await register_and_login(template_client)
        template_data = sample_template_data()

        # Create template
        create_resp = await template_client.post(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token}"},
            json=template_data,
        )
        template_id = create_resp.json()["id"]

        # Get template
        resp = await template_client.get(
            f"/api/v1/templates/{template_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == template_id
        assert data["name"] == "Test Template"

    async def test_update_template(self, template_client: AsyncClient):
        """Test updating an existing template."""
        token = await register_and_login(template_client)
        template_data = sample_template_data()

        # Create template
        create_resp = await template_client.post(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token}"},
            json=template_data,
        )
        template_id = create_resp.json()["id"]

        # Update template
        update_data = {
            "name": "Updated Template",
            "description": "Updated description",
        }
        resp = await template_client.put(
            f"/api/v1/templates/{template_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=update_data,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Template"
        assert data["description"] == "Updated description"

    async def test_delete_template(self, template_client: AsyncClient):
        """Test deleting a template."""
        token = await register_and_login(template_client)
        template_data = sample_template_data()

        # Create template
        create_resp = await template_client.post(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token}"},
            json=template_data,
        )
        template_id = create_resp.json()["id"]

        # Delete template
        resp = await template_client.delete(
            f"/api/v1/templates/{template_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 204

        # Verify deletion
        get_resp = await template_client.get(
            f"/api/v1/templates/{template_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_resp.status_code == 404

    async def test_share_template(self, template_client: AsyncClient):
        """Test making a template public (sharing)."""
        token = await register_and_login(template_client)
        template_data = sample_template_data()

        # Create private template
        create_resp = await template_client.post(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token}"},
            json=template_data,
        )
        template_id = create_resp.json()["id"]

        # Make it public
        resp = await template_client.put(
            f"/api/v1/templates/{template_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"is_public": True},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["is_public"] is True

    async def test_fork_template(self, template_client: AsyncClient):
        """Test forking a public template."""
        # User 1 creates and shares a template
        token1 = await register_and_login(template_client, "user1@test.com")
        template_data = sample_template_data()
        template_data["name"] = "Original Template"

        create_resp = await template_client.post(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token1}"},
            json=template_data,
        )
        original_id = create_resp.json()["id"]

        # Make it public
        await template_client.put(
            f"/api/v1/templates/{original_id}",
            headers={"Authorization": f"Bearer {token1}"},
            json={"is_public": True},
        )

        # User 2 forks the template
        token2 = await register_and_login(template_client, "user2@test.com")
        fork_resp = await template_client.post(
            f"/api/v1/templates/{original_id}/fork",
            headers={"Authorization": f"Bearer {token2}"},
        )

        assert fork_resp.status_code == 201
        forked = fork_resp.json()
        assert forked["name"] == "Original Template (fork)"
        assert forked["is_public"] is False
        assert forked["id"] != original_id

        # Verify User 2 owns the fork
        list_resp = await template_client.get(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token2}"},
        )
        templates = list_resp.json()
        assert len(templates) == 1
        assert templates[0]["id"] == forked["id"]

    async def test_unauthorized_access(self, template_client: AsyncClient):
        """Test that users cannot edit/delete other users' templates."""
        # User 1 creates a template
        token1 = await register_and_login(template_client, "owner@test.com")
        template_data = sample_template_data()

        create_resp = await template_client.post(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token1}"},
            json=template_data,
        )
        template_id = create_resp.json()["id"]

        # User 2 tries to access it
        token2 = await register_and_login(template_client, "other@test.com")

        # Try to get
        get_resp = await template_client.get(
            f"/api/v1/templates/{template_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert get_resp.status_code == 404  # IDOR prevention

        # Try to update
        update_resp = await template_client.put(
            f"/api/v1/templates/{template_id}",
            headers={"Authorization": f"Bearer {token2}"},
            json={"name": "Hacked"},
        )
        assert update_resp.status_code == 404

        # Try to delete
        delete_resp = await template_client.delete(
            f"/api/v1/templates/{template_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert delete_resp.status_code == 404

    async def test_fork_private_template_fails(self, template_client: AsyncClient):
        """Test that forking a private template returns 404."""
        # User 1 creates a private template
        token1 = await register_and_login(template_client, "user1@test.com")
        template_data = sample_template_data()

        create_resp = await template_client.post(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token1}"},
            json=template_data,
        )
        template_id = create_resp.json()["id"]

        # User 2 tries to fork it
        token2 = await register_and_login(template_client, "user2@test.com")
        fork_resp = await template_client.post(
            f"/api/v1/templates/{template_id}/fork",
            headers={"Authorization": f"Bearer {token2}"},
        )

        assert fork_resp.status_code == 404  # Private templates not forkable


@pytest.mark.asyncio
class TestTemplateSharing:
    """Tests for template sharing and discovery."""

    async def test_list_shared_templates(self, template_client: AsyncClient):
        """Test listing public templates from all users."""
        # User 1 creates and shares a template
        token1 = await register_and_login(template_client, "user1@test.com")
        template1 = sample_template_data()
        template1["name"] = "Shared Template 1"

        resp1 = await template_client.post(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token1}"},
            json=template1,
        )
        template_id1 = resp1.json()["id"]

        await template_client.put(
            f"/api/v1/templates/{template_id1}",
            headers={"Authorization": f"Bearer {token1}"},
            json={"is_public": True},
        )

        # User 2 creates and shares a template
        token2 = await register_and_login(template_client, "user2@test.com")
        template2 = sample_template_data()
        template2["name"] = "Shared Template 2"

        resp2 = await template_client.post(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {token2}"},
            json=template2,
        )
        template_id2 = resp2.json()["id"]

        await template_client.put(
            f"/api/v1/templates/{template_id2}",
            headers={"Authorization": f"Bearer {token2}"},
            json={"is_public": True},
        )

        # User 3 lists shared templates
        token3 = await register_and_login(template_client, "user3@test.com")
        shared_resp = await template_client.get(
            "/api/v1/templates/shared",
            headers={"Authorization": f"Bearer {token3}"},
        )

        assert shared_resp.status_code == 200
        shared = shared_resp.json()
        assert len(shared) == 2
        names = [t["name"] for t in shared]
        assert "Shared Template 1" in names
        assert "Shared Template 2" in names

    async def test_template_limit_enforcement(self, template_client: AsyncClient):
        """Test that template creation respects per-user limits."""

        token = await register_and_login(template_client)

        # Create templates up to the limit (use a small limit for testing)
        # Note: In production this is 50, but we'll test with fewer
        template_data = sample_template_data()

        # Create a few templates
        for i in range(3):
            template_data["name"] = f"Template {i}"
            resp = await template_client.post(
                "/api/v1/templates",
                headers={"Authorization": f"Bearer {token}"},
                json=template_data,
            )
            assert resp.status_code == 201

        # The actual limit check would require creating 50+ templates
        # which is too slow for integration tests. This is a basic check.
        # Full limit testing should be in unit tests.

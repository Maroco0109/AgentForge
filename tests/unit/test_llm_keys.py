"""Tests for LLM key management routes."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.gateway.auth import get_current_user
from backend.gateway.routes.llm_keys import router
from backend.shared.database import get_db


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.role = "free"
    return user


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_llm_key(mock_user):
    """Create a mock LLM key."""
    key = MagicMock()
    key.id = uuid.uuid4()
    key.user_id = mock_user.id
    key.provider = MagicMock()
    key.provider.value = "openai"
    key.key_prefix = "sk-proj-Ab..."
    key.is_active = True
    key.is_valid = True
    key.last_used_at = None
    key.last_validated_at = datetime.now(timezone.utc)
    key.created_at = datetime.now(timezone.utc)
    key.updated_at = datetime.now(timezone.utc)
    key.encrypted_key = b"encrypted"
    key.nonce = b"nonce12bytes"
    return key


@pytest.fixture
def app(mock_user, mock_db):
    """Create test FastAPI app with dependency overrides."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")

    async def override_get_current_user():
        return mock_user

    async def override_get_db():
        yield mock_db

    test_app.dependency_overrides[get_current_user] = override_get_current_user
    test_app.dependency_overrides[get_db] = override_get_db
    return test_app


class TestRegisterLLMKey:
    """Test POST /api/v1/llm-keys."""

    @pytest.mark.asyncio
    async def test_register_valid_key(self, app, mock_user, mock_db, mock_llm_key):
        """Test registering a valid LLM key."""
        with (
            patch(
                "backend.gateway.routes.llm_keys.validate_provider_key",
                new_callable=AsyncMock,
            ) as mock_validate,
            patch("backend.gateway.routes.llm_keys.encrypt_api_key") as mock_encrypt,
            patch("backend.gateway.routes.llm_keys.invalidate_user_cache"),
        ):
            mock_validate.return_value = (True, "Valid", ["gpt-4o"])
            mock_encrypt.return_value = (b"encrypted", b"nonce12bytes")

            # Mock DB: no existing key
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock(
                side_effect=lambda obj: (
                    setattr(obj, "id", mock_llm_key.id)
                    or setattr(obj, "created_at", mock_llm_key.created_at)
                    or setattr(obj, "updated_at", mock_llm_key.updated_at)
                )
            )

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/llm-keys",
                    json={"provider": "openai", "api_key": "sk-proj-test1234567890"},
                )

            assert response.status_code == 201
            data = response.json()
            assert data["provider"] == "openai"
            assert data["is_valid"] is True

    @pytest.mark.asyncio
    async def test_register_invalid_provider(self, app, mock_user, mock_db):
        """Test registering with unsupported provider."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/llm-keys",
                json={"provider": "invalid_provider", "api_key": "sk-test1234567890"},
            )

        assert response.status_code == 400
        assert "Unsupported provider" in response.json()["detail"]


class TestListLLMKeys:
    """Test GET /api/v1/llm-keys."""

    @pytest.mark.asyncio
    async def test_list_keys(self, app, mock_user, mock_db, mock_llm_key):
        """Test listing user's LLM keys."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_llm_key]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/llm-keys")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["provider"] == "openai"
        assert "api_key" not in data[0]  # Key must not be exposed


class TestDeleteLLMKey:
    """Test DELETE /api/v1/llm-keys/{key_id}."""

    @pytest.mark.asyncio
    async def test_delete_key(self, app, mock_user, mock_db, mock_llm_key):
        """Test deleting own key."""
        with patch("backend.gateway.routes.llm_keys.invalidate_user_cache"):
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_llm_key
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.delete = AsyncMock()
            mock_db.commit = AsyncMock()

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.delete(f"/api/v1/llm-keys/{mock_llm_key.id}")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key_returns_404(self, app, mock_user, mock_db):
        """Test IDOR: deleting non-existent or other user's key returns 404."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/api/v1/llm-keys/{uuid.uuid4()}")

        assert response.status_code == 404


class TestValidateLLMKey:
    """Test POST /api/v1/llm-keys/{key_id}/validate."""

    @pytest.mark.asyncio
    async def test_validate_key(self, app, mock_user, mock_db, mock_llm_key):
        """Test re-validating an existing key."""
        with (
            patch("backend.gateway.routes.llm_keys.decrypt_api_key") as mock_decrypt,
            patch(
                "backend.gateway.routes.llm_keys.validate_provider_key",
                new_callable=AsyncMock,
            ) as mock_validate,
            patch("backend.gateway.routes.llm_keys.invalidate_user_cache"),
        ):
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_llm_key
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.commit = AsyncMock()

            mock_decrypt.return_value = "sk-proj-test1234567890"
            mock_validate.return_value = (True, "OpenAI key is valid", ["gpt-4o"])

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/v1/llm-keys/{mock_llm_key.id}/validate"
                )

            assert response.status_code == 200
            data = response.json()
            assert data["is_valid"] is True
            assert "gpt-4o" in data["models_available"]

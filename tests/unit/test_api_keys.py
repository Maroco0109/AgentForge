"""Unit tests for API Key management and authentication."""

import hashlib
import uuid

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def auth_headers(client):
    """Create a user and return auth headers with JWT token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "apikey@test.com",
            "password": "TestPass1",
            "display_name": "API Key User",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def second_user_headers(client):
    """Create a second user and return auth headers."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "second@test.com",
            "password": "TestPass2",
            "display_name": "Second User",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAPIKeyCRUD:
    """Tests for API Key CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_api_key(self, client, auth_headers):
        """Test creating an API key returns correct structure."""
        response = await client.post(
            "/api/v1/api-keys",
            json={"name": "Test Key"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "name" in data
        assert "key" in data
        assert "key_prefix" in data
        assert "is_active" in data
        assert "created_at" in data
        assert "last_used_at" in data

        # Verify values
        assert data["name"] == "Test Key"
        assert data["is_active"] is True
        assert data["last_used_at"] is None

        # Verify key format (sk- prefix + 32 hex chars)
        assert data["key"].startswith("sk-")
        assert len(data["key"]) == 35  # "sk-" + 32 hex chars

        # Verify key_prefix matches first 11 chars of key
        assert data["key_prefix"] == data["key"][:11]

    @pytest.mark.asyncio
    async def test_create_api_key_returns_key_once(self, client, auth_headers):
        """Test that the plaintext key is only returned on creation."""
        # Create API key
        create_response = await client.post(
            "/api/v1/api-keys",
            json={"name": "Once Key"},
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        create_data = create_response.json()
        assert "key" in create_data

        # List API keys
        list_response = await client.get("/api/v1/api-keys", headers=auth_headers)
        assert list_response.status_code == 200
        list_data = list_response.json()

        # Verify key is NOT in list response
        assert len(list_data) == 1
        assert "key" not in list_data[0]
        assert "key_prefix" in list_data[0]

    @pytest.mark.asyncio
    async def test_list_api_keys(self, client, auth_headers):
        """Test listing API keys returns all user's keys."""
        # Create two API keys
        await client.post(
            "/api/v1/api-keys",
            json={"name": "Key 1"},
            headers=auth_headers,
        )
        await client.post(
            "/api/v1/api-keys",
            json={"name": "Key 2"},
            headers=auth_headers,
        )

        # List API keys
        response = await client.get("/api/v1/api-keys", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Verify count
        assert len(data) == 2

        # Verify structure (no plaintext key field)
        for key_data in data:
            assert "id" in key_data
            assert "name" in key_data
            assert "key_prefix" in key_data
            assert "is_active" in key_data
            assert "created_at" in key_data
            assert "last_used_at" in key_data
            assert "key" not in key_data

        # Verify names
        names = {key_data["name"] for key_data in data}
        assert names == {"Key 1", "Key 2"}

    @pytest.mark.asyncio
    async def test_list_api_keys_only_own(
        self, client, auth_headers, second_user_headers
    ):
        """Test that users can only see their own API keys."""
        # User 1 creates a key
        await client.post(
            "/api/v1/api-keys",
            json={"name": "User 1 Key"},
            headers=auth_headers,
        )

        # User 2 creates a key
        await client.post(
            "/api/v1/api-keys",
            json={"name": "User 2 Key"},
            headers=second_user_headers,
        )

        # User 1 lists keys
        response1 = await client.get("/api/v1/api-keys", headers=auth_headers)
        data1 = response1.json()
        assert len(data1) == 1
        assert data1[0]["name"] == "User 1 Key"

        # User 2 lists keys
        response2 = await client.get("/api/v1/api-keys", headers=second_user_headers)
        data2 = response2.json()
        assert len(data2) == 1
        assert data2[0]["name"] == "User 2 Key"

    @pytest.mark.asyncio
    async def test_delete_api_key(self, client, auth_headers):
        """Test deleting an API key."""
        # Create a key
        create_response = await client.post(
            "/api/v1/api-keys",
            json={"name": "Delete Me"},
            headers=auth_headers,
        )
        key_id = create_response.json()["id"]

        # Delete the key
        delete_response = await client.delete(
            f"/api/v1/api-keys/{key_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        # Verify it's gone
        list_response = await client.get("/api/v1/api-keys", headers=auth_headers)
        data = list_response.json()
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_delete_api_key_not_found(self, client, auth_headers):
        """Test deleting non-existent API key returns 404."""
        fake_id = str(uuid.uuid4())
        response = await client.delete(
            f"/api/v1/api-keys/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_api_key_not_owner(
        self, client, auth_headers, second_user_headers
    ):
        """Test that users cannot delete other users' API keys."""
        # User 1 creates a key
        create_response = await client.post(
            "/api/v1/api-keys",
            json={"name": "User 1 Key"},
            headers=auth_headers,
        )
        key_id = create_response.json()["id"]

        # User 2 tries to delete User 1's key
        delete_response = await client.delete(
            f"/api/v1/api-keys/{key_id}",
            headers=second_user_headers,
        )
        assert delete_response.status_code == 404
        assert "not found" in delete_response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_api_key_name_validation(self, client, auth_headers):
        """Test that empty API key name fails validation."""
        response = await client.post(
            "/api/v1/api-keys",
            json={"name": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestAPIKeyAuthentication:
    """Tests for API Key authentication."""

    @pytest.mark.asyncio
    async def test_api_key_auth(self, client, auth_headers):
        """Test using API key to authenticate requests."""
        # Create API key
        create_response = await client.post(
            "/api/v1/api-keys",
            json={"name": "Auth Test Key"},
            headers=auth_headers,
        )
        api_key = create_response.json()["key"]

        # Use API key to call /me endpoint
        response = await client.get(
            "/api/v1/auth/me",
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify correct user
        assert data["email"] == "apikey@test.com"
        assert data["display_name"] == "API Key User"

    @pytest.mark.asyncio
    async def test_api_key_auth_invalid(self, client):
        """Test that invalid API key returns 401."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"X-API-Key": "sk-invalid_key_12345678901234567890"},
        )
        assert response.status_code == 401
        assert "invalid api key" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_api_key_auth_updates_last_used(self, client, auth_headers):
        """Test that using API key updates last_used_at timestamp."""
        # Create API key
        create_response = await client.post(
            "/api/v1/api-keys",
            json={"name": "Usage Test Key"},
            headers=auth_headers,
        )
        api_key = create_response.json()["key"]
        key_id = create_response.json()["id"]

        # Verify last_used_at is None initially
        list_response = await client.get("/api/v1/api-keys", headers=auth_headers)
        initial_data = list_response.json()[0]
        assert initial_data["last_used_at"] is None

        # Use the API key
        await client.get(
            "/api/v1/auth/me",
            headers={"X-API-Key": api_key},
        )

        # Check last_used_at is now set
        list_response = await client.get("/api/v1/api-keys", headers=auth_headers)
        keys = list_response.json()
        used_key = next(k for k in keys if k["id"] == key_id)
        assert used_key["last_used_at"] is not None

    @pytest.mark.asyncio
    async def test_jwt_auth_still_works(self, client, auth_headers):
        """Test that JWT Bearer token authentication still works."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "apikey@test.com"

    @pytest.mark.asyncio
    async def test_no_auth_returns_401(self, client):
        """Test that requests without authentication return 401."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestAPIKeyHashStorage:
    """Tests for API key hash storage and security."""

    @pytest.mark.asyncio
    async def test_api_key_hash_storage(self, client, auth_headers, test_session):
        """Test that API key is stored as SHA-256 hash, not plaintext."""
        from sqlalchemy import select

        from backend.shared.models import APIKey

        # Create API key
        create_response = await client.post(
            "/api/v1/api-keys",
            json={"name": "Hash Test Key"},
            headers=auth_headers,
        )
        plaintext_key = create_response.json()["key"]
        key_id = uuid.UUID(create_response.json()["id"])

        # Fetch from database using ORM
        result = await test_session.execute(select(APIKey).where(APIKey.id == key_id))
        api_key = result.scalar_one()
        stored_hash = api_key.key_hash

        # Verify it's a hash, not plaintext
        assert stored_hash != plaintext_key

        # Verify it's a SHA-256 hash (64 hex chars)
        assert len(stored_hash) == 64
        assert all(c in "0123456789abcdef" for c in stored_hash)

        # Verify the hash matches
        expected_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()
        assert stored_hash == expected_hash

    @pytest.mark.asyncio
    async def test_api_key_prefix_stored(self, client, auth_headers, test_session):
        """Test that first 11 characters are stored as prefix."""
        from sqlalchemy import select

        from backend.shared.models import APIKey

        # Create API key
        create_response = await client.post(
            "/api/v1/api-keys",
            json={"name": "Prefix Test Key"},
            headers=auth_headers,
        )
        plaintext_key = create_response.json()["key"]
        key_id = uuid.UUID(create_response.json()["id"])

        # Fetch from database using ORM
        result = await test_session.execute(select(APIKey).where(APIKey.id == key_id))
        api_key = result.scalar_one()
        stored_prefix = api_key.key_prefix

        # Verify prefix matches first 11 chars
        assert stored_prefix == plaintext_key[:11]
        assert len(stored_prefix) == 11
        assert stored_prefix.startswith("sk-")

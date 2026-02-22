"""Tests for conversation endpoints with authentication."""

import uuid

import pytest

from backend.gateway.auth import create_access_token


def _auth_header(user_id: str, role: str = "free") -> dict:
    """Create authorization header with JWT token."""
    token = create_access_token(user_id, role)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_conversation(client, test_user):
    """Test creating a new conversation with auth."""
    headers = _auth_header(str(test_user.id))
    response = await client.post(
        "/api/v1/conversations",
        json={"title": "Test Conversation"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Conversation"
    assert data["status"] == "active"
    assert data["user_id"] == str(test_user.id)
    assert "id" in data


@pytest.mark.asyncio
async def test_create_conversation_no_auth(client):
    """Test creating conversation without auth returns 403."""
    response = await client.post(
        "/api/v1/conversations",
        json={"title": "No Auth Conv"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_conversations_filters_by_user(client, test_user):
    """Test listing conversations only returns user's own."""
    headers = _auth_header(str(test_user.id))

    # Create two conversations
    await client.post(
        "/api/v1/conversations",
        json={"title": "Conv 1"},
        headers=headers,
    )
    await client.post(
        "/api/v1/conversations",
        json={"title": "Conv 2"},
        headers=headers,
    )

    response = await client.get("/api/v1/conversations", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    for conv in data:
        assert conv["user_id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_list_conversations_no_auth(client):
    """Test listing conversations without auth returns 403."""
    response = await client.get("/api/v1/conversations")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_conversation(client, test_user):
    """Test getting a specific conversation with auth."""
    headers = _auth_header(str(test_user.id))

    # Create conversation
    create_resp = await client.post(
        "/api/v1/conversations",
        json={"title": "Get Test"},
        headers=headers,
    )
    conv_id = create_resp.json()["id"]

    # Get it
    response = await client.get(f"/api/v1/conversations/{conv_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Get Test"
    assert "messages" in data


@pytest.mark.asyncio
async def test_get_conversation_not_found(client, test_user):
    """Test getting a non-existent conversation returns 404."""
    headers = _auth_header(str(test_user.id))
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/conversations/{fake_id}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_conversation_wrong_user(client, test_user, test_session):
    """Test getting another user's conversation returns 404."""
    from backend.shared.models import User, UserRole

    # Create another user
    other_user = User(
        id=uuid.uuid4(),
        email="other@example.com",
        hashed_password="hashed",
        display_name="Other User",
        role=UserRole.FREE,
    )
    test_session.add(other_user)
    await test_session.commit()
    await test_session.refresh(other_user)

    # Create conversation as test_user
    headers = _auth_header(str(test_user.id))
    create_resp = await client.post(
        "/api/v1/conversations",
        json={"title": "Private Conv"},
        headers=headers,
    )
    conv_id = create_resp.json()["id"]

    # Try to access as other_user
    other_headers = _auth_header(str(other_user.id))
    response = await client.get(
        f"/api/v1/conversations/{conv_id}", headers=other_headers
    )
    assert response.status_code == 404

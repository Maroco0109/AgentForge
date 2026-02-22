"""Unit tests for authentication API endpoints."""

import uuid

import pytest

from backend.gateway.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
)
from backend.shared.models import User, UserRole


@pytest.mark.asyncio
async def test_register_success(client):
    """Test successful user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "display_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Verify tokens are JWT format (3 parts separated by dots)
    assert len(data["access_token"].split(".")) == 3
    assert len(data["refresh_token"].split(".")) == 3


@pytest.mark.asyncio
async def test_register_duplicate_email(client, test_user):
    """Test registration with already registered email."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user.email,  # Already exists in test_user fixture
            "password": "AnotherPass123",
            "display_name": "Duplicate User",
        },
    )
    assert response.status_code == 409
    data = response.json()
    assert "already registered" in data["detail"].lower()


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    """Test registration with invalid email format."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "SecurePass123",
            "display_name": "Test User",
        },
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_register_missing_fields(client):
    """Test registration with missing required fields."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            # Missing password and display_name
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client, test_session):
    """Test successful login with correct credentials."""
    # Create user with known password
    password = "TestPassword123"
    user = User(
        id=uuid.uuid4(),
        email="login@example.com",
        hashed_password=hash_password(password),
        display_name="Login Test",
        role=UserRole.FREE,
    )
    test_session.add(user)
    await test_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": password,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_session):
    """Test login with incorrect password."""
    password = "CorrectPassword123"
    user = User(
        id=uuid.uuid4(),
        email="wrongpass@example.com",
        hashed_password=hash_password(password),
        display_name="Wrong Pass Test",
        role=UserRole.FREE,
    )
    test_session.add(user)
    await test_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "WrongPassword456",
        },
    )
    assert response.status_code == 401
    data = response.json()
    assert "invalid" in data["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """Test login with non-existent email."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "SomePassword123",
        },
    )
    assert response.status_code == 401
    data = response.json()
    assert "invalid" in data["detail"].lower()


@pytest.mark.asyncio
async def test_login_invalid_email_format(client):
    """Test login with invalid email format."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "not-an-email",
            "password": "SomePassword123",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refresh_token_success(client, test_session):
    """Test refreshing access token with valid refresh token."""
    # Create user
    user = User(
        id=uuid.uuid4(),
        email="refresh@example.com",
        hashed_password=hash_password("password"),
        display_name="Refresh Test",
        role=UserRole.PRO,
    )
    test_session.add(user)
    await test_session.commit()

    # Generate refresh token
    refresh_token = create_refresh_token(str(user.id))

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Tokens are valid JWT format
    assert len(data["access_token"].split(".")) == 3
    assert len(data["refresh_token"].split(".")) == 3


@pytest.mark.asyncio
async def test_refresh_token_with_access_token(client, test_session):
    """Test that access token is rejected for refresh endpoint."""
    # Create user
    user = User(
        id=uuid.uuid4(),
        email="wrongtype@example.com",
        hashed_password=hash_password("password"),
        display_name="Wrong Type Test",
        role=UserRole.FREE,
    )
    test_session.add(user)
    await test_session.commit()

    # Try to use access token instead of refresh token
    access_token = create_access_token(str(user.id), user.role.value)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401
    data = response.json()
    assert "invalid token type" in data["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_token_nonexistent_user(client):
    """Test refresh token for non-existent user."""
    fake_user_id = str(uuid.uuid4())
    refresh_token = create_refresh_token(fake_user_id)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 401
    data = response.json()
    assert "user not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_token_invalid(client):
    """Test refresh endpoint with invalid token."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_success(client, test_session):
    """Test getting current user profile with valid token."""
    # Create user
    user = User(
        id=uuid.uuid4(),
        email="me@example.com",
        hashed_password=hash_password("password"),
        display_name="Me Test",
        role=UserRole.ADMIN,
    )
    test_session.add(user)
    await test_session.commit()

    # Generate access token
    access_token = create_access_token(str(user.id), user.role.value)

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["display_name"] == "Me Test"
    assert data["role"] == "admin"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_me_without_token(client):
    """Test /me endpoint without authentication token."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401  # HTTPBearer(auto_error=False) + manual check


@pytest.mark.asyncio
async def test_get_me_invalid_token(client):
    """Test /me endpoint with invalid token."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_refresh_token(client, test_session):
    """Test /me endpoint rejects refresh token (requires access token)."""
    # Create user
    user = User(
        id=uuid.uuid4(),
        email="refreshme@example.com",
        hashed_password=hash_password("password"),
        display_name="Refresh Me Test",
        role=UserRole.FREE,
    )
    test_session.add(user)
    await test_session.commit()

    # Try to use refresh token for /me endpoint
    refresh_token = create_refresh_token(str(user.id))

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "invalid token type" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_me_nonexistent_user(client):
    """Test /me endpoint with token for non-existent user."""
    fake_user_id = str(uuid.uuid4())
    access_token = create_access_token(fake_user_id, "free")

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "user not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_register_creates_free_user(client, test_session):
    """Test that registration creates user with FREE role by default."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "freerole@example.com",
            "password": "TestPass123",
            "display_name": "Free User",
        },
    )
    assert response.status_code == 201

    # Verify user was created with FREE role
    from sqlalchemy import select

    result = await test_session.execute(
        select(User).where(User.email == "freerole@example.com")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.role == UserRole.FREE


@pytest.mark.asyncio
async def test_login_preserves_role_in_token(client, test_session):
    """Test that login includes correct role in token."""
    # Create ADMIN user
    password = "AdminPass123"
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        hashed_password=hash_password(password),
        display_name="Admin User",
        role=UserRole.ADMIN,
    )
    test_session.add(user)
    await test_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": password,
        },
    )
    assert response.status_code == 200

    # Verify role in /me response
    access_token = response.json()["access_token"]
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_token_response_format(client, test_session):
    """Test that token response has correct format."""
    password = "FormatTest123"
    user = User(
        id=uuid.uuid4(),
        email="format@example.com",
        hashed_password=hash_password(password),
        display_name="Format Test",
        role=UserRole.FREE,
    )
    test_session.add(user)
    await test_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "format@example.com",
            "password": password,
        },
    )
    data = response.json()

    # Check all required fields
    assert "access_token" in data
    assert "refresh_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"

    # Check types
    assert isinstance(data["access_token"], str)
    assert isinstance(data["refresh_token"], str)
    assert isinstance(data["token_type"], str)

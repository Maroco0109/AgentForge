"""Unit tests for JWT authentication utilities."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from backend.gateway.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.shared.config import settings


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        password = "test_password_123"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_produces_different_hashes(self):
        """Test that same password produces different hashes (bcrypt salt)."""
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "correct_password"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "correct_password"
        hashed = hash_password(password)
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty(self):
        """Test password verification with empty password."""
        password = "test_password"
        hashed = hash_password(password)
        assert verify_password("", hashed) is False


class TestAccessToken:
    """Tests for JWT access token creation and validation."""

    def test_create_access_token_structure(self):
        """Test that access token has correct structure."""
        user_id = str(uuid.uuid4())
        role = "free"
        token = create_access_token(user_id, role)

        # Decode without verification to check structure
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["sub"] == user_id
        assert payload["role"] == role
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_access_token_expiration(self):
        """Test that access token has correct expiration time."""
        user_id = str(uuid.uuid4())
        role = "free"
        before = datetime.now(timezone.utc)
        token = create_access_token(user_id, role)
        after = datetime.now(timezone.utc)

        payload = jwt.decode(token, options={"verify_signature": False})
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

        # Check expiration is ~30 minutes from now (default setting)
        expected_exp = before + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        assert abs((exp - expected_exp).total_seconds()) < 5

        # Check issued time is approximately now
        assert before <= iat <= after

    def test_decode_valid_access_token(self):
        """Test decoding a valid access token."""
        user_id = str(uuid.uuid4())
        role = "pro"
        token = create_access_token(user_id, role)

        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["role"] == role
        assert payload["type"] == "access"

    def test_decode_expired_token(self):
        """Test that expired token raises HTTPException."""
        user_id = str(uuid.uuid4())
        role = "free"

        # Create token that expired 1 hour ago
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": user_id,
            "role": role,
            "type": "access",
            "exp": expire,
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(
            payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_decode_invalid_token(self):
        """Test that invalid token raises HTTPException."""
        invalid_token = "invalid.jwt.token"

        with pytest.raises(HTTPException) as exc_info:
            decode_token(invalid_token)
        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()

    def test_decode_token_wrong_signature(self):
        """Test that token with wrong signature raises HTTPException."""
        user_id = str(uuid.uuid4())
        role = "free"
        payload = {
            "sub": user_id,
            "role": role,
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "iat": datetime.now(timezone.utc),
        }
        # Sign with different key
        wrong_token = jwt.encode(
            payload, "wrong_secret_key", algorithm=settings.JWT_ALGORITHM
        )

        with pytest.raises(HTTPException) as exc_info:
            decode_token(wrong_token)
        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower()


class TestRefreshToken:
    """Tests for JWT refresh token creation and validation."""

    def test_create_refresh_token_structure(self):
        """Test that refresh token has correct structure."""
        user_id = str(uuid.uuid4())
        token = create_refresh_token(user_id)

        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload
        # Refresh tokens should not have role
        assert "role" not in payload

    def test_create_refresh_token_expiration(self):
        """Test that refresh token has correct expiration time."""
        user_id = str(uuid.uuid4())
        before = datetime.now(timezone.utc)
        token = create_refresh_token(user_id)
        after = datetime.now(timezone.utc)

        payload = jwt.decode(token, options={"verify_signature": False})
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

        # Check expiration is ~7 days from now (default setting)
        expected_exp = before + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        assert abs((exp - expected_exp).total_seconds()) < 5

        # Check issued time is approximately now
        assert before <= iat <= after

    def test_decode_valid_refresh_token(self):
        """Test decoding a valid refresh token."""
        user_id = str(uuid.uuid4())
        token = create_refresh_token(user_id)

        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_access_vs_refresh_token_type(self):
        """Test that access and refresh tokens have different types."""
        user_id = str(uuid.uuid4())
        access_token = create_access_token(user_id, "free")
        refresh_token = create_refresh_token(user_id)

        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"
        assert access_payload["type"] != refresh_payload["type"]


class TestTokenEdgeCases:
    """Tests for edge cases and error handling."""

    def test_decode_empty_token(self):
        """Test decoding empty token raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            decode_token("")
        assert exc_info.value.status_code == 401

    def test_create_token_with_special_characters(self):
        """Test creating token with special characters in user_id."""
        user_id = str(uuid.uuid4())
        role = "admin"
        token = create_access_token(user_id, role)

        payload = decode_token(token)
        assert payload["sub"] == user_id

    def test_token_without_exp_claim(self):
        """Test that token without exp claim is rejected."""
        payload = {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "iat": datetime.now(timezone.utc),
            # Missing exp
        }
        token = jwt.encode(
            payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        # JWT library should treat missing exp as invalid
        with pytest.raises(HTTPException):
            decode_token(token)

    def test_token_with_future_iat(self):
        """Test token with future issued time (iat)."""
        user_id = str(uuid.uuid4())
        future_iat = datetime.now(timezone.utc) + timedelta(hours=1)
        future_exp = future_iat + timedelta(minutes=30)

        payload = {
            "sub": user_id,
            "type": "access",
            "role": "free",
            "exp": future_exp,
            "iat": future_iat,
        }
        token = jwt.encode(
            payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        # Should still be valid if not expired
        decoded = decode_token(token)
        assert decoded["sub"] == user_id

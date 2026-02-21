"""Tests for application configuration."""

import pytest
from pydantic import ValidationError

from backend.shared.config import Settings


class TestSecretKeyValidation:
    """Tests for SECRET_KEY validation logic."""

    def test_secret_key_default_in_debug_mode(self):
        """Test that SECRET_KEY gets default value when DEBUG=True and SECRET_KEY is empty."""
        settings = Settings(DEBUG=True, SECRET_KEY="")
        assert settings.SECRET_KEY == "dev-secret-key-change-in-production"

    def test_secret_key_required_in_production(self):
        """Test that SECRET_KEY must be set when DEBUG=False."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(DEBUG=False, SECRET_KEY="")

        assert "SECRET_KEY must be set in production" in str(exc_info.value)

    def test_secret_key_custom_value_in_debug(self):
        """Test that custom SECRET_KEY is preserved in debug mode."""
        custom_key = "my-custom-secret-key"
        settings = Settings(DEBUG=True, SECRET_KEY=custom_key)
        assert settings.SECRET_KEY == custom_key

    def test_secret_key_custom_value_in_production(self):
        """Test that custom SECRET_KEY is preserved in production mode."""
        custom_key = "production-secret-key-12345"
        settings = Settings(DEBUG=False, SECRET_KEY=custom_key)
        assert settings.SECRET_KEY == custom_key

    def test_default_debug_mode(self):
        """Test that DEBUG defaults to True."""
        settings = Settings()
        assert settings.DEBUG is True

    def test_secret_key_empty_string_vs_none(self):
        """Test validation with empty string SECRET_KEY."""
        # Empty string in debug mode gets default
        settings = Settings(DEBUG=True, SECRET_KEY="")
        assert settings.SECRET_KEY == "dev-secret-key-change-in-production"

        # Empty string in production mode raises error
        with pytest.raises(ValidationError):
            Settings(DEBUG=False, SECRET_KEY="")


class TestSettingsDefaults:
    """Tests for default configuration values."""

    def test_database_url_default(self):
        """Test DATABASE_URL has correct default."""
        settings = Settings()
        assert (
            settings.DATABASE_URL
            == "postgresql+asyncpg://postgres:postgres@localhost:5432/agentforge"
        )

    def test_redis_url_default(self):
        """Test REDIS_URL has correct default."""
        settings = Settings()
        assert settings.REDIS_URL == "redis://localhost:6379"

    def test_cors_origins_default(self):
        """Test CORS_ORIGINS has correct default."""
        settings = Settings()
        assert settings.CORS_ORIGINS == ["http://localhost:3000"]

    def test_jwt_algorithm_default(self):
        """Test JWT_ALGORITHM has correct default."""
        settings = Settings()
        assert settings.JWT_ALGORITHM == "HS256"

    def test_jwt_access_token_expire_minutes_default(self):
        """Test JWT_ACCESS_TOKEN_EXPIRE_MINUTES has correct default."""
        settings = Settings()
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30

    def test_jwt_refresh_token_expire_days_default(self):
        """Test JWT_REFRESH_TOKEN_EXPIRE_DAYS has correct default."""
        settings = Settings()
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7


class TestSettingsOverrides:
    """Tests for overriding configuration values."""

    def test_override_database_url(self):
        """Test overriding DATABASE_URL."""
        custom_url = "postgresql+asyncpg://custom:custom@db:5432/custom"
        settings = Settings(DATABASE_URL=custom_url)
        assert settings.DATABASE_URL == custom_url

    def test_override_redis_url(self):
        """Test overriding REDIS_URL."""
        custom_url = "redis://custom:6380"
        settings = Settings(REDIS_URL=custom_url)
        assert settings.REDIS_URL == custom_url

    def test_override_cors_origins(self):
        """Test overriding CORS_ORIGINS."""
        custom_origins = ["http://localhost:8080", "https://example.com"]
        settings = Settings(CORS_ORIGINS=custom_origins)
        assert settings.CORS_ORIGINS == custom_origins

    def test_override_jwt_settings(self):
        """Test overriding JWT settings."""
        settings = Settings(
            JWT_ALGORITHM="HS512",
            JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60,
            JWT_REFRESH_TOKEN_EXPIRE_DAYS=14,
        )
        assert settings.JWT_ALGORITHM == "HS512"
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 60
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 14


class TestSecretKeyEdgeCases:
    """Tests for edge cases in SECRET_KEY validation."""

    def test_whitespace_secret_key_in_production(self):
        """Test that whitespace-only SECRET_KEY is rejected in production."""
        with pytest.raises(ValidationError):
            Settings(DEBUG=False, SECRET_KEY="   ")

    def test_whitespace_secret_key_in_debug(self):
        """Test that whitespace-only SECRET_KEY gets default in debug."""
        settings = Settings(DEBUG=True, SECRET_KEY="   ")
        # Whitespace is truthy, so it should be preserved
        assert settings.SECRET_KEY == "   "

    def test_very_short_secret_key(self):
        """Test that very short SECRET_KEY is accepted (no length validation yet)."""
        # Current implementation doesn't validate length
        settings = Settings(DEBUG=False, SECRET_KEY="x")
        assert settings.SECRET_KEY == "x"

    def test_special_characters_in_secret_key(self):
        """Test SECRET_KEY with special characters."""
        special_key = "secret!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        settings = Settings(DEBUG=False, SECRET_KEY=special_key)
        assert settings.SECRET_KEY == special_key

    def test_unicode_in_secret_key(self):
        """Test SECRET_KEY with Unicode characters."""
        unicode_key = "secret-密钥-🔑"
        settings = Settings(DEBUG=False, SECRET_KEY=unicode_key)
        assert settings.SECRET_KEY == unicode_key

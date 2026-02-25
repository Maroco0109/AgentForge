"""Application configuration using Pydantic Settings."""

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentforge"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = ""
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    DEBUG: bool = True

    # Auth settings
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM settings
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"

    # Data Collector settings
    DATA_COLLECTOR_URL: str = "http://localhost:8001"

    # Encryption
    ENCRYPTION_KEY: str = ""

    @model_validator(mode="after")
    def validate_secret_key(self):
        """Provide default SECRET_KEY in debug mode, require it in production."""
        if not self.SECRET_KEY:
            if self.DEBUG:
                self.SECRET_KEY = "dev-secret-key-change-in-production"
            else:
                raise ValueError("SECRET_KEY must be set in production")
        return self

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

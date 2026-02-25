"""Data Collector configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class CollectorSettings(BaseSettings):
    """Data Collector service settings."""

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentforge"
    REDIS_URL: str = "redis://localhost:6379"
    DEFAULT_RATE_LIMIT_SECONDS: float = 2.0
    MAX_COLLECTION_SIZE_MB: int = 100
    PII_DETECTION_ENABLED: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


collector_settings = CollectorSettings()

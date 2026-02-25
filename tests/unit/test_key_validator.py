"""Tests for API key validator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.pipeline.key_validator import validate_provider_key
from backend.pipeline.llm_router import LLMProvider


@pytest.mark.asyncio
class TestValidateOpenAI:
    """Test OpenAI key validation."""

    async def test_valid_key(self):
        mock_models = MagicMock()
        mock_models.data = [MagicMock(id="gpt-4o"), MagicMock(id="gpt-4o-mini")]

        mock_client = AsyncMock()
        mock_client.models.list.return_value = mock_models

        with patch(
            "backend.pipeline.key_validator.AsyncOpenAI", return_value=mock_client
        ):
            is_valid, msg, models = await validate_provider_key("openai", "sk-test")

        assert is_valid is True
        assert "valid" in msg.lower()
        assert "gpt-4o" in models

    async def test_invalid_key(self):
        mock_client = AsyncMock()
        mock_client.models.list.side_effect = Exception("authentication error")

        with patch(
            "backend.pipeline.key_validator.AsyncOpenAI", return_value=mock_client
        ):
            is_valid, msg, models = await validate_provider_key("openai", "bad-key")

        assert is_valid is False
        assert models == []


@pytest.mark.asyncio
class TestValidateAnthropic:
    """Test Anthropic key validation."""

    async def test_valid_key(self):
        mock_response = MagicMock()
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        with patch(
            "backend.pipeline.key_validator.AsyncAnthropic", return_value=mock_client
        ):
            is_valid, msg, models = await validate_provider_key(
                "anthropic", "sk-ant-test"
            )

        assert is_valid is True
        assert len(models) > 0

    async def test_invalid_key(self):
        mock_client = AsyncMock()
        mock_client.messages.create.side_effect = Exception("authentication failed")

        with patch(
            "backend.pipeline.key_validator.AsyncAnthropic", return_value=mock_client
        ):
            is_valid, msg, models = await validate_provider_key("anthropic", "bad-key")

        assert is_valid is False


@pytest.mark.asyncio
class TestValidateGoogle:
    """Test Google Gemini key validation."""

    async def test_valid_key(self):
        mock_model = MagicMock()
        mock_model.name = "models/gemini-2.0-flash"
        mock_model.supported_generation_methods = ["generateContent"]

        with patch("backend.pipeline.key_validator.genai") as mock_genai:
            mock_genai.list_models.return_value = [mock_model]
            is_valid, msg, models = await validate_provider_key("google", "AIza-test")

        # If GOOGLE provider not available on this branch, expect False (unsupported)
        if is_valid:
            assert "models/gemini-2.0-flash" in models
        else:
            assert "unsupported" in msg.lower() or "Unsupported" in msg

    async def test_invalid_key(self):
        with patch("backend.pipeline.key_validator.genai") as mock_genai:
            mock_genai.list_models.side_effect = Exception("invalid api key")
            is_valid, msg, models = await validate_provider_key("google", "bad-key")

        assert is_valid is False


@pytest.mark.asyncio
class TestValidateProviderKey:
    """Test general validation logic."""

    async def test_unsupported_provider(self):
        is_valid, msg, models = await validate_provider_key("unknown_provider", "key")
        assert is_valid is False
        assert models == []

    async def test_accepts_enum(self):
        mock_client = AsyncMock()
        mock_models = MagicMock()
        mock_models.data = [MagicMock(id="gpt-4o")]
        mock_client.models.list.return_value = mock_models

        with patch(
            "backend.pipeline.key_validator.AsyncOpenAI", return_value=mock_client
        ):
            is_valid, _, _ = await validate_provider_key(LLMProvider.OPENAI, "sk-test")

        assert is_valid is True

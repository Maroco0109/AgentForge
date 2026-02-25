"""Provider-specific API key validation."""

import asyncio
import logging

from backend.pipeline.llm_router import LLMProvider

logger = logging.getLogger(__name__)

# Module-level imports for patchability in tests.
try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore[assignment,misc]

try:
    from anthropic import AsyncAnthropic
except ImportError:  # pragma: no cover
    AsyncAnthropic = None  # type: ignore[assignment,misc]

try:
    from google import genai as google_genai
except ImportError:  # pragma: no cover
    google_genai = None  # type: ignore[assignment]

# Include GOOGLE if available on this branch (Phase 8-2 adds it)
_GOOGLE: LLMProvider | None = None
try:
    _GOOGLE = LLMProvider("google")
except ValueError:
    pass

# Validation timeout (seconds)
_VALIDATION_TIMEOUT = 15.0


async def validate_provider_key(
    provider: str | LLMProvider,
    api_key: str,
) -> tuple[bool, str, list[str]]:
    """Validate an API key for a specific provider.

    Returns:
        (is_valid, message, available_models) tuple.
    """
    if isinstance(provider, str):
        try:
            provider = LLMProvider(provider)
        except ValueError:
            return False, f"Unsupported provider: {provider}", []

    validators = {
        LLMProvider.OPENAI: _validate_openai,
        LLMProvider.ANTHROPIC: _validate_anthropic,
    }
    if _GOOGLE is not None:
        validators[_GOOGLE] = _validate_google

    validator = validators.get(provider)
    if not validator:
        return False, f"Unsupported provider: {provider.value}", []

    try:
        return await asyncio.wait_for(validator(api_key), timeout=_VALIDATION_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning(f"Key validation timed out for {provider.value}")
        return False, "Validation timed out", []
    except Exception as e:
        logger.warning(f"Key validation failed for {provider.value}: {e}")
        return False, f"Validation failed: {e}", []


async def _validate_openai(api_key: str) -> tuple[bool, str, list[str]]:
    """Validate OpenAI API key by listing models."""
    client = AsyncOpenAI(api_key=api_key)
    try:
        models_response = await client.models.list()
        model_ids = [m.id for m in models_response.data[:20]]
        return True, "OpenAI key is valid", model_ids
    except Exception as e:
        error_str = str(e).lower()
        if "authentication" in error_str or "invalid" in error_str:
            return False, "Invalid OpenAI API key", []
        raise


async def _validate_anthropic(api_key: str) -> tuple[bool, str, list[str]]:
    """Validate Anthropic API key with minimal message."""
    client = AsyncAnthropic(api_key=api_key)
    try:
        await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        return (
            True,
            "Anthropic key is valid",
            [
                "claude-haiku-4-5-20251001",
                "claude-sonnet-4-6",
                "claude-opus-4-6",
            ],
        )
    except Exception as e:
        error_str = str(e).lower()
        if "authentication" in error_str or "invalid" in error_str:
            return False, "Invalid Anthropic API key", []
        raise


async def _validate_google(api_key: str) -> tuple[bool, str, list[str]]:
    """Validate Google Gemini API key using instance-based client.

    Uses google.genai.Client for per-request isolation
    (avoids global genai.configure() race condition).
    """
    client = google_genai.Client(api_key=api_key)
    try:
        models = []
        async for model in await asyncio.to_thread(client.models.list):
            name = getattr(model, "name", "")
            methods = getattr(model, "supported_generation_methods", []) or []
            if "generateContent" in methods:
                models.append(name)
            if len(models) >= 20:
                break
        return True, "Google Gemini key is valid", models
    except TypeError:
        # client.models.list() may return a sync iterable
        models = []
        for model in await asyncio.to_thread(lambda: list(client.models.list())):
            name = getattr(model, "name", "")
            methods = getattr(model, "supported_generation_methods", []) or []
            if "generateContent" in methods:
                models.append(name)
            if len(models) >= 20:
                break
        return True, "Google Gemini key is valid", models
    except Exception as e:
        error_str = str(e).lower()
        if "api key" in error_str or "invalid" in error_str or "permission" in error_str:
            return False, "Invalid Google API key", []
        raise

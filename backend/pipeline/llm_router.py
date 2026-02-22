"""Multi-LLM Router for cost-optimized model selection."""

import enum
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.shared.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(str, enum.Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class TaskComplexity(str, enum.Enum):
    """Task complexity levels for model routing."""

    SIMPLE = "simple"  # GPT-4o-mini / Haiku
    STANDARD = "standard"  # GPT-4o / Sonnet
    COMPLEX = "complex"  # GPT-4o / Opus


@dataclass
class LLMResponse:
    """Standardized LLM response."""

    content: str
    model: str
    provider: str
    usage: dict  # {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
    cost_estimate: float  # Estimated cost in USD


@dataclass
class ModelConfig:
    """Configuration for a specific model."""

    provider: LLMProvider
    model_id: str
    cost_per_1m_input: float
    cost_per_1m_output: float
    max_tokens: int = 4096


# Model registry
MODEL_REGISTRY: dict[TaskComplexity, list[ModelConfig]] = {
    TaskComplexity.SIMPLE: [
        ModelConfig(LLMProvider.OPENAI, "gpt-4o-mini", 0.15, 0.60, 4096),
        ModelConfig(LLMProvider.ANTHROPIC, "claude-haiku-4-5-20251001", 0.25, 1.25, 4096),
    ],
    TaskComplexity.STANDARD: [
        ModelConfig(LLMProvider.OPENAI, "gpt-4o", 2.50, 10.00, 4096),
        ModelConfig(LLMProvider.ANTHROPIC, "claude-sonnet-4-5-20250929", 3.00, 15.00, 4096),
    ],
    TaskComplexity.COMPLEX: [
        ModelConfig(LLMProvider.OPENAI, "gpt-4o", 2.50, 10.00, 4096),
        ModelConfig(LLMProvider.ANTHROPIC, "claude-opus-4-6", 15.00, 75.00, 4096),
    ],
}


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the client is configured and available."""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def is_available(self) -> bool:
        return bool(settings.OPENAI_API_KEY)

    async def generate(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        usage = response.usage
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=model,
            provider=LLMProvider.OPENAI.value,
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
            cost_estimate=0.0,  # Calculated by router
        )


class AnthropicClient(BaseLLMClient):
    """Anthropic API client."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        return self._client

    def is_available(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    async def generate(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        client = self._get_client()
        # Convert OpenAI-style messages to Anthropic format
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})

        kwargs = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msg:
            kwargs["system"] = system_msg

        response = await client.messages.create(**kwargs)
        usage = response.usage
        return LLMResponse(
            content=response.content[0].text if response.content else "",
            model=model,
            provider=LLMProvider.ANTHROPIC.value,
            usage={
                "prompt_tokens": usage.input_tokens,
                "completion_tokens": usage.output_tokens,
                "total_tokens": usage.input_tokens + usage.output_tokens,
            },
            cost_estimate=0.0,
        )


class LLMRouter:
    """Routes requests to appropriate LLM based on task complexity."""

    def __init__(self):
        self._clients: dict[LLMProvider, BaseLLMClient] = {
            LLMProvider.OPENAI: OpenAIClient(),
            LLMProvider.ANTHROPIC: AnthropicClient(),
        }

    def classify_complexity(self, prompt: str) -> TaskComplexity:
        """Classify task complexity based on prompt characteristics."""
        word_count = len(prompt.split())

        # Simple heuristics for complexity classification
        complex_keywords = [
            "분석",
            "비교",
            "추론",
            "설계",
            "아키텍처",
            "debug",
            "optimize",
            "architect",
        ]
        standard_keywords = [
            "생성",
            "작성",
            "변환",
            "요약",
            "번역",
            "create",
            "generate",
            "summarize",
        ]

        prompt_lower = prompt.lower()

        if any(kw in prompt_lower for kw in complex_keywords) or word_count > 500:
            return TaskComplexity.COMPLEX
        elif any(kw in prompt_lower for kw in standard_keywords) or word_count > 100:
            return TaskComplexity.STANDARD
        else:
            return TaskComplexity.SIMPLE

    def _get_available_client(
        self, preferred_provider: LLMProvider | None = None
    ) -> tuple[LLMProvider, BaseLLMClient]:
        """Get an available LLM client, preferring the specified provider."""
        if preferred_provider:
            client = self._clients.get(preferred_provider)
            if client and client.is_available():
                return preferred_provider, client

        # Fallback: try any available client
        for provider, client in self._clients.items():
            if client.is_available():
                return provider, client

        raise RuntimeError(
            "No LLM provider is configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY."
        )

    def _select_model(self, complexity: TaskComplexity, provider: LLMProvider) -> ModelConfig:
        """Select the best model for the given complexity and provider."""
        models = MODEL_REGISTRY.get(complexity, MODEL_REGISTRY[TaskComplexity.SIMPLE])
        for model in models:
            if model.provider == provider:
                return model
        # Fallback to first available
        return models[0]

    def _calculate_cost(self, model_config: ModelConfig, usage: dict) -> float:
        """Calculate estimated cost."""
        input_cost = (usage.get("prompt_tokens", 0) / 1_000_000) * model_config.cost_per_1m_input
        output_cost = (
            usage.get("completion_tokens", 0) / 1_000_000
        ) * model_config.cost_per_1m_output
        return input_cost + output_cost

    async def generate(
        self,
        messages: list[dict],
        complexity: TaskComplexity | None = None,
        preferred_provider: LLMProvider | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Route and generate LLM response."""
        # Auto-classify complexity if not specified
        if complexity is None:
            user_content = " ".join(
                m.get("content", "") for m in messages if m.get("role") == "user"
            )
            complexity = self.classify_complexity(user_content)

        # Get available client
        provider, client = self._get_available_client(preferred_provider)

        # Select model
        model_config = self._select_model(complexity, provider)

        logger.info(f"LLM Router: {complexity.value} -> {provider.value}/{model_config.model_id}")

        # Generate response
        response = await client.generate(messages, model_config.model_id, max_tokens, temperature)

        # Calculate cost
        response.cost_estimate = self._calculate_cost(model_config, response.usage)

        return response


# Singleton router instance
llm_router = LLMRouter()

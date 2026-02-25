"""Tests for LLM Router - Multi-LLM routing and model selection."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.pipeline.llm_router import (
    AnthropicClient,
    GeminiClient,
    LLMProvider,
    LLMResponse,
    LLMRouter,
    ModelConfig,
    OpenAIClient,
    TaskComplexity,
    MODEL_REGISTRY,
)


class TestTaskComplexity:
    """Test TaskComplexity enum."""

    def test_enum_values(self):
        """Test that TaskComplexity has expected values."""
        assert TaskComplexity.SIMPLE.value == "simple"
        assert TaskComplexity.STANDARD.value == "standard"
        assert TaskComplexity.COMPLEX.value == "complex"

    def test_enum_membership(self):
        """Test enum membership."""
        assert TaskComplexity.SIMPLE in TaskComplexity
        assert TaskComplexity.STANDARD in TaskComplexity
        assert TaskComplexity.COMPLEX in TaskComplexity


class TestLLMProvider:
    """Test LLMProvider enum."""

    def test_enum_values(self):
        """Test that LLMProvider has expected values."""
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"


class TestModelRegistry:
    """Test MODEL_REGISTRY structure."""

    def test_registry_has_all_complexity_levels(self):
        """Test that registry has entries for all complexity levels."""
        assert TaskComplexity.SIMPLE in MODEL_REGISTRY
        assert TaskComplexity.STANDARD in MODEL_REGISTRY
        assert TaskComplexity.COMPLEX in MODEL_REGISTRY

    def test_registry_has_multiple_models_per_complexity(self):
        """Test that each complexity level has multiple model options."""
        for complexity in TaskComplexity:
            models = MODEL_REGISTRY[complexity]
            assert len(models) >= 2, f"{complexity} should have at least 2 models"

    def test_simple_models(self):
        """Test SIMPLE complexity models."""
        models = MODEL_REGISTRY[TaskComplexity.SIMPLE]
        model_ids = [m.model_id for m in models]
        assert "gpt-4o-mini" in model_ids
        assert "claude-haiku-4-5-20251001" in model_ids

    def test_standard_models(self):
        """Test STANDARD complexity models."""
        models = MODEL_REGISTRY[TaskComplexity.STANDARD]
        model_ids = [m.model_id for m in models]
        assert "gpt-4o" in model_ids
        assert "claude-sonnet-4-5-20250929" in model_ids

    def test_complex_models(self):
        """Test COMPLEX complexity models."""
        models = MODEL_REGISTRY[TaskComplexity.COMPLEX]
        model_ids = [m.model_id for m in models]
        assert "gpt-4o" in model_ids
        assert "claude-opus-4-6" in model_ids


class TestLLMRouter:
    """Test LLMRouter functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        self.router = LLMRouter()

    def test_classify_complexity_simple(self):
        """Test complexity classification for simple tasks."""
        simple_prompts = [
            "안녕하세요",
            "Hello",
            "What is Python?",
            "간단한 질문",
        ]
        for prompt in simple_prompts:
            complexity = self.router.classify_complexity(prompt)
            assert complexity == TaskComplexity.SIMPLE

    def test_classify_complexity_standard(self):
        """Test complexity classification for standard tasks."""
        standard_prompts = [
            "이 데이터를 요약해주세요",  # Has keyword "요약"
            "문서를 번역해주세요",  # Has keyword "번역"
            "보고서를 생성해주세요",  # Has keyword "생성"
            "Generate a summary of this article",  # Has keyword "generate"
            " ".join(["word"] * 101),  # >100 words, no keywords
        ]
        for prompt in standard_prompts:
            complexity = self.router.classify_complexity(prompt)
            assert complexity == TaskComplexity.STANDARD

    def test_classify_complexity_complex(self):
        """Test complexity classification for complex tasks."""
        complex_prompts = [
            "이 시스템의 아키텍처를 분석하고 최적화 방안을 제안해주세요",
            "Debug this code and optimize its performance",
            "설계 문서를 작성하고 비교 분석해주세요",
            "Analyze and compare these architectures",
        ]
        for prompt in complex_prompts:
            complexity = self.router.classify_complexity(prompt)
            assert complexity == TaskComplexity.COMPLEX

    def test_classify_complexity_by_word_count(self):
        """Test complexity classification based on word count."""
        # >500 words -> COMPLEX
        long_prompt = " ".join(["word"] * 501)
        assert self.router.classify_complexity(long_prompt) == TaskComplexity.COMPLEX

        # >100 words -> STANDARD
        medium_prompt = " ".join(["word"] * 101)
        assert self.router.classify_complexity(medium_prompt) == TaskComplexity.STANDARD

        # <=100 words -> SIMPLE
        short_prompt = " ".join(["word"] * 50)
        assert self.router.classify_complexity(short_prompt) == TaskComplexity.SIMPLE

    def test_select_model_openai(self):
        """Test model selection for OpenAI provider."""
        model = self.router._select_model(TaskComplexity.SIMPLE, LLMProvider.OPENAI)
        assert model.provider == LLMProvider.OPENAI
        assert model.model_id == "gpt-4o-mini"

    def test_select_model_anthropic(self):
        """Test model selection for Anthropic provider."""
        model = self.router._select_model(TaskComplexity.SIMPLE, LLMProvider.ANTHROPIC)
        assert model.provider == LLMProvider.ANTHROPIC
        assert model.model_id == "claude-haiku-4-5-20251001"

    def test_select_model_fallback(self):
        """Test model selection falls back to first model if provider not found."""
        # Create a mock provider that doesn't exist in registry
        mock_provider = MagicMock()
        mock_provider.value = "nonexistent"

        model = self.router._select_model(TaskComplexity.SIMPLE, mock_provider)
        # Should fallback to first model in registry
        assert model in MODEL_REGISTRY[TaskComplexity.SIMPLE]

    def test_calculate_cost(self):
        """Test cost calculation."""
        model_config = ModelConfig(
            provider=LLMProvider.OPENAI,
            model_id="gpt-4o-mini",
            cost_per_1m_input=0.15,
            cost_per_1m_output=0.60,
        )
        usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
        }
        cost = self.router._calculate_cost(model_config, usage)
        # (1000/1_000_000 * 0.15) + (500/1_000_000 * 0.60) = 0.00015 + 0.0003 = 0.00045
        assert cost == pytest.approx(0.00045)

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        model_config = ModelConfig(
            provider=LLMProvider.OPENAI,
            model_id="gpt-4o-mini",
            cost_per_1m_input=0.15,
            cost_per_1m_output=0.60,
        )
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        cost = self.router._calculate_cost(model_config, usage)
        assert cost == 0.0

    @patch("backend.pipeline.llm_router.settings")
    def test_get_available_client_openai(self, mock_settings):
        """Test getting available client when OpenAI is configured."""
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.ANTHROPIC_API_KEY = None

        provider, client = self.router._get_available_client()
        assert provider == LLMProvider.OPENAI
        assert isinstance(client, OpenAIClient)

    @patch("backend.pipeline.llm_router.settings")
    def test_get_available_client_anthropic(self, mock_settings):
        """Test getting available client when Anthropic is configured."""
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        provider, client = self.router._get_available_client()
        assert provider == LLMProvider.ANTHROPIC
        assert isinstance(client, AnthropicClient)

    @patch("backend.pipeline.llm_router.settings")
    def test_get_available_client_preferred(self, mock_settings):
        """Test getting available client with preferred provider."""
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        provider, client = self.router._get_available_client(LLMProvider.ANTHROPIC)
        assert provider == LLMProvider.ANTHROPIC
        assert isinstance(client, AnthropicClient)

    @patch("backend.pipeline.llm_router.settings")
    def test_get_available_client_no_provider(self, mock_settings):
        """Test getting available client when no provider is configured."""
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = ""

        with pytest.raises(RuntimeError, match="No LLM provider is configured"):
            self.router._get_available_client()

    @patch("backend.pipeline.llm_router.settings")
    async def test_generate_with_auto_complexity(self, mock_settings):
        """Test generate with auto-complexity classification."""
        mock_settings.OPENAI_API_KEY = "test-key"

        # Mock OpenAI client
        mock_client = AsyncMock(spec=OpenAIClient)
        mock_client.is_available.return_value = True
        mock_client.generate.return_value = LLMResponse(
            content="Test response",
            model="gpt-4o-mini",
            provider="openai",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            cost_estimate=0.0,
        )

        self.router._clients[LLMProvider.OPENAI] = mock_client

        messages = [{"role": "user", "content": "Simple question"}]
        response = await self.router.generate(messages)

        assert response.content == "Test response"
        assert response.model == "gpt-4o-mini"
        assert response.cost_estimate > 0  # Should calculate cost

    @patch("backend.pipeline.llm_router.settings")
    async def test_generate_with_explicit_complexity(self, mock_settings):
        """Test generate with explicit complexity."""
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        # Mock Anthropic client
        mock_client = AsyncMock(spec=AnthropicClient)
        mock_client.is_available.return_value = True
        mock_client.generate.return_value = LLMResponse(
            content="Complex response",
            model="claude-opus-4-6",
            provider="anthropic",
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
            cost_estimate=0.0,
        )

        self.router._clients[LLMProvider.ANTHROPIC] = mock_client

        messages = [{"role": "user", "content": "Complex task"}]
        response = await self.router.generate(
            messages,
            complexity=TaskComplexity.COMPLEX,
            preferred_provider=LLMProvider.ANTHROPIC,
        )

        assert response.content == "Complex response"
        assert response.provider == "anthropic"


class TestOpenAIClient:
    """Test OpenAIClient."""

    @patch("backend.pipeline.llm_router.settings")
    def test_is_available_with_key(self, mock_settings):
        """Test is_available returns True when API key is set."""
        mock_settings.OPENAI_API_KEY = "test-key"
        client = OpenAIClient()
        assert client.is_available() is True

    @patch("backend.pipeline.llm_router.settings")
    def test_is_available_without_key(self, mock_settings):
        """Test is_available returns False when API key is not set."""
        mock_settings.OPENAI_API_KEY = None
        client = OpenAIClient()
        assert client.is_available() is False

    @patch("backend.pipeline.llm_router.settings")
    async def test_generate(self, mock_settings):
        """Test OpenAI generate method."""
        mock_settings.OPENAI_API_KEY = "test-key"

        # Mock the OpenAI API response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Generated content"
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 150

        mock_openai_class = MagicMock()
        mock_openai_instance = AsyncMock()
        mock_openai_instance.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_instance

        with patch.dict(
            "sys.modules", {"openai": MagicMock(AsyncOpenAI=mock_openai_class)}
        ):
            client = OpenAIClient()
            messages = [{"role": "user", "content": "Test"}]
            response = await client.generate(messages, "gpt-4o-mini")

            assert response.content == "Generated content"
            assert response.model == "gpt-4o-mini"
            assert response.provider == "openai"
            assert response.usage["prompt_tokens"] == 50
            assert response.usage["completion_tokens"] == 100
            assert response.usage["total_tokens"] == 150


class TestAnthropicClient:
    """Test AnthropicClient."""

    @patch("backend.pipeline.llm_router.settings")
    def test_is_available_with_key(self, mock_settings):
        """Test is_available returns True when API key is set."""
        mock_settings.ANTHROPIC_API_KEY = "test-key"
        client = AnthropicClient()
        assert client.is_available() is True

    @patch("backend.pipeline.llm_router.settings")
    def test_is_available_without_key(self, mock_settings):
        """Test is_available returns False when API key is not set."""
        mock_settings.ANTHROPIC_API_KEY = None
        client = AnthropicClient()
        assert client.is_available() is False

    @patch("backend.pipeline.llm_router.settings")
    async def test_generate(self, mock_settings):
        """Test Anthropic generate method."""
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        # Mock the Anthropic API response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Generated content")]
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 100

        mock_anthropic_class = MagicMock()
        mock_anthropic_instance = AsyncMock()
        mock_anthropic_instance.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_anthropic_instance

        with patch.dict(
            "sys.modules", {"anthropic": MagicMock(AsyncAnthropic=mock_anthropic_class)}
        ):
            client = AnthropicClient()
            messages = [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Test"},
            ]
            response = await client.generate(messages, "claude-sonnet-4-5-20250929")

            assert response.content == "Generated content"
            assert response.model == "claude-sonnet-4-5-20250929"
            assert response.provider == "anthropic"
            assert response.usage["prompt_tokens"] == 50
            assert response.usage["completion_tokens"] == 100
            assert response.usage["total_tokens"] == 150

    @patch("backend.pipeline.llm_router.settings")
    async def test_generate_without_system_message(self, mock_settings):
        """Test Anthropic generate without system message."""
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20

        mock_anthropic_class = MagicMock()
        mock_anthropic_instance = AsyncMock()
        mock_anthropic_instance.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_anthropic_instance

        with patch.dict(
            "sys.modules", {"anthropic": MagicMock(AsyncAnthropic=mock_anthropic_class)}
        ):
            client = AnthropicClient()
            messages = [{"role": "user", "content": "Test"}]
            response = await client.generate(messages, "claude-haiku-4-5-20251001")

            # Verify system parameter was not passed
            call_kwargs = mock_anthropic_instance.messages.create.call_args.kwargs
            assert "system" not in call_kwargs
            assert response.content == "Response"


class TestGeminiClient:
    """Test GeminiClient."""

    @patch("backend.pipeline.llm_router.settings")
    def test_is_available_with_key(self, mock_settings):
        """Test is_available returns True when API key is set."""
        mock_settings.GOOGLE_API_KEY = "test-key"
        client = GeminiClient()
        assert client.is_available() is True

    @patch("backend.pipeline.llm_router.settings")
    def test_is_available_without_key(self, mock_settings):
        """Test is_available returns False when API key is not set."""
        mock_settings.GOOGLE_API_KEY = ""
        client = GeminiClient()
        assert client.is_available() is False

    def test_is_available_with_injected_key(self):
        """Test is_available with injected API key."""
        client = GeminiClient(api_key="test-key")
        assert client.is_available() is True


class TestLLMRouterUserKeys:
    """Test LLMRouter with user_keys (BYOK mode)."""

    def test_user_keys_creates_only_specified_clients(self):
        """Test that user_keys mode only creates clients for specified providers."""
        router = LLMRouter(user_keys={LLMProvider.OPENAI: "sk-test"})
        assert LLMProvider.OPENAI in router._clients
        assert LLMProvider.ANTHROPIC not in router._clients
        assert LLMProvider.GOOGLE not in router._clients

    def test_user_keys_multiple_providers(self):
        """Test user_keys with multiple providers."""
        router = LLMRouter(
            user_keys={
                LLMProvider.OPENAI: "sk-test",
                LLMProvider.ANTHROPIC: "sk-ant-test",
            }
        )
        assert LLMProvider.OPENAI in router._clients
        assert LLMProvider.ANTHROPIC in router._clients
        assert LLMProvider.GOOGLE not in router._clients

    def test_user_keys_clients_are_available(self):
        """Test that user_keys clients report as available."""
        router = LLMRouter(user_keys={LLMProvider.OPENAI: "sk-test"})
        provider, client = router._get_available_client()
        assert provider == LLMProvider.OPENAI
        assert client.is_available()

    def test_user_keys_no_provider_raises(self):
        """Test that user_keys with no providers raises RuntimeError."""
        router = LLMRouter(user_keys={})
        with pytest.raises(RuntimeError, match="No LLM provider"):
            router._get_available_client()

    def test_legacy_mode_backward_compatible(self):
        """Test that LLMRouter() without args still works."""
        router = LLMRouter()
        assert LLMProvider.OPENAI in router._clients
        assert LLMProvider.ANTHROPIC in router._clients
        assert LLMProvider.GOOGLE in router._clients

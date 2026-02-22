"""Real LLM integration tests — requires actual API keys.

Run with: OPENAI_API_KEY=sk-xxx pytest tests/integration/test_llm_real.py -v -m llm_integration
Cost: ~$0.001 per full run (gpt-4o-mini)
"""

import os

import pytest

from backend.pipeline.llm_router import (
    AnthropicClient,
    LLMRouter,
    OpenAIClient,
    TaskComplexity,
)

pytestmark = [
    pytest.mark.llm_integration,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set",
    ),
]


@pytest.fixture
def openai_client():
    return OpenAIClient()


@pytest.fixture
def router():
    return LLMRouter()


class TestOpenAIClientReal:
    """Tests using real OpenAI API calls."""

    async def test_openai_client_real_call(self, openai_client):
        """OpenAIClient.generate() returns valid LLMResponse structure."""
        messages = [{"role": "user", "content": "Say 'hello' in one word."}]
        response = await openai_client.generate(
            messages=messages,
            model="gpt-4o-mini",
            max_tokens=10,
            temperature=0.0,
        )

        assert response.content, "Response content should not be empty"
        assert response.model == "gpt-4o-mini"
        assert response.provider == "openai"
        assert isinstance(response.usage, dict)
        assert response.usage["prompt_tokens"] > 0
        assert response.usage["completion_tokens"] > 0
        assert response.usage["total_tokens"] > 0

    async def test_cost_calculation_real(self, router):
        """LLMRouter.generate() calculates cost_estimate > 0."""
        messages = [{"role": "user", "content": "Say 'yes'."}]
        response = await router.generate(
            messages=messages,
            complexity=TaskComplexity.SIMPLE,
            max_tokens=5,
            temperature=0.0,
        )

        assert response.cost_estimate > 0, "Cost estimate should be positive"

    async def test_token_usage_tracking(self, router):
        """Usage dict contains prompt_tokens and completion_tokens."""
        messages = [{"role": "user", "content": "Reply with the number 42."}]
        response = await router.generate(
            messages=messages,
            complexity=TaskComplexity.SIMPLE,
            max_tokens=10,
            temperature=0.0,
        )

        assert "prompt_tokens" in response.usage
        assert "completion_tokens" in response.usage
        assert "total_tokens" in response.usage
        assert response.usage["prompt_tokens"] > 0
        assert response.usage["completion_tokens"] > 0

    async def test_error_handling_invalid_key(self):
        """Invalid API key raises an error gracefully."""
        client = OpenAIClient()
        # Temporarily override the client with invalid key
        from openai import AsyncOpenAI

        client._client = AsyncOpenAI(api_key="sk-invalid-key-for-testing")

        messages = [{"role": "user", "content": "Hello"}]
        with pytest.raises(Exception):
            await client.generate(
                messages=messages,
                model="gpt-4o-mini",
                max_tokens=5,
            )


class TestRouterReal:
    """Tests for LLMRouter with real API."""

    async def test_router_auto_routing(self, router):
        """LLMRouter routes based on complexity classification."""
        # Simple prompt should use gpt-4o-mini
        simple_messages = [{"role": "user", "content": "Hi"}]
        response = await router.generate(
            messages=simple_messages,
            max_tokens=5,
            temperature=0.0,
        )
        assert response.model == "gpt-4o-mini"
        assert response.provider == "openai"


class TestIntentAnalyzerReal:
    """Tests for IntentAnalyzer with real LLM."""

    async def test_intent_analyzer_real(self):
        """IntentAnalyzer returns valid IntentResult from real LLM."""
        from backend.discussion.intent_analyzer import IntentAnalyzer

        analyzer = IntentAnalyzer()
        result = await analyzer.analyze("AI 뉴스를 분석해줘")

        assert result.task, "Task should not be empty"
        assert result.confidence > 0, "Confidence should be positive"
        assert result.summary, "Summary should not be empty"
        assert result.estimated_complexity in ("simple", "standard", "complex")


class TestDesignGeneratorReal:
    """Tests for DesignGenerator with real LLM."""

    async def test_design_generator_real(self):
        """DesignGenerator returns list of DesignProposal from real LLM."""
        from backend.discussion.design_generator import DesignGenerator

        generator = DesignGenerator()
        requirements = {
            "task": "sentiment_analysis",
            "source_type": "web_reviews",
            "output_format": "report",
            "estimated_complexity": "standard",
        }
        designs = await generator.generate_designs(requirements)

        assert len(designs) >= 1, "Should return at least 1 design"
        for design in designs:
            assert design.name, "Design name should not be empty"
            assert design.description, "Design description should not be empty"
            assert len(design.agents) >= 1, "Design should have at least 1 agent"


class TestAnthropicClientReal:
    """Tests for AnthropicClient — only runs if ANTHROPIC_API_KEY is set."""

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set",
    )
    async def test_anthropic_client_real_call(self):
        """AnthropicClient.generate() returns valid LLMResponse."""
        client = AnthropicClient()
        messages = [{"role": "user", "content": "Say 'hello' in one word."}]
        response = await client.generate(
            messages=messages,
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            temperature=0.0,
        )

        assert response.content, "Response content should not be empty"
        assert response.provider == "anthropic"
        assert isinstance(response.usage, dict)
        assert response.usage["prompt_tokens"] > 0
        assert response.usage["completion_tokens"] > 0

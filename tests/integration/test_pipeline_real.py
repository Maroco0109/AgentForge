"""Real pipeline execution tests — requires actual API keys.

Run with: OPENAI_API_KEY=sk-xxx pytest tests/integration/test_pipeline_real.py -v -m llm_integration
"""

import os

import pytest

from backend.discussion.design_generator import AgentSpec, DesignProposal
from backend.pipeline.orchestrator import PipelineOrchestrator

pytestmark = [
    pytest.mark.llm_integration,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set",
    ),
]


class TestPipelineReal:
    """Tests for PipelineOrchestrator with real LLM."""

    async def test_single_agent_pipeline_real(self):
        """Single-agent pipeline executes and returns valid PipelineResult."""
        design = DesignProposal(
            name="Single Agent Test",
            description="A simple test pipeline with one agent",
            agents=[
                AgentSpec(
                    name="analyzer",
                    role="analyzer",
                    llm_model="gpt-4o-mini",
                    description="Analyzes the given topic briefly",
                ),
            ],
            pros=["Simple"],
            cons=["Limited"],
            estimated_cost="~$0.001",
            complexity="low",
            recommended=True,
        )

        orchestrator = PipelineOrchestrator()
        status_updates = []

        async def on_status(data):
            status_updates.append(data)

        result = await orchestrator.execute(
            design=design,
            on_status=on_status,
            timeout=60,
        )

        assert result.design_name == "Single Agent Test"
        assert result.status in ("completed", "partial", "failed")
        assert result.total_duration > 0

        # Should have received status updates
        assert len(status_updates) >= 1
        assert status_updates[0]["type"] == "pipeline_started"

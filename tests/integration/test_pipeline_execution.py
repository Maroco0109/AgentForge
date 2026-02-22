"""Integration tests for pipeline execution.

Note: Pipeline tests use mocked LLM responses for deterministic testing.
Full end-to-end tests with real LLM calls require Docker environment.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from backend.discussion.design_generator import AgentSpec, DesignProposal
from backend.pipeline.llm_router import LLMResponse, LLMRouter
from backend.pipeline.orchestrator import PipelineOrchestrator


@pytest.mark.asyncio
class TestPipelineOrchestration:
    """Tests for pipeline orchestrator integration."""

    async def test_orchestrator_builds_from_design(self):
        """Test that orchestrator can build a pipeline from DesignProposal."""
        design = DesignProposal(
            name="Test Pipeline",
            description="A simple test pipeline",
            agents=[
                AgentSpec(
                    name="collector",
                    role="collector",
                    llm_model="gpt-4o-mini",
                    description="Collects data",
                ),
                AgentSpec(
                    name="analyzer",
                    role="analyzer",
                    llm_model="gpt-4o",
                    description="Analyzes data",
                ),
                AgentSpec(
                    name="reporter",
                    role="reporter",
                    llm_model="gpt-4o-mini",
                    description="Reports results",
                ),
            ],
            pros=["Fast", "Cheap"],
            cons=["Basic"],
            estimated_cost="~$0.01",
            complexity="low",
            recommended=True,
        )

        orchestrator = PipelineOrchestrator()

        # Build the graph (should not raise)
        try:
            compiled_graph = orchestrator.builder.build(design)
            assert compiled_graph is not None
        except ValueError as e:
            pytest.fail(f"Graph building failed: {e}")

    async def test_orchestrator_execute_with_mock_llm(self):
        """Test pipeline execution with mocked LLM responses."""
        design = DesignProposal(
            name="Mock Test Pipeline",
            description="Pipeline with mocked LLM",
            agents=[
                AgentSpec(
                    name="processor",
                    role="analyzer",
                    llm_model="gpt-4o-mini",
                    description="Processes data",
                ),
                AgentSpec(
                    name="reporter",
                    role="reporter",
                    llm_model="gpt-4o-mini",
                    description="Formats output",
                ),
            ],
            complexity="low",
        )

        orchestrator = PipelineOrchestrator()

        # Mock LLM router to return fixed responses
        mock_response = LLMResponse(
            content="Mock LLM output",
            model="gpt-4o-mini",
            provider="openai",
            usage={"prompt_tokens": 50, "completion_tokens": 50, "total_tokens": 100},
            cost_estimate=0.001,
        )

        with patch.object(
            LLMRouter, "generate", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_response

            result = await orchestrator.execute(design, max_steps=10, timeout=30)

            assert result.status in ("completed", "partial", "failed")
            assert result.design_name == "Mock Test Pipeline"
            assert result.total_duration >= 0

    async def test_pipeline_status_updates(self):
        """Test that on_status callback receives updates during execution."""
        design = DesignProposal(
            name="Status Test Pipeline",
            description="Tests status callbacks",
            agents=[
                AgentSpec(
                    name="agent1",
                    role="analyzer",
                    llm_model="gpt-4o-mini",
                    description="First agent",
                ),
            ],
            complexity="low",
        )

        orchestrator = PipelineOrchestrator()
        status_updates = []

        async def on_status(status_data: dict):
            """Capture status updates."""
            status_updates.append(status_data)

        # Mock LLM
        mock_response = LLMResponse(
            content="Test output",
            model="gpt-4o-mini",
            provider="openai",
            usage={"prompt_tokens": 25, "completion_tokens": 25, "total_tokens": 50},
            cost_estimate=0.0005,
        )

        with patch.object(
            LLMRouter, "generate", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_response

            await orchestrator.execute(design, on_status=on_status, timeout=30)

            # Verify we received status updates
            assert len(status_updates) > 0
            # Should have at least pipeline_started
            assert any(u.get("type") == "pipeline_started" for u in status_updates)

    async def test_pipeline_timeout_handling(self):
        """Test that pipeline respects timeout settings."""
        design = DesignProposal(
            name="Timeout Test",
            description="Tests timeout behavior",
            agents=[
                AgentSpec(
                    name="slow_agent",
                    role="analyzer",
                    llm_model="gpt-4o",
                    description="Slow agent",
                ),
            ],
            complexity="medium",
        )

        orchestrator = PipelineOrchestrator()

        # Mock LLM to simulate slow response
        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(5)  # Longer than timeout
            return LLMResponse(
                content="Too late",
                model="gpt-4o",
                provider="openai",
                usage={
                    "prompt_tokens": 50,
                    "completion_tokens": 50,
                    "total_tokens": 100,
                },
                cost_estimate=0.002,
            )

        with patch.object(
            LLMRouter, "generate", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.side_effect = slow_generate

            result = await orchestrator.execute(design, timeout=2)

            # Should timeout
            assert result.status == "timeout"
            assert "timed out" in result.error.lower()

    async def test_parallel_execution_config(self):
        """Test pipeline with parallel node execution configuration."""
        # Create a design with multiple agents that could run in parallel
        design = DesignProposal(
            name="Parallel Test",
            description="Tests parallel execution",
            agents=[
                AgentSpec(
                    name="collector1",
                    role="collector",
                    llm_model="gpt-4o-mini",
                    description="Collector 1",
                ),
                AgentSpec(
                    name="collector2",
                    role="collector",
                    llm_model="gpt-4o-mini",
                    description="Collector 2",
                ),
                AgentSpec(
                    name="analyzer",
                    role="analyzer",
                    llm_model="gpt-4o",
                    description="Combines results",
                ),
            ],
            complexity="medium",
        )

        orchestrator = PipelineOrchestrator()

        mock_response = LLMResponse(
            content="Parallel output",
            model="gpt-4o-mini",
            provider="openai",
            usage={"prompt_tokens": 35, "completion_tokens": 40, "total_tokens": 75},
            cost_estimate=0.001,
        )

        with patch.object(
            LLMRouter, "generate", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.return_value = mock_response

            result = await orchestrator.execute(design, timeout=30)

            # Pipeline should complete
            assert result.status in ("completed", "partial")
            # Should have results from all agents
            assert len(result.agent_results) > 0


@pytest.mark.asyncio
class TestPipelineResult:
    """Tests for pipeline result handling."""

    async def test_pipeline_result_aggregation(self):
        """Test that pipeline results are properly aggregated."""
        design = DesignProposal(
            name="Result Aggregation Test",
            description="Tests result aggregation",
            agents=[
                AgentSpec(
                    name="agent1",
                    role="analyzer",
                    llm_model="gpt-4o-mini",
                    description="Agent 1",
                ),
                AgentSpec(
                    name="agent2",
                    role="reporter",
                    llm_model="gpt-4o-mini",
                    description="Agent 2",
                ),
            ],
            complexity="low",
        )

        orchestrator = PipelineOrchestrator()

        mock_response1 = LLMResponse(
            content="Agent 1 output",
            model="gpt-4o-mini",
            provider="openai",
            usage={"prompt_tokens": 50, "completion_tokens": 50, "total_tokens": 100},
            cost_estimate=0.001,
        )
        mock_response2 = LLMResponse(
            content="Agent 2 output (final)",
            model="gpt-4o-mini",
            provider="openai",
            usage={"prompt_tokens": 75, "completion_tokens": 75, "total_tokens": 150},
            cost_estimate=0.0015,
        )

        responses = [mock_response1, mock_response2]
        call_count = [0]

        async def mock_generate(*args, **kwargs):
            response = responses[call_count[0] % len(responses)]
            call_count[0] += 1
            return response

        with patch.object(LLMRouter, "generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = mock_generate

            result = await orchestrator.execute(design, timeout=30)

            # Verify aggregated metrics
            assert result.total_tokens >= 0
            assert result.total_cost >= 0
            assert result.total_duration >= 0
            # Final output should come from the last successful reporter
            if result.status == "completed":
                assert result.output is not None

    async def test_pipeline_error_handling(self):
        """Test that pipeline handles agent errors gracefully."""
        design = DesignProposal(
            name="Error Handling Test",
            description="Tests error handling",
            agents=[
                AgentSpec(
                    name="failing_agent",
                    role="analyzer",
                    llm_model="gpt-4o",
                    description="Will fail",
                ),
            ],
            complexity="low",
        )

        orchestrator = PipelineOrchestrator()

        # Mock LLM to raise an error
        with patch.object(
            LLMRouter, "generate", new_callable=AsyncMock
        ) as mock_generate:
            mock_generate.side_effect = Exception("LLM API error")

            result = await orchestrator.execute(design, timeout=30)

            # Pipeline should handle the error
            assert result.status in ("failed", "partial")


@pytest.mark.asyncio
class TestGraphBuilder:
    """Tests for LangGraph pipeline builder."""

    async def test_graph_structure_validation(self):
        """Test that graph builder validates agent dependencies."""
        from backend.pipeline.graph_builder import PipelineGraphBuilder

        builder = PipelineGraphBuilder()

        # Valid design
        valid_design = DesignProposal(
            name="Valid",
            description="Valid pipeline",
            agents=[
                AgentSpec(
                    name="start",
                    role="collector",
                    llm_model="gpt-4o-mini",
                    description="Start",
                ),
                AgentSpec(
                    name="end",
                    role="reporter",
                    llm_model="gpt-4o-mini",
                    description="End",
                ),
            ],
            complexity="low",
        )

        # Should build successfully
        try:
            graph = builder.build(valid_design)
            assert graph is not None
        except ValueError as e:
            pytest.fail(f"Valid design should not raise ValueError: {e}")

    async def test_empty_design_handling(self):
        """Test that builder handles empty agent lists."""
        from backend.pipeline.graph_builder import PipelineGraphBuilder

        builder = PipelineGraphBuilder()

        # Empty design
        empty_design = DesignProposal(
            name="Empty",
            description="No agents",
            agents=[],
            complexity="low",
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="no agents defined"):
            builder.build(empty_design)

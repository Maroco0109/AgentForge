"""Tests for pipeline orchestrator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


from backend.discussion.design_generator import AgentSpec, DesignProposal
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.pipeline.result import PipelineResult


def _make_design(**overrides) -> DesignProposal:
    defaults = {
        "name": "Test Pipeline",
        "description": "A test pipeline design",
        "agents": [
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
                description="Generates report",
            ),
        ],
        "estimated_cost": "~$0.05",
        "complexity": "medium",
    }
    defaults.update(overrides)
    return DesignProposal(**defaults)


class TestPipelineOrchestrator:
    """Tests for PipelineOrchestrator."""

    async def test_execute_empty_design(self):
        """Empty design should return failed result."""
        orchestrator = PipelineOrchestrator()
        design = _make_design(agents=[])
        result = await orchestrator.execute(design)

        assert isinstance(result, PipelineResult)
        assert result.status == "failed"
        assert "no agents" in result.error.lower()

    @patch("backend.pipeline.orchestrator.PipelineGraphBuilder")
    async def test_execute_success(self, mock_builder_class):
        """Successful pipeline execution."""
        # Mock the graph builder and compiled graph
        mock_graph = MagicMock()
        mock_graph.astream = _mock_stream_events
        mock_builder = MagicMock()
        mock_builder.build.return_value = mock_graph
        mock_builder_class.return_value = mock_builder

        orchestrator = PipelineOrchestrator()
        design = _make_design()
        result = await orchestrator.execute(design)

        assert isinstance(result, PipelineResult)
        assert result.status == "completed"
        assert result.design_name == "Test Pipeline"
        assert len(result.agent_results) == 3  # All 3 agents accumulated
        mock_builder.build.assert_called_once()

    @patch("backend.pipeline.orchestrator.PipelineGraphBuilder")
    async def test_execute_with_status_callback(self, mock_builder_class):
        """Status callback is invoked during execution."""
        mock_graph = MagicMock()
        mock_graph.astream = _mock_stream_events
        mock_builder = MagicMock()
        mock_builder.build.return_value = mock_graph
        mock_builder_class.return_value = mock_builder

        callback = AsyncMock()
        orchestrator = PipelineOrchestrator()
        design = _make_design()
        await orchestrator.execute(design, on_status=callback)

        # Should have been called at least for pipeline_started
        assert callback.call_count >= 1

    @patch("backend.pipeline.orchestrator.PipelineGraphBuilder")
    async def test_execute_timeout(self, mock_builder_class):
        """Pipeline timeout produces timeout result."""
        import asyncio

        async def slow_stream(*args, **kwargs):
            await asyncio.sleep(10)
            yield {}  # Never reached

        mock_graph = AsyncMock()
        mock_graph.astream = slow_stream
        mock_builder = MagicMock()
        mock_builder.build.return_value = mock_graph
        mock_builder_class.return_value = mock_builder

        orchestrator = PipelineOrchestrator()
        design = _make_design()
        result = await orchestrator.execute(design, timeout=1)

        assert result.status == "timeout"
        assert "timed out" in result.error.lower()

    @patch("backend.pipeline.orchestrator.PipelineGraphBuilder")
    async def test_execute_graph_exception(self, mock_builder_class):
        """Graph execution error produces failed result."""

        async def error_stream(*args, **kwargs):
            raise RuntimeError("Graph execution failed")
            yield  # Make it an async generator

        mock_graph = AsyncMock()
        mock_graph.astream = error_stream
        mock_builder = MagicMock()
        mock_builder.build.return_value = mock_graph
        mock_builder_class.return_value = mock_builder

        orchestrator = PipelineOrchestrator()
        design = _make_design()
        result = await orchestrator.execute(design)

        assert result.status == "failed"
        assert result.error is not None


async def _mock_stream_events(*args, **kwargs):
    """Generate mock stream events simulating agent execution."""
    yield {
        "collector": {
            "agent_results": [
                {
                    "agent_name": "collector",
                    "role": "collector",
                    "content": "Collected data from sources",
                    "tokens_used": 150,
                    "cost_estimate": 0.001,
                    "duration_seconds": 1.5,
                    "status": "success",
                    "error": None,
                }
            ],
            "current_step": 1,
            "cost_total": 0.001,
            "current_agent": "collector",
        }
    }
    yield {
        "analyzer": {
            "agent_results": [
                {
                    "agent_name": "analyzer",
                    "role": "analyzer",
                    "content": "Analysis results",
                    "tokens_used": 300,
                    "cost_estimate": 0.005,
                    "duration_seconds": 3.0,
                    "status": "success",
                    "error": None,
                }
            ],
            "current_step": 2,
            "cost_total": 0.006,
            "current_agent": "analyzer",
        }
    }
    yield {
        "reporter": {
            "agent_results": [
                {
                    "agent_name": "reporter",
                    "role": "reporter",
                    "content": "# Final Report\n\nResults summary here.",
                    "tokens_used": 200,
                    "cost_estimate": 0.002,
                    "duration_seconds": 2.0,
                    "status": "success",
                    "error": None,
                }
            ],
            "current_step": 3,
            "cost_total": 0.008,
            "current_agent": "reporter",
        }
    }

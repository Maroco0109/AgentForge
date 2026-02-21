"""Pipeline Orchestrator - Main execution engine."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from backend.pipeline.graph_builder import PipelineGraphBuilder
from backend.pipeline.result import AgentResult, PipelineResult
from backend.pipeline.state import PipelineState

if TYPE_CHECKING:
    from collections.abc import Callable

    from backend.discussion.design_generator import DesignProposal

logger = logging.getLogger(__name__)

DEFAULT_MAX_STEPS = 50
DEFAULT_TIMEOUT = 300  # 5 minutes


class PipelineOrchestrator:
    """Executes pipelines built from DesignProposals using LangGraph."""

    def __init__(self):
        self.builder = PipelineGraphBuilder()

    async def execute(
        self,
        design: DesignProposal,
        on_status: Callable[[dict], Any] | None = None,
        max_steps: int = DEFAULT_MAX_STEPS,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> PipelineResult:
        """Execute a pipeline from a DesignProposal.

        Args:
            design: The confirmed design to execute.
            on_status: Optional callback for status updates (for WebSocket).
            max_steps: Maximum execution steps.
            timeout: Timeout in seconds.

        Returns:
            PipelineResult with all agent results and final output.
        """
        start_time = time.time()

        # Build the LangGraph
        try:
            compiled_graph = self.builder.build(design)
        except ValueError as e:
            return PipelineResult(
                design_name=design.name,
                status="failed",
                error=f"Failed to build pipeline graph: {e}",
            )

        # Prepare initial state
        initial_state: PipelineState = {
            "design": design.model_dump(),
            "current_step": 0,
            "max_steps": max_steps,
            "timeout_seconds": timeout,
            "agent_results": [],
            "errors": [],
            "status": "running",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "cost_total": 0.0,
            "current_agent": "",
            "output": "",
        }

        if on_status:
            await self._notify(
                on_status,
                {
                    "type": "pipeline_started",
                    "design_name": design.name,
                    "agent_count": len(design.agents),
                },
            )

        # Execute with timeout
        try:
            final_state = await asyncio.wait_for(
                self._run_graph(compiled_graph, initial_state, on_status),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Pipeline '{design.name}' timed out after {timeout}s")
            if on_status:
                await self._notify(
                    on_status,
                    {
                        "type": "pipeline_failed",
                        "reason": "timeout",
                    },
                )
            return PipelineResult(
                design_name=design.name,
                status="timeout",
                total_duration=round(time.time() - start_time, 2),
                error=f"Pipeline timed out after {timeout} seconds",
            )
        except Exception as e:
            logger.error(f"Pipeline '{design.name}' failed: {e}")
            if on_status:
                await self._notify(
                    on_status,
                    {
                        "type": "pipeline_failed",
                        "reason": str(e),
                    },
                )
            return PipelineResult(
                design_name=design.name,
                status="failed",
                total_duration=round(time.time() - start_time, 2),
                error=str(e),
            )

        # Build result from final state
        return self._build_result(design.name, final_state, start_time)

    async def _run_graph(
        self,
        compiled_graph: Any,
        initial_state: PipelineState,
        on_status: Callable[[dict], Any] | None,
    ) -> dict:
        """Run the compiled graph and stream status updates."""
        final_state: dict = dict(initial_state)
        async for event in compiled_graph.astream(initial_state):
            for node_name, state_update in event.items():
                if not isinstance(state_update, dict):
                    continue
                # Accumulate list fields (mirrors LangGraph reducer behavior)
                for key in ("agent_results", "errors"):
                    if key in state_update:
                        final_state.setdefault(key, []).extend(state_update[key])
                # Overwrite scalar fields
                for key, value in state_update.items():
                    if key not in ("agent_results", "errors"):
                        final_state[key] = value

                if on_status:
                    agent_results = state_update.get("agent_results", [])
                    for result in agent_results:
                        await self._notify(
                            on_status,
                            {
                                "type": "agent_completed",
                                "agent_name": result.get("agent_name", node_name),
                                "status": result.get("status", "unknown"),
                                "duration": result.get("duration_seconds", 0),
                            },
                        )
        return final_state

    def _build_result(
        self,
        design_name: str,
        final_state: dict,
        start_time: float,
    ) -> PipelineResult:
        """Build PipelineResult from final graph state."""
        agent_results_raw = final_state.get("agent_results", [])
        agent_results = [AgentResult(**r) for r in agent_results_raw]

        total_cost = sum(r.cost_estimate for r in agent_results)
        total_tokens = sum(r.tokens_used for r in agent_results)
        total_duration = round(time.time() - start_time, 2)

        # Determine final status
        errors = final_state.get("errors", [])
        failed_agents = [r for r in agent_results if r.status == "failed"]

        if failed_agents and len(failed_agents) == len(agent_results):
            status = "failed"
        else:
            status = "completed"

        # Use the last successful reporter/synthesizer output as the final output
        output = ""
        for r in reversed(agent_results):
            if r.status == "success" and r.role in ("reporter", "synthesizer"):
                output = r.content
                break
        if not output:
            # Fallback: use last successful agent output
            for r in reversed(agent_results):
                if r.status == "success":
                    output = r.content
                    break

        return PipelineResult(
            design_name=design_name,
            status=status,
            agent_results=agent_results,
            total_cost=round(total_cost, 6),
            total_duration=total_duration,
            total_tokens=total_tokens,
            output=output,
            error="; ".join(errors) if errors else None,
        )

    @staticmethod
    async def _notify(callback: Callable[[dict], Any], data: dict) -> None:
        """Send status notification via callback."""
        try:
            result = callback(data)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.warning(f"Status callback error: {e}")

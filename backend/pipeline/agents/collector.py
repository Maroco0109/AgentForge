"""Collector agent node - Data Collector HTTP integration."""

from __future__ import annotations

import logging
import time

import httpx

from backend.pipeline.agents.base import BaseAgentNode
from backend.pipeline.result import AgentResult
from backend.pipeline.state import PipelineState
from backend.shared.config import settings

logger = logging.getLogger(__name__)

# Timeout for individual HTTP requests to data-collector
HTTP_TIMEOUT = 60.0


class CollectorNode(BaseAgentNode):
    """Collects data via the Data Collector microservice.

    If the design contains source URLs/hints, calls the data-collector API.
    Otherwise, falls back to LLM-based collection planning.
    """

    def build_messages(self, state: PipelineState) -> list[dict]:
        """Build LLM messages for fallback mode (no source URL)."""
        design = state["design"]
        return [
            {
                "role": "system",
                "content": (
                    "You are a data collection planning agent. "
                    "Analyze the pipeline requirements and describe what data should be collected, "
                    "from what sources, and how it should be structured. "
                    "Return a structured data collection plan."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Pipeline: {design.get('name', 'Unknown')}\n"
                    f"Description: {design.get('description', '')}\n"
                    f"My role: {self.description}\n\n"
                    "Create a data collection plan for this pipeline."
                ),
            },
        ]

    def _extract_source_url(self, state: PipelineState) -> str | None:
        """Extract source URL from design metadata or agent descriptions."""
        design = state["design"]

        # Check source_hints in design metadata
        source_hints = design.get("source_hints", [])
        if source_hints:
            for hint in source_hints:
                if isinstance(hint, str) and hint.startswith("http"):
                    return hint

        # Check agents for collector description with URLs
        for agent in design.get("agents", []):
            desc = agent.get("description", "")
            if "http://" in desc or "https://" in desc:
                for word in desc.split():
                    if word.startswith("http://") or word.startswith("https://"):
                        return word.rstrip(".,;)")

        return None

    async def execute(self, state: PipelineState) -> PipelineState:
        """Execute data collection via Data Collector API or LLM fallback."""
        source_url = self._extract_source_url(state)

        if not source_url:
            # No source URL found - use LLM fallback
            return await super().execute(state)

        start_time = time.time()
        base_url = settings.DATA_COLLECTOR_URL.rstrip("/")

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                # Step 1: Create collection
                create_resp = await client.post(
                    f"{base_url}/api/v1/collections",
                    json={"url": source_url, "source_type": "web"},
                )
                create_resp.raise_for_status()
                collection_id = create_resp.json()["id"]

                # Step 2: Check compliance
                compliance_resp = await client.get(
                    f"{base_url}/api/v1/collections/{collection_id}/compliance"
                )
                compliance_resp.raise_for_status()
                compliance = compliance_resp.json()

                if compliance.get("status") == "blocked":
                    duration = round(time.time() - start_time, 2)
                    reason = compliance.get("reason", "Compliance check failed")
                    result = AgentResult(
                        agent_name=self.name,
                        role=self.role,
                        content="",
                        duration_seconds=duration,
                        status="failed",
                        error=f"Collection blocked: {reason}",
                    )
                    return {
                        "agent_results": [result.model_dump()],
                        "errors": [f"Agent '{self.name}': collection blocked - {reason}"],
                        "current_step": state["current_step"] + 1,
                        "current_agent": self.name,
                    }

                # Step 3: Execute collection
                collect_resp = await client.post(
                    f"{base_url}/api/v1/collections/{collection_id}/collect"
                )
                collect_resp.raise_for_status()

                # Step 4: Get results
                data_resp = await client.get(f"{base_url}/api/v1/collections/{collection_id}/data")
                data_resp.raise_for_status()
                collected_data = data_resp.json()

                duration = round(time.time() - start_time, 2)
                content = (
                    f"Data collected from {source_url}.\n"
                    f"Items: {collected_data.get('total_items', 0)}\n"
                    f"Data: {str(collected_data.get('items', []))[:2000]}"
                )

                result = AgentResult(
                    agent_name=self.name,
                    role=self.role,
                    content=content,
                    duration_seconds=duration,
                    status="success",
                )
                return {
                    "agent_results": [result.model_dump()],
                    "current_step": state["current_step"] + 1,
                    "current_agent": self.name,
                }

        except httpx.ConnectError:
            logger.warning(f"Data Collector not reachable at {base_url}, falling back to LLM")
            return await super().execute(state)

        except httpx.TimeoutException:
            duration = round(time.time() - start_time, 2)
            result = AgentResult(
                agent_name=self.name,
                role=self.role,
                content="",
                duration_seconds=duration,
                status="failed",
                error=f"Data Collector timed out after {HTTP_TIMEOUT}s",
            )
            return {
                "agent_results": [result.model_dump()],
                "errors": [f"Agent '{self.name}': data collector timeout"],
                "current_step": state["current_step"] + 1,
                "current_agent": self.name,
            }

        except httpx.HTTPStatusError as e:
            duration = round(time.time() - start_time, 2)
            result = AgentResult(
                agent_name=self.name,
                role=self.role,
                content="",
                duration_seconds=duration,
                status="failed",
                error=f"Data Collector HTTP error: {e.response.status_code}",
            )
            return {
                "agent_results": [result.model_dump()],
                "errors": [f"Agent '{self.name}': HTTP {e.response.status_code}"],
                "current_step": state["current_step"] + 1,
                "current_agent": self.name,
            }

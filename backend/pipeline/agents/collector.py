"""Collector agent node - data collection (mock until Phase 7)."""

from __future__ import annotations

from backend.pipeline.agents.base import BaseAgentNode
from backend.pipeline.state import PipelineState


class CollectorNode(BaseAgentNode):
    """Collects data from sources. Mock implementation until Phase 7 Data Collector integration."""

    def build_messages(self, state: PipelineState) -> list[dict]:
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

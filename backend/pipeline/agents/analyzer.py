"""Analyzer agent node - LLM-based data analysis."""

from __future__ import annotations

from backend.pipeline.agents.base import BaseAgentNode
from backend.pipeline.state import PipelineState
from backend.shared.security import input_sanitizer


class AnalyzerNode(BaseAgentNode):
    """Performs LLM-based analysis on pipeline data."""

    def build_messages(self, state: PipelineState) -> list[dict]:
        design = state["design"]
        # Gather previous agent outputs as context
        previous_outputs = ""
        for r in state.get("agent_results", []):
            if r.get("status") == "success" and r.get("content"):
                content = r["content"]
                is_safe, _ = input_sanitizer.check(content)
                if not is_safe:
                    content = "[Content filtered: injection pattern detected]"
                previous_outputs += f"\n--- {r['agent_name']} ({r['role']}) ---\n{content}\n"

        return [
            {
                "role": "system",
                "content": (
                    "You are a data analysis agent. "
                    "Analyze the provided data and previous agent outputs thoroughly. "
                    "Provide structured insights, patterns, and actionable findings."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Pipeline: {design.get('name', 'Unknown')}\n"
                    f"Description: {design.get('description', '')}\n"
                    f"My role: {self.description}\n\n"
                    f"Previous agent outputs:{previous_outputs or ' (none yet)'}\n\n"
                    "Perform your analysis based on the pipeline requirements and available data."
                ),
            },
        ]

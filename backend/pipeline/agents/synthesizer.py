"""Synthesizer agent node - synthesizes multi-agent findings."""

from __future__ import annotations

from backend.pipeline.agents.base import BaseAgentNode
from backend.pipeline.state import PipelineState
from backend.shared.security import input_sanitizer


class SynthesizerNode(BaseAgentNode):
    """Synthesizes findings from multiple agents into coherent conclusions."""

    def build_messages(self, state: PipelineState) -> list[dict]:
        design = state["design"]
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
                    "You are a synthesis agent. "
                    "Combine findings from multiple analysis agents into a coherent narrative. "
                    "Identify common themes, resolve contradictions, and highlight key insights. "
                    "Produce a unified synthesis that is greater than the sum of its parts."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Pipeline: {design.get('name', 'Unknown')}\n"
                    f"Description: {design.get('description', '')}\n\n"
                    f"Findings from multiple agents:{previous_outputs or ' (none)'}\n\n"
                    "Synthesize all the above findings into a unified analysis."
                ),
            },
        ]

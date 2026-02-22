"""Validator agent node - data validation and quality checks."""

from __future__ import annotations

from backend.pipeline.agents.base import BaseAgentNode
from backend.pipeline.state import PipelineState
from backend.shared.security import input_sanitizer


class ValidatorNode(BaseAgentNode):
    """Validates data quality and completeness."""

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
                    "You are a data validation agent. "
                    "Check the provided data for completeness, accuracy, and quality issues. "
                    "Flag any problems found and suggest corrections. "
                    "Return a validation report with pass/fail status for each check."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Pipeline: {design.get('name', 'Unknown')}\n"
                    f"Description: {design.get('description', '')}\n"
                    f"My role: {self.description}\n\n"
                    f"Data to validate:{previous_outputs or ' (none)'}\n\n"
                    "Validate the above data and report any quality issues."
                ),
            },
        ]

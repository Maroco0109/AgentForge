"""Reporter agent node - generates final reports."""

from __future__ import annotations

from backend.pipeline.agents.base import BaseAgentNode
from backend.pipeline.state import PipelineState
from backend.shared.security import input_sanitizer


class ReporterNode(BaseAgentNode):
    """Generates structured reports from pipeline results."""

    def build_messages(self, state: PipelineState) -> list[dict]:
        design = state["design"]
        # Compile all successful results
        all_outputs = ""
        for r in state.get("agent_results", []):
            if r.get("status") == "success" and r.get("content"):
                content = r["content"]
                is_safe, _ = input_sanitizer.check(content)
                if not is_safe:
                    content = "[Content filtered: injection pattern detected]"
                all_outputs += f"\n--- {r['agent_name']} ({r['role']}) ---\n{content}\n"

        return [
            {
                "role": "system",
                "content": (
                    "You are a report generation agent. "
                    "Compile all pipeline results into a clear, structured report. "
                    "Include an executive summary, key findings, and recommendations. "
                    "Format the report in Markdown."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Pipeline: {design.get('name', 'Unknown')}\n"
                    f"Description: {design.get('description', '')}\n\n"
                    f"Agent outputs to compile:{all_outputs or ' (none)'}\n\n"
                    "Generate a comprehensive report based on all the above results."
                ),
            },
        ]

"""Custom agent node for user-defined roles."""

from __future__ import annotations

from backend.pipeline.agents.base import BaseAgentNode
from backend.pipeline.state import PipelineState


class CustomAgentNode(BaseAgentNode):
    """Agent node for user-defined custom roles."""

    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        llm_model: str = "gpt-4o-mini",
        router=None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        retry_count: int = 3,
        custom_prompt: str | None = None,
    ):
        super().__init__(
            name=name,
            role=role,
            description=description,
            llm_model=llm_model,
            router=router,
            temperature=temperature,
            max_tokens=max_tokens,
            retry_count=retry_count,
        )
        self.custom_prompt = custom_prompt

    def build_messages(self, state: PipelineState) -> list[dict]:
        """Build messages with optional custom system prompt."""
        design = state.get("design", {})
        previous_results = state.get("agent_results", [])

        system_content = self.custom_prompt or (
            f"You are a {self.role} agent named '{self.name}'. Your task: {self.description}"
        )

        context_parts = [
            f"Design: {design.get('name', 'N/A')} - {design.get('description', 'N/A')}"
        ]
        if previous_results:
            context_parts.append("\nPrevious agent results:")
            for r in previous_results[-3:]:
                context_parts.append(
                    f"- {r.get('agent_name', 'unknown')}: {str(r.get('content', ''))[:200]}"
                )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": "\n".join(context_parts)},
        ]

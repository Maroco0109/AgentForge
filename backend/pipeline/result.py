from __future__ import annotations

from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    """Result from a single agent node execution."""

    agent_name: str
    role: str
    content: str
    tokens_used: int = 0
    cost_estimate: float = 0.0
    duration_seconds: float = 0.0
    status: str = "success"
    error: str | None = None


class PipelineResult(BaseModel):
    """Final result of a complete pipeline execution."""

    design_name: str
    status: str
    agent_results: list[AgentResult] = Field(default_factory=list)
    total_cost: float = 0.0
    total_duration: float = 0.0
    total_tokens: int = 0
    output: str = ""
    error: str | None = None

"""Extended models for Phase 8B advanced pipeline features."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from backend.discussion.design_generator import AgentSpec, DesignProposal


class ExtendedAgentSpec(AgentSpec):
    """AgentSpec with advanced configuration options."""

    custom_prompt: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    retry_count: int = 3
    is_custom_role: bool = False

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Ensure temperature is between 0.0 and 2.0."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """Ensure max_tokens is between 1 and 16384."""
        if not 1 <= v <= 16384:
            raise ValueError("max_tokens must be between 1 and 16384")
        return v

    @field_validator("retry_count")
    @classmethod
    def validate_retry_count(cls, v: int) -> int:
        """Ensure retry_count is between 0 and 10."""
        if not 0 <= v <= 10:
            raise ValueError("retry_count must be between 0 and 10")
        return v


class EdgeSpec(BaseModel):
    """Specification for an edge between two agent nodes."""

    source: str
    target: str
    condition: str | None = None  # "field op value" (e.g. "score > 0.8")


class ExtendedDesignProposal(DesignProposal):
    """DesignProposal with explicit edge topology and extended agents."""

    edges: list[EdgeSpec] | None = None  # None = sequential execution
    agents: list[ExtendedAgentSpec] = Field(default_factory=list)

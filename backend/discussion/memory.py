"""Discussion Memory - Tracks agreements, preferences, and history."""

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DiscussionMemory(BaseModel):
    """Persistent memory for a discussion session."""

    agreements: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    user_preferences: dict[str, Any] = Field(default_factory=dict)
    design_history: list[dict] = Field(default_factory=list)
    critique_history: list[dict] = Field(default_factory=list)
    round_summaries: list[str] = Field(default_factory=list)
    resolved_questions: list[dict[str, str]] = Field(default_factory=list)

    def add_agreement(self, agreement: str) -> None:
        """Record an agreed-upon decision."""
        if agreement not in self.agreements:
            self.agreements.append(agreement)
            logger.debug(f"Agreement added: {agreement}")

    def add_open_question(self, question: str) -> None:
        """Add an unresolved question."""
        if question not in self.open_questions:
            self.open_questions.append(question)
            logger.debug(f"Open question added: {question}")

    def resolve_question(self, question: str, resolution: str) -> None:
        """Resolve an open question."""
        if question in self.open_questions:
            self.open_questions.remove(question)
            self.resolved_questions.append({"question": question, "resolution": resolution})
            logger.debug(f"Question resolved: {question} -> {resolution}")

    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference."""
        self.user_preferences[key] = value
        logger.debug(f"Preference set: {key}={value}")

    def add_design_snapshot(self, designs: list[dict]) -> None:
        """Record a snapshot of designs for history tracking."""
        self.design_history.append(
            {
                "round": len(self.design_history),
                "designs": designs,
            }
        )

    def add_critique_snapshot(self, critiques: list[dict]) -> None:
        """Record critique results for history tracking."""
        self.critique_history.append(
            {
                "round": len(self.critique_history),
                "critiques": critiques,
            }
        )

    def add_round_summary(self, summary: str) -> None:
        """Add a summary for the current round."""
        self.round_summaries.append(summary)

    def get_context_for_llm(self) -> str:
        """Generate context string for LLM prompts.

        Provides a concise summary of the discussion state
        for inclusion in LLM system/user prompts.
        """
        parts: list[str] = []

        if self.agreements:
            parts.append("## Agreed Decisions")
            for a in self.agreements:
                parts.append(f"- {a}")

        if self.open_questions:
            parts.append("\n## Open Questions")
            for q in self.open_questions:
                parts.append(f"- {q}")

        if self.user_preferences:
            parts.append("\n## User Preferences")
            for k, v in self.user_preferences.items():
                parts.append(f"- {k}: {v}")

        if self.round_summaries:
            parts.append("\n## Previous Round Summaries")
            for i, s in enumerate(self.round_summaries):
                parts.append(f"Round {i + 1}: {s}")

        if self.resolved_questions:
            parts.append("\n## Resolved Questions")
            for rq in self.resolved_questions:
                parts.append(f"- Q: {rq['question']} -> A: {rq['resolution']}")

        return "\n".join(parts) if parts else "No prior discussion context."

    def to_dict(self) -> dict:
        """Serialize memory to dict."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "DiscussionMemory":
        """Deserialize memory from dict."""
        return cls(**data)

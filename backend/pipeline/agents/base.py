"""Base agent node for pipeline execution."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod

from backend.pipeline.llm_router import LLMResponse, LLMRouter, TaskComplexity, llm_router
from backend.pipeline.result import AgentResult
from backend.pipeline.state import PipelineState
from backend.shared.security import input_sanitizer

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class BaseAgentNode(ABC):
    """Abstract base class for pipeline agent nodes."""

    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        llm_model: str = "gpt-4o-mini",
        router: LLMRouter | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        retry_count: int = 3,
    ):
        self.name = name
        self.role = role
        self.description = description
        self.llm_model = llm_model
        self.router = router or llm_router
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.retry_count = retry_count

    @abstractmethod
    def build_messages(self, state: PipelineState) -> list[dict]:
        """Build the LLM messages for this agent."""

    def get_complexity(self) -> TaskComplexity:
        """Determine task complexity based on the agent's LLM model."""
        model_lower = self.llm_model.lower()
        if "mini" in model_lower or "haiku" in model_lower:
            return TaskComplexity.SIMPLE
        elif "opus" in model_lower:
            return TaskComplexity.COMPLEX
        return TaskComplexity.STANDARD

    async def execute(self, state: PipelineState) -> PipelineState:
        """Execute this agent node. Called by LangGraph."""
        start_time = time.time()

        # Check design data for injection patterns
        design_text = str(state.get("design", {}))
        is_safe, matches = input_sanitizer.check(design_text)
        if not is_safe:
            logger.warning(
                f"Agent '{self.name}': potential injection in design data "
                f"({len(matches)} pattern(s))"
            )
            result = AgentResult(
                agent_name=self.name,
                role=self.role,
                content="",
                duration_seconds=round(time.time() - start_time, 2),
                status="failed",
                error="Potential prompt injection detected in design data",
            )
            return {
                "agent_results": [result.model_dump()],
                "errors": [f"Agent '{self.name}': prompt injection detected"],
                "current_step": state["current_step"] + 1,
                "current_agent": self.name,
            }

        retries = self.retry_count
        for attempt in range(1, retries + 1):
            try:
                messages = self.build_messages(state)
                response: LLMResponse = await self.router.generate(
                    messages=messages,
                    complexity=self.get_complexity(),
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )

                duration = time.time() - start_time
                result = AgentResult(
                    agent_name=self.name,
                    role=self.role,
                    content=response.content,
                    tokens_used=response.usage.get("total_tokens", 0),
                    cost_estimate=response.cost_estimate,
                    duration_seconds=round(duration, 2),
                    status="success",
                )

                logger.info(f"Agent '{self.name}' completed in {duration:.2f}s")
                return {
                    "agent_results": [result.model_dump()],
                    "current_step": state["current_step"] + 1,
                    "cost_total": state["cost_total"] + response.cost_estimate,
                    "current_agent": self.name,
                }

            except Exception as e:
                logger.warning(f"Agent '{self.name}' attempt {attempt}/{retries} failed: {e}")
                if attempt < retries:
                    # Exponential backoff before retry
                    await asyncio.sleep(2**attempt)
                else:
                    duration = time.time() - start_time
                    result = AgentResult(
                        agent_name=self.name,
                        role=self.role,
                        content="",
                        duration_seconds=round(duration, 2),
                        status="failed",
                        error=str(e),
                    )
                    return {
                        "agent_results": [result.model_dump()],
                        "errors": [f"Agent '{self.name}' failed after {retries} retries: {e}"],
                        "current_step": state["current_step"] + 1,
                        "current_agent": self.name,
                    }

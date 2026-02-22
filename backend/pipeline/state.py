from __future__ import annotations

import operator

from typing_extensions import Annotated, TypedDict


class PipelineState(TypedDict):
    """LangGraph pipeline state with reducer pattern for accumulating results."""

    design: dict
    current_step: int
    max_steps: int
    timeout_seconds: int
    agent_results: Annotated[list[dict], operator.add]
    errors: Annotated[list[str], operator.add]
    status: str
    start_time: str
    cost_total: float
    current_agent: str
    output: str

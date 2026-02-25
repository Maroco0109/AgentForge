"""Pipeline execution API routes."""

from __future__ import annotations

import collections
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.discussion.design_generator import DesignProposal
from backend.gateway.auth import get_current_user
from backend.gateway.cost_tracker import (
    acquire_pipeline_lock,
    check_budget,
    record_cost,
    release_pipeline_lock,
)
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.pipeline.result import PipelineResult
from backend.pipeline.user_router_factory import get_user_router
from backend.shared.database import AsyncSessionLocal
from backend.shared.models import User

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for pipeline runs with max 1000 entries (replaced with DB in Phase 7)
_MAX_PIPELINE_RUNS = 1000
_pipeline_runs: collections.OrderedDict[str, dict] = collections.OrderedDict()


class PipelineExecuteRequest(BaseModel):
    """Request to execute a pipeline."""

    design: DesignProposal


class PipelineStatusResponse(BaseModel):
    """Pipeline execution status."""

    pipeline_id: str
    status: str
    design_name: str
    started_at: str
    result: PipelineResult | None = None


async def _execute_pipeline_core(
    design: DesignProposal,
    current_user: User,
) -> PipelineStatusResponse:
    """Core pipeline execution logic shared by execute and execute-direct.

    Handles budget check, pipeline lock, orchestrator execution, and cost recording.
    """
    pipeline_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    # Evict oldest entries if at capacity
    while len(_pipeline_runs) >= _MAX_PIPELINE_RUNS:
        _pipeline_runs.popitem(last=False)

    _pipeline_runs[pipeline_id] = {
        "user_id": str(current_user.id),
        "status": "running",
        "design_name": design.name,
        "started_at": started_at,
        "result": None,
    }

    # Cost circuit breaker: check budget before execution
    user_id_str = str(current_user.id)
    allowed, current, limit = await check_budget(user_id_str, current_user.role)
    if not allowed:
        del _pipeline_runs[pipeline_id]
        raise HTTPException(
            status_code=402,
            detail=f"Daily cost limit exceeded: ${current:.2f}/${limit:.2f}",
        )

    # Per-user pipeline lock to prevent TOCTOU race condition
    if not await acquire_pipeline_lock(user_id_str):
        del _pipeline_runs[pipeline_id]
        raise HTTPException(
            status_code=429,
            detail="A pipeline is already running. Please wait for it to complete.",
        )

    # Get user-specific LLM router (BYOK)
    try:
        async with AsyncSessionLocal() as session:
            user_router = await get_user_router(user_id_str, session)
    except ValueError as e:
        del _pipeline_runs[pipeline_id]
        await release_pipeline_lock(user_id_str)
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    orchestrator = PipelineOrchestrator(router=user_router)

    try:
        result = await orchestrator.execute(design=design)
        _pipeline_runs[pipeline_id]["status"] = result.status
        _pipeline_runs[pipeline_id]["result"] = result
        # Record cost
        if result.total_cost:
            await record_cost(user_id_str, result.total_cost)
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        _pipeline_runs[pipeline_id]["status"] = "failed"
        result = PipelineResult(
            design_name=design.name,
            status="failed",
            error="Pipeline execution failed. Please try again.",
        )
        _pipeline_runs[pipeline_id]["result"] = result
    finally:
        await release_pipeline_lock(user_id_str)

    return PipelineStatusResponse(
        pipeline_id=pipeline_id,
        status=result.status,
        design_name=design.name,
        started_at=started_at,
        result=result,
    )


@router.post("/pipelines/execute", response_model=PipelineStatusResponse)
async def execute_pipeline(
    request: PipelineExecuteRequest,
    current_user: User = Depends(get_current_user),
) -> PipelineStatusResponse:
    """Execute a pipeline from a design proposal.

    Requires authentication. Currently runs synchronously.
    Phase 7 will add background execution.
    """
    return await _execute_pipeline_core(request.design, current_user)


@router.post("/pipelines/execute-direct", response_model=PipelineStatusResponse)
async def execute_direct(
    request: PipelineExecuteRequest,
    current_user: User = Depends(get_current_user),
) -> PipelineStatusResponse:
    """Execute a pipeline directly from the visual editor.

    Bypasses the discussion engine. Same cost/lock checks apply.
    Future: may add editor-specific features (e.g., step-by-step execution).
    """
    return await _execute_pipeline_core(request.design, current_user)


def _get_user_pipeline(pipeline_id: str, user_id: str) -> dict:
    """Get a pipeline run owned by the given user, or raise 404/403."""
    run = _pipeline_runs.get(pipeline_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    if run.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return run


@router.get("/pipelines/{pipeline_id}/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
) -> PipelineStatusResponse:
    """Get the status of a pipeline execution."""
    run = _get_user_pipeline(pipeline_id, str(current_user.id))

    return PipelineStatusResponse(
        pipeline_id=pipeline_id,
        status=run["status"],
        design_name=run["design_name"],
        started_at=run["started_at"],
        result=run.get("result"),
    )


@router.get("/pipelines/{pipeline_id}/result")
async def get_pipeline_result(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
) -> PipelineResult:
    """Get the result of a completed pipeline execution."""
    run = _get_user_pipeline(pipeline_id, str(current_user.id))

    result = run.get("result")
    if result is None:
        return JSONResponse(status_code=202, content={"detail": "Pipeline still running"})

    return result

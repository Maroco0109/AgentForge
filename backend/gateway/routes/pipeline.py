"""Pipeline execution API routes."""

from __future__ import annotations

import collections
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.discussion.design_generator import DesignProposal
from backend.gateway.auth import get_current_user
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.pipeline.result import PipelineResult
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


@router.post("/pipelines/execute", response_model=PipelineStatusResponse)
async def execute_pipeline(
    request: PipelineExecuteRequest,
    current_user: User = Depends(get_current_user),
) -> PipelineStatusResponse:
    """Execute a pipeline from a design proposal.

    Requires authentication. Currently runs synchronously.
    Phase 7 will add background execution.
    """
    pipeline_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    # Evict oldest entries if at capacity
    while len(_pipeline_runs) >= _MAX_PIPELINE_RUNS:
        _pipeline_runs.popitem(last=False)

    _pipeline_runs[pipeline_id] = {
        "status": "running",
        "design_name": request.design.name,
        "started_at": started_at,
        "result": None,
    }

    orchestrator = PipelineOrchestrator()

    try:
        result = await orchestrator.execute(design=request.design)
        _pipeline_runs[pipeline_id]["status"] = result.status
        _pipeline_runs[pipeline_id]["result"] = result
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        _pipeline_runs[pipeline_id]["status"] = "failed"
        result = PipelineResult(
            design_name=request.design.name,
            status="failed",
            error=str(e),
        )
        _pipeline_runs[pipeline_id]["result"] = result

    return PipelineStatusResponse(
        pipeline_id=pipeline_id,
        status=result.status,
        design_name=request.design.name,
        started_at=started_at,
        result=result,
    )


@router.get("/pipelines/{pipeline_id}/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
) -> PipelineStatusResponse:
    """Get the status of a pipeline execution."""
    run = _pipeline_runs.get(pipeline_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

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
    run = _pipeline_runs.get(pipeline_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    result = run.get("result")
    if result is None:
        raise HTTPException(status_code=202, detail="Pipeline still running")

    return result

"""Dashboard statistics routes."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.gateway.auth import get_current_user
from backend.shared.database import get_db
from backend.shared.models import (
    Conversation,
    Message,
    PipelineExecution,
    PipelineTemplate,
    User,
    UserDailyCost,
)

router = APIRouter(prefix="/stats", tags=["stats"])


class UsageHistoryItem(BaseModel):
    """Daily usage data point."""

    date: str
    cost: float
    request_count: int


class PipelineHistoryItem(BaseModel):
    """Pipeline execution history item."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    design_name: str
    status: str
    duration_seconds: float | None
    agent_count: int
    created_at: datetime


class DashboardSummary(BaseModel):
    """Dashboard summary counts."""

    total_conversations: int
    total_messages: int
    total_templates: int
    total_pipelines: int


@router.get("/usage-history", response_model=list[UsageHistoryItem])
async def get_usage_history(
    days: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UsageHistoryItem]:
    """Get daily usage history for dashboard chart."""
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    result = await db.execute(
        select(UserDailyCost)
        .where(
            UserDailyCost.user_id == current_user.id,
            UserDailyCost.date >= start_date,
        )
        .order_by(UserDailyCost.date)
    )
    costs = result.scalars().all()

    # Count messages per day
    msg_result = await db.execute(
        select(
            func.date(Message.created_at).label("date"),
            func.count().label("count"),
        )
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == current_user.id,
            Message.created_at >= datetime.now(timezone.utc) - timedelta(days=days),
        )
        .group_by(func.date(Message.created_at))
    )
    msg_counts = {str(row.date): row.count for row in msg_result}

    return [
        UsageHistoryItem(
            date=c.date,
            cost=c.total_cost,
            request_count=msg_counts.get(c.date, 0),
        )
        for c in costs
    ]


@router.get("/pipeline-history", response_model=list[PipelineHistoryItem])
async def get_pipeline_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PipelineHistoryItem]:
    """Get recent pipeline execution history."""
    result = await db.execute(
        select(PipelineExecution)
        .where(PipelineExecution.user_id == current_user.id)
        .order_by(PipelineExecution.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    """Get dashboard summary counts."""
    convs = await db.execute(
        select(func.count())
        .select_from(Conversation)
        .where(Conversation.user_id == current_user.id)
    )
    msgs = await db.execute(
        select(func.count())
        .select_from(Message)
        .join(Conversation)
        .where(Conversation.user_id == current_user.id)
    )
    templates = await db.execute(
        select(func.count())
        .select_from(PipelineTemplate)
        .where(PipelineTemplate.user_id == current_user.id)
    )
    pipelines = await db.execute(
        select(func.count())
        .select_from(PipelineExecution)
        .where(PipelineExecution.user_id == current_user.id)
    )

    return DashboardSummary(
        total_conversations=convs.scalar() or 0,
        total_messages=msgs.scalar() or 0,
        total_templates=templates.scalar() or 0,
        total_pipelines=pipelines.scalar() or 0,
    )

"""Pipeline template CRUD API routes."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.gateway.auth import get_current_user
from backend.shared.database import get_db
from backend.shared.models import PipelineTemplate, User
from backend.shared.schemas import (
    TemplateCreate,
    TemplateListResponse,
    TemplateResponse,
    TemplateUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_TEMPLATES_PER_USER = 50


def _get_owned_template_query(template_id: uuid.UUID, user_id: uuid.UUID):
    """Build a query for a template owned by the given user."""
    return select(PipelineTemplate).where(
        PipelineTemplate.id == template_id,
        PipelineTemplate.user_id == user_id,
    )


@router.post("/templates", response_model=TemplateResponse, status_code=201)
async def create_template(
    body: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PipelineTemplate:
    """Create a new pipeline template."""
    # Check per-user limit (soft limit; concurrent requests may slightly exceed)
    count_result = await db.execute(
        select(func.count()).where(PipelineTemplate.user_id == current_user.id)
    )
    count = count_result.scalar_one()
    if count >= MAX_TEMPLATES_PER_USER:
        limit = MAX_TEMPLATES_PER_USER
        raise HTTPException(
            status_code=400,
            detail=f"Template limit reached ({limit}). Delete some first.",
        )

    template = PipelineTemplate(
        id=uuid.uuid4(),
        user_id=current_user.id,
        name=body.name,
        description=body.description or None,
        graph_data=body.graph_data,
        design_data=body.design_data,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


@router.get("/templates", response_model=list[TemplateListResponse])
async def list_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PipelineTemplate]:
    """List the current user's pipeline templates."""
    result = await db.execute(
        select(PipelineTemplate)
        .where(PipelineTemplate.user_id == current_user.id)
        .order_by(PipelineTemplate.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PipelineTemplate:
    """Get a specific pipeline template (owner only)."""
    result = await db.execute(_get_owned_template_query(template_id, current_user.id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    body: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PipelineTemplate:
    """Update a pipeline template (owner only)."""
    result = await db.execute(_get_owned_template_query(template_id, current_user.id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.flush()
    await db.refresh(template)
    return template


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a pipeline template (owner only)."""
    result = await db.execute(_get_owned_template_query(template_id, current_user.id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    return Response(status_code=204)

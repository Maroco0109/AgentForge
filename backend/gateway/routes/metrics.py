"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Expose Prometheus metrics. No authentication required."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

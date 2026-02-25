"""Global exception handlers for FastAPI."""

import logging

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTPException -- return detail without extra info."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle RequestValidationError -- strip internal structure."""
    errors = []
    for error in exc.errors():
        loc = error.get("loc", ())
        # Remove "body" prefix from location to avoid exposing internal structure
        field_parts = [str(part) for part in loc if part != "body"]
        errors.append(
            {
                "field": ".".join(field_parts) if field_parts else "unknown",
                "msg": error.get("msg", "Validation error"),
            }
        )
    return JSONResponse(
        status_code=422,
        content={"detail": errors},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions -- log but never expose stack trace."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

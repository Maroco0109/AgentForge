"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.shared.config import settings
from backend.shared.database import init_db
from backend.shared.exception_handlers import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from backend.shared.middleware import PrometheusMiddleware
from backend.shared.schemas import HealthResponse
from backend.shared.security_headers import SecurityHeadersMiddleware

from .rate_limiter import close_redis, init_redis
from .routes import (
    api_keys,
    auth,
    chat,
    conversations,
    llm_keys,
    metrics,
    pipeline,
    stats,
    templates,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Initialize database and Redis
    await init_db()
    await init_redis()
    yield
    # Shutdown: cleanup
    await close_redis()


# Create FastAPI application
app = FastAPI(
    title="AgentForge API",
    version="0.2.0",
    description="Multi-agent discussion and pipeline API",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    expose_headers=["Retry-After"],
)

# Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware, debug=settings.DEBUG)

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(conversations.router, prefix="/api/v1", tags=["conversations"])
app.include_router(pipeline.router, prefix="/api/v1", tags=["pipelines"])
app.include_router(api_keys.router, prefix="/api/v1", tags=["api-keys"])
app.include_router(llm_keys.router, prefix="/api/v1", tags=["llm-keys"])
app.include_router(templates.router, prefix="/api/v1", tags=["templates"])
app.include_router(stats.router, prefix="/api/v1", tags=["stats"])
app.include_router(metrics.router, tags=["metrics"])

# Exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.2.0",
        timestamp=datetime.now(timezone.utc),
    )

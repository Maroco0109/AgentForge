"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.shared.config import settings
from backend.shared.database import init_db
from backend.shared.schemas import HealthResponse

from .rate_limiter import close_redis, init_redis
from .routes import auth, chat, conversations, pipeline


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
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(conversations.router, prefix="/api/v1", tags=["conversations"])
app.include_router(pipeline.router, prefix="/api/v1", tags=["pipelines"])


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.2.0",
        timestamp=datetime.now(timezone.utc),
    )

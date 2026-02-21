"""Redis-based sliding window rate limiter."""

import logging
import time
import uuid as uuid_mod

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from backend.shared.config import settings

from .auth import get_current_user
from .rbac import get_permission, is_unlimited

logger = logging.getLogger(__name__)

# Module-level Redis client (initialized at startup)
_redis_client: Redis | None = None


async def init_redis() -> Redis | None:
    """Initialize the Redis connection.

    Returns:
        Redis client or None if connection fails.
    """
    global _redis_client  # noqa: PLW0603
    try:
        _redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        await _redis_client.ping()
        logger.info("Redis connected at %s", settings.REDIS_URL)
        return _redis_client
    except Exception:
        logger.warning(
            "Redis unavailable at %s — rate limiting disabled (graceful degradation)",
            settings.REDIS_URL,
        )
        _redis_client = None
        return None


async def close_redis() -> None:
    """Close the Redis connection."""
    global _redis_client  # noqa: PLW0603
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")


def get_redis() -> Redis | None:
    """Get the current Redis client (may be None)."""
    return _redis_client


async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window_seconds: int = 60,
) -> tuple[bool, int, int]:
    """Check and increment a sliding window rate limit.

    Args:
        redis: Redis client.
        key: The rate limit key.
        limit: Maximum requests allowed in the window.
        window_seconds: Window duration in seconds.

    Returns:
        Tuple of (allowed, remaining, retry_after_seconds).
    """
    now = time.time()
    window_start = now - window_seconds

    # Use unique member key to prevent collision on concurrent requests
    member = f"{now}-{uuid_mod.uuid4().hex[:8]}"

    pipe = redis.pipeline()
    # Remove expired entries
    pipe.zremrangebyscore(key, 0, window_start)
    # Count requests in window BEFORE adding
    pipe.zcard(key)
    # Set expiry on the key
    pipe.expire(key, window_seconds)

    results = await pipe.execute()
    request_count = results[1]

    if request_count >= limit:
        # Over limit — do NOT add to set; calculate retry-after
        oldest = await redis.zrange(key, 0, 0, withscores=True)
        if oldest:
            retry_after = int(oldest[0][1] + window_seconds - now) + 1
        else:
            retry_after = window_seconds
        return False, 0, max(retry_after, 1)

    # Under limit — add current request
    await redis.zadd(key, {member: now})
    await redis.expire(key, window_seconds)

    remaining = limit - request_count - 1
    return True, remaining, 0


class RateLimiter:
    """FastAPI dependency for rate limiting based on user role permissions."""

    def __init__(self, window_seconds: int = 60):
        """Initialize rate limiter.

        Args:
            window_seconds: Sliding window duration in seconds.
        """
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        """Check rate limit for the current request.

        Requires authentication (get_current_user) to have already run,
        so the user is available in request.state.
        """
        redis = get_redis()
        if redis is None:
            # Graceful degradation: allow request when Redis is down
            logger.debug("Rate limiting skipped — Redis unavailable")
            return

        # Get user from request state (set by auth middleware or dependency)
        user = request.state.current_user
        role = user.role
        limit = get_permission(role, "max_requests_per_minute")

        if is_unlimited(limit):
            return

        key = f"rate_limit:{user.id}:{self.window_seconds}s"

        try:
            allowed, remaining, retry_after = await check_rate_limit(
                redis, key, limit, self.window_seconds
            )
        except Exception:
            logger.warning("Rate limit check failed — allowing request", exc_info=True)
            return

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )

        # Set rate limit headers on response (via middleware or state)
        request.state.rate_limit_remaining = remaining
        request.state.rate_limit_limit = limit


async def rate_limit_dependency(
    request: Request,
    current_user=Depends(get_current_user),
) -> None:
    """FastAPI dependency that authenticates and rate-limits in one step.

    Usage:
        @router.get("/endpoint", dependencies=[Depends(rate_limit_dependency)])
    """
    # Store user on request state for rate limiter access
    request.state.current_user = current_user

    limiter = RateLimiter(window_seconds=60)
    await limiter(request)


async def ws_track_connection(
    redis: Redis | None,
    user_id: str,
    max_connections: int,
) -> bool:
    """Track and check WebSocket connection count for a user.

    Args:
        redis: Redis client (may be None).
        user_id: The user's ID.
        max_connections: Maximum allowed concurrent connections (-1 = unlimited).

    Returns:
        True if connection is allowed, False if limit exceeded.
    """
    if redis is None or is_unlimited(max_connections):
        return True

    key = f"ws_connections:{user_id}"
    try:
        current = await redis.incr(key)
        # Set a TTL as a safety net (connections should be cleaned up on disconnect)
        await redis.expire(key, 3600)

        if current > max_connections:
            await redis.decr(key)
            return False
        return True
    except Exception:
        logger.warning("WS connection tracking failed — allowing", exc_info=True)
        return True


async def ws_release_connection(redis: Redis | None, user_id: str) -> None:
    """Release a tracked WebSocket connection.

    Args:
        redis: Redis client (may be None).
        user_id: The user's ID.
    """
    if redis is None:
        return
    key = f"ws_connections:{user_id}"
    try:
        current = await redis.decr(key)
        if current <= 0:
            await redis.delete(key)
    except Exception:
        logger.warning("WS connection release failed", exc_info=True)

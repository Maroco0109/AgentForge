"""IP-based rate limiter for authentication endpoints."""

import logging

from fastapi import HTTPException, Request, status

from backend.shared.config import settings

from .rate_limiter import check_rate_limit, get_redis

logger = logging.getLogger(__name__)

AUTH_RATE_LIMIT = settings.AUTH_RATE_LIMIT
AUTH_RATE_WINDOW_SECONDS = settings.AUTH_RATE_WINDOW_SECONDS


def _get_client_ip(request: Request) -> str:
    """Extract client IP using TRUSTED_PROXY_COUNT for safety.

    When TRUSTED_PROXY_COUNT == 0 (default, no proxy): use request.client.host directly.
    When TRUSTED_PROXY_COUNT > 0 (behind proxy): extract the Nth IP from the right
    of X-Forwarded-For, since rightmost entries are added by trusted proxies.
    """
    proxy_count = settings.TRUSTED_PROXY_COUNT
    if proxy_count <= 0:
        return request.client.host if request.client else "unknown"

    forwarded_for = request.headers.get("x-forwarded-for", "")
    if not forwarded_for:
        return request.client.host if request.client else "unknown"

    ips = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
    # With N trusted proxies, client IP is at position -(N+1) from right
    target_index = -(proxy_count + 1)
    if abs(target_index) <= len(ips):
        return ips[target_index]
    # Fallback: if not enough IPs, use the leftmost
    return ips[0]


async def check_auth_rate_limit(request: Request) -> None:
    """FastAPI dependency to rate-limit auth endpoints by client IP.

    Usage:
        @router.post("/login", dependencies=[Depends(check_auth_rate_limit)])
    """
    redis = get_redis()
    if redis is None:
        return

    client_ip = _get_client_ip(request)
    key = f"auth_rate_limit:{client_ip}:{AUTH_RATE_WINDOW_SECONDS}s"

    try:
        allowed, remaining, retry_after = await check_rate_limit(
            redis, key, AUTH_RATE_LIMIT, AUTH_RATE_WINDOW_SECONDS
        )
    except Exception:
        logger.warning("Auth rate limit check failed — allowing request", exc_info=True)
        return

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

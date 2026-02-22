"""Redis-based daily LLM cost tracking with circuit breaker."""

import logging
from datetime import datetime, timezone

from backend.gateway.rate_limiter import get_redis
from backend.gateway.rbac import get_permission, is_unlimited
from backend.shared.database import AsyncSessionLocal
from backend.shared.models import UserDailyCost, UserRole

logger = logging.getLogger(__name__)


def _today_key(user_id: str) -> str:
    """Build Redis key for today's cost budget."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"cost_budget:{user_id}:{today}"


async def get_daily_cost(user_id: str) -> float:
    """Get today's accumulated cost from Redis."""
    redis = get_redis()
    if redis is None:
        return 0.0
    try:
        value = await redis.get(_today_key(user_id))
        return float(value) if value else 0.0
    except Exception:
        logger.warning("Failed to get daily cost from Redis", exc_info=True)
        return 0.0


async def check_budget(user_id: str, role: UserRole) -> tuple[bool, float, float]:
    """Check if user is within daily cost budget.

    Returns:
        Tuple of (allowed, current_cost, limit).
    """
    limit = get_permission(role, "max_cost_per_day_usd")
    if is_unlimited(limit):
        current = await get_daily_cost(user_id)
        return True, current, -1

    current = await get_daily_cost(user_id)
    return current < limit, current, float(limit)


async def record_cost(user_id: str, cost: float) -> float:
    """Record LLM cost and return new accumulated total.

    Uses Redis INCRBYFLOAT with 48-hour TTL.
    Also persists to PostgreSQL for audit.
    """
    if cost <= 0:
        return await get_daily_cost(user_id)

    redis = get_redis()
    new_total = 0.0

    if redis is not None:
        try:
            key = _today_key(user_id)
            new_total = float(await redis.incrbyfloat(key, cost))
            await redis.expire(key, 172800)  # 48 hours TTL
        except Exception:
            logger.warning("Failed to record cost in Redis", exc_info=True)
            new_total = cost

    # Persist to DB asynchronously (best-effort)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await _persist_daily_cost(user_id, today, new_total)

    return new_total


async def _persist_daily_cost(user_id: str, date: str, total: float) -> None:
    """Persist daily cost to PostgreSQL for audit."""
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(UserDailyCost).where(
                    UserDailyCost.user_id == user_id,
                    UserDailyCost.date == date,
                )
            )
            record = result.scalar_one_or_none()
            if record:
                record.total_cost = total
            else:
                record = UserDailyCost(
                    user_id=user_id,
                    date=date,
                    total_cost=total,
                )
                session.add(record)
            await session.commit()
    except Exception:
        logger.warning("Failed to persist daily cost to DB", exc_info=True)

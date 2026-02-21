"""Per-site rate limiter for data collection."""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class SiteRateLimiter:
    """Rate limiter that respects per-site crawl delays."""

    def __init__(self, default_delay: float = 2.0):
        self.default_delay = default_delay
        self._last_request: dict[str, float] = {}
        self._delays: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def set_delay(self, domain: str, delay: float):
        """Set crawl delay for a specific domain."""
        self._delays[domain] = max(delay, 0.5)  # Minimum 0.5s

    def get_delay(self, domain: str) -> float:
        """Get the delay for a domain."""
        return self._delays.get(domain, self.default_delay)

    def _get_lock(self, domain: str) -> asyncio.Lock:
        """Get or create a lock for a specific domain."""
        if domain not in self._locks:
            self._locks[domain] = asyncio.Lock()
        return self._locks[domain]

    async def wait(self, domain: str):
        """Wait until it's safe to make a request to the domain."""
        lock = self._get_lock(domain)

        # Calculate wait time inside the lock
        async with lock:
            delay = self.get_delay(domain)
            last = self._last_request.get(domain, 0)
            elapsed = time.time() - last

            if elapsed < delay:
                wait_time = delay - elapsed
            else:
                wait_time = 0

            # Update timestamp while still holding the lock
            self._last_request[domain] = time.time() + wait_time

        # Sleep outside the lock to avoid blocking other domains
        if wait_time > 0:
            logger.debug(f"Rate limiting {domain}: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)


site_rate_limiter = SiteRateLimiter()

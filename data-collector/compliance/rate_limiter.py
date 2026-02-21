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
        self._lock = asyncio.Lock()

    def set_delay(self, domain: str, delay: float):
        """Set crawl delay for a specific domain."""
        self._delays[domain] = max(delay, 0.5)  # Minimum 0.5s

    def get_delay(self, domain: str) -> float:
        """Get the delay for a domain."""
        return self._delays.get(domain, self.default_delay)

    async def wait(self, domain: str):
        """Wait until it's safe to make a request to the domain."""
        async with self._lock:
            delay = self.get_delay(domain)
            last = self._last_request.get(domain, 0)
            elapsed = time.time() - last

            if elapsed < delay:
                wait_time = delay - elapsed
                logger.debug(f"Rate limiting {domain}: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

            self._last_request[domain] = time.time()


site_rate_limiter = SiteRateLimiter()

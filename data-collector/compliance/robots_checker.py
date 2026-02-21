"""robots.txt compliance checker."""

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)


class RobotsChecker:
    """Check if a URL is allowed by robots.txt."""

    USER_AGENT = "AgentForgeBot/1.0"

    def __init__(self):
        self._cache: dict[str, RobotFileParser] = {}

    async def is_allowed(self, url: str) -> tuple[bool, str]:
        """Check if URL is allowed by robots.txt.

        Returns: (is_allowed, reason)
        """
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        try:
            parser = await self._get_parser(robots_url)

            if parser is None:
                return True, "robots.txt not found - assuming allowed"

            # Agent-specific rule takes priority over wildcard
            allowed = parser.can_fetch(self.USER_AGENT, url)

            if not allowed:
                return False, f"Blocked by robots.txt for {parsed.netloc}"

            # Check crawl delay
            crawl_delay = parser.crawl_delay(self.USER_AGENT)
            if crawl_delay is None:
                crawl_delay = parser.crawl_delay("*")

            reason = "Allowed by robots.txt"
            if crawl_delay:
                reason += f" (crawl-delay: {crawl_delay}s)"

            return True, reason

        except Exception as e:
            logger.warning(f"Error checking robots.txt for {robots_url}: {e}")
            return True, f"robots.txt check failed ({e}) - assuming allowed"

    async def get_crawl_delay(self, url: str) -> float | None:
        """Get the crawl delay for a URL's domain."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        try:
            parser = await self._get_parser(robots_url)
            if parser is None:
                return None

            delay = parser.crawl_delay(self.USER_AGENT)
            if delay is None:
                delay = parser.crawl_delay("*")
            return delay
        except Exception:
            return None

    async def _get_parser(self, robots_url: str) -> RobotFileParser | None:
        """Fetch and parse robots.txt with caching."""
        if robots_url in self._cache:
            return self._cache[robots_url]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(robots_url)

            if response.status_code == 404:
                self._cache[robots_url] = None
                return None

            if response.status_code != 200:
                self._cache[robots_url] = None
                return None

            parser = RobotFileParser()
            parser.parse(response.text.splitlines())
            self._cache[robots_url] = parser
            return parser

        except httpx.RequestError as e:
            logger.warning(f"Failed to fetch {robots_url}: {e}")
            self._cache[robots_url] = None
            return None


robots_checker = RobotsChecker()

"""Web crawler using httpx + BeautifulSoup (no Playwright for MVP)."""

import logging
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result of a web crawl."""

    url: str
    status_code: int
    title: str = ""
    text_content: str = ""
    html_content: str = ""
    links: list[str] = field(default_factory=list)
    error: str | None = None
    success: bool = True


class WebCrawler:
    """Simple web crawler using httpx + BeautifulSoup."""

    DEFAULT_HEADERS = {
        "User-Agent": "AgentForgeBot/1.0 (+https://github.com/Maroco0109/AgentForge)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    }

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def crawl(self, url: str) -> CrawlResult:
        """Crawl a single URL and extract content."""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.DEFAULT_HEADERS,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)

            if response.status_code != 200:
                return CrawlResult(
                    url=url,
                    status_code=response.status_code,
                    error=f"HTTP {response.status_code}",
                    success=False,
                )

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Extract title
            title = soup.title.string if soup.title else ""

            # Extract text content
            text_content = soup.get_text(separator="\n", strip=True)

            # Extract links
            links = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if href.startswith("http"):
                    links.append(href)

            return CrawlResult(
                url=url,
                status_code=response.status_code,
                title=title or "",
                text_content=text_content,
                html_content=response.text,
                links=links[:50],  # Limit to 50 links
            )

        except httpx.RequestError as e:
            return CrawlResult(
                url=url,
                status_code=0,
                error=str(e),
                success=False,
            )

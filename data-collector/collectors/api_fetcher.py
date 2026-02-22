"""Async API fetcher using httpx."""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    """Result of an API fetch."""

    url: str
    status_code: int
    data: dict | list | str | None = None
    content_type: str = ""
    error: str | None = None
    success: bool = True


class APIFetcher:
    """Fetch data from REST/GraphQL APIs."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def get(
        self, url: str, headers: dict | None = None, params: dict | None = None
    ) -> FetchResult:
        """Perform a GET request."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=headers or {}, params=params or {})

            content_type = response.headers.get("content-type", "")
            data = None
            if "json" in content_type:
                data = response.json()
            else:
                data = response.text

            return FetchResult(
                url=url,
                status_code=response.status_code,
                data=data,
                content_type=content_type,
                success=response.is_success,
            )
        except httpx.RequestError as e:
            return FetchResult(url=url, status_code=0, error=str(e), success=False)

    async def post(
        self, url: str, json_data: dict | None = None, headers: dict | None = None
    ) -> FetchResult:
        """Perform a POST request."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=json_data, headers=headers or {})

            content_type = response.headers.get("content-type", "")
            data = response.json() if "json" in content_type else response.text

            return FetchResult(
                url=url,
                status_code=response.status_code,
                data=data,
                content_type=content_type,
                success=response.is_success,
            )
        except httpx.RequestError as e:
            return FetchResult(url=url, status_code=0, error=str(e), success=False)

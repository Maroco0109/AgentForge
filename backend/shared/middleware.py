"""HTTP middleware for Prometheus metrics instrumentation."""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from backend.shared.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware that records HTTP request metrics."""

    # Endpoints to exclude from metrics (avoid self-referential loops)
    EXCLUDE_PATHS = {"/metrics", "/api/v1/health"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if path in self.EXCLUDE_PATHS:
            return await call_next(request)

        method = request.method
        # Normalize path: collapse ID segments to {id} to limit cardinality
        endpoint = self._normalize_path(path)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        status = str(response.status_code)

        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=status).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(duration)

        return response

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Collapse UUID and numeric path segments to {id}."""
        parts = path.split("/")
        normalized = []
        for part in parts:
            if not part:
                normalized.append(part)
                continue
            # UUID pattern or numeric ID
            if len(part) == 36 and part.count("-") == 4:
                normalized.append("{id}")
            elif part.isdigit():
                normalized.append("{id}")
            else:
                normalized.append(part)
        return "/".join(normalized)

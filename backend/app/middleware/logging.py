"""
PAMASMMA v4 — Logging Middleware
Structured JSON request/response logging via structlog.
Logs: method, path, status, latency, client IP, request ID.
Skips health check path to avoid log noise.
"""
import time
import uuid
from collections.abc import Callable
from typing import cast

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

log = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured request logging. Attaches X-Request-ID to every response.
    Uses structlog for JSON-compatible output — pairs with Railway log drain.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip health endpoint — too noisy in production
        if path == "/health":
            return cast(Response, await call_next(request))

        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        start = time.perf_counter()

        # Bind request context for this scope
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=path,
            client=self._get_client_ip(request),
        )

        log.info("request_start")

        try:
            response = cast(Response, await call_next(request))
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            log.error(
                "request_error",
                error=str(exc),
                latency_ms=round(elapsed, 2),
            )
            raise

        elapsed = (time.perf_counter() - start) * 1000
        log.info(
            "request_end",
            status=response.status_code,
            latency_ms=round(elapsed, 2),
        )

        response.headers["X-Request-ID"] = request_id
        return response

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

"""
PAMASMMA v4.1 — Rate limiting middleware.
Uses Redis in durable mode and the in-memory limiter in kernel/demo mode.
"""
import logging
import time
from collections.abc import Callable
from typing import cast

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.redis_client import check_rate_limit

log = logging.getLogger(__name__)
settings = get_settings()

ROUTE_LIMITS = [
    ("/api/v1/auth", settings.rate_limit_auth_per_minute),
    ("/api/v1/cognitive", settings.rate_limit_cognitive_per_minute),
    ("/api/v1", settings.rate_limit_api_per_minute),
]

GLOBAL_LIMIT = 120


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting with graceful Redis degradation."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in {"/health", "/", "/docs", "/openapi.json"}:
            return cast(Response, await call_next(request))

        client_ip = self._get_client_ip(request)

        allowed, remaining = await check_rate_limit(
            f"global:{client_ip}",
            GLOBAL_LIMIT,
            60,
        )
        if not allowed:
            return self._too_many(60, "Global rate limit exceeded.")

        route_remaining = remaining
        for prefix, limit in ROUTE_LIMITS:
            if path.startswith(prefix):
                allowed, route_remaining = await check_rate_limit(
                    f"{prefix}:{client_ip}",
                    limit,
                    60,
                )
                if not allowed:
                    return self._too_many(
                        60,
                        f"Rate limit exceeded for {prefix}.",
                    )
                break

        response = cast(Response, await call_next(request))
        response.headers["X-RateLimit-Remaining"] = str(route_remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            values = [value.strip() for value in forwarded.split(",") if value.strip()]
            if values:
                # Render/proxies append the connecting client; using the
                # right-most value avoids trusting an attacker-supplied prefix.
                return values[-1]
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _too_many(reset_in: int, detail: str) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": detail},
            headers={
                "Retry-After": str(reset_in),
                "X-RateLimit-Remaining": "0",
            },
        )

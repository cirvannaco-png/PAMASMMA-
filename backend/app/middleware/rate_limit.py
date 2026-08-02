"""
PAMASMMA v4 — Rate Limiting Middleware
Sliding window counter via Redis. Applied at the ASGI layer for early rejection.
Limits: cognitive endpoints (20/min), auth (5/min), global (120/min).
Returns 429 with Retry-After header on breach.
"""
import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.redis_client import redis_client
from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

# ── Route → limit mapping ─────────────────────────────────────────────────────
ROUTE_LIMITS: list[tuple[str, int, int]] = [
    # (path_prefix, requests_per_window, window_seconds)
    ("/api/v1/auth",      settings.rate_limit_auth_per_minute,      60),
    ("/api/v1/cognitive", settings.rate_limit_cognitive_per_minute,  60),
    ("/api/v1",           settings.rate_limit_api_per_minute,        60),
]

GLOBAL_LIMIT = 120   # requests / 60s per IP, across all paths


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-IP sliding window rate limiter.
    Skips health check and static paths.
    Adds X-RateLimit-* headers to all responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip health and non-API paths
        path = request.url.path
        if path in ("/health", "/", "/docs", "/openapi.json"):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # Global limit
        allowed, remaining, reset_in = await self._check(
            f"rl:global:{client_ip}", GLOBAL_LIMIT, 60
        )
        if not allowed:
            return self._too_many(reset_in, "Global rate limit exceeded.")

        # Route-specific limit
        for prefix, limit, window in ROUTE_LIMITS:
            if path.startswith(prefix):
                route_key = f"rl:{prefix.replace('/', '_')}:{client_ip}"
                allowed, remaining, reset_in = await self._check(route_key, limit, window)
                if not allowed:
                    return self._too_many(reset_in, f"Rate limit exceeded for {prefix}.")
                break

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + reset_in)
        return response

    async def _check(
        self, key: str, limit: int, window: int
    ) -> tuple[bool, int, int]:
        """
        Atomic incr + expire. Returns (allowed, remaining, reset_in_seconds).
        """
        try:
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            results = await pipe.execute()
            count: int = results[0]
            ttl: int = results[1]

            if ttl == -1:                        # key exists but no TTL — fix it
                await redis_client.expire(key, window)
                ttl = window
            elif ttl == -2 or count == 1:        # key is fresh
                await redis_client.expire(key, window)
                ttl = window

            remaining = max(0, limit - count)
            return count <= limit, remaining, ttl
        except Exception as exc:
            # Redis failure → fail open (don't block requests)
            log.warning(f"Rate limit Redis error: {exc}")
            return True, limit, 60

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _too_many(self, reset_in: int, detail: str) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": detail},
            headers={
                "Retry-After": str(reset_in),
                "X-RateLimit-Remaining": "0",
            },
        )

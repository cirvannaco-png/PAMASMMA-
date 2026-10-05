"""
PAMASMMA v4.1 — FastAPI application.
"""
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.config import get_settings
from app.database import close_db, init_db, pg_event_bus
from app.events.handlers import (
    handle_cognitive_invocation,
    handle_override_queue,
    handle_scheduler_event,
)
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.redis_client import close_redis
from app.routers.cognitive import router as cognitive_router
from app.routers.events import broadcast, router as events_router
from app.routers.health import router as health_router
from app.scheduler.jobs import configure_scheduler, scheduler

settings = get_settings()

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(
        "PAMASMMA starting",
        version=settings.app_version,
        env=settings.app_env,
        persistence=settings.persistence_mode,
        intelligence=settings.model_provider,
    )

    await init_db()

    await pg_event_bus.connect()
    pg_event_bus.subscribe("cognitive_invocation", handle_cognitive_invocation)
    pg_event_bus.subscribe("override_queue", handle_override_queue)
    pg_event_bus.subscribe("scheduler_event", handle_scheduler_event)
    # Bridge Postgres/in-process events into authenticated SSE subscribers.
    for channel in ("cognitive_invocation", "override_queue", "scheduler_event"):
        pg_event_bus.subscribe(channel, broadcast)
    await pg_event_bus.start_listening()

    if settings.scheduler_enabled:
        configure_scheduler()
        scheduler.start()
        log.info("Scheduler started")
    else:
        log.info("Scheduler disabled")

    yield

    if settings.scheduler_enabled:
        scheduler.shutdown(wait=False)
    await pg_event_bus.disconnect()
    await close_redis()
    await close_db()
    log.info("PAMASMMA shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="PAMASMMA",
        description="Governed Synthetic Executive Intelligence — Cirvanna",
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
    )

    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Bootstrap-Token",
            "X-Request-ID",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Response-Time-Ms",
            "X-RateLimit-Remaining",
        ],
    )

    @app.middleware("http")
    async def add_timing(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Response-Time-Ms"] = (
            f"{(time.perf_counter() - start) * 1000:.2f}"
        )
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        log.error(
            "Unhandled exception",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error.",
                "path": str(request.url.path),
            },
        )

    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(cognitive_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    return app


app = create_app()

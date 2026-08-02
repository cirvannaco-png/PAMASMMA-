"""
PAMASMMA v4 — FastAPI Application
Lifespan: DB init → Redis → PGEventBus → Scheduler → Shutdown.
Middleware: RateLimiting → Logging → CORS → Timing.
"""
import logging
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db, pg_event_bus
from app.redis_client import redis_client
from app.scheduler.jobs import configure_scheduler, scheduler
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.logging import LoggingMiddleware
from app.events.handlers import (
    handle_cognitive_invocation,
    handle_override_queue,
    handle_scheduler_event,
)
from app.routers.health import router as health_router
from app.routers.cognitive import router as cognitive_router
from app.routers.events import router as events_router
from app.auth.router import router as auth_router

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
    log.info("PAMASMMA v4 starting", env=settings.app_env)

    await init_db()
    log.info("Database + pgvector ready")

    await pg_event_bus.connect()
    pg_event_bus.subscribe("cognitive_invocation", handle_cognitive_invocation)
    pg_event_bus.subscribe("override_queue",       handle_override_queue)
    pg_event_bus.subscribe("scheduler_event",      handle_scheduler_event)
    await pg_event_bus.start_listening()
    log.info("PGEventBus ready — 3 channels")

    configure_scheduler()
    scheduler.start()
    log.info("Scheduler started — 6 jobs active")

    log.info("PAMASMMA v4 ONLINE — all systems GO")
    yield

    log.info("PAMASMMA v4 shutting down")
    scheduler.shutdown(wait=False)
    await pg_event_bus.disconnect()
    await redis_client.aclose()
    log.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="PAMASMMA",
        description="Governed Synthetic Executive Intelligence — Cirvanna",
        version="4.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
    )

    # Middleware stack (outermost → innermost)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Response-Time-Ms", "X-RateLimit-Remaining"],
    )

    @app.middleware("http")
    async def add_timing(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time-Ms"] = f"{elapsed:.2f}"
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        log.error("Unhandled exception", path=request.url.path, error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error.", "path": str(request.url.path)},
        )

    app.include_router(health_router)
    app.include_router(auth_router,      prefix="/api/v1")
    app.include_router(cognitive_router, prefix="/api/v1")
    app.include_router(events_router,    prefix="/api/v1")

    return app


app = create_app()

"""
PAMASMMA v4 — Test Configuration
Shared fixtures for the entire test suite.
All external services (DB, Redis, Anthropic) are mocked by default.
Integration tests can opt-in via markers.
"""
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


# ── Session-scoped event loop ─────────────────────────────────────────────────
@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


# ── App fixture — full stack with mocked externals ────────────────────────────
@pytest_asyncio.fixture(scope="function")
async def app():
    """
    Create the FastAPI app with all external services mocked.
    DB, Redis, Anthropic, and Scheduler are replaced with AsyncMocks.
    """
    with (
        patch("app.database.init_db", new_callable=AsyncMock),
        patch("app.database.pg_event_bus.connect", new_callable=AsyncMock),
        patch("app.database.pg_event_bus.subscribe"),
        patch("app.database.pg_event_bus.start_listening", new_callable=AsyncMock),
        patch("app.database.pg_event_bus.disconnect", new_callable=AsyncMock),
        patch("app.database.pg_event_bus.publish", new_callable=AsyncMock),
        patch("app.redis_client.redis_client") as mock_redis,
        patch("app.scheduler.jobs.configure_scheduler"),
        patch("app.scheduler.jobs.scheduler") as mock_scheduler,
    ):
        # Redis mock — sensible defaults
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.pipeline.return_value.__aenter__ = AsyncMock()
        mock_redis.pipeline.return_value.__aexit__ = AsyncMock()
        mock_redis.aclose = AsyncMock()

        mock_scheduler.start = MagicMock()
        mock_scheduler.shutdown = MagicMock()

        from app.main import create_app
        application = create_app()

        async with application.router.lifespan_context(application):
            yield application


@pytest_asyncio.fixture(scope="function")
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client bound to the app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── Auth helpers ──────────────────────────────────────────────────────────────
@pytest.fixture
def mock_current_user():
    return {
        "user_id": "kelson-mwangi-cirvanna",
        "session_id": "test-session-abc123",
        "session": {"user_id": "kelson-mwangi-cirvanna"},
    }


@pytest.fixture
def auth_headers(mock_current_user):
    """
    Return headers that bypass JWT validation via patching get_current_user.
    Usage: use alongside `patch("app.auth.dependencies.get_current_user", ...)`.
    """
    return {"Authorization": "Bearer test-token-bypass"}


# ── Rate limit bypass ─────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def bypass_rate_limit():
    """Disable rate limiting in all tests by default."""
    with patch(
        "app.middleware.rate_limit.RateLimitMiddleware.dispatch",
        new_callable=AsyncMock,
    ) as mock_dispatch:
        # Passthrough — let request proceed normally, skip rate check
        async def passthrough(request, call_next):
            return await call_next(request)
        mock_dispatch.side_effect = passthrough
        yield

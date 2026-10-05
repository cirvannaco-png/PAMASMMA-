"""
PAMASMMA v4.0.1 — Shared Test Configuration
External services are mocked by default; tests must explicitly exercise real
integration boundaries.
"""
import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="function")
async def app():
    """Create the FastAPI app with external infrastructure mocked."""
    with (
        patch("app.database.init_db", new_callable=AsyncMock),
        patch("app.database.close_db", new_callable=AsyncMock),
        patch("app.database.pg_event_bus.connect", new_callable=AsyncMock),
        patch("app.database.pg_event_bus.subscribe"),
        patch("app.database.pg_event_bus.start_listening", new_callable=AsyncMock),
        patch("app.database.pg_event_bus.disconnect", new_callable=AsyncMock),
        patch("app.database.pg_event_bus.publish", new_callable=AsyncMock),
        patch("app.redis_client.redis_client") as mock_redis,
        patch("app.scheduler.jobs.configure_scheduler"),
        patch("app.scheduler.jobs.scheduler") as mock_scheduler,
    ):
        from app.config import get_settings

        get_settings().bootstrap_token = SecretStr("test-bootstrap-token")

        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.pipeline.return_value.__aenter__ = AsyncMock()
        mock_redis.pipeline.return_value.__aexit__ = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_redis.aclose = AsyncMock()

        mock_scheduler.start = MagicMock()
        mock_scheduler.shutdown = MagicMock()

        from app.main import create_app

        application = create_app()

        async with application.router.lifespan_context(application):
            yield application


@pytest_asyncio.fixture(scope="function")
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client bound to the test application."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def mock_current_user():
    return {
        "user_id": "kelson-mwangi-cirvanna",
        "session_id": "test-session-abc123",
        "session": {"user_id": "kelson-mwangi-cirvanna"},
    }


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token-bypass"}


@pytest.fixture(autouse=True)
def bypass_rate_limit():
    """Bypass outer middleware; endpoint-level auth limits are tested directly."""
    with patch(
        "app.middleware.rate_limit.RateLimitMiddleware.dispatch",
        new_callable=AsyncMock,
    ) as mock_dispatch:
        async def passthrough(request, call_next):
            return await call_next(request)

        mock_dispatch.side_effect = passthrough
        yield

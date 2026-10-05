"""
Durable Postgres + Valkey smoke tests.
Enabled only by the dedicated CI durable-infrastructure job.
"""
import os
import uuid

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(
    os.getenv("RUN_DURABLE_TESTS") != "1",
    reason="durable infrastructure tests are opt-in",
)
async def test_durable_postgres_and_valkey() -> None:
    from app.database import engine
    from app.redis_client import delete_session, get_session, redis_ping, set_session

    assert engine is not None
    assert await redis_ping()

    session_id = "durable-smoke-" + uuid.uuid4().hex
    await set_session(session_id, {"user_id": "durable-smoke"})
    try:
        assert await get_session(session_id) == {"user_id": "durable-smoke"}
    finally:
        await delete_session(session_id)

    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT 1")) == 1
        assert await connection.scalar(text(
            "SELECT version_num FROM alembic_version"
        )) == "002"
        assert await connection.scalar(text(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        )) is not None
        tables = {
            row[0] for row in (await connection.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ))).all()
        }

    assert {
        "pamasmma_users",
        "pamasmma_memories",
        "pamasmma_action_log",
        "pamasmma_override_queue",
    }.issubset(tables)

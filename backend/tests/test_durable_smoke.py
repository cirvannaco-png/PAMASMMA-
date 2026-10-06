"""
Durable Postgres + Valkey smoke tests.
Enabled only by the dedicated CI durable-infrastructure job.
"""
import os
import uuid

import pyotp
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(
    os.getenv("RUN_DURABLE_TESTS") != "1",
    reason="durable infrastructure tests are opt-in",
)
async def test_durable_postgres_valkey_auth_and_kernel() -> None:
    from app.auth.service import setup_totp, verify_totp_for_user
    from app.database import AsyncSessionLocal, engine
    from app.intelligence.registry import get_model_provider
    from app.redis_client import delete_session, get_session, redis_ping, set_session

    assert engine is not None
    assert AsyncSessionLocal is not None
    assert await redis_ping()

    session_id = "durable-smoke-" + uuid.uuid4().hex
    await set_session(session_id, {"user_id": "durable-smoke"})
    try:
        assert await get_session(session_id) == {"user_id": "durable-smoke"}
    finally:
        await delete_session(session_id)

    user_id = "durable-auth-" + uuid.uuid4().hex
    username = f"{user_id}@example.invalid"
    try:
        secret = await setup_totp(user_id, username)
        code = pyotp.TOTP(secret).now()
        assert await verify_totp_for_user(user_id, code)
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("DELETE FROM pamasmma_users WHERE user_key = :user_id"),
                {"user_id": user_id},
            )
            await session.commit()

    provider = get_model_provider()
    response = await provider.generate(
        "You are a durable CI smoke-test assistant.",
        [{"role": "user", "content": "State the next action."}],
        256,
    )
    assert "DECISION FRAME" in response

    async with engine.connect() as connection:
        assert await connection.scalar(text("SELECT 1")) == 1
        assert await connection.scalar(text(
            "SELECT version_num FROM alembic_version"
        )) == "005"
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
        "pamasmma_decisions",
        "pamasmma_beliefs",
        "pamasmma_outcomes",
        "pamasmma_world_entities",
        "pamasmma_world_relationships",
        "pamasmma_knowledge_sources",
        "pamasmma_knowledge_chunks",
    }.issubset(tables)

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
        assert await connection.scalar(
            text("SELECT version_num FROM alembic_version")
         ) == "013"
        assert await connection.scalar(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        ) is not None
        tables = {
            row[0]
            for row in (
                await connection.execute(
                    text(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname = 'public'"
                    )
                )
            ).all()
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
        "pamasmma_social_accounts",
        "pamasmma_social_posts",
        "pamasmma_social_engagement",
        "pamasmma_social_campaigns",
        "pamasmma_mcp_connectors",
        "pamasmma_mcp_tool_audit",
        "pamasmma_jarvis_conversations",
        "pamasmma_jarvis_messages",
    }.issubset(tables)

    from app.jarvis.service import (
        TurnAlreadyInProgress,
        begin_turn,
        create_conversation,
        finish_turn,
        get_conversation,
    )

    async with AsyncSessionLocal() as session:
        conversation = await create_conversation(
            session,
            user_id="durable-jarvis-" + uuid.uuid4().hex,
            title="Durable JARVIS smoke test",
        )
        owner_id = conversation.user_id
        conversation_id = conversation.id
        turn_id, history, user_message = await begin_turn(
            session,
            owner_id,
            conversation_id,
            "Test durable JARVIS conversation persistence.",
        )
        assert user_message["role"] == "user"
        assert history[-1]["content"] == "Test durable JARVIS conversation persistence."

        with pytest.raises(TurnAlreadyInProgress):
            await begin_turn(
                session,
                owner_id,
                conversation_id,
                "This concurrent turn must be rejected.",
            )
        await session.rollback()

        assistant_message = await finish_turn(
            session,
            owner_id,
            conversation_id,
            turn_id,
            "Durable assistant response.",
        )
        assert assistant_message is not None
        assert assistant_message["role"] == "assistant"

        stored_conversation, stored_messages = await get_conversation(
            session,
            owner_id,
            conversation_id,
        )
        assert stored_conversation.id == conversation_id
        assert [message.role for message in stored_messages] == ["user", "assistant"]

        voice_turn_id, voice_history, voice_user_message = await begin_turn(
            session,
            owner_id,
            conversation_id,
            "Check this voice transcript.",
            modality="voice",
            delegation_id="item_voice_durable_test",
        )
        assert voice_user_message["role"] == "user"
        voice_assistant_message = await finish_turn(
            session,
            owner_id,
            conversation_id,
            voice_turn_id,
            "Voice response persisted.",
            modality="voice",
        )
        assert voice_assistant_message is not None
        assert voice_assistant_message["modality"] == "voice"

        _, all_messages = await get_conversation(session, owner_id, conversation_id)
        assert [message.modality for message in all_messages] == ["text", "text", "voice", "voice"]
        await session.execute(
            text("DELETE FROM pamasmma_jarvis_conversations WHERE id = CAST(:id AS uuid)"),
            {"id": str(conversation_id)},
        )
        await session.commit()

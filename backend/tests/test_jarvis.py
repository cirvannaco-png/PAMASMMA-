"""Regression tests for JARVIS identity, memory isolation and persistence policy."""
import pytest
from httpx import AsyncClient

from app.auth.dependencies import get_current_user
from app.intelligence.context import ContextAssembler
from app.jarvis.scope import jarvis_memory_scope
from app.jarvis.system import JarvisSystem


def test_jarvis_memory_scope_is_stable_and_user_isolated():
    first = jarvis_memory_scope("founder-user")
    assert first == jarvis_memory_scope("founder-user")
    assert first != jarvis_memory_scope("another-user")
    assert first.startswith("jarvis:")
    assert len(first) < 100


def test_jarvis_system_is_pamasmma_scoped_and_has_no_action_claims():
    system = JarvisSystem(jarvis_memory_scope("founder-user"))
    assert system.system_id == "JARVIS"
    assert "PAMASMMA" in system.system_name
    assert "no action tools" in system.directive.lower()
    assert "Midas-touch2" in system.directive


def test_cognitive_context_accepts_a_separate_memory_namespace():
    context = ContextAssembler.assemble(
        [{"role": "user", "content": "Plan the next PAMASMMA milestone."}],
        user_id="founder-user",
        primary_system_id="JARVIS",
    )
    context.memory_scope_id = jarvis_memory_scope("founder-user")
    assert context.user_id == "founder-user"
    assert context.memory_scope_id != context.user_id
    assert context.primary_system_id == "JARVIS"


@pytest.mark.asyncio
async def test_jarvis_fails_closed_when_persistence_is_ephemeral(app, client: AsyncClient):
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "jarvis-test-user",
        "session_id": "jarvis-test-session",
        "session": {"user_id": "jarvis-test-user"},
    }
    try:
        response = await client.post(
            "/api/v1/jarvis/conversations",
            json={"title": "Ephemeral must not be accepted"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 503
    assert "durable PostgreSQL" in response.json()["detail"]


@pytest.mark.asyncio
async def test_live_voice_session_is_server_authenticated_and_event_scoped(monkeypatch):
    from types import SimpleNamespace
    from uuid import uuid4
    from typing import cast

    from sqlalchemy.ext.asyncio import AsyncSession

    import app.jarvis.router as jarvis_router

    captured = {}

    class FakeResponse:
        status_code = 201

        @staticmethod
        def json():
            return {
                "session": {"id": "live_test_session"},
                "transport": {"type": "webrtc", "sdp": "answer-sdp"},
            }

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, url, headers, json):
            captured.update({"url": url, "headers": headers, "payload": json})
            return FakeResponse()

    async def fake_get_conversation(db, user_id, conversation_id):
        return (
            SimpleNamespace(
                status="active",
                active_turn_id=None,
                active_turn_expires_at=None,
            ),
            [SimpleNamespace(role="user", content="Earlier context.")],
        )

    monkeypatch.setattr(jarvis_router, "get_conversation", fake_get_conversation)
    monkeypatch.setattr(
        jarvis_router,
        "get_settings",
        lambda: SimpleNamespace(openai_api_key="server-only-test-key"),
    )
    monkeypatch.setattr(jarvis_router.httpx, "AsyncClient", FakeAsyncClient)

    result = await jarvis_router.create_jarvis_voice_session(
        uuid4(),
        jarvis_router.VoiceSessionRequest(sdp="offer-sdp"),
        {"user_id": "voice-test-user"},
        cast(AsyncSession, object()),
    )

    assert result["session_id"] == "live_test_session"
    assert result["sdp"] == "answer-sdp"
    assert captured["url"] == "https://api.openai.com/v1/live/sessions"
    assert captured["headers"]["Authorization"] == "Bearer server-only-test-key"
    assert captured["headers"]["OpenAI-Safety-Identifier"].startswith("jarvis:")
    session = captured["payload"]["session"]
    assert session["model"] == "gpt-live-1.1"
    assert session["audio"]["output"]["voice"] == "vesper"
    assert session["delegation"]["type"] == "client"
    assert session["store"] is False
    assert session["client"]["data_channel"]["allowed_client_events"] == [
        "session.commentary.append",
        "session.close",
    ]
    assert {"type": "session.delegation.created"} in session["client"]["data_channel"]["allowed_server_events"]
    assert "server-only-test-key" not in str(result)

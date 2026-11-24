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

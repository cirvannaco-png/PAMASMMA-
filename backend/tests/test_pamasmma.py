"""
PAMASMMA v4 — Test Suite
pytest-asyncio. Uses in-memory overrides for external services.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """ASGI test client with mocked DB/Redis."""
    with patch("app.database.init_db", new_callable=AsyncMock), \
         patch("app.database.pg_event_bus.connect", new_callable=AsyncMock), \
         patch("app.database.pg_event_bus.start_listening", new_callable=AsyncMock), \
         patch("app.scheduler.jobs.configure_scheduler"), \
         patch("app.scheduler.jobs.scheduler") as mock_sched:
        mock_sched.start = MagicMock()
        mock_sched.shutdown = MagicMock()
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac


# ── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint(client):
    with patch("app.routers.health.redis_ping", return_value=True), \
         patch("app.routers.health.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)
        res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "version" in data
    assert data["version"] == "4.0.0"


# ── Auth — TOTP ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_totp_setup(client):
    with patch("app.redis_client.check_rate_limit", return_value=(True, 4)):
        res = await client.post("/api/v1/auth/totp/setup", json={
            "user_id": "test-user-001",
            "username": "test@example.com",
        })
    assert res.status_code == 200
    data = res.json()
    assert "secret" in data
    assert "uri" in data
    assert len(data["secret"]) >= 16


@pytest.mark.asyncio
async def test_totp_verify_invalid_code(client):
    with patch("app.redis_client.check_rate_limit", return_value=(True, 4)), \
         patch("app.auth.core.verify_totp", return_value=False):
        res = await client.post("/api/v1/auth/totp/verify", json={
            "user_id": "test-user-001",
            "secret": "JBSWY3DPEHPK3PXP",
            "code": "000000",
        })
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_totp_verify_valid_code(client):
    with patch("app.redis_client.check_rate_limit", return_value=(True, 4)), \
         patch("app.auth.core.verify_totp", return_value=True), \
         patch("app.auth.core.create_auth_session", return_value="test-session-id"):
        res = await client.post("/api/v1/auth/totp/verify", json={
            "user_id": "test-user-001",
            "secret": "JBSWY3DPEHPK3PXP",
            "code": "123456",
        })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_totp_rate_limit(client):
    with patch("app.redis_client.check_rate_limit", return_value=(False, 0)):
        res = await client.post("/api/v1/auth/totp/setup", json={
            "user_id": "attacker",
            "username": "attacker@evil.com",
        })
    assert res.status_code == 429


# ── Auth — TOTP Replay Prevention ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_totp_replay_attack_blocked():
    """A valid TOTP code used twice must be rejected on second use."""
    import pyotp
    from app.auth.core import verify_totp

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    code = totp.now()

    with patch("app.redis_client.mark_totp_used", return_value=True):
        first = await verify_totp("user-1", secret, code)
    assert first is True

    with patch("app.redis_client.mark_totp_used", return_value=False):
        second = await verify_totp("user-1", secret, code)
    assert second is False


# ── Cognitive Systems ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_systems_requires_auth(client):
    res = await client.get("/api/v1/cognitive/systems")
    assert res.status_code == 403  # no bearer token


@pytest.mark.asyncio
async def test_list_systems_authenticated(client):
    mock_user = {"user_id": "kelson", "session_id": "sess-001", "session": {}}
    with patch("app.auth.dependencies.get_current_user", return_value=mock_user):
        res = await client.get(
            "/api/v1/cognitive/systems",
            headers={"Authorization": "Bearer test-token"},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 10
    system_ids = [s["id"] for s in data["systems"]]
    for expected in ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"]:
        assert expected in system_ids


@pytest.mark.asyncio
async def test_invoke_invalid_system(client):
    mock_user = {"user_id": "kelson", "session_id": "sess-001", "session": {}}
    with patch("app.auth.dependencies.get_current_user", return_value=mock_user):
        res = await client.post(
            "/api/v1/cognitive/invoke",
            headers={"Authorization": "Bearer test-token"},
            json={
                "system_id": "S99",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
    assert res.status_code == 422  # pydantic validation rejects S99


@pytest.mark.asyncio
async def test_invoke_s1_executive(client):
    mock_user = {"user_id": "kelson", "session_id": "sess-001", "session": {}}
    with patch("app.auth.dependencies.get_current_user", return_value=mock_user), \
         patch("app.systems.s1_executive.s1_executive_system.invoke", new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = "Execute the quarterly brand audit across all channels."
        res = await client.post(
            "/api/v1/cognitive/invoke",
            headers={"Authorization": "Bearer test-token"},
            json={
                "system_id": "S1",
                "messages": [{"role": "user", "content": "What should I prioritize this week?"}],
                "stream": False,
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert data["system_id"] == "S1"
    assert len(data["response"]) > 0


# ── Systems Registry ──────────────────────────────────────────────────────────

def test_all_systems_registered():
    from app.systems import SYSTEMS, get_system
    assert len(SYSTEMS) == 10
    for sid in ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"]:
        system = get_system(sid)
        assert system.system_id == sid
        assert len(system.system_name) > 0
        assert len(system.directive) > 50


def test_unknown_system_raises():
    from app.systems import get_system
    with pytest.raises(KeyError):
        get_system("S99")


# ── JWT ───────────────────────────────────────────────────────────────────────

def test_jwt_issue_and_decode():
    from app.auth.core import issue_access_token, decode_token
    token = issue_access_token("user-123", "sess-abc")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["sid"] == "sess-abc"
    assert payload["type"] == "access"


def test_jwt_refresh_token_type():
    from app.auth.core import issue_refresh_token, decode_token
    token = issue_refresh_token("user-123", "sess-abc")
    payload = decode_token(token)
    assert payload["type"] == "refresh"

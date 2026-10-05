"""
PAMASMMA v4.1.0 — Test Suite
Tests exercise real module boundaries rather than patching imported aliases.
"""
from unittest.mock import AsyncMock, patch

import pyotp
import pytest

from app.auth.dependencies import get_current_user
from app.routers.events import broadcast, register_subscriber, unregister_subscriber


@pytest.mark.asyncio
async def test_health_endpoint(client):
    with patch("app.routers.health.redis_ping", return_value=True), \
         patch("app.routers.health.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["version"] == "4.1.0"



@pytest.mark.asyncio
async def test_health_ready_endpoint(client):
    with patch("app.routers.health.redis_ping", new=AsyncMock(return_value=True)), \
         patch("app.routers.health.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"



@pytest.mark.asyncio
async def test_auth_status_is_non_sensitive(client):
    response = await client.get(
        "/api/v1/auth/status",
        params={"user_id": "kelson-mwangi-cirvanna"},
    )
    assert response.status_code == 200
    assert set(response.json()) == {
        "setup_required",
        "totp_enabled",
        "webauthn_registered",
    }


@pytest.mark.asyncio
async def test_auth_status_rejects_unknown_identity(client):
    response = await client.get(
        "/api/v1/auth/status",
        params={"user_id": "attacker"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_totp_setup_requires_bootstrap_token(client):
    response = await client.post(
        "/api/v1/auth/totp/setup",
        json={
            "user_id": "kelson-mwangi-cirvanna",
            "username": "kelson@cirvanna.co",
        },
    )
    assert response.status_code in {401, 422}


@pytest.mark.asyncio
async def test_totp_setup_success(client):
    with patch(
        "app.auth.router.check_rate_limit",
        new=AsyncMock(return_value=(True, 4)),
    ), patch(
        "app.auth.router.setup_totp",
        new=AsyncMock(return_value="JBSWY3DPEHPK3PXP"),
    ):
        response = await client.post(
            "/api/v1/auth/totp/setup",
            headers={"X-Bootstrap-Token": "test-bootstrap-token"},
            json={
                "user_id": "kelson-mwangi-cirvanna",
                "username": "kelson@cirvanna.co",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["secret"] == "JBSWY3DPEHPK3PXP"
    assert data["uri"].startswith("otpauth://")
    assert data["issuer"] == "PAMASMMA"


@pytest.mark.asyncio
async def test_totp_setup_rejects_non_founder(client):
    with patch(
        "app.auth.router.check_rate_limit",
        new=AsyncMock(return_value=(True, 4)),
    ):
        response = await client.post(
            "/api/v1/auth/totp/setup",
            headers={"X-Bootstrap-Token": "test-bootstrap-token"},
            json={
                "user_id": "attacker",
                "username": "attacker@example.com",
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_totp_verify_uses_server_secret(client):
    with patch(
        "app.auth.router.check_rate_limit",
        new=AsyncMock(return_value=(True, 4)),
    ), patch(
        "app.auth.router.verify_totp_for_user",
        new=AsyncMock(return_value=False),
    ) as verify:
        response = await client.post(
            "/api/v1/auth/totp/verify",
            json={
                "user_id": "kelson-mwangi-cirvanna",
                "code": "000000",
                "secret": "ATTACKER_SUPPLIED_SECRET",
            },
        )

    assert response.status_code == 401
    verify.assert_awaited_once_with("kelson-mwangi-cirvanna", "000000")


@pytest.mark.asyncio
async def test_totp_verify_valid_code(client):
    with patch(
        "app.auth.router.check_rate_limit",
        new=AsyncMock(return_value=(True, 4)),
    ), patch(
        "app.auth.router.verify_totp_for_user",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.auth.router.create_auth_session",
        new=AsyncMock(return_value="test-session-id"),
    ):
        response = await client.post(
            "/api/v1/auth/totp/verify",
            json={
                "user_id": "kelson-mwangi-cirvanna",
                "code": "123456",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_totp_replay_attack_blocked():
    from app.auth.core import verify_totp

    secret = pyotp.random_base32()
    code = pyotp.TOTP(secret).now()

    with patch(
        "app.auth.core.mark_totp_used",
        new=AsyncMock(return_value=True),
    ):
        first = await verify_totp("user-1", secret, code)

    with patch(
        "app.auth.core.mark_totp_used",
        new=AsyncMock(return_value=False),
    ):
        second = await verify_totp("user-1", secret, code)

    assert first is True
    assert second is False


def test_totp_secret_encryption_round_trip():
    from app.security.crypto import decrypt_secret, encrypt_secret

    original = "TOP-SECRET-TOTP-VALUE"
    encrypted = encrypt_secret(original)

    assert encrypted != original
    assert decrypt_secret(encrypted) == original


@pytest.mark.asyncio
async def test_webauthn_registration_requires_authenticated_session(client):
    response = await client.post("/api/v1/auth/webauthn/register/begin")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_systems_authenticated(client, mock_current_user):
    from app.auth.dependencies import get_current_user

    app = client._transport.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    try:
        response = await client.get("/api/v1/cognitive/systems")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 10
    assert {s["id"] for s in data["systems"]} == {
        "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"
    }


@pytest.mark.asyncio
async def test_invoke_invalid_system(client, mock_current_user):
    app = client._transport.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    try:
        response = await client.post(
            "/api/v1/cognitive/invoke",
            json={
                "system_id": "S99",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invoke_s1_executive(client, mock_current_user):
    app = client._transport.app
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    try:
        with patch(
            "app.systems.s1_executive.s1_executive_system.invoke",
            new_callable=AsyncMock,
            return_value="Execute the quarterly brand audit across all channels.",
        ):
            response = await client.post(
                "/api/v1/cognitive/invoke",
                json={
                    "system_id": "S1",
                    "messages": [
                        {
                            "role": "user",
                            "content": "What should I prioritize this week?",
                        }
                    ],
                    "stream": False,
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["system_id"] == "S1"
    assert response.json()["response"]


def test_all_systems_registered():
    from app.systems import SYSTEMS, get_system

    assert len(SYSTEMS) == 10
    for system_id in [
        "S1", "S2", "S3", "S4", "S5",
        "S6", "S7", "S8", "S9", "S10",
    ]:
        system = get_system(system_id)
        assert system.system_id == system_id
        assert system.system_name
        assert len(system.directive) > 50


def test_unknown_system_raises():
    from app.systems import get_system

    with pytest.raises(KeyError):
        get_system("S99")


def test_jwt_issue_and_decode():
    from app.auth.core import decode_token, issue_access_token

    token = issue_access_token("user-123", "sess-abc")
    payload = decode_token(token)

    assert payload["sub"] == "user-123"
    assert payload["sid"] == "sess-abc"
    assert payload["type"] == "access"
    assert payload["jti"]


def test_jwt_refresh_token_type():
    from app.auth.core import decode_token, issue_refresh_token

    token = issue_refresh_token("user-123", "sess-abc")
    assert decode_token(token)["type"] == "refresh"


@pytest.mark.asyncio
async def test_refresh_token_requires_live_session(client):
    from app.auth.core import issue_refresh_token

    refresh_token = issue_refresh_token(
        "kelson-mwangi-cirvanna",
        "old-session",
    )

    session_mock = AsyncMock(
        side_effect=[
            {"user_id": "kelson-mwangi-cirvanna"},
            None,
        ]
    )

    with patch(
        "app.auth.router.check_rate_limit",
        new=AsyncMock(return_value=(True, 9)),
    ), patch(
        "app.auth.router.get_session",
        new=session_mock,
    ), patch(
        "app.auth.router.create_auth_session",
        new=AsyncMock(return_value="new-session"),
    ):
        first = await client.post(
            "/api/v1/auth/token/refresh",
            json={"refresh_token": refresh_token},
        )
        second = await client.post(
            "/api/v1/auth/token/refresh",
            json={"refresh_token": refresh_token},
        )

    assert first.status_code == 200
    assert second.status_code == 401


@pytest.mark.asyncio
async def test_sse_events_are_user_isolated():
    user_a = register_subscriber("cognitive_invocation", "user-a")
    user_b = register_subscriber("cognitive_invocation", "user-b")

    try:
        await broadcast(
            "cognitive_invocation",
            {"user_id": "user-a", "system_id": "S1"},
        )

        assert user_a.qsize() == 1
        assert user_b.qsize() == 0
    finally:
        unregister_subscriber("cognitive_invocation", user_a)
        unregister_subscriber("cognitive_invocation", user_b)

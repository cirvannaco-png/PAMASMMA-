"""Persistence for external integrations using PAMASMMA's encrypted secret boundary."""
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.integrations.google import refresh_access_token
from app.redis_client import cache_pop, cache_set
from app.security.crypto import decrypt_secret, encrypt_secret

settings = get_settings()


def _now() -> datetime:
    return datetime.now(UTC)


async def save_oauth_state(state: str, user_id: str) -> None:
    await cache_set(
        f"integration:google:oauth:{state}",
        {"user_id": user_id},
        ttl=600,
    )


async def pop_oauth_state(state: str) -> dict[str, Any] | None:
    return await cache_pop(f"integration:google:oauth:{state}")


async def save_google_account(
    user_id: str,
    token: dict[str, Any],
    identity: dict[str, Any],
) -> dict[str, Any]:
    access = str(token.get("access_token") or "")
    refresh = str(token.get("refresh_token") or "")
    if not access or not refresh:
        raise ValueError(
            "Google OAuth did not return the required access and refresh tokens."
        )

    account_id = uuid.uuid4()
    expires = int(token.get("expires_in") or 3600)
    record = {
        "id": account_id,
        "user_id": user_id,
        "provider": "google",
        "external_account_id": str(
            identity.get("sub") or identity.get("email") or account_id
        ),
        "display_name": identity.get("email") or identity.get("name"),
        "access_token_enc": encrypt_secret(access),
        "refresh_token_enc": encrypt_secret(refresh),
        "token_expires_at": _now() + timedelta(seconds=max(60, expires - 60)),
        "scopes": str(token.get("scope") or "").split(),
        "metadata": identity,
    }

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO pamasmma_integration_accounts
                (id,user_id,provider,external_account_id,display_name,
                 access_token_enc,refresh_token_enc,token_expires_at,scopes,
                 metadata,status)
                VALUES
                (:id,:user_id,:provider,:external_account_id,:display_name,
                 :access_token_enc,:refresh_token_enc,:token_expires_at,:scopes,
                 :metadata,'active')
                ON CONFLICT (user_id,provider,external_account_id)
                DO UPDATE SET
                  display_name=EXCLUDED.display_name,
                  access_token_enc=EXCLUDED.access_token_enc,
                  refresh_token_enc=EXCLUDED.refresh_token_enc,
                  token_expires_at=EXCLUDED.token_expires_at,
                  scopes=EXCLUDED.scopes,
                  metadata=EXCLUDED.metadata,
                  status='active',
                  updated_at=now()
                """
            ),
            record,
        )
        await session.commit()

    return {
        "id": str(account_id),
        "provider": "google",
        "external_account_id": record["external_account_id"],
        "display_name": record["display_name"],
        "scopes": record["scopes"],
        "status": "active",
    }


async def list_integrations(user_id: str) -> list[dict[str, Any]]:
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT id::text AS id, provider, external_account_id,
                       display_name, scopes, status, created_at, updated_at
                FROM pamasmma_integration_accounts
                WHERE user_id=:user_id
                ORDER BY created_at DESC
                """
            ),
            {"user_id": user_id},
        )
        return [dict(row) for row in result.mappings().all()]


async def get_integration(
    user_id: str,
    account_id: str,
) -> dict[str, Any] | None:
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT *
                FROM pamasmma_integration_accounts
                WHERE id=:id AND user_id=:user_id AND status='active'
                """
            ),
            {"id": account_id, "user_id": user_id},
        )
        row = result.mappings().first()
    return dict(row) if row else None


async def google_access_token(user_id: str, account_id: str) -> str:
    account = await get_integration(user_id, account_id)
    if not account:
        raise ValueError("Google integration account not found.")

    access = decrypt_secret(account["access_token_enc"])
    expires = account.get("token_expires_at")
    if expires and expires > _now() + timedelta(seconds=30):
        return access

    token = await refresh_access_token(
        decrypt_secret(account["refresh_token_enc"])
    )
    new_access = str(token.get("access_token") or "")
    if not new_access:
        raise ValueError("Google token refresh returned no access token.")

    new_exp = _now() + timedelta(
        seconds=max(60, int(token.get("expires_in") or 3600) - 60)
    )
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                UPDATE pamasmma_integration_accounts
                SET access_token_enc=:token,
                    token_expires_at=:expires,
                    updated_at=now()
                WHERE id=:id AND user_id=:user_id
                """
            ),
            {
                "token": encrypt_secret(new_access),
                "expires": new_exp,
                "id": account_id,
                "user_id": user_id,
            },
        )
        await session.commit()
    return new_access


async def save_mcp_connector(
    user_id: str,
    name: str,
    endpoint: str,
    bearer_token: str | None,
    enabled: bool,
) -> dict[str, Any]:
    parsed = urlparse(endpoint)
    if parsed.scheme != "https":
        raise ValueError("MCP endpoints must use HTTPS in production.")

    allowed = {
        host.lower()
        for host in settings.mcp_allowed_hosts
        if host.strip()
    }
    if allowed and (parsed.hostname or "").lower() not in allowed:
        raise ValueError("MCP endpoint host is not allowlisted.")

    assert AsyncSessionLocal is not None
    connector_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO pamasmma_mcp_connectors
                (id,user_id,name,endpoint,bearer_token_enc,enabled)
                VALUES (:id,:user_id,:name,:endpoint,:token,:enabled)
                """
            ),
            {
                "id": connector_id,
                "user_id": user_id,
                "name": name,
                "endpoint": endpoint,
                "token": encrypt_secret(bearer_token) if bearer_token else None,
                "enabled": enabled,
            },
        )
        await session.commit()

    return {
        "id": str(connector_id),
        "name": name,
        "endpoint": endpoint,
        "enabled": enabled,
    }


async def list_mcp_connectors(user_id: str) -> list[dict[str, Any]]:
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT id::text AS id, name, endpoint, enabled,
                       created_at, updated_at
                FROM pamasmma_mcp_connectors
                WHERE user_id=:user_id
                ORDER BY created_at DESC
                """
            ),
            {"user_id": user_id},
        )
        return [dict(row) for row in result.mappings().all()]


async def get_mcp_connector(
    user_id: str,
    connector_id: str,
) -> dict[str, Any] | None:
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT *
                FROM pamasmma_mcp_connectors
                WHERE id=:id AND user_id=:user_id AND enabled=true
                """
            ),
            {"id": connector_id, "user_id": user_id},
        )
        row = result.mappings().first()
    return dict(row) if row else None

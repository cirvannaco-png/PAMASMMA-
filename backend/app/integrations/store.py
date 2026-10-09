"""Persistence for external integrations using PAMASMMA's encrypted secret boundary."""
import hashlib
import ipaddress
import json
import socket
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

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


def validate_mcp_endpoint(endpoint: str) -> str:
    """Validate remote MCP egress against transport and host policy."""
    parsed = urlparse(endpoint)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https":
        raise ValueError("MCP endpoints must use HTTPS.")
    if not host or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("MCP endpoint must be an HTTPS URL without embedded credentials or fragments.")
    if parsed.port not in (None, 443):
        raise ValueError("MCP endpoint must use the standard HTTPS port 443.")

    local_suffixes = (".localhost", ".local", ".internal", ".lan", ".home")
    if host in {"localhost", "metadata.google.internal"} or host.endswith(local_suffixes):
        raise ValueError("Local and internal MCP destinations are not permitted.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        # Some URL/network stacks accept legacy IPv4 forms such as 127.1,
        # 2130706433, or 0x7f000001 and normalize them to loopback addresses.
        # Reject any host that inet_aton recognizes as an address but
        # ipaddress did not accept as a canonical IPv4/IPv6 literal.
        try:
            socket.inet_aton(host)
        except OSError:
            address = None
        else:
            raise ValueError("Non-canonical IP literal addresses are not permitted.")
    if address and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise ValueError("Private, loopback, link-local and reserved IP destinations are not permitted.")

    allowed = {
        item.strip().lower().rstrip(".")
        for item in settings.mcp_allowed_hosts
        if item.strip()
    }
    if settings.is_production and not allowed:
        raise ValueError("MCP connections are disabled in production until MCP_ALLOWED_HOSTS is configured.")
    if allowed and host not in allowed:
        raise ValueError("MCP endpoint host is not in MCP_ALLOWED_HOSTS.")
    return host


async def save_mcp_connector(
    user_id: str,
    name: str,
    endpoint: str,
    bearer_token: str | None,
    enabled: bool,
    auth_mode: str = "bearer",
) -> dict[str, Any]:
    validate_mcp_endpoint(endpoint)
    if auth_mode not in {"bearer", "oauth"}:
        raise ValueError("MCP auth_mode must be 'bearer' or 'oauth'.")
    if auth_mode == "oauth" and bearer_token:
        raise ValueError("Do not supply a bearer token when auth_mode is 'oauth'.")

    assert AsyncSessionLocal is not None
    connector_id = uuid.uuid4()
    auth_status = "disconnected" if auth_mode == "oauth" else "configured"
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO pamasmma_mcp_connectors
                (id,user_id,name,endpoint,bearer_token_enc,enabled,auth_mode,auth_status)
                VALUES (:id,:user_id,:name,:endpoint,:token,:enabled,:auth_mode,:auth_status)
                """
            ),
            {
                "id": connector_id,
                "user_id": user_id,
                "name": name,
                "endpoint": endpoint,
                "token": encrypt_secret(bearer_token) if bearer_token else None,
                "enabled": enabled,
                "auth_mode": auth_mode,
                "auth_status": auth_status,
            },
        )
        await session.commit()

    return {
        "id": str(connector_id),
        "name": name,
        "endpoint": endpoint,
        "enabled": enabled,
        "auth_mode": auth_mode,
        "auth_status": auth_status,
    }


async def list_mcp_connectors(user_id: str) -> list[dict[str, Any]]:
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT id::text AS id, name, endpoint, enabled, auth_mode, auth_status,
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


async def _save_mcp_oauth_blob(
    user_id: str,
    connector_id: str,
    column: str,
    value: dict[str, Any],
) -> None:
    columns = {
        "tokens": "oauth_tokens_enc",
        "client_info": "oauth_client_info_enc",
    }
    if column not in columns:
        raise ValueError("Unsupported OAuth credential type.")
    encrypted = encrypt_secret(json.dumps(value))
    auth_status = ", auth_status='connected'" if column == "tokens" else ""
    statement = (
        f"UPDATE pamasmma_mcp_connectors SET {columns[column]}=:payload"
        f"{auth_status}, updated_at=now() "
        "WHERE id=:id AND user_id=:user_id AND enabled=true AND auth_mode='oauth'"
    )
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(statement),
            {"payload": encrypted, "id": connector_id, "user_id": user_id},
        )
        await session.commit()
        if cast(CursorResult[Any], result).rowcount != 1:
            raise ValueError("OAuth MCP connector not found or disabled.")


async def save_mcp_oauth_tokens(
    user_id: str,
    connector_id: str,
    value: dict[str, Any],
) -> None:
    await _save_mcp_oauth_blob(user_id, connector_id, "tokens", value)


async def save_mcp_oauth_client_info(
    user_id: str,
    connector_id: str,
    value: dict[str, Any],
) -> None:
    await _save_mcp_oauth_blob(user_id, connector_id, "client_info", value)


async def clear_mcp_oauth_credentials(user_id: str, connector_id: str) -> None:
    """Clear tokens while retaining OAuth client registration for safe reconnects."""
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                UPDATE pamasmma_mcp_connectors
                SET oauth_tokens_enc=NULL, auth_status='disconnected', updated_at=now()
                WHERE id=:id AND user_id=:user_id AND auth_mode='oauth'
                """
            ),
            {"id": connector_id, "user_id": user_id},
        )
        await session.commit()
        if cast(CursorResult[Any], result).rowcount != 1:
            raise ValueError("OAuth MCP connector not found.")



async def update_mcp_oauth_status(
    user_id: str,
    connector_id: str,
    status: str,
) -> None:
    if status not in {"disconnected", "connected", "error"}:
        raise ValueError("Unsupported MCP OAuth status.")
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                UPDATE pamasmma_mcp_connectors
                SET auth_status=:status, updated_at=now()
                WHERE id=:id AND user_id=:user_id AND auth_mode='oauth' AND enabled=true
                """
            ),
            {"status": status, "id": connector_id, "user_id": user_id},
        )
        await session.commit()
        if cast(CursorResult[Any], result).rowcount != 1:
            raise ValueError("OAuth MCP connector not found or disabled.")


async def delete_mcp_connector(user_id: str, connector_id: str) -> bool:
    """Delete one connector and its encrypted credentials for the owning user only."""
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                DELETE FROM pamasmma_mcp_connectors
                WHERE id=:id AND user_id=:user_id
                """
            ),
            {"id": connector_id, "user_id": user_id},
        )
        await session.commit()
    return cast(CursorResult[Any], result).rowcount == 1



def _sha256_json(value: Any) -> str:
    serialized = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


async def create_mcp_tool_audit(
    user_id: str,
    connector_id: str,
    connector_name: str,
    tool_name: str,
    arguments: dict[str, Any],
    confirmation_required: bool,
    confirmed: bool,
    status: str = "started",
) -> str:
    """Persist metadata and a digest, never raw tool arguments or results."""
    if status not in {"started", "blocked"}:
        raise ValueError("Initial MCP audit status must be started or blocked.")
    audit_id = uuid.uuid4()
    created_at = _now()
    finished_at = created_at if status == "blocked" else None
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO pamasmma_mcp_tool_audit
                (id,user_id,connector_id,connector_name,tool_name,status,
                 confirmation_required,confirmed,arguments_sha256,created_at,finished_at)
                VALUES
                (:id,:user_id,:connector_id,:connector_name,:tool_name,:status,
                 :confirmation_required,:confirmed,:arguments_sha256,:created_at,:finished_at)
                """
            ),
            {
                "id": audit_id,
                "user_id": user_id,
                "connector_id": uuid.UUID(str(connector_id)),
                "connector_name": connector_name,
                "tool_name": tool_name,
                "status": status,
                "confirmation_required": confirmation_required,
                "confirmed": confirmed,
                "arguments_sha256": _sha256_json(arguments),
                "created_at": created_at,
                "finished_at": finished_at,
            },
        )
        await session.commit()
    return str(audit_id)


async def finish_mcp_tool_audit(
    user_id: str,
    audit_id: str,
    status: str,
    duration_ms: int,
    result: Any = None,
    error_type: str | None = None,
) -> None:
    if status not in {"succeeded", "failed"}:
        raise ValueError("Final MCP audit status must be succeeded or failed.")
    result_hash = _sha256_json(result) if result is not None else None
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        updated = await session.execute(
            text(
                """
                UPDATE pamasmma_mcp_tool_audit
                SET status=:status,result_sha256=:result_sha256,duration_ms=:duration_ms,
                    error_type=:error_type,finished_at=:finished_at
                WHERE id=:id AND user_id=:user_id AND status='started'
                """
            ),
            {
                "id": uuid.UUID(audit_id),
                "user_id": user_id,
                "status": status,
                "result_sha256": result_hash,
                "duration_ms": max(0, duration_ms),
                "error_type": error_type[:120] if error_type else None,
                "finished_at": _now(),
            },
        )
        await session.commit()
        if cast(CursorResult[Any], updated).rowcount != 1:
            raise ValueError("MCP audit record not found or already finalized.")


async def list_mcp_tool_audit(
    user_id: str,
    limit: int = 50,
    connector_id: str | None = None,
) -> list[dict[str, Any]]:
    bounded_limit = min(max(limit, 1), 200)
    filters = "user_id=:user_id"
    params: dict[str, Any] = {"user_id": user_id, "limit": bounded_limit}
    if connector_id:
        filters += " AND connector_id=:connector_id"
        params["connector_id"] = uuid.UUID(connector_id)

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                f"""
                SELECT id::text AS id, connector_id::text AS connector_id,
                       connector_name, tool_name, status, confirmation_required,
                       confirmed, arguments_sha256, result_sha256, duration_ms,
                       error_type, created_at, finished_at
                FROM pamasmma_mcp_tool_audit
                WHERE {filters}
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            params,
        )
        return [dict(row) for row in result.mappings().all()]

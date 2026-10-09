"""Governed MCP bridge with persisted MCP SDK OAuth client support."""
import asyncio
import logging
import time
from typing import Any, cast
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import httpx2
from jsonschema import ValidationError as JSONSchemaValidationError
from jsonschema import validate as validate_json_schema
from mcp import Client
from mcp.client.auth import AuthorizationCodeResult, OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
from pydantic import AnyUrl

from app.config import get_settings
from app.integrations.store import (
    clear_mcp_oauth_credentials,
    create_mcp_tool_audit,
    finish_mcp_tool_audit,
    get_mcp_connector,
    save_mcp_oauth_client_info,
    save_mcp_oauth_tokens,
    update_mcp_oauth_status,
    validate_mcp_endpoint,
)
from app.redis_client import cache_pop, cache_set
from app.security.crypto import decrypt_secret

log = logging.getLogger(__name__)
settings = get_settings()
_OAUTH_KEY_PREFIX = "integration:mcp:oauth:"
_oauth_tasks: dict[str, asyncio.Task[None]] = {}


class InvalidMcpToolArguments(ValueError):
    """MCP call arguments do not match the currently discovered tool schema."""


def requires_confirmation(
    tool_name: str,
    annotations: dict[str, Any] | None = None,
) -> bool:
    """Require confirmation unless the server explicitly marks a tool read-only."""
    del tool_name  # Names are not a trustworthy security boundary.
    metadata = annotations or {}
    read_only = metadata.get("readOnlyHint", metadata.get("read_only_hint"))
    destructive = metadata.get("destructiveHint", metadata.get("destructive_hint"))
    open_world = metadata.get("openWorldHint", metadata.get("open_world_hint"))
    return not (
        read_only is True
        and destructive is not True
        and open_world is not True
    )


class _PersistentOAuthStorage:
    """MCP SDK token-storage adapter backed by encrypted PAMASMMA persistence."""

    def __init__(self, user_id: str, connector_id: str) -> None:
        self.user_id = user_id
        self.connector_id = connector_id

    async def get_tokens(self) -> OAuthToken | None:
        connector = await get_mcp_connector(self.user_id, self.connector_id)
        encrypted = connector.get("oauth_tokens_enc") if connector else None
        if not encrypted:
            return None
        payload = decrypt_secret(encrypted)
        return OAuthToken.model_validate_json(payload)

    async def set_tokens(self, tokens: OAuthToken) -> None:
        await save_mcp_oauth_tokens(
            self.user_id,
            self.connector_id,
            tokens.model_dump(mode="json"),
        )

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        connector = await get_mcp_connector(self.user_id, self.connector_id)
        encrypted = connector.get("oauth_client_info_enc") if connector else None
        if not encrypted:
            return None
        payload = decrypt_secret(encrypted)
        return OAuthClientInformationFull.model_validate_json(payload)

    async def set_client_info(
        self,
        client_info: OAuthClientInformationFull,
    ) -> None:
        await save_mcp_oauth_client_info(
            self.user_id,
            self.connector_id,
            client_info.model_dump(mode="json"),
        )


def _oauth_client(
    connector: dict[str, Any],
    user_id: str,
    flow_id: str | None,
) -> OAuthClientProvider:
    """Build the official MCP SDK OAuth client with PAMASMMA-backed token storage."""
    callback_state: dict[str, str] = {}

    async def redirect_handler(authorization_url: str) -> None:
        if not flow_id:
            raise PermissionError(
                "MCP OAuth authorization is required. Start an authorization flow from Integrations."
            )
        state_values = parse_qs(urlparse(authorization_url).query).get("state", [])
        if not state_values or not state_values[0]:
            raise RuntimeError("MCP OAuth authorization URL omitted state.")
        state = state_values[0]
        callback_state["state"] = state
        await cache_set(
            f"{_OAUTH_KEY_PREFIX}pending:{state}",
            {
                "user_id": user_id,
                "connector_id": str(connector["id"]),
                "flow_id": flow_id,
            },
            ttl=settings.mcp_oauth_flow_timeout_seconds,
        )
        await cache_set(
            f"{_OAUTH_KEY_PREFIX}ready:{flow_id}",
            {"authorization_url": authorization_url, "state": state},
            ttl=90,
        )

    async def callback_handler() -> AuthorizationCodeResult:
        state = callback_state.get("state")
        if not state:
            raise RuntimeError("MCP OAuth callback cannot be matched to an authorization state.")
        deadline = time.monotonic() + settings.mcp_oauth_flow_timeout_seconds
        while time.monotonic() < deadline:
            payload = await cache_pop(f"{_OAUTH_KEY_PREFIX}callback:{state}")
            if payload:
                if payload.get("error"):
                    raise RuntimeError("MCP OAuth authorization was declined or failed.")
                return AuthorizationCodeResult(
                    code=str(payload["code"]),
                    state=str(payload["state"]),
                    iss=str(payload["iss"]) if payload.get("iss") else None,
                )
            await asyncio.sleep(0.25)
        raise TimeoutError("MCP OAuth authorization expired before callback.")

    redirect_uri = settings.mcp_oauth_redirect_uri
    if settings.is_production and urlparse(redirect_uri).scheme != "https":
        raise ValueError("MCP_OAUTH_REDIRECT_URI must use HTTPS in production.")

    return OAuthClientProvider(
        server_url=connector["endpoint"],
        client_metadata=OAuthClientMetadata(
            client_name="PAMASMMA",
            redirect_uris=[AnyUrl(redirect_uri)],
        ),
        storage=_PersistentOAuthStorage(user_id, str(connector["id"])),
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )


async def _client(
    connector: dict[str, Any],
    user_id: str,
    oauth_flow_id: str | None = None,
):
    validate_mcp_endpoint(str(connector["endpoint"]))
    headers: dict[str, str] = {}
    auth = None
    auth_mode = str(connector.get("auth_mode") or "bearer")
    if auth_mode == "oauth":
        auth = _oauth_client(connector, user_id, oauth_flow_id)
    elif connector.get("bearer_token_enc"):
        headers["Authorization"] = (
            f"Bearer {decrypt_secret(connector['bearer_token_enc'])}"
        )

    http_client = httpx2.AsyncClient(
        headers=headers,
        auth=auth,
        timeout=httpx2.Timeout(30, read=300),
        follow_redirects=False,
    )
    transport = streamable_http_client(
        connector["endpoint"],
        http_client=http_client,
    )
    return http_client, transport


async def discover_tools(
    user_id: str,
    connector_id: str,
    oauth_flow_id: str | None = None,
) -> list[dict[str, Any]]:
    connector = await get_mcp_connector(user_id, connector_id)
    if not connector:
        raise ValueError("MCP connector not found or disabled.")
    if (
        connector.get("auth_mode") == "oauth"
        and not connector.get("oauth_tokens_enc")
        and not oauth_flow_id
    ):
        raise PermissionError("Authorize this MCP connector before discovering tools.")

    http_client, transport = await _client(connector, user_id, oauth_flow_id)
    async with http_client:
        async with Client(transport) as mcp:
            result = await mcp.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                }
                for tool in result.tools
            ]


async def call_tool(
    user_id: str,
    connector_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    confirmed: bool = False,
) -> dict[str, Any]:
    connector = await get_mcp_connector(user_id, connector_id)
    if not connector:
        raise ValueError("MCP connector not found or disabled.")
    if (
        connector.get("auth_mode") == "oauth"
        and not connector.get("oauth_tokens_enc")
    ):
        raise PermissionError("Authorize this MCP connector before using its tools.")

    http_client, transport = await _client(connector, user_id)
    async with http_client:
        async with Client(transport) as mcp:
            listed = await mcp.list_tools()
            tool = next(
                (candidate for candidate in listed.tools if candidate.name == tool_name),
                None,
            )
            if tool is None:
                raise ValueError("MCP tool is not present in the connector's current tool list.")

            raw_tool = (
                tool.model_dump(mode="json", by_alias=True)
                if hasattr(tool, "model_dump")
                else {}
            )
            annotations = raw_tool.get("annotations") if isinstance(raw_tool, dict) else {}
            if not isinstance(annotations, dict):
                annotations = {}

            input_schema = getattr(tool, "input_schema", None)
            if isinstance(input_schema, dict):
                try:
                    validate_json_schema(instance=arguments, schema=input_schema)
                except JSONSchemaValidationError as exc:
                    audit_id = await create_mcp_tool_audit(
                        user_id=user_id,
                        connector_id=str(connector["id"]),
                        connector_name=str(connector["name"]),
                        tool_name=tool_name,
                        arguments=arguments,
                        confirmation_required=True,
                        confirmed=False,
                        status="blocked",
                    )
                    log.warning(
                        "MCP tool call blocked by input validation",
                        extra={
                            "user_id": user_id,
                            "connector_id": str(connector["id"]),
                            "tool_name": tool_name,
                            "audit_id": audit_id,
                        },
                    )
                    raise InvalidMcpToolArguments(
                        "MCP tool arguments do not match the discovered input schema."
                    ) from exc

            confirmation_required = requires_confirmation(tool_name, annotations)
            if confirmation_required and not confirmed:
                await create_mcp_tool_audit(
                    user_id=user_id,
                    connector_id=str(connector["id"]),
                    connector_name=str(connector["name"]),
                    tool_name=tool_name,
                    arguments=arguments,
                    confirmation_required=True,
                    confirmed=False,
                    status="blocked",
                )
                raise PermissionError(
                    "This MCP tool is not explicitly known to be read-only. "
                    "Explicit confirmation is required."
                )

            # Persist the invocation record before allowing any external side effect.
            audit_id = await create_mcp_tool_audit(
                user_id=user_id,
                connector_id=str(connector["id"]),
                connector_name=str(connector["name"]),
                tool_name=tool_name,
                arguments=arguments,
                confirmation_required=confirmation_required,
                confirmed=confirmed,
                status="started",
            )
            started_at = time.monotonic()
            try:
                result = await mcp.call_tool(tool_name, arguments)
            except Exception as exc:
                try:
                    await finish_mcp_tool_audit(
                        user_id=user_id,
                        audit_id=audit_id,
                        status="failed",
                        duration_ms=int((time.monotonic() - started_at) * 1000),
                        error_type=type(exc).__name__,
                    )
                except Exception as audit_exc:
                    log.error(
                        "Could not finalize failed MCP audit record",
                        extra={
                            "audit_id": audit_id,
                            "error_type": type(audit_exc).__name__,
                        },
                    )
                raise

            content = [
                item.model_dump(mode="json")
                if hasattr(item, "model_dump")
                else str(item)
                for item in result.content
            ]
            result_payload = {
                "content": content,
                "structured_content": result.structured_content,
                "is_error": bool(getattr(result, "isError", False)),
            }
            is_error = result_payload["is_error"]
            audit_status = "recorded"
            try:
                await finish_mcp_tool_audit(
                    user_id=user_id,
                    audit_id=audit_id,
                    status="failed" if is_error else "succeeded",
                    duration_ms=int((time.monotonic() - started_at) * 1000),
                    result=result_payload,
                    error_type="MCPToolResultError" if is_error else None,
                )
            except Exception as audit_exc:
                # The external operation already ran; do not induce a duplicate by
                # failing the response solely because final audit persistence failed.
                audit_status = "completion_pending_reconciliation"
                log.error(
                    "MCP result returned but audit finalization failed",
                    extra={
                        "audit_id": audit_id,
                        "error_type": type(audit_exc).__name__,
                    },
                )

            return {
                **result_payload,
                "audit_id": audit_id,
                "audit_status": audit_status,
                "source": "mcp_external",
                "trusted": False,
                "confirmation_required": confirmation_required,
            }



async def _run_oauth_flow(user_id: str, connector_id: str, flow_id: str) -> None:
    try:
        await discover_tools(user_id, connector_id, oauth_flow_id=flow_id)
        await cache_set(
            f"{_OAUTH_KEY_PREFIX}result:{flow_id}",
            {"status": "connected"},
            ttl=600,
        )
    except Exception as exc:
        log.warning("MCP OAuth flow failed for connector %s: %s", connector_id, type(exc).__name__)
        try:
            await update_mcp_oauth_status(user_id, connector_id, "error")
        except ValueError:
            pass
        await cache_set(
            f"{_OAUTH_KEY_PREFIX}result:{flow_id}",
            {"status": "failed", "message": "Authorization failed. Retry the connection."},
            ttl=600,
        )


async def begin_oauth_authorization(user_id: str, connector_id: str) -> dict[str, Any]:
    connector = await get_mcp_connector(user_id, connector_id)
    if not connector:
        raise ValueError("MCP connector not found or disabled.")
    if connector.get("auth_mode") != "oauth":
        raise ValueError("This connector is configured for bearer-token authentication, not OAuth.")
    validate_mcp_endpoint(str(connector["endpoint"]))

    flow_id = uuid4().hex
    task = asyncio.create_task(_run_oauth_flow(user_id, connector_id, flow_id))
    _oauth_tasks[flow_id] = task
    task.add_done_callback(lambda _: _oauth_tasks.pop(flow_id, None))

    deadline = time.monotonic() + min(45, settings.mcp_oauth_flow_timeout_seconds)
    while time.monotonic() < deadline:
        ready = await cache_pop(f"{_OAUTH_KEY_PREFIX}ready:{flow_id}")
        if ready:
            return {
                "status": "authorization_required",
                "flow_id": flow_id,
                "authorization_url": ready["authorization_url"],
            }
        result = await cache_pop(f"{_OAUTH_KEY_PREFIX}result:{flow_id}")
        if isinstance(result, dict) and result:
            return cast(dict[str, Any], result)
        await asyncio.sleep(0.2)
    raise TimeoutError("MCP server did not complete OAuth discovery in time.")


async def receive_oauth_callback(
    code: str | None,
    state: str,
    issuer: str | None,
    error: str | None,
) -> dict[str, Any]:
    pending = await cache_pop(f"{_OAUTH_KEY_PREFIX}pending:{state}")
    if not pending:
        raise ValueError("MCP OAuth state is invalid, expired, or already used.")
    callback: dict[str, Any] = {"state": state, "iss": issuer}
    if error or not code:
        callback["error"] = error or "missing_code"
    else:
        callback["code"] = code
    await cache_set(f"{_OAUTH_KEY_PREFIX}callback:{state}", callback, ttl=90)
    return {"flow_id": pending["flow_id"], "status": "callback_received"}


async def disconnect_oauth(user_id: str, connector_id: str) -> None:
    await clear_mcp_oauth_credentials(user_id, connector_id)


async def registry_search(
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    async with httpx2.AsyncClient(timeout=httpx2.Timeout(20)) as client:
        response = await client.get(
            "https://registry.modelcontextprotocol.io/v0.1/servers",
            params={
                "search": query,
                "version": "latest",
                "limit": min(limit, 100),
            },
        )
    response.raise_for_status()
    payload = cast(dict[str, Any], response.json())
    return cast(list[dict[str, Any]], payload.get("servers", []))

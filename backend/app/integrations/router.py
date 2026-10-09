"""HTTP boundary for Google Workspace and governed MCP connectors."""
import base64
import secrets
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.integrations.contracts import (
    DriveUpload,
    GoogleSendEmail,
    McpConnectorCreate,
    McpToolCall,
)
from app.integrations.google import (
    GoogleProviderError,
    authorization_url,
    delete_drive_file,
    exchange_code,
    get_drive_file,
    get_message,
    list_drive,
    list_messages,
    send_message,
    upload_drive_file,
    userinfo,
)
from app.integrations.mcp import (
    begin_oauth_authorization,
    call_tool,
    disconnect_oauth,
    discover_tools,
    receive_oauth_callback,
    registry_search,
)
from app.integrations.mcp_catalog import get_mcp_connection_profile, recommended_mcp_connections
from app.integrations.store import (
    google_access_token,
    list_integrations,
    list_mcp_connectors,
    pop_oauth_state,
    save_google_account,
    save_mcp_connector,
    save_oauth_state,
)

router = APIRouter(prefix="/integrations", tags=["Integrations"])
CurrentUser = Annotated[dict, Depends(get_current_user)]
settings = get_settings()


def _frontend(query: str) -> str:
    origin = (
        settings.allowed_origins[0].rstrip("/")
        if settings.allowed_origins
        else "http://localhost:3000"
    )
    return f"{origin}/dashboard?{query}"


@router.get("/google/start")
async def google_start(current_user: CurrentUser) -> dict:
    state = secrets.token_urlsafe(32)
    await save_oauth_state(state, current_user["user_id"])
    return {"authorization_url": authorization_url(state), "state": state}


@router.get("/google/callback")
async def google_callback(
    code: str | None = Query(default=None),
    state: str = Query(...),
    error: str | None = Query(default=None),
):
    payload = await pop_oauth_state(state)
    if not payload:
        raise HTTPException(400, "Invalid or expired Google OAuth state.")
    if error:
        return RedirectResponse(
            _frontend(f"integration_error={quote(error)}"),
            303,
        )
    if not code:
        raise HTTPException(400, "Google authorization code is missing.")

    try:
        token = await exchange_code(code)
        identity = await userinfo(str(token["access_token"]))
        await save_google_account(payload["user_id"], token, identity)
        return RedirectResponse(_frontend("google_connected=1"), 303)
    except (GoogleProviderError, ValueError) as exc:
        return RedirectResponse(
            _frontend(f"integration_error={quote(str(exc))}"),
            303,
        )


@router.get("")
async def integrations(current_user: CurrentUser) -> dict:
    return {
        "integrations": await list_integrations(current_user["user_id"]),
        "mcp": await list_mcp_connectors(current_user["user_id"]),
    }


async def _account_token(current_user: dict, account_id: str) -> str:
    return await google_access_token(current_user["user_id"], account_id)


@router.get("/google/{account_id}/gmail/messages")
async def gmail_messages(
    account_id: str,
    current_user: CurrentUser,
    q: str | None = None,
    max_results: int = Query(50, ge=1, le=100),
) -> dict:
    return await list_messages(
        await _account_token(current_user, account_id),
        q,
        max_results,
    )


@router.get("/google/{account_id}/gmail/messages/{message_id}")
async def gmail_message(
    account_id: str,
    message_id: str,
    current_user: CurrentUser,
) -> dict:
    return await get_message(
        await _account_token(current_user, account_id),
        message_id,
    )


@router.post("/google/{account_id}/gmail/send")
async def gmail_send(
    account_id: str,
    body: GoogleSendEmail,
    current_user: CurrentUser,
) -> dict:
    return await send_message(
        await _account_token(current_user, account_id),
        body.model_dump(),
    )


@router.get("/google/{account_id}/drive/files")
async def drive_files(
    account_id: str,
    current_user: CurrentUser,
    q: str | None = None,
    page_size: int = Query(100, ge=1, le=1000),
) -> dict:
    return await list_drive(
        await _account_token(current_user, account_id),
        q,
        page_size,
    )


@router.get("/google/{account_id}/drive/files/{file_id}")
async def drive_file(
    account_id: str,
    file_id: str,
    current_user: CurrentUser,
) -> dict:
    return await get_drive_file(
        await _account_token(current_user, account_id),
        file_id,
    )


@router.post("/google/{account_id}/drive/upload")
async def drive_upload(
    account_id: str,
    body: DriveUpload,
    current_user: CurrentUser,
) -> dict:
    try:
        content = base64.b64decode(body.content_base64, validate=True)
    except ValueError as exc:
        raise HTTPException(422, "content_base64 is invalid.") from exc
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "Drive upload exceeds 15 MiB API boundary.")
    return await upload_drive_file(
        await _account_token(current_user, account_id),
        body.name,
        body.mime_type,
        content,
        body.parent_id,
    )


@router.delete("/google/{account_id}/drive/files/{file_id}")
async def drive_delete(
    account_id: str,
    file_id: str,
    current_user: CurrentUser,
) -> dict:
    return await delete_drive_file(
        await _account_token(current_user, account_id),
        file_id,
    )


@router.post("/mcp")
async def mcp_add(
    body: McpConnectorCreate,
    current_user: CurrentUser,
) -> dict:
    try:
        return await save_mcp_connector(
            current_user["user_id"],
            body.name,
            str(body.endpoint),
            body.bearer_token,
            body.enabled,
            body.auth_mode,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/mcp")
async def mcp_list(current_user: CurrentUser) -> dict:
    return {"connectors": await list_mcp_connectors(current_user["user_id"])}


@router.get("/mcp/registry/search")
async def mcp_registry_search(
    current_user: CurrentUser,
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    del current_user
    return {"servers": await registry_search(q, limit)}


@router.get("/mcp/recommended")
async def mcp_recommended(
    current_user: CurrentUser,
    role: str | None = Query(default=None, max_length=80),
    priority: str | None = Query(default=None, max_length=20),
) -> dict:
    del current_user
    return {"connections": recommended_mcp_connections(role=role, priority=priority)}


@router.get("/mcp/catalog/{connection_id}")
async def mcp_catalog_profile(
    connection_id: str,
    current_user: CurrentUser,
) -> dict:
    del current_user
    profile = get_mcp_connection_profile(connection_id)
    if not profile:
        raise HTTPException(404, "MCP catalog connection not found.")
    return {"connection": profile}

@router.get("/mcp/oauth/callback")
async def mcp_oauth_callback(
    state: str = Query(..., min_length=1, max_length=500),
    code: str | None = Query(default=None, max_length=10000),
    iss: str | None = Query(default=None, max_length=2000),
    error: str | None = Query(default=None, max_length=500),
) -> RedirectResponse:
    try:
        await receive_oauth_callback(code, state, iss, error)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if error:
        return RedirectResponse(_frontend("mcp_oauth=denied"), 303)
    if not code:
        return RedirectResponse(_frontend("mcp_oauth=failed"), 303)
    return RedirectResponse(_frontend("mcp_oauth=callback_received"), 303)


@router.post("/mcp/{connector_id}/oauth/start")
async def mcp_oauth_start(
    connector_id: str,
    current_user: CurrentUser,
) -> dict:
    try:
        return await begin_oauth_authorization(current_user["user_id"], connector_id)
    except PermissionError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(504, str(exc)) from exc


@router.post("/mcp/{connector_id}/oauth/disconnect")
async def mcp_oauth_disconnect(
    connector_id: str,
    current_user: CurrentUser,
) -> dict:
    try:
        await disconnect_oauth(current_user["user_id"], connector_id)
        return {"status": "disconnected", "connector_id": connector_id}
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

@router.get("/mcp/{connector_id}/tools")
async def mcp_tools(
    connector_id: str,
    current_user: CurrentUser,
) -> dict:
    try:
        return {
            "tools": await discover_tools(
                current_user["user_id"],
                connector_id,
            )
        }
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/mcp/{connector_id}/call")
async def mcp_call(
    connector_id: str,
    body: McpToolCall,
    current_user: CurrentUser,
) -> dict:
    try:
        return await call_tool(
            current_user["user_id"],
            connector_id,
            body.tool_name,
            body.arguments,
            body.confirmed,
        )
    except PermissionError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

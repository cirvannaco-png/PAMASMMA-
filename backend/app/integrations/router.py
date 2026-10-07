"""HTTP boundary for Google Workspace and governed MCP connectors."""
import base64
import secrets
from typing import Annotated
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.integrations.contracts import DriveUpload, GoogleSendEmail, McpConnectorCreate, McpToolCall
from app.integrations.google import authorization_url, exchange_code, userinfo, list_messages, get_message, send_message, list_drive, get_drive_file, delete_drive_file, upload_drive_file, GoogleProviderError
from app.integrations.mcp import discover_tools, call_tool, registry_search
from app.integrations.store import google_access_token, list_integrations, save_google_account, pop_oauth_state, save_oauth_state, save_mcp_connector, list_mcp_connectors
router=APIRouter(prefix="/integrations",tags=["Integrations"])
CurrentUser=Annotated[dict,Depends(get_current_user)]
settings=get_settings()
def _frontend(query:str)->str:
    origin=settings.allowed_origins[0].rstrip("/") if settings.allowed_origins else "http://localhost:3000"
    return f"{origin}/dashboard?{query}"
@router.get("/google/start")
async def google_start(current_user:CurrentUser):
    state=secrets.token_urlsafe(32);await save_oauth_state(state,current_user["user_id"]);return {"authorization_url":authorization_url(state),"state":state}
@router.get("/google/callback")
async def google_callback(code:str|None=Query(default=None),state:str=Query(...),error:str|None=Query(default=None)):
    payload=await pop_oauth_state(state)
    if not payload: raise HTTPException(400,"Invalid or expired Google OAuth state.")
    if error: return RedirectResponse(_frontend(f"integration_error={quote(error)}"),303)
    if not code: raise HTTPException(400,"Google authorization code is missing.")
    try:
        token=await exchange_code(code);identity=await userinfo(str(token["access_token"]));await save_google_account(payload["user_id"],token,identity)
        return RedirectResponse(_frontend("google_connected=1"),303)
    except (GoogleProviderError,ValueError) as exc: return RedirectResponse(_frontend(f"integration_error={quote(str(exc))}"),303)
@router.get("")
async def integrations(current_user:CurrentUser): return {"integrations":await list_integrations(current_user["user_id"]),"mcp":await list_mcp_connectors(current_user["user_id"])}
async def _account_token(current_user:dict,account_id:str): return await google_access_token(current_user["user_id"],account_id)
@router.get("/google/{account_id}/gmail/messages")
async def gmail_messages(account_id:str,current_user:CurrentUser,q:str|None=None,max_results:int=Query(50,ge=1,le=100)): return await list_messages(await _account_token(current_user,account_id),q,max_results)
@router.get("/google/{account_id}/gmail/messages/{message_id}")
async def gmail_message(account_id:str,message_id:str,current_user:CurrentUser): return await get_message(await _account_token(current_user,account_id),message_id)
@router.post("/google/{account_id}/gmail/send")
async def gmail_send(account_id:str,body:GoogleSendEmail,current_user:CurrentUser): return await send_message(await _account_token(current_user,account_id),body.model_dump())
@router.get("/google/{account_id}/drive/files")
async def drive_files(account_id:str,current_user:CurrentUser,q:str|None=None,page_size:int=Query(100,ge=1,le=1000)): return await list_drive(await _account_token(current_user,account_id),q,page_size)
@router.get("/google/{account_id}/drive/files/{file_id}")
async def drive_file(account_id:str,file_id:str,current_user:CurrentUser): return await get_drive_file(await _account_token(current_user,account_id),file_id)
@router.post("/google/{account_id}/drive/upload")
async def drive_upload(account_id:str,body:DriveUpload,current_user:CurrentUser):
    try: content=base64.b64decode(body.content_base64,validate=True)
    except ValueError as exc: raise HTTPException(422,"content_base64 is invalid.") from exc
    if len(content)>15*1024*1024: raise HTTPException(413,"Drive upload exceeds 15 MiB API boundary.")
    return await upload_drive_file(await _account_token(current_user,account_id),body.name,body.mime_type,content,body.parent_id)
@router.delete("/google/{account_id}/drive/files/{file_id}")
async def drive_delete(account_id:str,file_id:str,current_user:CurrentUser): return await delete_drive_file(await _account_token(current_user,account_id),file_id)
@router.post("/mcp")
async def mcp_add(body:McpConnectorCreate,current_user:CurrentUser):
    try: return await save_mcp_connector(current_user["user_id"],body.name,str(body.endpoint),body.bearer_token,body.enabled)
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
@router.get("/mcp")
async def mcp_list(current_user:CurrentUser): return {"connectors":await list_mcp_connectors(current_user["user_id"])}
@router.get("/mcp/registry/search")
async def mcp_registry_search(current_user:CurrentUser,q:str=Query(...,min_length=1,max_length=100),limit:int=Query(20,ge=1,le=100)):
    del current_user
    return {"servers":await registry_search(q,limit)}
@router.get("/mcp/{connector_id}/tools")
async def mcp_tools(connector_id:str,current_user:CurrentUser):
    try: return {"tools":await discover_tools(current_user["user_id"],connector_id)}
    except ValueError as exc: raise HTTPException(404,str(exc)) from exc
@router.post("/mcp/{connector_id}/call")
async def mcp_call(connector_id:str,body:McpToolCall,current_user:CurrentUser):
    try: return await call_tool(current_user["user_id"],connector_id,body.tool_name,body.arguments,body.confirmed)
    except PermissionError as exc: raise HTTPException(409,str(exc)) from exc
    except ValueError as exc: raise HTTPException(404,str(exc)) from exc

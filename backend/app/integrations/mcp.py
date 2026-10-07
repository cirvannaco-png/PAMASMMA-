"""Governed MCP client bridge for external Streamable HTTP servers."""
from typing import Any
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from app.integrations.store import get_mcp_connector
from app.security.crypto import decrypt_secret
async def _client(connector:dict[str,Any]):
    headers={}
    if connector.get("bearer_token_enc"): headers["Authorization"]=f"Bearer {decrypt_secret(connector['bearer_token_enc'])}"
    http_client=httpx2.AsyncClient(headers=headers,timeout=httpx2.Timeout(30,read=300))
    transport=streamable_http_client(connector["endpoint"],http_client=http_client)
    return http_client,transport
async def discover_tools(user_id:str,connector_id:str)->list[dict[str,Any]]:
    connector=await get_mcp_connector(user_id,connector_id)
    if not connector: raise ValueError("MCP connector not found or disabled.")
    http_client,transport=await _client(connector)
    try:
        async with http_client:
            async with Client(transport) as mcp:
                result=await mcp.list_tools();return [{"name":t.name,"description":t.description,"input_schema":t.inputSchema} for t in result.tools]
    finally: pass
async def call_tool(user_id:str,connector_id:str,tool_name:str,arguments:dict[str,Any],confirmed:bool=False)->dict[str,Any]:
    connector=await get_mcp_connector(user_id,connector_id)
    if not connector: raise ValueError("MCP connector not found or disabled.")
    http_client,transport=await _client(connector)
    async with http_client:
        async with Client(transport) as mcp:
            result=await mcp.call_tool(tool_name,arguments)
            return {"content":[x.model_dump(mode="json") if hasattr(x,"model_dump") else str(x) for x in result.content],"structured_content":result.structured_content}


async def registry_search(query: str, limit: int = 20) -> list[dict[str, Any]]:
    async with httpx2.AsyncClient(timeout=httpx2.Timeout(20)) as client:
        response = await client.get(
            "https://registry.modelcontextprotocol.io/v0.1/servers",
            params={"search": query, "version": "latest", "limit": min(limit, 100)},
        )
    response.raise_for_status()
    return response.json().get("servers", [])

def requires_confirmation(tool_name: str) -> bool:
    lowered = tool_name.lower()
    return any(token in lowered for token in (
        "delete","remove","write","create","update","send","publish","post",
        "execute","run","deploy","purchase","transfer",
    ))

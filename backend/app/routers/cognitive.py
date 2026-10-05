"""
PAMASMMA v4 — Cognitive Router
Endpoints: invoke system (sync + stream), list systems, action log, override queue.
All endpoints require JWT authentication.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.auth.dependencies import get_current_user
from app.systems import SYSTEM_METADATA, get_system
from app.database import pg_event_bus
from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/cognitive", tags=["Cognitive Systems"])

CurrentUser = Annotated[dict, Depends(get_current_user)]


# ── Schemas ───────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=32000)


class InvokeRequest(BaseModel):
    system_id: str = Field(..., pattern="^S([1-9]|10)$")
    messages: list[Message] = Field(..., min_length=1, max_length=50)
    stream: bool = False


class OverrideRequest(BaseModel):
    system_id: str
    directive: str = Field(..., min_length=10, max_length=2000)
    reason: str = Field(..., min_length=5, max_length=500)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/systems")
async def list_systems(_: CurrentUser) -> dict:
    """List all 10 cognitive systems with metadata."""
    return {"systems": SYSTEM_METADATA, "count": len(SYSTEM_METADATA)}


@router.post("/invoke")
async def invoke_system(
    body: InvokeRequest,
    current_user: CurrentUser,
) -> dict | StreamingResponse:
    """
    Invoke a cognitive system with conversation history.
    Supports streaming (SSE) via stream=true.
    """
    try:
        system = get_system(body.system_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System {body.system_id} not found.",
        )

    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    user_id = current_user["user_id"]

    if body.stream:
        async def event_stream():
            generator = await system.invoke(messages, user_id, stream=True)
            async for chunk in generator:
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    response = await system.invoke(messages, user_id, stream=False)
    return {
        "system_id": body.system_id,
        "system_name": system.system_name,
        "response": response,
    }


@router.get("/action-log")
async def get_action_log(
    current_user: CurrentUser,
    limit: int = Query(default=50, le=200),
    system_id: str | None = Query(default=None),
) -> dict:
    """
    Retrieve the PAMASMMA action log from Postgres.
    Filterable by system_id.
    """
    from app.database import AsyncSessionLocal
    from sqlalchemy import text

    query = """
        SELECT id, system_id, system_name, user_id,
               query_preview, latency_ms, created_at
        FROM pamasmma_action_log
        WHERE user_id = :user_id
        {system_filter}
        ORDER BY created_at DESC
        LIMIT :limit
    """.format(
        system_filter="AND system_id = :system_id" if system_id else ""
    )

    params: dict = {"user_id": current_user["user_id"], "limit": limit}
    if system_id:
        params["system_id"] = system_id.upper()

    async with AsyncSessionLocal() as session:
        result = await session.execute(text(query), params)
        rows = result.fetchall()

    return {
        "entries": [
            {
                "id": str(row.id),
                "system_id": row.system_id,
                "system_name": row.system_name,
                "query_preview": row.query_preview,
                "latency_ms": row.latency_ms,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
        "count": len(rows),
    }


@router.post("/override")
async def queue_override(
    body: OverrideRequest,
    current_user: CurrentUser,
) -> dict:
    """
    Queue a behavioral override directive for a cognitive system.
    Emits a pg_notify event for the override queue consumer.
    """
    try:
        get_system(body.system_id)  # validate system exists
    except KeyError:
        raise HTTPException(status_code=404, detail=f"System {body.system_id} not found.")

    await pg_event_bus.publish(
        channel="override_queue",
        payload={
            "system_id": body.system_id.upper(),
            "directive": body.directive,
            "reason": body.reason,
            "user_id": current_user["user_id"],
        },
    )
    return {"status": "queued", "system_id": body.system_id.upper()}

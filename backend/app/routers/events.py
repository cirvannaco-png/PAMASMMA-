"""
PAMASMMA v4 — Events Router
Server-Sent Events (SSE) stream for real-time frontend updates.
Subscribes to Postgres LISTEN/NOTIFY channels and forwards to the client.
Auth: token query param (Bearer not usable in EventSource).
"""
import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.auth.core import decode_token
from app.redis_client import get_session

log = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["Events"])

# In-process subscriber queues: channel → list[asyncio.Queue]
_subscribers: dict[str, list[asyncio.Queue]] = {}


def register_subscriber(channel: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.setdefault(channel, []).append(q)
    return q


def unregister_subscriber(channel: str, q: asyncio.Queue) -> None:
    if channel in _subscribers:
        try:
            _subscribers[channel].remove(q)
        except ValueError:
            pass


async def broadcast(channel: str, data: dict) -> None:
    """Called by PGEventBus handlers to fan-out to all SSE subscribers."""
    for q in list(_subscribers.get(channel, [])):
        try:
            q.put_nowait({"type": channel, "data": data})
        except asyncio.QueueFull:
            pass  # slow client — drop event


CHANNELS = ["cognitive_invocation", "override_queue", "scheduler_event"]


async def _event_generator(user_id: str) -> AsyncGenerator[str, None]:
    queues = {ch: register_subscriber(ch) for ch in CHANNELS}

    try:
        # Initial connection confirmation
        yield f"data: {json.dumps({'type': 'connected', 'data': {'user_id': user_id}})}\n\n"

        while True:
            # Wait for any event across all channels
            done, _ = await asyncio.wait(
                [asyncio.ensure_future(q.get()) for q in queues.values()],
                timeout=30,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                # 30s heartbeat to keep connection alive
                yield "data: {\"type\":\"heartbeat\"}\n\n"
                continue

            for task in done:
                try:
                    event = task.result()
                    yield f"data: {json.dumps(event)}\n\n"
                except Exception as exc:
                    log.debug(f"SSE event error: {exc}")

            # Cancel pending tasks
            for task in [t for t in done if not t.done()]:
                task.cancel()

    except asyncio.CancelledError:
        pass
    finally:
        for ch, q in queues.items():
            unregister_subscriber(ch, q)
        log.debug(f"SSE client disconnected: {user_id}")


@router.get("/stream")
async def event_stream(token: str = Query(...)) -> StreamingResponse:
    """
    SSE endpoint. Auth via ?token= query param (EventSource doesn't support headers).
    Streams cognitive_invocation, override_queue, scheduler_event channels.
    """
    # Validate token
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Not an access token")
        user_id = payload["sub"]
        session_id = payload["sid"]
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    # Confirm session is live
    session = await get_session(session_id)
    if not session or session.get("user_id") != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Session expired.")

    return StreamingResponse(
        _event_generator(user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

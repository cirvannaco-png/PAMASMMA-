"""
PAMASMMA v4.0.1 — Events Router
User-isolated Server-Sent Events stream for realtime frontend updates.
"""
import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.auth.core import decode_token
from app.redis_client import get_session

log = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["Events"])

# channel -> subscriber id -> (user_id, queue)
_subscribers: dict[str, dict[int, tuple[str, asyncio.Queue]]] = {}

CHANNELS = [
    "cognitive_invocation",
    "override_queue",
    "scheduler_event",
]
USER_SCOPED_CHANNELS = {"cognitive_invocation", "override_queue"}


def register_subscriber(channel: str, user_id: str) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    subscribers = _subscribers.setdefault(channel, {})
    subscribers[id(queue)] = (user_id, queue)
    return queue


def unregister_subscriber(channel: str, queue: asyncio.Queue) -> None:
    subscribers = _subscribers.get(channel)
    if not subscribers:
        return
    subscribers.pop(id(queue), None)
    if not subscribers:
        _subscribers.pop(channel, None)


async def broadcast(channel: str, data: dict) -> None:
    """Fan out only events authorized for each connected SSE subscriber."""
    for subscriber_user_id, queue in list(_subscribers.get(channel, {}).values()):
        if (
            channel in USER_SCOPED_CHANNELS
            and data.get("user_id") != subscriber_user_id
        ):
            continue
        try:
            queue.put_nowait({"type": channel, "data": data})
        except asyncio.QueueFull:
            log.warning(
                "Dropping SSE event for slow client: channel=%s user=%s",
                channel,
                subscriber_user_id,
            )


async def _event_generator(user_id: str) -> AsyncGenerator[str, None]:
    queues = {
        channel: register_subscriber(channel, user_id)
        for channel in CHANNELS
    }

    try:
        yield (
            "data: "
            + json.dumps(
                {
                    "type": "connected",
                    "data": {"user_id": user_id},
                }
            )
            + "\n\n"
        )

        while True:
            tasks = {
                asyncio.create_task(queue.get())
                for queue in queues.values()
            }

            done: set[asyncio.Task] = set()
            pending: set[asyncio.Task] = set()
            try:
                done, pending = await asyncio.wait(
                    tasks,
                    timeout=30,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if not done:
                    yield "data: {\"type\":\"heartbeat\"}\n\n"
                    continue

                for task in done:
                    try:
                        event = task.result()
                    except asyncio.CancelledError:
                        continue
                    except Exception:
                        log.exception("SSE event task failed")
                        continue

                    yield f"data: {json.dumps(event)}\n\n"
            finally:
                for task in pending:
                    task.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)

    except asyncio.CancelledError:
        log.debug("SSE client disconnected: %s", user_id)
    finally:
        for channel, queue in queues.items():
            unregister_subscriber(channel, queue)


@router.get("/stream")
async def event_stream(token: str = Query(..., min_length=1)) -> StreamingResponse:
    """
    SSE endpoint. Authentication remains query-token based for native
    EventSource compatibility; sessions are still validated in Redis.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Not an access token")
        user_id = str(payload["sub"])
        session_id = str(payload["sid"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from None

    session = await get_session(session_id)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(status_code=401, detail="Session expired.")

    return StreamingResponse(
        _event_generator(user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

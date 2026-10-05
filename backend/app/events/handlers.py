"""
PAMASMMA v4.1 — Event Handlers
Durable mode persists to Postgres; memory mode records bounded in-process events.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.runtime import memory_store

log = logging.getLogger(__name__)
settings = get_settings()


async def handle_cognitive_invocation(channel: str, data: dict) -> None:
    if not settings.is_persistent:
        memory_store.action_log.append(
            {
                "id": f"memory-{len(memory_store.action_log) + 1}",
                "system_id": data.get("system_id", "UNKNOWN"),
                "system_name": data.get("system_name"),
                "user_id": data.get("user_id", "UNKNOWN"),
                "query_preview": (data.get("query_preview") or "")[:500],
                "latency_ms": data.get("latency_ms"),
                "created_at": datetime.now(timezone.utc),
            }
        )
        del memory_store.action_log[:-1000]
        return

    assert AsyncSessionLocal is not None
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO pamasmma_action_log
                        (system_id, system_name, user_id, query_preview, latency_ms, created_at)
                    VALUES
                        (:system_id, :system_name, :user_id, :query_preview, :latency_ms, NOW())
                """),
                {
                    "system_id": data.get("system_id", "UNKNOWN"),
                    "system_name": data.get("system_name"),
                    "user_id": data.get("user_id", "UNKNOWN"),
                    "query_preview": (data.get("query_preview") or "")[:500],
                    "latency_ms": data.get("latency_ms"),
                },
            )
            await session.commit()
    except Exception:
        log.exception("handle_cognitive_invocation failed")


async def handle_override_queue(channel: str, data: dict) -> None:
    if not settings.is_persistent:
        memory_store.overrides.append(
            {
                "id": f"memory-{len(memory_store.overrides) + 1}",
                "system_id": data.get("system_id", "UNKNOWN"),
                "directive": data.get("directive", ""),
                "reason": data.get("reason"),
                "user_id": data.get("user_id", "UNKNOWN"),
                "status": "pending",
                "created_at": datetime.now(timezone.utc),
            }
        )
        del memory_store.overrides[:-500]
        return

    assert AsyncSessionLocal is not None
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO pamasmma_override_queue
                        (system_id, directive, reason, user_id, status, created_at)
                    VALUES
                        (:system_id, :directive, :reason, :user_id, 'pending', NOW())
                """),
                {
                    "system_id": data.get("system_id", "UNKNOWN"),
                    "directive": data.get("directive", ""),
                    "reason": data.get("reason"),
                    "user_id": data.get("user_id", "UNKNOWN"),
                },
            )
            await session.commit()
    except Exception:
        log.exception("handle_override_queue failed")


async def handle_scheduler_event(channel: str, data: dict) -> None:
    job_id = data.get("job", "?")
    name = data.get("name", "?")
    ts = data.get("triggered_at", "?")
    extras = {
        key: value
        for key, value in data.items()
        if key not in {"job", "name", "triggered_at"}
    }
    log.info(
        "Scheduler [%s] %s at %s%s",
        job_id,
        name,
        ts,
        f" extras={extras}" if extras else "",
    )

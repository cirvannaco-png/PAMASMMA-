"""
PAMASMMA v4 — Event Handlers
Postgres LISTEN/NOTIFY consumers.
Each handler is idempotent and non-blocking — failures are logged, not raised.

Channels:
  cognitive_invocation → persist to pamasmma_action_log
  override_queue       → persist to pamasmma_override_queue
  scheduler_event      → structured log entry
"""
import logging

from sqlalchemy import text

from app.database import AsyncSessionLocal

log = logging.getLogger(__name__)


async def handle_cognitive_invocation(channel: str, data: dict) -> None:
    """
    Persist a cognitive system invocation to the action log.
    Triggered on every S1–S10 invoke via pg_notify('cognitive_invocation', ...).
    """
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
                    "system_id":    data.get("system_id", "UNKNOWN"),
                    "system_name":  data.get("system_name"),
                    "user_id":      data.get("user_id", "UNKNOWN"),
                    "query_preview": (data.get("query_preview") or "")[:500],
                    "latency_ms":   data.get("latency_ms"),
                },
            )
            await session.commit()
        log.debug(f"Action log: {data.get('system_id')} — {data.get('latency_ms')}ms")
    except Exception as exc:
        log.error(f"handle_cognitive_invocation failed: {exc}")


async def handle_override_queue(channel: str, data: dict) -> None:
    """
    Persist an override directive to the override queue table.
    Triggered when a founder queues a behavioral override via POST /cognitive/override.
    """
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
                    "reason":    data.get("reason"),
                    "user_id":   data.get("user_id", "UNKNOWN"),
                },
            )
            await session.commit()
        log.info(f"Override queued for {data.get('system_id')}: {data.get('reason', '')[:80]}")
    except Exception as exc:
        log.error(f"handle_override_queue failed: {exc}")


async def handle_scheduler_event(channel: str, data: dict) -> None:
    """
    Log scheduler job completion events.
    No DB write — scheduler events are observability-only.
    """
    job_id = data.get("job", "?")
    name   = data.get("name", "?")
    ts     = data.get("triggered_at", "?")
    extras = {k: v for k, v in data.items() if k not in ("job", "name", "triggered_at")}
    log.info(f"Scheduler [{job_id}] {name} at {ts}" + (f" extras={extras}" if extras else ""))

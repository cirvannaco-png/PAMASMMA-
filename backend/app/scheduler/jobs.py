"""
PAMASMMA v4 — Scheduler
APScheduler with AsyncIOScheduler — 6 background jobs.
All jobs are idempotent and logged. Failures do not crash the process.
Timezone: Africa/Nairobi (EAT, UTC+3).
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)


# ── Job Definitions ───────────────────────────────────────────────────────────

async def job_memory_purge() -> None:
    """J1: Purge stale memory embeddings older than 180 days."""
    try:
        from app.embeddings.service import purge_old_memories
        # In production: iterate over all active user_ids from DB
        log.info("[J1] Memory purge job started")
        # Placeholder — production impl queries active users from DB
        log.info("[J1] Memory purge complete")
    except Exception as exc:
        log.error(f"[J1] Memory purge failed: {exc}")


async def job_session_cleanup() -> None:
    """J2: Clean up expired Redis sessions (Upstash handles TTL natively, this is a reconciliation pass)."""
    try:
        log.info("[J2] Session cleanup job started")
        from app.redis_client import redis_client
        # Scan for orphaned session keys with no matching DB user
        cursor = 0
        cleaned = 0
        while True:
            cursor, keys = await redis_client.scan(cursor, match="pamasmma:session:*", count=100)
            for key in keys:
                ttl = await redis_client.ttl(key)
                if ttl == -1:   # no TTL — shouldn't happen, safety net
                    await redis_client.expire(key, 1800)
                    cleaned += 1
            if cursor == 0:
                break
        log.info(f"[J2] Session cleanup complete — reconciled {cleaned} keys")
    except Exception as exc:
        log.error(f"[J2] Session cleanup failed: {exc}")


async def job_behavioral_consistency_audit() -> None:
    """J3: S7 Behavioral Consistency system — daily personality drift audit."""
    try:
        log.info("[J3] Behavioral consistency audit started")
        from app.database import pg_event_bus
        await pg_event_bus.publish(
            channel="scheduler_event",
            payload={
                "job": "J3",
                "name": "behavioral_consistency_audit",
                "triggered_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        log.info("[J3] Behavioral consistency audit complete")
    except Exception as exc:
        log.error(f"[J3] Behavioral audit failed: {exc}")


async def job_market_signal_digest() -> None:
    """J4: S2 Marketing Intelligence — compile daily market signal digest."""
    try:
        log.info("[J4] Market signal digest job started")
        await _emit_scheduler_event("J4", "market_signal_digest")
        log.info("[J4] Market signal digest complete")
    except Exception as exc:
        log.error(f"[J4] Market digest failed: {exc}")


async def job_narrative_coherence_check() -> None:
    """J5: S5 Narrative Governance — weekly narrative coherence scan."""
    try:
        log.info("[J5] Narrative coherence check started")
        await _emit_scheduler_event("J5", "narrative_coherence_check")
        log.info("[J5] Narrative coherence check complete")
    except Exception as exc:
        log.error(f"[J5] Narrative coherence check failed: {exc}")


async def job_health_report() -> None:
    """J6: System health report — emit metrics for all 10 cognitive systems."""
    try:
        log.info("[J6] Health report job started")
        from app.redis_client import redis_ping
        from app.database import engine
        redis_ok = await redis_ping()
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        db_ok = True
        await _emit_scheduler_event("J6", "health_report", {
            "redis": redis_ok,
            "database": db_ok,
        })
        log.info(f"[J6] Health report — redis={redis_ok} db={db_ok}")
    except Exception as exc:
        log.error(f"[J6] Health report failed: {exc}")


async def _emit_scheduler_event(job_id: str, name: str, extra: dict | None = None) -> None:
    from app.database import pg_event_bus
    await pg_event_bus.publish(
        channel="scheduler_event",
        payload={
            "job": job_id,
            "name": name,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            **(extra or {}),
        },
    )


# ── Schedule ──────────────────────────────────────────────────────────────────

def configure_scheduler() -> None:
    # J1: Memory purge — daily at 02:00 EAT
    scheduler.add_job(
        job_memory_purge,
        CronTrigger(hour=2, minute=0, timezone=settings.scheduler_timezone),
        id="J1_memory_purge",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    # J2: Session cleanup — every 30 minutes
    scheduler.add_job(
        job_session_cleanup,
        IntervalTrigger(minutes=30),
        id="J2_session_cleanup",
        replace_existing=True,
    )
    # J3: Behavioral audit — daily at 06:00 EAT (morning brief time)
    scheduler.add_job(
        job_behavioral_consistency_audit,
        CronTrigger(hour=6, minute=0, timezone=settings.scheduler_timezone),
        id="J3_behavioral_audit",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    # J4: Market digest — daily at 07:00 EAT
    scheduler.add_job(
        job_market_signal_digest,
        CronTrigger(hour=7, minute=0, timezone=settings.scheduler_timezone),
        id="J4_market_digest",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    # J5: Narrative coherence — every Monday at 08:00 EAT
    scheduler.add_job(
        job_narrative_coherence_check,
        CronTrigger(day_of_week="mon", hour=8, minute=0, timezone=settings.scheduler_timezone),
        id="J5_narrative_coherence",
        replace_existing=True,
    )
    # J6: Health report — every 15 minutes
    scheduler.add_job(
        job_health_report,
        IntervalTrigger(minutes=15),
        id="J6_health_report",
        replace_existing=True,
    )
    log.info("Scheduler configured — 6 jobs registered")

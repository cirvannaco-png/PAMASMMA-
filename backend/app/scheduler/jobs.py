"""
PAMASMMA v4 — Scheduler
APScheduler with a single API instance. Future scale should extract these jobs
into a worker/cron service rather than running them on every web replica.
"""
import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()
scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
SESSION_KEY_PATTERN = "pamasmma:v2:session:*"


async def job_memory_purge() -> None:
    """J1: Memory retention hook; purge implementation remains policy-dependent."""
    try:
        log.info("[J1] Memory purge job started")
        log.info("[J1] Memory purge complete")
    except Exception as exc:
        log.error("[J1] Memory purge failed: %s", exc)


async def job_session_cleanup() -> None:
    """J2: Reconcile TTLs on the actual versioned session namespace."""
    try:
        from app.redis_client import redis_client
        if redis_client is None:
            raise RuntimeError("Redis client is unavailable in durable scheduler mode")
        cursor = 0
        cleaned = 0
        while True:
            cursor, keys = await redis_client.scan(
                cursor, match=SESSION_KEY_PATTERN, count=100
            )
            for key in keys:
                if await redis_client.ttl(key) == -1:
                    await redis_client.expire(key, 1800)
                    cleaned += 1
            if cursor == 0:
                break
        log.info("[J2] Session cleanup complete — reconciled %s keys", cleaned)
    except Exception as exc:
        log.error("[J2] Session cleanup failed: %s", exc)


async def job_behavioral_consistency_audit() -> None:
    try:
        from app.database import pg_event_bus
        await pg_event_bus.publish(
            "scheduler_event",
            {"job": "J3", "name": "behavioral_consistency_audit",
             "triggered_at": datetime.now(UTC).isoformat()},
        )
    except Exception as exc:
        log.error("[J3] Behavioral audit failed: %s", exc)


async def job_market_signal_digest() -> None:
    try:
        await _emit_scheduler_event("J4", "market_signal_digest")
    except Exception as exc:
        log.error("[J4] Market digest failed: %s", exc)


async def job_narrative_coherence_check() -> None:
    try:
        await _emit_scheduler_event("J5", "narrative_coherence_check")
    except Exception as exc:
        log.error("[J5] Narrative coherence check failed: %s", exc)


async def job_health_report() -> None:
    try:
        from app.database import engine
        from app.redis_client import redis_ping
        if engine is None:
            raise RuntimeError("Database engine is unavailable in durable scheduler mode")
        redis_ok = await redis_ping()
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        await _emit_scheduler_event(
            "J6", "health_report", {"redis": redis_ok, "database": True}
        )
    except Exception as exc:
        log.error("[J6] Health report failed: %s", exc)


async def _emit_scheduler_event(
    job_id: str, name: str, extra: dict | None = None
) -> None:
    from app.database import pg_event_bus
    await pg_event_bus.publish(
        channel="scheduler_event",
        payload={
            "job": job_id, "name": name,
            "triggered_at": datetime.now(UTC).isoformat(),
            **(extra or {}),
        },
    )


def configure_scheduler() -> None:
    scheduler.add_job(
        job_memory_purge, CronTrigger(hour=2, minute=0, timezone=settings.scheduler_timezone),
        id="J1_memory_purge", replace_existing=True, misfire_grace_time=3600,
    )
    scheduler.add_job(
        job_session_cleanup, IntervalTrigger(minutes=30),
        id="J2_session_cleanup", replace_existing=True,
    )
    scheduler.add_job(
        job_behavioral_consistency_audit,
        CronTrigger(hour=6, minute=0, timezone=settings.scheduler_timezone),
        id="J3_behavioral_audit", replace_existing=True, misfire_grace_time=3600,
    )
    scheduler.add_job(
        job_market_signal_digest,
        CronTrigger(hour=7, minute=0, timezone=settings.scheduler_timezone),
        id="J4_market_digest", replace_existing=True, misfire_grace_time=3600,
    )
    scheduler.add_job(
        job_narrative_coherence_check,
        CronTrigger(day_of_week="mon", hour=8, minute=0, timezone=settings.scheduler_timezone),
        id="J5_narrative_coherence", replace_existing=True,
    )
    scheduler.add_job(
        job_health_report, IntervalTrigger(minutes=15),
        id="J6_health_report", replace_existing=True,
    )

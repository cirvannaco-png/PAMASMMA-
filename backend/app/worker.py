"""PAMASMMA durable background worker.

The HTTP API and recurring jobs are deliberately separated so web replicas do
not duplicate scheduler execution. The worker also waits for the production
Alembic head before starting recurring jobs during a fresh deployment.
"""
import asyncio
import logging
import signal
from time import monotonic

from sqlalchemy import text

from app.config import get_settings
from app.database import close_db, engine, init_db, pg_event_bus
from app.redis_client import close_redis
from app.scheduler.jobs import configure_scheduler, scheduler

log = logging.getLogger(__name__)
settings = get_settings()
SCHEMA_HEAD = "009"
SCHEMA_WAIT_TIMEOUT_SECONDS = 180
SCHEMA_WAIT_INITIAL_DELAY_SECONDS = 2
SCHEMA_WAIT_MAX_DELAY_SECONDS = 10


async def wait_for_schema_head() -> None:
    """Wait for the database to reach the worker-compatible migration head."""
    if not settings.is_persistent:
        return
    if engine is None:
        raise RuntimeError("Database engine is unavailable in durable worker mode.")

    deadline = monotonic() + SCHEMA_WAIT_TIMEOUT_SECONDS
    delay = SCHEMA_WAIT_INITIAL_DELAY_SECONDS

    while monotonic() < deadline:
        try:
            async with engine.connect() as connection:
                result = await connection.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                )
                row = result.first()
            current = str(row[0]) if row else None
            if current == SCHEMA_HEAD:
                log.info("Worker schema check passed at Alembic head %s", SCHEMA_HEAD)
                return
            log.warning(
                "Worker waiting for Alembic head %s; current=%s",
                SCHEMA_HEAD,
                current or "uninitialized",
            )
        except Exception as exc:
            log.warning(
                "Worker waiting for database schema to become ready: %s",
                type(exc).__name__,
            )

        await asyncio.sleep(delay)
        delay = min(delay * 2, SCHEMA_WAIT_MAX_DELAY_SECONDS)

    raise RuntimeError(
        f"Database did not reach Alembic head {SCHEMA_HEAD} within "
        f"{SCHEMA_WAIT_TIMEOUT_SECONDS} seconds."
    )


async def run_worker() -> None:
    if not settings.scheduler_enabled:
        raise RuntimeError("SCHEDULER_ENABLED must be true for the PAMASMMA worker.")

    stop_event = asyncio.Event()

    def request_shutdown() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, lambda _signum, _frame: request_shutdown())
        except (ValueError, RuntimeError):
            # Signal registration is best-effort for embedded/test execution.
            pass

    await init_db()
    await wait_for_schema_head()
    await pg_event_bus.connect()
    configure_scheduler()
    scheduler.start()
    log.info("PAMASMMA worker started", extra={"version": settings.app_version})

    try:
        await stop_event.wait()
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await pg_event_bus.disconnect()
        await close_redis()
        await close_db()
        log.info("PAMASMMA worker stopped")


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

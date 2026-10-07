"""PAMASMMA background worker entrypoint.

Runs the durable scheduler outside the HTTP process so scheduled social delivery,
health reports, memory maintenance, and other recurring jobs are not coupled to
web-request replicas.
"""
import asyncio
import logging
import signal

from app.config import get_settings
from app.database import close_db, init_db, pg_event_bus
from app.redis_client import close_redis
from app.scheduler.jobs import configure_scheduler, scheduler

log = logging.getLogger(__name__)
settings = get_settings()


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

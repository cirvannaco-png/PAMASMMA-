"""
PAMASMMA v4 — Database
Async SQLAlchemy + Postgres LISTEN/NOTIFY event bus.
pgvector extension enabled on first connection.
"""
import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Callable

import asyncpg
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()


# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_pre_ping=True,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ── Base Model ────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency ────────────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Init ──────────────────────────────────────────────────────────────────────
async def init_db() -> None:
    """Enable pgvector and create tables on startup."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database initialized — pgvector enabled")


# ── Postgres LISTEN/NOTIFY Event Bus ─────────────────────────────────────────
class PGEventBus:
    """
    Lightweight event bus over Postgres LISTEN/NOTIFY.
    Replaces Kafka for PAMASMMA's inter-system event propagation.
    Single connection, asyncpg-native, zero external dependencies.
    """

    def __init__(self) -> None:
        self._conn: asyncpg.Connection | None = None
        self._handlers: dict[str, list[Callable]] = {}
        self._listen_task: asyncio.Task | None = None

    async def connect(self) -> None:
        dsn = settings.database_url.replace("+asyncpg", "")
        self._conn = await asyncpg.connect(dsn)
        log.info("PGEventBus connected")

    async def disconnect(self) -> None:
        if self._listen_task:
            self._listen_task.cancel()
        if self._conn:
            await self._conn.close()
        log.info("PGEventBus disconnected")

    def subscribe(self, channel: str, handler: Callable) -> None:
        self._handlers.setdefault(channel, []).append(handler)

    async def start_listening(self) -> None:
        if not self._conn:
            raise RuntimeError("PGEventBus not connected")
        for channel in self._handlers:
            await self._conn.add_listener(channel, self._dispatch)
            await self._conn.execute(f"LISTEN {channel}")
            log.info(f"PGEventBus listening on channel: {channel}")

    async def _dispatch(
        self,
        conn: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            data = {"raw": payload}
        handlers = self._handlers.get(channel, [])
        for handler in handlers:
            try:
                await handler(channel, data)
            except Exception as exc:
                log.error(f"PGEventBus handler error [{channel}]: {exc}")

    async def publish(self, channel: str, payload: dict) -> None:
        if not self._conn:
            raise RuntimeError("PGEventBus not connected")
        await self._conn.execute(
            f"SELECT pg_notify($1, $2)",
            channel,
            json.dumps(payload),
        )


# Singleton
pg_event_bus = PGEventBus()

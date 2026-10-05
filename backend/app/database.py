"""
PAMASMMA v4.1 — Database infrastructure.
Postgres is the durable production path. Memory mode is an explicit deployment
fallback used only when no durable database is available.
"""
import json
import logging
import re
from collections.abc import AsyncGenerator, Callable
from typing import Any

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings
from app.runtime import memory_store

log = logging.getLogger(__name__)
settings = get_settings()
_CHANNEL_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

engine = None
AsyncSessionLocal = None

if settings.is_persistent:
    assert settings.database_url is not None
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


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession | None, None]:
    if not settings.is_persistent:
        yield None
        return

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    if not settings.is_persistent:
        log.warning("PAMASMMA running with ephemeral memory persistence")
        return

    assert engine is not None
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    log.info("Database connectivity verified")


async def close_db() -> None:
    if engine is not None:
        await engine.dispose()
        log.info("Database engine disposed")


class PGEventBus:
    """Postgres LISTEN/NOTIFY bus with an in-process fallback for memory mode."""

    def __init__(self) -> None:
        self._conn: asyncpg.Connection | None = None
        self._handlers: dict[str, list[Callable]] = {}

    async def connect(self) -> None:
        if settings.is_persistent:
            assert settings.database_url is not None
            self._conn = await asyncpg.connect(
                settings.database_url.replace("+asyncpg", "")
            )
            log.info("PGEventBus connected")
        else:
            log.info("Memory EventBus connected")

    async def disconnect(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    def subscribe(self, channel: str, handler: Callable) -> None:
        self._validate_channel(channel)
        self._handlers.setdefault(channel, []).append(handler)

    async def start_listening(self) -> None:
        if not settings.is_persistent:
            return
        if not self._conn:
            raise RuntimeError("PGEventBus not connected")
        for channel in self._handlers:
            self._validate_channel(channel)
            await self._conn.add_listener(channel, self._dispatch)
            await self._conn.execute(f"LISTEN {channel}")

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
        for handler in self._handlers.get(channel, []):
            try:
                await handler(channel, data)
            except Exception:
                log.exception("PGEventBus handler error [%s]", channel)

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        self._validate_channel(channel)

        if not settings.is_persistent:
            data = dict(payload)
            # Preserve SSE fanout in memory mode without pretending events are durable.
            for handler in self._handlers.get(channel, []):
                try:
                    await handler(channel, data)
                except Exception:
                    log.exception("Memory EventBus handler error [%s]", channel)
            return

        if not self._conn:
            raise RuntimeError("PGEventBus not connected")
        await self._conn.execute(
            "SELECT pg_notify($1, $2)",
            channel,
            json.dumps(payload),
        )

    @staticmethod
    def _validate_channel(channel: str) -> None:
        if not _CHANNEL_RE.fullmatch(channel):
            raise ValueError(f"Invalid PostgreSQL notification channel: {channel!r}")


pg_event_bus = PGEventBus()

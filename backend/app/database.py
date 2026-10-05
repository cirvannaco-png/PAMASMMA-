"""
PAMASMMA v4.0.1 — Database infrastructure.

Alembic owns schema creation and migration. Application startup only verifies
database connectivity; it never mutates production schema.
"""
import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator
from typing import Callable

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

_CHANNEL_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Verify database connectivity; schema changes belong to Alembic."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    log.info("Database connectivity verified")


async def close_db() -> None:
    """Dispose the SQLAlchemy connection pool during application shutdown."""
    await engine.dispose()
    log.info("Database engine disposed")


class PGEventBus:
    """
    Lightweight event bus over Postgres LISTEN/NOTIFY.

    Channels are application constants. Channel validation additionally prevents
    accidental SQL identifier injection if this class is reused elsewhere.
    """

    def __init__(self) -> None:
        self._conn: asyncpg.Connection | None = None
        self._handlers: dict[str, list[Callable]] = {}

    async def connect(self) -> None:
        dsn = settings.database_url.replace("+asyncpg", "")
        self._conn = await asyncpg.connect(dsn)
        log.info("PGEventBus connected")

    async def disconnect(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None
        log.info("PGEventBus disconnected")

    def subscribe(self, channel: str, handler: Callable) -> None:
        self._validate_channel(channel)
        self._handlers.setdefault(channel, []).append(handler)

    async def start_listening(self) -> None:
        if not self._conn:
            raise RuntimeError("PGEventBus not connected")

        for channel in self._handlers:
            self._validate_channel(channel)
            await self._conn.add_listener(channel, self._dispatch)
            await self._conn.execute(f"LISTEN {channel}")
            log.info("PGEventBus listening on channel: %s", channel)

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

    async def publish(self, channel: str, payload: dict) -> None:
        if not self._conn:
            raise RuntimeError("PGEventBus not connected")
        self._validate_channel(channel)
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

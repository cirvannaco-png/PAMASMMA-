"""
PAMASMMA v4 — Cognitive Models
ORM models for: Memory store, Action log, Override queue.
pgvector column handled via raw SQL in migration; ORM uses Text for compatibility.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Memory(Base):
    """Semantic memory store backed by pgvector."""
    __tablename__ = "pamasmma_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.uuid_generate_v4())
    user_id: Mapped[str]    = mapped_column(String(255), nullable=False, index=True)
    system_id: Mapped[str]  = mapped_column(String(10),  nullable=False, index=True)
    content: Mapped[str]    = mapped_column(Text,         nullable=False)
    # embedding stored as vector(1536) in Postgres; accessed via raw SQL
    metadata_: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<Memory id={self.id} system={self.system_id}>"


class ActionLog(Base):
    """Append-only log of every cognitive system invocation."""
    __tablename__ = "pamasmma_action_log"

    id: Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.uuid_generate_v4())
    system_id: Mapped[str]      = mapped_column(String(10),   nullable=False, index=True)
    system_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_id: Mapped[str]        = mapped_column(String(255),  nullable=False, index=True)
    query_preview: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latency_ms: Mapped[float | None]  = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<ActionLog id={self.id} system={self.system_id} latency={self.latency_ms}ms>"


class OverrideQueue(Base):
    """Pending and applied behavioral override directives."""
    __tablename__ = "pamasmma_override_queue"

    id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.uuid_generate_v4())
    system_id: Mapped[str]     = mapped_column(String(10),  nullable=False, index=True)
    directive: Mapped[str]     = mapped_column(Text,         nullable=False)
    reason: Mapped[str | None] = mapped_column(Text,         nullable=True)
    user_id: Mapped[str]       = mapped_column(String(255),  nullable=False)
    status: Mapped[str]        = mapped_column(String(20),   default="pending", nullable=False)
    created_at: Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<OverrideQueue id={self.id} system={self.system_id} status={self.status}>"

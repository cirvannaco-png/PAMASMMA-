"""Durable JARVIS conversation and message models."""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class JarvisConversation(Base):
    __tablename__ = "pamasmma_jarvis_conversations"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_jarvis_conversation_status"),
        Index("ix_jarvis_conversations_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="New conversation")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    active_turn_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    active_turn_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JarvisMessage(Base):
    __tablename__ = "pamasmma_jarvis_messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence", name="uq_jarvis_message_sequence"),
        CheckConstraint("role IN ('user', 'assistant')", name="ck_jarvis_message_role"),
        CheckConstraint("modality IN ('text', 'voice')", name="ck_jarvis_message_modality"),
        Index("ix_jarvis_messages_owner_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=func.uuid_generate_v4(),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pamasmma_jarvis_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    modality: Mapped[str] = mapped_column(String(16), nullable=False, default="text")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class JarvisVoiceSession(Base):
    __tablename__ = "pamasmma_jarvis_voice_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'closed', 'failed', 'expired')", name="ck_jarvis_voice_session_status"),
        Index("ix_jarvis_voice_sessions_owner_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_session_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pamasmma_jarvis_conversations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, server_default="openai")
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JarvisVoiceDelegation(Base):
    __tablename__ = "pamasmma_jarvis_voice_delegations"
    __table_args__ = (
        UniqueConstraint("user_id", "conversation_id", "delegation_id", name="uq_jarvis_voice_delegation_owner_key"),
        CheckConstraint("status IN ('processing', 'completed', 'failed')", name="ck_jarvis_voice_delegation_status"),
        Index("ix_jarvis_voice_delegations_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pamasmma_jarvis_conversations.id", ondelete="CASCADE"), nullable=False
    )
    provider_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delegation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    transcript_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="processing")
    response_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class JarvisVoiceUsage(Base):
    __tablename__ = "pamasmma_jarvis_voice_usage"
    __table_args__ = (
        UniqueConstraint("voice_session_id", name="uq_jarvis_voice_usage_session"),
        CheckConstraint("status IN ('awaiting_provider', 'captured', 'unavailable')", name="ck_jarvis_voice_usage_status"),
        Index("ix_jarvis_voice_usage_owner_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    voice_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pamasmma_jarvis_voice_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="awaiting_provider")
    input_audio_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_audio_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_text_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_text_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

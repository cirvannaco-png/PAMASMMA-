"""Contracts for governed source ingestion and retrieval."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class KnowledgeTrainingMode(StrEnum):
    REFERENCE = "reference"
    BEHAVIORAL = "behavioral"
    DOMAIN_PLAYBOOK = "domain_playbook"


class KnowledgeSourceStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    AWAITING_TRANSCRIPTION = "awaiting_transcription"
    FAILED = "failed"


class KnowledgeItem(BaseModel):
    source_id: str
    title: str
    source_name: str
    ordinal: int
    content: str
    training_mode: KnowledgeTrainingMode = KnowledgeTrainingMode.REFERENCE
    similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    reliability: float = Field(default=0.75, ge=0.0, le=1.0)
    scope_system_id: str | None = None
    citation: str = ""


class KnowledgeSource(BaseModel):
    id: str
    title: str
    filename: str
    media_type: str
    training_mode: KnowledgeTrainingMode
    status: KnowledgeSourceStatus
    extraction_method: str
    size_bytes: int
    content_hash: str
    scope_system_id: str | None = None
    language: str | None = None
    chunk_count: int = 0
    error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KnowledgeUploadResponse(BaseModel):
    status: str
    source: KnowledgeSource

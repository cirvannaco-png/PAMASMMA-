"""Governed knowledge ingestion, storage and retrieval."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.embeddings.service import embed_text
from app.intelligence.contracts import MemoryItem, MemoryType
from app.knowledge.extractors import ExtractedSegment, extract_document
from app.runtime import memory_store

settings = get_settings()
log = logging.getLogger(__name__)


class DuplicateKnowledgeSource(ValueError):
    """Raised when the same active source is already ingested for a user."""


def _chunks(
    content: str,
    size: int,
    overlap: int,
    locator: str,
) -> list[tuple[str, str]]:
    words = re.findall(r"\S+", content)
    if not words:
        return []

    step = max(1, size - overlap)
    chunks: list[tuple[str, str]] = []
    for index, start in enumerate(range(0, len(words), step), 1):
        value = " ".join(words[start : start + size]).strip()
        if not value:
            continue
        chunks.append((value, f"{locator}#chunk:{index}"))
    return chunks


def _chunk_segments(
    segments: list[ExtractedSegment],
    size: int,
    overlap: int,
) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    for segment in segments:
        chunks.extend(_chunks(segment.content, size, overlap, segment.locator))
    return chunks


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _memory_type_for_mode(mode: str) -> MemoryType:
    return (
        MemoryType.PROCEDURAL
        if mode == "procedure"
        else MemoryType.SEMANTIC
    )


async def _find_duplicate(
    *,
    user_id: str,
    digest: str,
    mode: str,
) -> dict | None:
    if not settings.is_persistent:
        for item in reversed(memory_store.knowledge_sources):
            if (
                item["user_id"] == user_id
                and item.get("content_hash") == digest
                and item.get("training_mode") == mode
                and item.get("status") in {"processing", "ready"}
            ):
                return item
        return None

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT id,status,filename,chunk_count,content_hash,training_mode "
                "FROM pamasmma_knowledge_sources "
                "WHERE user_id=:user_id AND content_hash=:digest "
                "AND training_mode=:mode AND status IN ('processing','ready') "
                "ORDER BY updated_at DESC LIMIT 1"
            ),
            {"user_id": user_id, "digest": digest, "mode": mode},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None


async def ingest_file(
    *,
    user_id: str,
    filename: str,
    data: bytes,
    mode: str = "knowledge",
    content_type: str | None = None,
) -> dict:
    if mode not in {"knowledge", "procedure"}:
        raise ValueError("Unsupported knowledge training mode.")
    if len(data) > settings.knowledge_max_upload_bytes:
        raise ValueError(
            f"Upload exceeds the {settings.knowledge_max_upload_mb} MB knowledge limit."
        )

    safe_filename = Path(filename).name
    if not safe_filename or safe_filename in {".", ".."}:
        raise ValueError("A valid upload filename is required.")

    digest = _hash(data)
    duplicate = await _find_duplicate(
        user_id=user_id,
        digest=digest,
        mode=mode,
    )
    if duplicate:
        return {
            "source_id": str(duplicate["id"]),
            "status": str(duplicate["status"]),
            "filename": str(duplicate["filename"]),
            "chunks": int(duplicate.get("chunk_count") or 0),
            "mode": str(duplicate["training_mode"]),
            "content_hash": digest,
            "deduplicated": True,
        }

    source_id = str(uuid.uuid4())
    media_type = Path(safe_filename).suffix.lower().lstrip(".")
    source_metadata = {
        "content_type": content_type or "application/octet-stream",
        "hash_algorithm": "sha256",
        "filename": safe_filename,
    }

    if settings.is_persistent:
        assert AsyncSessionLocal is not None
        async with AsyncSessionLocal() as session:
            await session.execute(
                text(
                    """INSERT INTO pamasmma_knowledge_sources
                    (id,user_id,filename,media_type,status,content_hash,size_bytes,
                     training_mode,metadata,created_at,updated_at)
                    VALUES (:id,:user_id,:filename,:media_type,'processing',:hash,
                            :size,:mode,:metadata,NOW(),NOW())"""
                ),
                {
                    "id": source_id,
                    "user_id": user_id,
                    "filename": safe_filename,
                    "media_type": media_type,
                    "hash": digest,
                    "size": len(data),
                    "mode": mode,
                    "metadata": json.dumps(source_metadata),
                },
            )
            await session.commit()
    else:
        memory_store.knowledge_sources.append(
            {
                "id": source_id,
                "user_id": user_id,
                "filename": safe_filename,
                "media_type": media_type,
                "status": "processing",
                "content_hash": digest,
                "size_bytes": len(data),
                "chunk_count": 0,
                "training_mode": mode,
                "metadata": source_metadata,
                "error": None,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )

    try:
        with tempfile.TemporaryDirectory(prefix="pamasmma-knowledge-") as directory:
            path = Path(directory) / safe_filename
            path.write_bytes(data)
            segments = extract_document(path)

        chunks = _chunk_segments(
            segments,
            settings.knowledge_chunk_size,
            settings.knowledge_chunk_overlap,
        )
        if not chunks:
            raise ValueError("No readable text was extracted from the upload.")

        memory_type = _memory_type_for_mode(mode)

        if settings.is_persistent:
            assert AsyncSessionLocal is not None
            async with AsyncSessionLocal() as session:
                for ordinal, (chunk, locator) in enumerate(chunks):
                    metadata = {
                        "knowledge_source_id": source_id,
                        "source_filename": safe_filename,
                        "training_mode": mode,
                        "importance": 0.7,
                        "reliability": 0.75,
                        "memory_type": memory_type.value,
                    }
                    embedding = await embed_text(chunk)
                    await session.execute(
                        text(
                            """INSERT INTO pamasmma_knowledge_chunks
                            (id,source_id,user_id,ordinal,content,locator,embedding,
                             metadata,created_at)
                            VALUES (:id,:source_id,:user_id,:ordinal,:content,:locator,
                                    CAST(:embedding AS vector),:metadata,NOW())"""
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "source_id": source_id,
                            "user_id": user_id,
                            "ordinal": ordinal,
                            "content": chunk,
                            "locator": locator,
                            "embedding": str(embedding),
                            "metadata": json.dumps(metadata),
                        },
                    )
                await session.execute(
                    text(
                        "UPDATE pamasmma_knowledge_sources "
                        "SET status='ready',chunk_count=:count,updated_at=NOW() "
                        "WHERE id=:id AND user_id=:user_id"
                    ),
                    {
                        "count": len(chunks),
                        "id": source_id,
                        "user_id": user_id,
                    },
                )
                await session.commit()
        else:
            for ordinal, (chunk, locator) in enumerate(chunks):
                metadata = {
                    "knowledge_source_id": source_id,
                    "source_filename": safe_filename,
                    "training_mode": mode,
                    "importance": 0.7,
                    "reliability": 0.75,
                    "memory_type": memory_type.value,
                }
                embedding = await embed_text(chunk)
                memory_store.knowledge_chunks.append(
                    {
                        "id": str(uuid.uuid4()),
                        "source_id": source_id,
                        "user_id": user_id,
                        "ordinal": ordinal,
                        "content": chunk,
                        "embedding": embedding,
                        "metadata": metadata,
                        "created_at": datetime.now(UTC),
                        "locator": locator,
                    }
                )
            for item in memory_store.knowledge_sources:
                if item["id"] == source_id and item["user_id"] == user_id:
                    item["status"] = "ready"
                    item["chunk_count"] = len(chunks)
                    item["updated_at"] = datetime.now(UTC)
                    break

        return {
            "source_id": source_id,
            "status": "ready",
            "filename": safe_filename,
            "chunks": len(chunks),
            "mode": mode,
            "content_hash": digest,
            "deduplicated": False,
        }
    except Exception as exc:
        log.exception("Knowledge ingestion failed")
        if settings.is_persistent:
            assert AsyncSessionLocal is not None
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text(
                        "UPDATE pamasmma_knowledge_sources "
                        "SET status='failed',error=:error,updated_at=NOW() "
                        "WHERE id=:id AND user_id=:user_id"
                    ),
                    {
                        "error": str(exc)[:2000],
                        "id": source_id,
                        "user_id": user_id,
                    },
                )
                await session.commit()
        else:
            for item in memory_store.knowledge_sources:
                if item["id"] == source_id and item["user_id"] == user_id:
                    item["status"] = "failed"
                    item["error"] = str(exc)[:2000]
                    item["updated_at"] = datetime.now(UTC)
                    break
        raise


async def list_sources(user_id: str, limit: int = 100) -> list[dict]:
    if not settings.is_persistent:
        return [
            item
            for item in memory_store.knowledge_sources
            if item["user_id"] == user_id
        ][-limit:][::-1]

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT id,filename,media_type,status,content_hash,size_bytes,"
                "chunk_count,training_mode,metadata,error,created_at,updated_at "
                "FROM pamasmma_knowledge_sources "
                "WHERE user_id=:user_id ORDER BY created_at DESC LIMIT :limit"
            ),
            {"user_id": user_id, "limit": limit},
        )
        return [dict(row._mapping) for row in result.fetchall()]


async def list_source_chunks(
    user_id: str,
    source_id: str,
    limit: int = 100,
) -> list[dict]:
    if not settings.is_persistent:
        rows = [
            item
            for item in memory_store.knowledge_chunks
            if item["user_id"] == user_id and item["source_id"] == source_id
        ]
        return [
            {
                "ordinal": item["ordinal"],
                "locator": item["locator"],
                "content": item["content"],
                "metadata": item["metadata"],
            }
            for item in sorted(rows, key=lambda row: row["ordinal"])[:limit]
        ]

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT c.ordinal,c.locator,c.content,c.metadata "
                "FROM pamasmma_knowledge_chunks c "
                "JOIN pamasmma_knowledge_sources s ON s.id=c.source_id "
                "WHERE c.user_id=:user_id AND c.source_id=:source_id "
                "AND s.user_id=:user_id "
                "ORDER BY c.ordinal LIMIT :limit"
            ),
            {
                "user_id": user_id,
                "source_id": source_id,
                "limit": limit,
            },
        )
        return [dict(row._mapping) for row in result.fetchall()]


async def delete_source(user_id: str, source_id: str) -> bool:
    if not settings.is_persistent:
        source_before = [
            item
            for item in memory_store.knowledge_sources
            if item["user_id"] == user_id and item["id"] == source_id
        ]
        if not source_before:
            return False
        memory_store.knowledge_chunks[:] = [
            item
            for item in memory_store.knowledge_chunks
            if not (
                item["user_id"] == user_id
                and item["source_id"] == source_id
            )
        ]
        memory_store.knowledge_sources[:] = [
            item
            for item in memory_store.knowledge_sources
            if not (
                item["user_id"] == user_id
                and item["id"] == source_id
            )
        ]
        return True

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "DELETE FROM pamasmma_knowledge_sources "
                "WHERE id=:id AND user_id=:user_id"
            ),
            {"id": source_id, "user_id": user_id},
        )
        await session.commit()
        return bool(getattr(result, "rowcount", 0))


async def retrieve_knowledge_items(
    query: str,
    user_id: str,
    limit: int = 5,
) -> list[MemoryItem]:
    if not query.strip():
        return []

    query_embedding = await embed_text(query)
    rows = []
    if not settings.is_persistent:
        for item in memory_store.knowledge_chunks:
            if item["user_id"] != user_id:
                continue
            rows.append(
                (
                    item["content"],
                    item["created_at"],
                    _cosine(query_embedding, item["embedding"]),
                    item["metadata"],
                    item["locator"],
                    item["source_id"],
                    item["metadata"].get("source_filename", ""),
                )
            )
    else:
        assert AsyncSessionLocal is not None
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    """SELECT c.content,c.created_at,
                    1-(c.embedding <=> CAST(:vec AS vector)) AS similarity,
                    c.metadata,c.locator,c.source_id,s.filename
                    FROM pamasmma_knowledge_chunks c
                    JOIN pamasmma_knowledge_sources s ON s.id=c.source_id
                    WHERE c.user_id=:user_id AND s.status='ready'
                    ORDER BY c.embedding <=> CAST(:vec AS vector)
                    LIMIT :limit"""
                ),
                {
                    "vec": str(query_embedding),
                    "user_id": user_id,
                    "limit": max(limit * 5, 25),
                },
            )
            rows = [
                (
                    row.content,
                    row.created_at,
                    float(row.similarity or 0),
                    (
                        json.loads(row.metadata or "{}")
                        if isinstance(row.metadata, str)
                        else (row.metadata or {})
                    ),
                    row.locator,
                    str(row.source_id),
                    row.filename,
                )
                for row in result.fetchall()
            ]

    results = []
    for content, created, similarity, metadata, locator, source_id, filename in rows:
        if similarity < settings.knowledge_similarity_threshold:
            continue

        memory_type = MemoryType(
            metadata.get("memory_type", MemoryType.SEMANTIC.value)
        )
        results.append(
            MemoryItem(
                content=f"[{filename} · {locator}]\n{content}",
                memory_type=memory_type,
                similarity=similarity,
                recency=0.5,
                importance=float(metadata.get("importance", 0.7)),
                reliability=float(metadata.get("reliability", 0.75)),
                outcome_relevance=0.5,
                contextual_fit=0.0,
                score=similarity,
                created_at=created,
                metadata={
                    **metadata,
                    "knowledge_source_id": source_id,
                    "locator": locator,
                },
            )
        )

    results.sort(key=lambda item: item.score, reverse=True)
    return results[:limit]


def _cosine(a: list[float], b: list[float]) -> float:
    numerator = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return float(numerator / (norm_a * norm_b)) if norm_a and norm_b else 0.0

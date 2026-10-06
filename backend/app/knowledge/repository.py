"""Persistence boundary for governed knowledge sources and chunks."""
from __future__ import annotations

import json
import uuid

from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.knowledge.contracts import (
    KnowledgeItem,
    KnowledgeSource,
    KnowledgeSourceStatus,
    KnowledgeTrainingMode,
)
from app.runtime import memory_store

settings = get_settings()


def _source_from_row(row) -> KnowledgeSource:  # noqa: ANN001
    metadata = row.metadata if isinstance(row.metadata, dict) else json.loads(row.metadata or "{}")
    return KnowledgeSource(
        id=str(row.id), title=row.title, filename=row.filename,
        media_type=row.media_type,
        training_mode=KnowledgeTrainingMode(row.training_mode),
        status=KnowledgeSourceStatus(row.status),
        extraction_method=row.extraction_method, size_bytes=int(row.size_bytes),
        content_hash=row.content_hash,
        scope_system_id=metadata.get("scope_system_id"),
        language=metadata.get("language"), chunk_count=int(metadata.get("chunk_count", 0)),
        error=row.error, created_at=row.created_at, updated_at=row.updated_at,
    )


def _source_from_dict(item: dict) -> KnowledgeSource:
    return KnowledgeSource(**item)


async def find_source_by_hash(user_id: str, content_hash: str) -> KnowledgeSource | None:
    if not settings.is_persistent:
        for item in reversed(memory_store.knowledge_sources):
            if item["user_id"] == user_id and item["content_hash"] == content_hash:
                return _source_from_dict(item["source"])
        return None
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id, title, filename, media_type, training_mode, status,
                       extraction_method, size_bytes, content_hash, metadata,
                       error, created_at, updated_at
                FROM pamasmma_knowledge_sources
                WHERE user_id = :user_id AND content_hash = :content_hash
                LIMIT 1
            """),
            {"user_id": user_id, "content_hash": content_hash},
        )
        row = result.fetchone()
        return _source_from_row(row) if row else None


async def create_source(*, user_id: str, source: KnowledgeSource) -> None:
    if not settings.is_persistent:
        memory_store.knowledge_sources.append({
            "user_id": user_id,
            "content_hash": source.content_hash,
            "source": source.model_dump(mode="python"),
        })
        del memory_store.knowledge_sources[:-200]
        return
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO pamasmma_knowledge_sources
                    (id, user_id, title, filename, media_type, training_mode, status,
                     extraction_method, size_bytes, content_hash, metadata, error,
                     created_at, updated_at)
                VALUES
                    (:id, :user_id, :title, :filename, :media_type, :training_mode, :status,
                     :extraction_method, :size_bytes, :content_hash, CAST(:metadata AS jsonb), :error,
                     NOW(), NOW())
            """),
            {
                "id": uuid.UUID(source.id), "user_id": user_id,
                "title": source.title, "filename": source.filename,
                "media_type": source.media_type,
                "training_mode": source.training_mode.value,
                "status": source.status.value,
                "extraction_method": source.extraction_method,
                "size_bytes": source.size_bytes,
                "content_hash": source.content_hash,
                "metadata": json.dumps({
                    "scope_system_id": source.scope_system_id,
                    "language": source.language,
                    "chunk_count": source.chunk_count,
                }),
                "error": source.error,
            },
        )
        await session.commit()


async def update_source(source: KnowledgeSource, user_id: str) -> None:
    if not settings.is_persistent:
        for item in memory_store.knowledge_sources:
            if item["user_id"] == user_id and item["source"]["id"] == source.id:
                item["source"] = source.model_dump(mode="python")
                return
        return
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                UPDATE pamasmma_knowledge_sources
                SET title = :title, training_mode = :training_mode, status = :status,
                    extraction_method = :extraction_method, metadata = CAST(:metadata AS jsonb),
                    error = :error, updated_at = NOW()
                WHERE id = :id AND user_id = :user_id
            """),
            {
                "id": uuid.UUID(source.id), "user_id": user_id, "title": source.title,
                "training_mode": source.training_mode.value, "status": source.status.value,
                "extraction_method": source.extraction_method,
                "metadata": json.dumps({
                    "scope_system_id": source.scope_system_id,
                    "language": source.language,
                    "chunk_count": source.chunk_count,
                }),
                "error": source.error,
            },
        )
        await session.commit()


async def insert_chunks(user_id: str, chunks: list[KnowledgeItem], embeddings: list[list[float]]) -> None:
    if not settings.is_persistent:
        for item, embedding in zip(chunks, embeddings, strict=True):
            memory_store.knowledge_chunks.append({
                "user_id": user_id,
                "item": item.model_dump(mode="python"),
                "embedding": embedding,
            })
        del memory_store.knowledge_chunks[:-10000]
        return
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        for item, embedding in zip(chunks, embeddings, strict=True):
            await session.execute(
                text("""
                    INSERT INTO pamasmma_knowledge_chunks
                        (id, source_id, user_id, ordinal, content, embedding, metadata, created_at)
                    VALUES
                        (:id, :source_id, :user_id, :ordinal, :content,
                         CAST(:embedding AS vector), CAST(:metadata AS jsonb), NOW())
                """),
                {
                    "id": uuid.uuid4(), "source_id": uuid.UUID(item.source_id),
                    "user_id": user_id, "ordinal": item.ordinal, "content": item.content,
                    "embedding": str(embedding),
                    "metadata": json.dumps({
                        "title": item.title, "source_name": item.source_name,
                        "training_mode": item.training_mode.value,
                        "scope_system_id": item.scope_system_id,
                        "citation": item.citation,
                    }),
                },
            )
        await session.commit()


async def list_sources(user_id: str, limit: int = 100) -> list[KnowledgeSource]:
    if not settings.is_persistent:
        rows = [item["source"] for item in reversed(memory_store.knowledge_sources) if item["user_id"] == user_id][:limit]
        return [_source_from_dict(row) for row in rows]
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id, title, filename, media_type, training_mode, status,
                       extraction_method, size_bytes, content_hash, metadata,
                       error, created_at, updated_at
                FROM pamasmma_knowledge_sources
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"user_id": user_id, "limit": limit},
        )
        return [_source_from_row(row) for row in result.fetchall()]


async def delete_source(user_id: str, source_id: str) -> bool:
    if not settings.is_persistent:
        before = len(memory_store.knowledge_sources)
        memory_store.knowledge_sources[:] = [
            item for item in memory_store.knowledge_sources
            if not (item["user_id"] == user_id and item["source"]["id"] == source_id)
        ]
        memory_store.knowledge_chunks[:] = [
            item for item in memory_store.knowledge_chunks
            if item["item"]["source_id"] != source_id or item["user_id"] != user_id
        ]
        return len(memory_store.knowledge_sources) < before
    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                DELETE FROM pamasmma_knowledge_sources
                WHERE id = :id AND user_id = :user_id
                RETURNING id
            """),
            {"id": uuid.UUID(source_id), "user_id": user_id},
        )
        deleted = result.fetchone() is not None
        await session.commit()
        return deleted


async def search_knowledge(
    *, user_id: str, query: str, embedding: list[float], limit: int = 6,
    scope_system_id: str | None = None,
) -> list[KnowledgeItem]:
    def lexical_fit(query_text: str, content: str) -> float:
        query_words = {word for word in query_text.lower().split() if len(word) > 3}
        content_words = {word for word in content.lower().split() if len(word) > 3}
        if not query_words or not content_words:
            return 0.0
        return min(1.0, len(query_words & content_words) / max(1, min(len(query_words), 12)))

    if not settings.is_persistent:
        from app.embeddings.service import _cosine_similarity
        rows = []
        for record in memory_store.knowledge_chunks:
            if record["user_id"] != user_id:
                continue
            item = record["item"]
            if scope_system_id and item.get("scope_system_id") not in {None, scope_system_id}:
                continue
            similarity = _cosine_similarity(embedding, record["embedding"])
            score = (similarity * 0.70) + (lexical_fit(query, item["content"]) * 0.30)
            rows.append((item, similarity, score))
        rows.sort(key=lambda row: row[2], reverse=True)
        return [
            KnowledgeItem(
                **item,
                similarity=max(0.0, min(1.0, similarity)),
                score=max(0.0, min(1.0, score)),
            )
            for item, similarity, score in rows[:limit]
            if score >= settings.knowledge_similarity_threshold
        ]

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        scope_clause = (
            "AND (metadata->>'scope_system_id' IS NULL OR "
            "metadata->>'scope_system_id' = :scope_system_id)"
            if scope_system_id else ""
        )
        params: dict[str, object] = {
            "user_id": user_id, "embedding": str(embedding),
            "limit": limit * 5,
        }
        if scope_system_id:
            params["scope_system_id"] = scope_system_id
        result = await session.execute(
            text(f"""
                SELECT source_id, ordinal, content, metadata,
                       1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM pamasmma_knowledge_chunks
                WHERE user_id = :user_id
                  {scope_clause}
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """),
            params,
        )
        ranked: list[KnowledgeItem] = []
        for row in result.fetchall():
            metadata = row.metadata if isinstance(row.metadata, dict) else json.loads(row.metadata or "{}")
            similarity = max(0.0, min(1.0, float(row.similarity or 0.0)))
            mode = KnowledgeTrainingMode(
                metadata.get("training_mode", KnowledgeTrainingMode.REFERENCE.value)
            )
            mode_boost = {
                KnowledgeTrainingMode.REFERENCE: 0.0,
                KnowledgeTrainingMode.BEHAVIORAL: 0.03,
                KnowledgeTrainingMode.DOMAIN_PLAYBOOK: 0.02,
            }[mode]
            score = (similarity * 0.70) + (lexical_fit(query, row.content) * 0.30) + mode_boost
            if score < settings.knowledge_similarity_threshold:
                continue
            ranked.append(KnowledgeItem(
                source_id=str(row.source_id),
                title=metadata.get("title", "Untitled source"),
                source_name=metadata.get("source_name", "Unknown source"),
                ordinal=int(row.ordinal), content=row.content, training_mode=mode,
                similarity=similarity, score=max(0.0, min(1.0, score)),
                reliability=0.75, scope_system_id=metadata.get("scope_system_id"),
                citation=metadata.get("citation", f"Source · chunk {row.ordinal}"),
            ))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:limit]

"""
PAMASMMA v4.1 — Memory service.
Local embeddings are default and durable Postgres/pgvector is optional.
"""
import json
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.intelligence.memory import LocalEmbeddingProvider
from app.runtime import memory_store

log = logging.getLogger(__name__)
settings = get_settings()


async def embed_text(content: str) -> list[float]:
    if settings.embedding_provider.lower() == "local":
        return LocalEmbeddingProvider.embed(content)

    if settings.embedding_provider.lower() == "openai":
        from openai import AsyncOpenAI

        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        try:
            response = await client.embeddings.create(
                model=settings.embedding_model,
                input=content[:8000],
                dimensions=settings.embedding_dimensions,
            )
            return response.data[0].embedding
        finally:
            await client.close()

    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER: {settings.embedding_provider!r}"
    )


async def store_memory(
    user_id: str,
    system_id: str,
    content: str,
    metadata: dict | None = None,
) -> None:
    try:
        embedding = await embed_text(content)

        if not settings.is_persistent:
            memory_store.memories.append(
                {
                    "user_id": user_id,
                    "system_id": system_id,
                    "content": content[:4000],
                    "embedding": embedding,
                    "metadata": metadata or {},
                    "created_at": datetime.now(UTC),
                }
            )
            # Bound ephemeral growth to keep the free service memory-safe.
            del memory_store.memories[:-1000]
            return

        assert AsyncSessionLocal is not None
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO pamasmma_memories
                        (user_id, system_id, content, embedding, metadata, created_at)
                    VALUES
                        (:user_id, :system_id, :content, :embedding, :metadata, NOW())
                """),
                {
                    "user_id": user_id,
                    "system_id": system_id,
                    "content": content[:4000],
                    "embedding": str(embedding),
                    "metadata": json.dumps(metadata or {}),
                },
            )
            await session.commit()
    except Exception:
        log.exception("Memory store failed [%s]", system_id)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    numerator = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if not norm_a or not norm_b:
        return 0.0
    return float(numerator / (norm_a * norm_b))


async def retrieve_relevant_memories(
    query: str,
    user_id: str,
    system_id: str,
    limit: int = 5,
    max_age_days: int = 90,
) -> str:
    if not query.strip():
        return ""

    try:
        query_embedding = await embed_text(query)
        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)

        if not settings.is_persistent:
            candidates = [
                item for item in memory_store.memories
                if item["user_id"] == user_id
                and item["system_id"] == system_id
                and item["created_at"] > cutoff
            ]
            candidates.sort(
                key=lambda item: _cosine_similarity(
                    query_embedding,
                    item["embedding"],
                ),
                reverse=True,
            )
            selected = candidates[:limit]
            return "\n---\n".join(
                f"[{item['created_at']:%Y-%m-%d} | sim="
                f"{_cosine_similarity(query_embedding, item['embedding']):.2f}]\n"
                f"{item['content']}"
                for item in selected
            )

        assert AsyncSessionLocal is not None
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT content, created_at,
                           1 - (embedding <=> CAST(:query_vec AS vector)) AS similarity
                    FROM pamasmma_memories
                    WHERE user_id = :user_id
                      AND system_id = :system_id
                      AND created_at > :cutoff
                      AND 1 - (embedding <=> CAST(:query_vec AS vector)) > :threshold
                    ORDER BY embedding <=> CAST(:query_vec AS vector)
                    LIMIT :limit
                """),
                {
                    "query_vec": str(query_embedding),
                    "user_id": user_id,
                    "system_id": system_id,
                    "cutoff": cutoff,
                    "threshold": settings.vector_similarity_threshold,
                    "limit": limit,
                },
            )
            rows = result.fetchall()

        return "\n---\n".join(
            f"[{row.created_at:%Y-%m-%d} | sim={row.similarity:.2f}]\n{row.content}"
            for row in rows
        )
    except Exception:
        log.exception("Memory retrieval failed")
        return ""


async def purge_old_memories(
    user_id: str,
    max_age_days: int = 180,
) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)

    if not settings.is_persistent:
        before = len(memory_store.memories)
        memory_store.memories[:] = [
            item for item in memory_store.memories
            if not (item["user_id"] == user_id and item["created_at"] < cutoff)
        ]
        return before - len(memory_store.memories)

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                DELETE FROM pamasmma_memories
                WHERE user_id = :user_id AND created_at < :cutoff
            """),
            {"user_id": user_id, "cutoff": cutoff},
        )
        await session.commit()
        return int(getattr(result, "rowcount", 0) or 0)


async def purge_expired_memories(max_age_days: int = 180) -> int:
    """Delete all persisted memory records outside the retention window."""
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)

    if not settings.is_persistent:
        before = len(memory_store.memories)
        memory_store.memories[:] = [
            item for item in memory_store.memories if item["created_at"] >= cutoff
        ]
        return before - len(memory_store.memories)

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "DELETE FROM pamasmma_memories "
                "WHERE created_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
        await session.commit()
        return int(getattr(result, "rowcount", 0) or 0)

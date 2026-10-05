"""
PAMASMMA v4.1 — Memory / embeddings service.
Local hashing embeddings are the default, eliminating the OpenAI API-key
dependency. OpenAI remains an optional provider for stronger semantic search.
"""
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.intelligence.memory import LocalEmbeddingProvider

log = logging.getLogger(__name__)
settings = get_settings()


def _local_embedding(content: str) -> list[float]:
    return LocalEmbeddingProvider.embed(content)


async def embed_text(content: str) -> list[float]:
    provider = settings.embedding_provider.lower()
    if provider == "local":
        return _local_embedding(content)

    if provider == "openai":
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

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.embedding_provider!r}")


async def store_memory(
    user_id: str,
    system_id: str,
    content: str,
    metadata: dict | None = None,
) -> None:
    """Embed and persist one interaction. Memory failures never break inference."""
    try:
        embedding = await embed_text(content)
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


async def retrieve_relevant_memories(
    query: str,
    user_id: str,
    system_id: str,
    limit: int = 5,
    max_age_days: int = 90,
) -> str:
    """Retrieve fresh, semantically similar memories for prompt grounding."""
    if not query.strip():
        return ""

    try:
        query_embedding = await embed_text(query)
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

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
            memories = result.fetchall()

        return "\n---\n".join(
            f"[{row.created_at:%Y-%m-%d} | sim={row.similarity:.2f}]\n{row.content}"
            for row in memories
        )
    except Exception:
        log.exception("Memory retrieval failed")
        return ""


async def purge_old_memories(user_id: str, max_age_days: int = 180) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                DELETE FROM pamasmma_memories
                WHERE user_id = :user_id AND created_at < :cutoff
            """),
            {"user_id": user_id, "cutoff": cutoff},
        )
        await session.commit()
        return int(result.rowcount or 0)

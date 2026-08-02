"""
PAMASMMA v4 — Embeddings Service
pgvector-backed memory: store interactions, retrieve relevant context.
Uses text-embedding-3-small via OpenAI-compatible endpoint.
Freshness policy: memories older than 90 days are deprioritized in retrieval.
"""
import logging
from datetime import datetime, timezone, timedelta

from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal

log = logging.getLogger(__name__)
settings = get_settings()

# Re-use OpenAI client for embeddings (Anthropic doesn't yet provide embeddings)
_openai = AsyncOpenAI(api_key=settings.openai_api_key)


async def embed_text(content: str) -> list[float]:
    """Generate a vector embedding for arbitrary text."""
    response = await _openai.embeddings.create(
        model=settings.embedding_model,
        input=content[:8000],  # token safety cap
        dimensions=settings.embedding_dimensions,
    )
    return response.data[0].embedding


async def store_memory(
    user_id: str,
    system_id: str,
    content: str,
    metadata: dict | None = None,
) -> None:
    """
    Embed and store a memory in pgvector.
    Table: pamasmma_memories (created in migration 001).
    """
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
                    "metadata": str(metadata or {}),
                },
            )
            await session.commit()
    except Exception as exc:
        log.error(f"Memory store failed [{system_id}]: {exc}")


async def retrieve_relevant_memories(
    query: str,
    user_id: str,
    system_id: str,
    limit: int = 5,
    max_age_days: int = 90,
) -> str:
    """
    Retrieve the top-K most semantically relevant memories for a query.
    Applies a freshness decay: memories older than max_age_days are excluded.
    Returns formatted string for injection into system prompt.
    """
    if not query.strip():
        return ""
    try:
        query_embedding = await embed_text(query)
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                text("""
                    SELECT content, created_at,
                           1 - (embedding <=> :query_vec::vector) AS similarity
                    FROM pamasmma_memories
                    WHERE user_id = :user_id
                      AND system_id = :system_id
                      AND created_at > :cutoff
                      AND 1 - (embedding <=> :query_vec::vector) > :threshold
                    ORDER BY embedding <=> :query_vec::vector
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
            memories = rows.fetchall()

        if not memories:
            return ""

        formatted = "\n---\n".join(
            f"[{row.created_at.strftime('%Y-%m-%d')} | sim={row.similarity:.2f}]\n{row.content}"
            for row in memories
        )
        return formatted

    except Exception as exc:
        log.warning(f"Memory retrieval failed: {exc}")
        return ""


async def purge_old_memories(user_id: str, max_age_days: int = 180) -> int:
    """
    Scheduler job: remove memories older than max_age_days.
    Returns number of records deleted.
    """
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
        return result.rowcount

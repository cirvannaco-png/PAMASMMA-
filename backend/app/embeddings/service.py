"""
PAMASMMA v4.2 — Memory fabric storage and retrieval.
Local deterministic embeddings are a compatibility fallback; OpenAI embeddings
remain available for higher semantic fidelity.
"""
import json
import logging
import math
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.intelligence.contracts import MemoryItem, MemoryType
from app.intelligence.memory import LocalEmbeddingProvider
from app.runtime import memory_store

log = logging.getLogger(__name__)
settings = get_settings()


async def embed_text(content: str) -> list[float]:
    provider = settings.embedding_provider.lower()
    if provider in {"local", "hash"}:
        return LocalEmbeddingProvider.embed(content)

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


def _parse_metadata(value) -> dict:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _recency_score(
    created_at: datetime | None,
    half_life_days: float = 45.0,
) -> float:
    if not created_at:
        return 0.5
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    age_days = max(
        0.0,
        (datetime.now(UTC) - created_at).total_seconds() / 86400,
    )
    return math.exp(-age_days / half_life_days)


def _lexical_fit(query: str, content: str) -> float:
    q = {word for word in query.lower().split() if len(word) > 3}
    c = {word for word in content.lower().split() if len(word) > 3}
    if not q or not c:
        return 0.0
    return min(1.0, len(q & c) / max(1, min(len(q), 12)))


def _score_memory(
    similarity: float,
    created_at: datetime | None,
    metadata: dict,
    query: str,
    content: str,
) -> tuple[float, float]:
    recency = _recency_score(created_at)
    importance = float(metadata.get("importance", 0.5))
    reliability = float(metadata.get("reliability", 0.5))
    outcome_relevance = float(metadata.get("outcome_relevance", 0.5))
    contextual_fit = max(
        _lexical_fit(query, content),
        float(metadata.get("contextual_fit", 0.0)),
    )
    score = (
        similarity * 0.50
        + recency * 0.15
        + importance * 0.15
        + reliability * 0.10
        + outcome_relevance * 0.05
        + contextual_fit * 0.05
    )
    return max(0.0, min(1.0, score)), contextual_fit


async def store_memory(
    user_id: str,
    system_id: str,
    content: str,
    metadata: dict | None = None,
) -> None:
    try:
        embedding = await embed_text(content)
        metadata = metadata or {}

        if not settings.is_persistent:
            memory_store.memories.append(
                {
                    "user_id": user_id,
                    "system_id": system_id,
                    "content": content[:4000],
                    "embedding": embedding,
                    "metadata": metadata,
                    "created_at": datetime.now(UTC),
                }
            )
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
                    "metadata": json.dumps(metadata),
                },
            )
            await session.commit()
    except Exception:
        log.exception("Memory store failed [%s]", system_id)


async def retrieve_memory_items(
    query: str,
    user_id: str,
    system_id: str,
    limit: int = 5,
    max_age_days: int = 90,
) -> list[MemoryItem]:
    if not query.strip():
        return []

    try:
        query_embedding = await embed_text(query)
        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
        candidate_limit = max(limit * 5, 25)

        if not settings.is_persistent:
            candidates = [
                item
                for item in memory_store.memories
                if item["user_id"] == user_id
                and item["system_id"] == system_id
                and item["created_at"] > cutoff
            ]
            rows = [
                (
                    item["content"],
                    item["created_at"],
                    _cosine_similarity(
                        query_embedding,
                        item["embedding"],
                    ),
                    item.get("metadata", {}),
                )
                for item in candidates
            ]
        else:
            assert AsyncSessionLocal is not None
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("""
                        SELECT content, created_at,
                               1 - (embedding <=> CAST(:query_vec AS vector)) AS similarity,
                               metadata
                        FROM pamasmma_memories
                        WHERE user_id = :user_id
                          AND system_id = :system_id
                          AND created_at > :cutoff
                        ORDER BY embedding <=> CAST(:query_vec AS vector)
                        LIMIT :candidate_limit
                    """),
                    {
                        "query_vec": str(query_embedding),
                        "user_id": user_id,
                        "system_id": system_id,
                        "cutoff": cutoff,
                        "candidate_limit": candidate_limit,
                    },
                )
                fetched = result.fetchall()
            rows = [
                (
                    row.content,
                    row.created_at,
                    float(row.similarity or 0.0),
                    _parse_metadata(row.metadata),
                )
                for row in fetched
            ]

        scored: list[MemoryItem] = []
        for content, created_at, similarity, metadata in rows:
            score, contextual_fit = _score_memory(
                similarity,
                created_at,
                metadata,
                query,
                content,
            )
            if (
                similarity < settings.vector_similarity_threshold
                and score < settings.vector_similarity_threshold
            ):
                continue

            try:
                memory_kind = MemoryType(
                    metadata.get(
                        "memory_type",
                        MemoryType.SEMANTIC.value,
                    )
                )
            except ValueError:
                memory_kind = MemoryType.SEMANTIC

            scored.append(
                MemoryItem(
                    content=content,
                    memory_type=memory_kind,
                    similarity=round(similarity, 4),
                    recency=round(
                        _recency_score(created_at),
                        4,
                    ),
                    importance=float(metadata.get("importance", 0.5)),
                    reliability=float(metadata.get("reliability", 0.5)),
                    outcome_relevance=float(
                        metadata.get("outcome_relevance", 0.5)
                    ),
                    contextual_fit=round(contextual_fit, 4),
                    score=round(score, 4),
                    created_at=created_at,
                    metadata=metadata,
                )
            )

        scored.sort(
            key=lambda item: item.score,
            reverse=True,
        )
        return scored[:limit]
    except Exception:
        log.exception("Memory retrieval failed")
        return []


async def retrieve_relevant_memories(
    query: str,
    user_id: str,
    system_id: str,
    limit: int = 5,
    max_age_days: int = 90,
) -> str:
    items = await retrieve_memory_items(
        query,
        user_id,
        system_id,
        limit,
        max_age_days,
    )
    return "\n---\n".join(
        f"[{item.created_at:%Y-%m-%d} | score={item.score:.2f} | "
        f"type={item.memory_type.value} | reliability={item.reliability:.2f}]\n"
        f"{item.content}"
        for item in items
    )


def _cosine_similarity(
    a: list[float],
    b: list[float],
) -> float:
    numerator = sum(
        x * y for x, y in zip(a, b, strict=False)
    )
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if not norm_a or not norm_b:
        return 0.0
    return float(
        numerator / (norm_a * norm_b)
    )


async def purge_old_memories(
    user_id: str,
    max_age_days: int = 180,
) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)

    if not settings.is_persistent:
        before = len(memory_store.memories)
        memory_store.memories[:] = [
            item
            for item in memory_store.memories
            if not (
                item["user_id"] == user_id
                and item["created_at"] < cutoff
            )
        ]
        return before - len(memory_store.memories)

    assert AsyncSessionLocal is not None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                DELETE FROM pamasmma_memories
                WHERE user_id = :user_id
                  AND created_at < :cutoff
            """),
            {
                "user_id": user_id,
                "cutoff": cutoff,
            },
        )
        await session.commit()
        return int(
            getattr(result, "rowcount", 0) or 0
        )


async def purge_expired_memories(
    max_age_days: int = 180,
) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)

    if not settings.is_persistent:
        before = len(memory_store.memories)
        memory_store.memories[:] = [
            item
            for item in memory_store.memories
            if item["created_at"] >= cutoff
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
        return int(
            getattr(result, "rowcount", 0) or 0
        )

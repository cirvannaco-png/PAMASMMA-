"""
PAMASMMA — Action-log application service.
Keeps persistence details out of HTTP routers.
"""
from collections.abc import Iterable
from typing import Any

from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.runtime import memory_store

settings = get_settings()


def _serialize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    created_at = entry.get("created_at")
    return {
        "id": str(entry["id"]),
        "system_id": entry["system_id"],
        "system_name": entry.get("system_name"),
        "query_preview": entry.get("query_preview", ""),
        "latency_ms": entry.get("latency_ms"),
        "created_at": (
            created_at.isoformat()
            if hasattr(created_at, "isoformat")
            else str(created_at)
        ),
    }


def _filter_memory_entries(
    entries: Iterable[dict[str, Any]],
    user_id: str,
    system_id: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    selected = [
        entry
        for entry in reversed(list(entries))
        if entry.get("user_id") == user_id
        and (not system_id or entry.get("system_id") == system_id.upper())
    ][:limit]
    return [_serialize_entry(entry) for entry in selected]


async def list_action_log(
    user_id: str,
    limit: int = 50,
    system_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return recent action-log entries for one authenticated user."""
    if not settings.is_persistent:
        return _filter_memory_entries(
            memory_store.action_log,
            user_id,
            system_id,
            limit,
        )

    assert AsyncSessionLocal is not None
    system_filter = "AND system_id = :system_id" if system_id else ""
    params: dict[str, object] = {"user_id": user_id, "limit": limit}
    if system_id:
        params["system_id"] = system_id.upper()

    query = f"""
        SELECT id, system_id, system_name, query_preview, latency_ms, created_at
        FROM pamasmma_action_log
        WHERE user_id = :user_id
        {system_filter}
        ORDER BY created_at DESC
        LIMIT :limit
    """

    async with AsyncSessionLocal() as session:
        result = await session.execute(text(query), params)
        rows = result.fetchall()

    return [
        {
            "id": str(row.id),
            "system_id": row.system_id,
            "system_name": row.system_name,
            "query_preview": row.query_preview,
            "latency_ms": row.latency_ms,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]

"""
PAMASMMA v4.1 — Health and readiness endpoints.
Liveness is diagnostic; readiness fails closed for durable production.
"""
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.redis_client import redis_ping

router = APIRouter(prefix="/health", tags=["Health"])
settings = get_settings()


async def _dependency_status() -> dict:
    if not settings.is_persistent:
        return {
            "database": False,
            "redis": False,
            "persistence": "memory",
            "intelligence": settings.model_provider,
            "embeddings": settings.embedding_provider,
            "version": settings.app_version,
        }

    db_ok = False
    if engine is not None:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            pass

    redis_ok = await redis_ping()
    return {
        "database": db_ok,
        "redis": redis_ok,
        "persistence": "postgres",
        "intelligence": settings.model_provider,
        "embeddings": settings.embedding_provider,
        "version": settings.app_version,
    }


@router.get("")
async def health() -> dict:
    """Liveness endpoint."""
    data = await _dependency_status()
    data["status"] = (
        "healthy"
        if not settings.is_persistent or (data["database"] and data["redis"])
        else "degraded"
    )
    return data


@router.get("/ready")
async def readiness(response: Response) -> dict:
    """Render readiness endpoint; returns 503 when durable dependencies are unavailable."""
    data = await _dependency_status()
    ready = not settings.is_persistent or (data["database"] and data["redis"])
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        data["status"] = "not_ready"
        return data
    data["status"] = "ready"
    return data

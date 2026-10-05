"""
PAMASMMA v4.1 — Health endpoint.
The endpoint reports infrastructure capability separately from service liveness.
"""
from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.redis_client import redis_ping

router = APIRouter(prefix="/health", tags=["Health"])
settings = get_settings()


@router.get("")
async def health() -> dict:
    if not settings.is_persistent:
        return {
            "status": "healthy",
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
        "status": "healthy" if db_ok and redis_ok else "degraded",
        "database": db_ok,
        "redis": redis_ok,
        "persistence": "postgres",
        "intelligence": settings.model_provider,
        "embeddings": settings.embedding_provider,
        "version": settings.app_version,
    }

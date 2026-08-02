"""
PAMASMMA v4 — Health Router
"""
from fastapi import APIRouter
from app.redis_client import redis_ping
from app.database import engine
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health() -> dict:
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    redis_ok = await redis_ping()

    return {
        "status": "healthy" if (db_ok and redis_ok) else "degraded",
        "database": db_ok,
        "redis": redis_ok,
        "version": "4.0.0",
    }

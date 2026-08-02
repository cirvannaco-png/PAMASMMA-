"""
PAMASMMA v4 — Redis Client
Upstash Redis: session store, cache, rate limiting, WebAuthn challenge store.
All keys namespaced under `pamasmma:` to prevent collisions.
"""
import json
import logging
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

# ── Namespace prefixes ────────────────────────────────────────────────────────
NS_SESSION     = "pamasmma:session:"
NS_WEBAUTHN    = "pamasmma:webauthn:"
NS_RATE_LIMIT  = "pamasmma:ratelimit:"
NS_CACHE       = "pamasmma:cache:"
NS_TOTP        = "pamasmma:totp_used:"      # replay-attack prevention


def _make_client() -> Redis:
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30,
    )


redis_client: Redis = _make_client()


# ── Session Store ─────────────────────────────────────────────────────────────
async def set_session(session_id: str, data: dict, ttl: int | None = None) -> None:
    key = f"{NS_SESSION}{session_id}"
    ttl = ttl or settings.redis_session_ttl_seconds
    await redis_client.setex(key, ttl, json.dumps(data))


async def get_session(session_id: str) -> dict | None:
    key = f"{NS_SESSION}{session_id}"
    raw = await redis_client.get(key)
    return json.loads(raw) if raw else None


async def delete_session(session_id: str) -> None:
    await redis_client.delete(f"{NS_SESSION}{session_id}")


async def refresh_session(session_id: str) -> bool:
    key = f"{NS_SESSION}{session_id}"
    return bool(await redis_client.expire(key, settings.redis_session_ttl_seconds))


# ── WebAuthn Challenge Store ──────────────────────────────────────────────────
async def store_webauthn_challenge(user_id: str, challenge: str, ttl: int = 120) -> None:
    """Store a WebAuthn challenge with 2-minute TTL — single-use."""
    key = f"{NS_WEBAUTHN}challenge:{user_id}"
    await redis_client.setex(key, ttl, challenge)


async def pop_webauthn_challenge(user_id: str) -> str | None:
    """Atomically retrieve and delete the WebAuthn challenge (single-use)."""
    key = f"{NS_WEBAUTHN}challenge:{user_id}"
    pipe = redis_client.pipeline()
    pipe.get(key)
    pipe.delete(key)
    results = await pipe.execute()
    return results[0]


async def store_webauthn_credential(user_id: str, credential: dict) -> None:
    key = f"{NS_WEBAUTHN}credential:{user_id}"
    await redis_client.set(key, json.dumps(credential))


async def get_webauthn_credential(user_id: str) -> dict | None:
    key = f"{NS_WEBAUTHN}credential:{user_id}"
    raw = await redis_client.get(key)
    return json.loads(raw) if raw else None


# ── Rate Limiting (sliding window) ────────────────────────────────────────────
async def check_rate_limit(
    identifier: str,
    limit: int,
    window_seconds: int = 60,
) -> tuple[bool, int]:
    """
    Sliding window rate limit.
    Returns (allowed: bool, remaining: int).
    """
    key = f"{NS_RATE_LIMIT}{identifier}"
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    results = await pipe.execute()
    count = results[0]
    remaining = max(0, limit - count)
    return count <= limit, remaining


# ── TOTP Replay Prevention ────────────────────────────────────────────────────
async def mark_totp_used(user_id: str, code: str) -> bool:
    """
    Marks a TOTP code as used for replay-attack prevention.
    Returns True if the code was NOT previously used (fresh).
    TTL = 2× the TOTP interval to cover clock skew.
    """
    key = f"{NS_TOTP}{user_id}:{code}"
    result = await redis_client.set(key, "1", ex=settings.totp_interval * 2, nx=True)
    return result is True   # nx=True returns None if key exists


# ── Generic Cache ─────────────────────────────────────────────────────────────
async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    ttl = ttl or settings.redis_cache_ttl_seconds
    await redis_client.setex(f"{NS_CACHE}{key}", ttl, json.dumps(value))


async def cache_get(key: str) -> Any | None:
    raw = await redis_client.get(f"{NS_CACHE}{key}")
    return json.loads(raw) if raw else None


async def cache_invalidate(key: str) -> None:
    await redis_client.delete(f"{NS_CACHE}{key}")


# ── Health Check ──────────────────────────────────────────────────────────────
async def redis_ping() -> bool:
    try:
        return await redis_client.ping()
    except Exception as exc:
        log.error(f"Redis health check failed: {exc}")
        return False

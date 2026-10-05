"""
PAMASMMA v4.1 — Redis/session infrastructure.
Redis is the durable production path. Memory mode is a bounded single-instance
fallback for the zero-datastore intelligence deployment.
"""
import json
import logging
import time
from typing import Any, cast

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import get_settings
from app.runtime import memory_store

log = logging.getLogger(__name__)
settings = get_settings()

NS_SESSION = "pamasmma:v2:session:"
NS_WEBAUTHN = "pamasmma:v2:webauthn:"
NS_RATE_LIMIT = "pamasmma:ratelimit:"
NS_CACHE = "pamasmma:cache:"
NS_TOTP = "pamasmma:v2:totp_used:"

redis_client: Redis | None = None
if settings.is_persistent:
    assert settings.redis_url is not None
    redis_client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30,
    )


async def set_session(session_id: str, data: dict, ttl: int | None = None) -> None:
    ttl = ttl or settings.redis_session_ttl_seconds
    if not settings.is_persistent:
        memory_store.sessions[session_id] = dict(data)
        return
    assert redis_client is not None
    await redis_client.setex(f"{NS_SESSION}{session_id}", ttl, json.dumps(data))


async def get_session(session_id: str) -> dict | None:
    if not settings.is_persistent:
        return memory_store.sessions.get(session_id)
    assert redis_client is not None
    raw = await redis_client.get(f"{NS_SESSION}{session_id}")
    return cast(dict[str, Any] | None, json.loads(raw) if raw else None)


async def delete_session(session_id: str) -> None:
    if not settings.is_persistent:
        memory_store.sessions.pop(session_id, None)
        return
    assert redis_client is not None
    await redis_client.delete(f"{NS_SESSION}{session_id}")


async def refresh_session(session_id: str) -> bool:
    if not settings.is_persistent:
        return session_id in memory_store.sessions
    assert redis_client is not None
    return bool(
        await redis_client.expire(
            f"{NS_SESSION}{session_id}",
            settings.redis_session_ttl_seconds,
        )
    )


async def store_webauthn_challenge(user_id: str, challenge: str, ttl: int = 120) -> None:
    if not settings.is_persistent:
        memory_store.webauthn_challenges[user_id] = challenge
        return
    assert redis_client is not None
    await redis_client.setex(f"{NS_WEBAUTHN}challenge:{user_id}", ttl, challenge)


async def pop_webauthn_challenge(user_id: str) -> str | None:
    if not settings.is_persistent:
        return memory_store.webauthn_challenges.pop(user_id, None)
    assert redis_client is not None
    key = f"{NS_WEBAUTHN}challenge:{user_id}"
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.get(key)
        pipe.delete(key)
        results = await pipe.execute()
    return cast(str | None, results[0])


async def store_webauthn_credential(user_id: str, credential: dict) -> None:
    if not settings.is_persistent:
        memory_store.webauthn_credentials[user_id] = dict(credential)
        return
    assert redis_client is not None
    await redis_client.set(
        f"{NS_WEBAUTHN}credential:{user_id}",
        json.dumps(credential),
    )


async def get_webauthn_credential(user_id: str) -> dict | None:
    if not settings.is_persistent:
        credential = memory_store.webauthn_credentials.get(user_id)
        return dict(credential) if credential else None
    assert redis_client is not None
    raw = await redis_client.get(f"{NS_WEBAUTHN}credential:{user_id}")
    return cast(dict[str, Any] | None, json.loads(raw) if raw else None)


async def check_rate_limit(
    identifier: str,
    limit: int,
    window_seconds: int = 60,
) -> tuple[bool, int]:
    if not settings.is_persistent:
        now = time.monotonic()
        count, reset_at = memory_store.rate_limits[identifier]
        if now >= reset_at:
            count, reset_at = 0, now + window_seconds
        count += 1
        memory_store.rate_limits[identifier] = (count, reset_at)
        return count <= limit, max(0, limit - count)

    assert redis_client is not None
    key = f"{NS_RATE_LIMIT}{identifier}"
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()
    count = int(results[0])
    return count <= limit, max(0, limit - count)


async def mark_totp_used(user_id: str, code: str) -> bool:
    key = f"{user_id}:{code}"
    if not settings.is_persistent:
        if key in memory_store.totp_used:
            return False
        memory_store.totp_used.add(key)
        return True

    assert redis_client is not None
    result = await redis_client.set(
        f"{NS_TOTP}{key}",
        "1",
        ex=settings.totp_interval * 2,
        nx=True,
    )
    return result is True


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    ttl = ttl or settings.redis_cache_ttl_seconds
    if not settings.is_persistent:
        memory_store.sessions[f"cache:{key}"] = {"value": value, "expires_at": time.monotonic() + ttl}
        return
    assert redis_client is not None
    await redis_client.setex(f"{NS_CACHE}{key}", ttl, json.dumps(value))


async def cache_get(key: str) -> Any | None:
    if not settings.is_persistent:
        item = memory_store.sessions.get(f"cache:{key}")
        if not item or item["expires_at"] < time.monotonic():
            memory_store.sessions.pop(f"cache:{key}", None)
            return None
        return item["value"]
    assert redis_client is not None
    raw = await redis_client.get(f"{NS_CACHE}{key}")
    return json.loads(raw) if raw else None


async def cache_invalidate(key: str) -> None:
    if not settings.is_persistent:
        memory_store.sessions.pop(f"cache:{key}", None)
        return
    assert redis_client is not None
    await redis_client.delete(f"{NS_CACHE}{key}")


async def redis_ping() -> bool:
    if not settings.is_persistent:
        return True
    assert redis_client is not None
    try:
        return bool(await redis_client.ping())
    except Exception as exc:
        log.error("Redis health check failed: %s", exc)
        return False


async def close_redis() -> None:
    if redis_client is not None:
        await redis_client.close()

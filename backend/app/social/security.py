"""OAuth state and encrypted token primitives."""
import hashlib, json, secrets
from app.redis_client import cache_set, cache_get, cache_invalidate
from app.security.crypto import encrypt_secret, decrypt_secret

async def create_oauth_state(user_id: str, platform: str, redirect_uri: str) -> str:
    state=secrets.token_urlsafe(32)
    await cache_set(f"social:oauth:{state}", {"user_id":user_id,"platform":platform,"redirect_uri":redirect_uri}, ttl=600)
    return state
async def consume_oauth_state(state: str) -> dict | None:
    data=await cache_get(f"social:oauth:{state}")
    await cache_invalidate(f"social:oauth:{state}")
    return data

def protect_token(value: str) -> str: return encrypt_secret(value)
def reveal_token(value: str) -> str: return decrypt_secret(value)
def request_hash(payload: dict) -> str: return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()

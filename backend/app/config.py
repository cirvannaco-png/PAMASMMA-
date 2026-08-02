"""
PAMASMMA v4 — Configuration
Validated settings loaded from environment. Fail-fast on missing secrets.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "PAMASMMA"
    app_version: str = "4.0.0"
    app_env: str = "production"
    debug: bool = False

    # ── Security ─────────────────────────────────────────────────────────────
    secret_key: str                          # 64-char hex, non-negotiable
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    allowed_origins: List[str] = ["http://localhost:3000"]

    # ── Database (Supabase / Postgres) ────────────────────────────────────────
    database_url: str                        # postgresql+asyncpg://...
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30

    # ── Redis (Upstash) ───────────────────────────────────────────────────────
    redis_url: str                           # rediss://...@upstash.io:6380
    redis_session_ttl_seconds: int = 1800   # 30 min
    redis_cache_ttl_seconds: int = 300

    # ── Anthropic ─────────────────────────────────────────────────────────────
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_max_tokens: int = 2048
    anthropic_timeout_seconds: int = 60

    # ── OpenAI (embeddings) ───────────────────────────────────────────────────
    openai_api_key: str                      # for text-embedding-3-small

    # ── WebAuthn / FIDO2 ─────────────────────────────────────────────────────
    webauthn_rp_id: str = "pamasmma.app"
    webauthn_rp_name: str = "PAMASMMA"
    webauthn_origin: str = "https://pamasmma.app"

    # ── TOTP ─────────────────────────────────────────────────────────────────
    totp_issuer: str = "PAMASMMA"
    totp_digits: int = 6
    totp_interval: int = 30

    # ── pgvector ─────────────────────────────────────────────────────────────
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    vector_similarity_threshold: float = 0.78

    # ── Scheduler ────────────────────────────────────────────────────────────
    scheduler_timezone: str = "Africa/Nairobi"

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_auth_per_minute: int = 5
    rate_limit_api_per_minute: int = 60
    rate_limit_cognitive_per_minute: int = 20

    # ── Personality Baseline (immutable core) ────────────────────────────────
    personality_assertiveness: float = 0.84
    personality_verbosity: float = 0.72
    personality_formality: float = 0.61
    personality_strategic_depth: float = 0.91

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()

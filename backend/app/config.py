"""
PAMASMMA v4.1 — Configuration
Provider-neutral intelligence with explicit durable/ephemeral persistence modes.
"""
from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        protected_namespaces=("settings_",),
    )

    app_name: str = "PAMASMMA"
    app_version: str = "4.1.0"
    app_env: str = "production"
    debug: bool = False

    secret_key: str = Field(default="", min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    allowed_origins: list[str] = ["http://localhost:3000"]
    bootstrap_token: SecretStr = SecretStr("")

    founder_user_id: str = "kelson-mwangi-cirvanna"
    founder_username: str = "kelson@cirvanna.co"

    # Persistence
    # postgres = durable Postgres + Redis
    # memory = explicit ephemeral single-instance mode for demos/CI
    persistence_mode: str = "postgres"
    database_url: str | None = None
    database_pool_size: int = 5
    database_max_overflow: int = 5
    database_pool_timeout: int = 30
    redis_url: str | None = None
    redis_session_ttl_seconds: int = 1800
    redis_cache_ttl_seconds: int = 300

    # Intelligence provider
    model_provider: str = "kernel"
    model_name: str = "llama3.2:3b"
    model_max_tokens: int = 2048
    model_api_base_url: str | None = None
    model_api_key: SecretStr | None = None
    model_timeout_seconds: int = 60

    # Optional cloud model adapter
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_max_tokens: int = 2048
    anthropic_timeout_seconds: int = 60

    # Embeddings
    embedding_provider: str = "local"
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    vector_similarity_threshold: float = 0.78

    webauthn_rp_id: str = "pamasmma.app"
    webauthn_rp_name: str = "PAMASMMA"
    webauthn_origin: str = "https://pamasmma.app"

    totp_issuer: str = "PAMASMMA"
    totp_digits: int = 6
    totp_interval: int = 30

    scheduler_timezone: str = "Africa/Nairobi"
    scheduler_enabled: bool = True

    rate_limit_auth_per_minute: int = 5
    rate_limit_api_per_minute: int = 60
    rate_limit_cognitive_per_minute: int = 20

    personality_assertiveness: float = 0.84
    personality_verbosity: float = 0.72
    personality_formality: float = 0.61
    personality_strategic_depth: float = 0.91

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_persistent(self) -> bool:
        return self.persistence_mode.lower() == "postgres"

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if self.persistence_mode not in {"postgres", "memory"}:
            raise ValueError("PERSISTENCE_MODE must be 'postgres' or 'memory'.")

        if self.is_production and not self.bootstrap_token.get_secret_value().strip():
            raise ValueError(
                "PAMASMMA_BOOTSTRAP_TOKEN must be configured in production."
            )

        if self.is_persistent and (not self.database_url or not self.redis_url):
            raise ValueError(
                "DATABASE_URL and REDIS_URL are required when PERSISTENCE_MODE=postgres."
            )

        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai."
            )

        if self.model_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required when MODEL_PROVIDER=anthropic."
            )

        if self.model_provider == "openai-compatible" and not self.model_api_base_url:
            raise ValueError(
                "MODEL_API_BASE_URL is required for openai-compatible provider."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

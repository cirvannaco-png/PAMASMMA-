"""PAMASMMA v4.2 — Configuration
Provider-neutral intelligence with explicit durable/ephemeral persistence modes.
"""
from functools import lru_cache
from secrets import token_urlsafe

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
    app_version: str = "4.2.1"
    app_env: str = "production"
    debug: bool = False

    secret_key: str | None = Field(default=None, min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    allowed_origins: list[str] = ["http://localhost:3000"]
    bootstrap_token: SecretStr = SecretStr("")

    founder_user_id: str = "kelson-mwangi-cirvanna"
    founder_username: str = "kelson@cirvanna.co"

    persistence_mode: str = "postgres"
    database_url: str | None = None
    database_pool_size: int = 5
    database_max_overflow: int = 5
    database_pool_timeout: int = 30
    redis_url: str | None = None
    redis_session_ttl_seconds: int = 1800
    redis_cache_ttl_seconds: int = 300

    model_provider: str = "kernel"
    model_name: str = "llama3.2:3b"
    model_max_tokens: int = 2048
    model_api_base_url: str | None = None
    model_api_key: SecretStr | None = None
    model_timeout_seconds: int = 60

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_max_tokens: int = 2048
    anthropic_timeout_seconds: int = 60

    embedding_provider: str = "local"
    openai_api_key: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    vector_similarity_threshold: float = 0.78

    knowledge_max_upload_mb: int = 100
    knowledge_max_archive_extract_mb: int = 250
    knowledge_max_archive_files: int = 2000
    knowledge_max_chunks_per_source: int = 10000
    knowledge_memory_source_limit: int = 25
    knowledge_memory_chunk_limit: int = 1000
    knowledge_chunk_size: int = 420
    knowledge_chunk_overlap: int = 60
    knowledge_similarity_threshold: float = 0.68
    knowledge_transcription_provider: str = "openai"
    knowledge_transcription_model: str = "gpt-4o-mini-transcribe"
    knowledge_media_timeout_seconds: int = 900

    @property
    def knowledge_max_upload_bytes(self) -> int:
        return self.knowledge_max_upload_mb * 1024 * 1024

    @property
    def knowledge_max_archive_extract_bytes(self) -> int:
        return self.knowledge_max_archive_extract_mb * 1024 * 1024

    intelligence_memory_limit: int = 5
    intelligence_max_specialists: int = 4
    intelligence_revision_enabled: bool = True
    intelligence_cloud_for_sensitive: bool = False

    webauthn_rp_id: str = "pamasmma.app"
    webauthn_rp_name: str = "PAMASMMA"
    webauthn_origin: str = "https://pamasmma.app"

    totp_issuer: str = "PAMASMMA"
    totp_digits: int = 6
    totp_interval: int = 30

    scheduler_timezone: str = "Africa/Nairobi"
    scheduler_enabled: bool = False

    rate_limit_auth_per_minute: int = 5
    rate_limit_api_per_minute: int = 60
    rate_limit_cognitive_per_minute: int = 20

    personality_assertiveness: float = 0.84
    personality_verbosity: float = 0.72
    personality_formality: float = 0.61
    personality_strategic_depth: float = 0.91

    # Google Workspace OAuth. Secrets are injected at deployment time.\n    google_client_id: str | None = None\n    google_client_secret: str | None = None\n    google_redirect_uri: str | None = None\n    mcp_allowed_hosts: list[str] = []\n\n    # Social Growth / Platform OAuth. Secrets are injected at deployment time.
    social_meta_client_id: str | None = None
    social_meta_client_secret: str | None = None
    social_meta_redirect_uri: str | None = None
    social_meta_graph_version: str = "v23.0"
    social_meta_scopes: str = "pages_show_list,pages_manage_posts,pages_read_engagement,instagram_basic,instagram_content_publish,instagram_manage_comments"
    social_tiktok_client_key: str | None = None
    social_tiktok_client_secret: str | None = None
    social_tiktok_redirect_uri: str | None = None
    social_tiktok_scopes: str = "user.info.basic,video.publish"
    social_youtube_client_id: str | None = None
    social_youtube_client_secret: str | None = None
    social_youtube_redirect_uri: str | None = None
    social_youtube_scopes: str = "https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl https://www.googleapis.com/auth/yt-analytics.readonly"
    social_linkedin_client_id: str | None = None
    social_linkedin_client_secret: str | None = None
    social_linkedin_redirect_uri: str | None = None
    social_linkedin_scopes: str = "openid profile w_member_social rw_ads"
    social_linkedin_version: str = "202609"
    social_x_client_id: str | None = None
    social_x_client_secret: str | None = None
    social_x_redirect_uri: str | None = None
    social_x_scopes: str = "tweet.read tweet.write users.read offline.access"
    social_threads_client_id: str | None = None
    social_threads_client_secret: str | None = None
    social_threads_redirect_uri: str | None = None
    social_threads_scopes: str = "threads_basic,threads_content_publish,threads_manage_replies"
    social_pinterest_app_id: str | None = None
    social_pinterest_app_secret: str | None = None
    social_pinterest_redirect_uri: str | None = None
    social_pinterest_scopes: str = "user_accounts:read,boards:read,boards:write,pins:read,pins:write,ads:read,ads:write"
    social_reddit_client_id: str | None = None
    social_reddit_client_secret: str | None = None
    social_reddit_redirect_uri: str | None = None
    social_reddit_scopes: str = "identity,submit,read,comment"
    social_telegram_bot_token: str | None = None
    social_whatsapp_access_token: str | None = None
    social_autopilot_enabled: bool = False
    social_ads_autonomous_enabled: bool = False
    social_sync_batch_size: int = 100
    social_delivery_max_attempts: int = 5
    social_delivery_retry_base_seconds: int = 30
    social_delivery_lease_seconds: int = 300

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
        if not self.secret_key:
            if self.is_production:
                raise ValueError("SECRET_KEY must be configured in production.")
            self.secret_key = token_urlsafe(48)
        if self.is_production and not self.bootstrap_token.get_secret_value().strip():
            raise ValueError("PAMASMMA_BOOTSTRAP_TOKEN must be configured in production.")
        if self.is_persistent and (not self.database_url or not self.redis_url):
            raise ValueError("DATABASE_URL and REDIS_URL are required when PERSISTENCE_MODE=postgres.")
        if self.social_delivery_max_attempts < 1:
            raise ValueError("SOCIAL_DELIVERY_MAX_ATTEMPTS must be at least 1.")
        if self.social_delivery_retry_base_seconds < 1:
            raise ValueError("SOCIAL_DELIVERY_RETRY_BASE_SECONDS must be at least 1.")
        if self.social_delivery_lease_seconds < 30:
            raise ValueError("SOCIAL_DELIVERY_LEASE_SECONDS must be at least 30.")
        if self.knowledge_max_upload_mb < 1:
            raise ValueError("KNOWLEDGE_MAX_UPLOAD_MB must be at least 1.")
        if (
            self.knowledge_chunk_overlap < 0
            or self.knowledge_chunk_overlap >= self.knowledge_chunk_size
        ):
            raise ValueError("Knowledge chunk overlap must be non-negative and smaller than chunk size.")
        if self.knowledge_max_archive_extract_mb < 1:
            raise ValueError("KNOWLEDGE_MAX_ARCHIVE_EXTRACT_MB must be at least 1.")
        if self.knowledge_max_archive_files < 1:
            raise ValueError("KNOWLEDGE_MAX_ARCHIVE_FILES must be at least 1.")
        if self.knowledge_max_chunks_per_source < 1:
            raise ValueError("KNOWLEDGE_MAX_CHUNKS_PER_SOURCE must be at least 1.")
        if self.knowledge_memory_source_limit < 1:
            raise ValueError("KNOWLEDGE_MEMORY_SOURCE_LIMIT must be at least 1.")
        if self.knowledge_memory_chunk_limit < 1:
            raise ValueError("KNOWLEDGE_MEMORY_CHUNK_LIMIT must be at least 1.")
        if self.embedding_provider == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai.")
        if self.model_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when MODEL_PROVIDER=anthropic.")
        if self.model_provider == "openai-compatible" and not self.model_api_base_url:
            raise ValueError("MODEL_API_BASE_URL is required for openai-compatible provider.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

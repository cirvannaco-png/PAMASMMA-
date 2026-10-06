"""Provider-neutral contracts for social publishing, engagement, analytics and ads."""
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class Platform(StrEnum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    X = "x"
    THREADS = "threads"
    PINTEREST = "pinterest"
    REDDIT = "reddit"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"

class Capability(StrEnum):
    PUBLISH = "publish"
    COMMENTS_READ = "comments_read"
    COMMENTS_WRITE = "comments_write"
    MENTIONS_READ = "mentions_read"
    ANALYTICS = "analytics"
    ADS_READ = "ads_read"
    ADS_WRITE = "ads_write"

class SocialAction(StrEnum):
    PUBLISH = "publish"
    REPLY = "reply"
    SYNC_ENGAGEMENT = "sync_engagement"
    SYNC_ANALYTICS = "sync_analytics"
    PLAN_CAMPAIGN = "plan_campaign"
    EXECUTE_CAMPAIGN = "execute_campaign"

class PublishCommand(BaseModel):
    account_id: str
    text: str = Field(default="", max_length=10000)
    media_url: HttpUrl | None = None
    media_type: str | None = Field(default=None, max_length=50)
    title: str | None = Field(default=None, max_length=500)
    link_url: HttpUrl | None = None
    reply_to_id: str | None = Field(default=None, max_length=255)
    platform_options: dict[str, Any] = Field(default_factory=dict)

class ReplyCommand(BaseModel):
    account_id: str
    item_id: str
    external_account_id: str | None = None
    text: str = Field(..., min_length=1, max_length=5000)

class CampaignPlan(BaseModel):
    account_id: str
    ad_account_id: str | None = Field(default=None, max_length=255)
    name: str = Field(..., min_length=2, max_length=255)
    objective: str = Field(..., min_length=2, max_length=100)
    daily_budget: float | None = Field(default=None, ge=0)
    lifetime_budget: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    targeting: dict[str, Any] = Field(default_factory=dict)
    creative: dict[str, Any] = Field(default_factory=dict)
    start_at: str | None = None
    end_at: str | None = None
    provider_options: dict[str, Any] = Field(default_factory=dict)

class AccountView(BaseModel):
    id: str
    platform: Platform
    external_account_id: str
    display_name: str | None
    status: str
    scopes: list[str]
    capabilities: list[Capability]

class EngagementView(BaseModel):
    id: str
    platform: Platform
    item_id: str
    kind: str
    author_name: str | None
    text: str | None
    intent: str | None
    sentiment: str | None
    priority: str
    responded_at: str | None
    created_at: str

class AnalyticsView(BaseModel):
    platform: Platform
    account_id: str
    period_start: str | None
    period_end: str | None
    metrics: dict[str, float | int]

class SocialProviderError(RuntimeError):
    def __init__(self, platform: Platform, code: str, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.platform = platform
        self.code = code
        self.status_code = status_code

class UnsupportedCapability(SocialProviderError):
    def __init__(self, platform: Platform, capability: Capability) -> None:
        super().__init__(platform, "capability_not_supported", f"{platform.value} does not support {capability.value} in this adapter.", 422)

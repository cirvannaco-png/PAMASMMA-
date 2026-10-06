"""HTTP boundary for PAMASMMA social growth operations."""
import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.redis_client import cache_pop, cache_set
from app.social.contracts import (
    CampaignPlan,
    Platform,
    PublishCommand,
    ReplyCommand,
    SocialProviderError,
)
from app.social.providers.adapters import PROVIDERS, get_provider
from app.social.store import (
    approve_campaign,
    create_account,
    delete_account,
    get_analytics,
    list_accounts,
    list_engagement,
    plan_campaign,
    process_due_posts,
    publish_batch,
    publish_now,
    queue_post,
    reply_to_engagement,
    sync_engagement,
)

router = APIRouter(prefix="/social", tags=["Social Growth"])
CurrentUser = Annotated[dict, Depends(get_current_user)]
settings = get_settings()


class ManualAccountRequest(BaseModel):
    platform: Platform
    access_token: str = Field(..., min_length=8, max_length=10000)
    refresh_token: str | None = Field(default=None, max_length=10000)
    external_account_id: str = Field(..., min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    scopes: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ScheduledPublishRequest(BaseModel):
    command: PublishCommand
    scheduled_at: datetime | None = None


class BatchPublishRequest(BaseModel):
    commands: list[PublishCommand] = Field(
        ...,
        min_length=1,
        max_length=50,
    )


@router.get("/platforms")
async def platforms(_: CurrentUser) -> dict:
    return {
        "platforms": [
            {
                "platform": platform.value,
                "capabilities": [
                    capability.value
                    for capability in provider.capabilities
                ],
            }
            for platform, provider in PROVIDERS.items()
        ]
    }


@router.get("/oauth/{platform}/start")
async def oauth_start(
    platform: Platform,
    current_user: CurrentUser,
    external_account_id: str | None = Query(
        default=None,
        max_length=255,
    ),
) -> dict:
    provider = get_provider(platform)
    state = secrets.token_urlsafe(32)
    await cache_set(
        f"social:oauth:{state}",
        {
            "user_id": current_user["user_id"],
            "platform": platform.value,
            "external_account_id": external_account_id,
        },
        ttl=600,
    )
    return {
        "platform": platform.value,
        "authorization_url": provider.authorization_url(state),
        "state": state,
    }


@router.get("/oauth/{platform}/callback")
async def oauth_callback(
    platform: Platform,
    code: str = Query(..., min_length=1),
    state: str = Query(..., min_length=10),
    external_account_id: str | None = Query(
        default=None,
        max_length=255,
    ),
) -> dict:
    payload = await cache_pop(f"social:oauth:{state}")
    if not payload or payload.get("platform") != platform.value:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired social OAuth state.",
        )

    try:
        token_data = await get_provider(platform).exchange_code(
            code,
            state,
        )
        account = await create_account(
            payload["user_id"],
            platform,
            token_data,
            external_account_id or payload.get("external_account_id"),
        )
        return {"status": "connected", "account": account}
    except (SocialProviderError, ValueError) as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", 400),
            detail=str(exc),
        ) from exc


@router.post("/accounts/manual")
async def manual_account(
    body: ManualAccountRequest,
    current_user: CurrentUser,
) -> dict:
    token_data = {
        "access_token": body.access_token,
        "refresh_token": body.refresh_token,
        "scope": " ".join(body.scopes),
        "metadata": body.metadata,
    }
    try:
        account = await create_account(
            current_user["user_id"],
            body.platform,
            token_data,
            body.external_account_id,
            body.display_name,
        )
        return {"account": account}
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.get("/accounts")
async def accounts(current_user: CurrentUser) -> dict:
    rows = await list_accounts(current_user["user_id"])
    return {"accounts": rows, "count": len(rows)}


@router.delete("/accounts/{account_id}")
async def remove_account(
    account_id: str,
    current_user: CurrentUser,
) -> dict:
    deleted = await delete_account(
        current_user["user_id"],
        account_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Social account not found.",
        )
    return {
        "status": "disconnected",
        "account_id": account_id,
    }


@router.post("/publish")
async def publish(
    body: ScheduledPublishRequest,
    current_user: CurrentUser,
) -> dict:
    try:
        if body.scheduled_at:
            scheduled_at = body.scheduled_at.astimezone(UTC)
            if scheduled_at <= datetime.now(UTC):
                return await publish_now(
                    current_user["user_id"],
                    body.command,
                )
            return await queue_post(
                current_user["user_id"],
                body.command,
                scheduled_at,
            )
        return await publish_now(
            current_user["user_id"],
            body.command,
        )
    except (SocialProviderError, ValueError) as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", 422),
            detail=str(exc),
        ) from exc


@router.post("/publish/batch")
async def publish_multiple(
    body: BatchPublishRequest,
    current_user: CurrentUser,
) -> dict:
    return await publish_batch(
        current_user["user_id"],
        body.commands,
    )


@router.get("/analytics/{account_id}")
async def analytics(
    account_id: str,
    current_user: CurrentUser,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    try:
        return await get_analytics(
            current_user["user_id"],
            account_id,
            start,
            end,
        )
    except (SocialProviderError, ValueError) as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", 422),
            detail=str(exc),
        ) from exc


@router.post("/engagement/sync/{account_id}")
async def engagement_sync(
    account_id: str,
    current_user: CurrentUser,
) -> dict:
    try:
        return await sync_engagement(
            current_user["user_id"],
            account_id,
        )
    except (SocialProviderError, ValueError) as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", 422),
            detail=str(exc),
        ) from exc


@router.get("/engagement")
async def engagement(
    current_user: CurrentUser,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    rows = await list_engagement(
        current_user["user_id"],
        limit,
    )
    return {"items": rows, "count": len(rows)}


@router.post("/engagement/reply")
async def engagement_reply(
    body: ReplyCommand,
    current_user: CurrentUser,
) -> dict:
    try:
        return await reply_to_engagement(
            current_user["user_id"],
            body,
        )
    except (SocialProviderError, ValueError) as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", 422),
            detail=str(exc),
        ) from exc


@router.post("/campaigns")
async def campaign_plan(
    body: CampaignPlan,
    current_user: CurrentUser,
) -> dict:
    try:
        return await plan_campaign(
            current_user["user_id"],
            body.model_dump(mode="json"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.post("/campaigns/{campaign_id}/approve")
async def campaign_approve(
    campaign_id: str,
    current_user: CurrentUser,
) -> dict:
    try:
        return await approve_campaign(
            current_user["user_id"],
            campaign_id,
        )
    except (SocialProviderError, ValueError) as exc:
        raise HTTPException(
            status_code=getattr(exc, "status_code", 422),
            detail=str(exc),
        ) from exc


@router.post("/scheduled/process")
async def process_scheduled(
    current_user: CurrentUser,
) -> dict:
    return {
        "processed": await process_due_posts(),
        "requested_by": current_user["user_id"],
    }

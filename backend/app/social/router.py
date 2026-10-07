"""HTTP boundary for PAMASMMA social growth operations."""
import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.redis_client import cache_get, cache_pop, cache_set
from app.security.crypto import decrypt_secret, encrypt_secret
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


class OAuthAccountSelection(BaseModel):
    external_account_id: str = Field(..., min_length=1, max_length=255)


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
    payload = {
        "user_id": current_user["user_id"],
        "platform": platform.value,
        "external_account_id": external_account_id,
    }
    authorization_url = provider.authorization_url(state)
    if platform is Platform.X:
        code_verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).decode("ascii").rstrip("=")
        payload["pkce_verifier_enc"] = encrypt_secret(code_verifier)
        authorization_url = provider.authorization_url(
            state,
            code_challenge=challenge,
        )
    await cache_set(f"social:oauth:{state}", payload, ttl=600)
    return {
        "platform": platform.value,
        "authorization_url": authorization_url,
        "state": state,
    }


def _social_frontend_url(query: str) -> str:
    origin = (
        settings.allowed_origins[0].rstrip("/")
        if settings.allowed_origins
        else "http://localhost:3000"
    )
    return f"{origin}/social?{query}"


@router.get("/oauth/{platform}/callback")
async def oauth_callback(
    platform: Platform,
    code: str | None = Query(default=None, min_length=1),
    state: str = Query(..., min_length=10),
    external_account_id: str | None = Query(default=None, max_length=255),
    error: str | None = Query(default=None, max_length=255),
    error_description: str | None = Query(default=None, max_length=1000),
) -> RedirectResponse:
    payload = await cache_pop(f"social:oauth:{state}")
    if not payload or payload.get("platform") != platform.value:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired social OAuth state.",
        )

    if error:
        message = quote(error_description or error, safe="")
        return RedirectResponse(
            _social_frontend_url(f"social_error={message}"),
            status_code=303,
        )

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is missing.")

    provider = get_provider(platform)

    try:
        exchange_kwargs: dict[str, str] = {}
        if platform is Platform.X:
            verifier_enc = payload.get("pkce_verifier_enc")
            if not verifier_enc:
                raise ValueError("X OAuth PKCE verifier is missing or expired.")
            exchange_kwargs["code_verifier"] = decrypt_secret(verifier_enc)
        token_data = await provider.exchange_code(
            code,
            state,
            **exchange_kwargs,
        )
        access_token = str(
            token_data.get("access_token") or token_data.get("token") or ""
        )
        discovered = await provider.discover_accounts(access_token)

        requested = external_account_id or payload.get("external_account_id")
        if requested:
            selected = next(
                (
                    item
                    for item in discovered
                    if item.get("external_account_id") == requested
                ),
                None,
            )
            if discovered and not selected:
                raise ValueError(
                    "The requested account is not available to the authorized user."
                )
            selected_data = dict(token_data)
            if selected:
                selected_data.update(selected.get("token_data") or {})
            await create_account(
                payload["user_id"],
                platform,
                selected_data,
                requested,
                selected.get("display_name") if selected else None,
            )
            return RedirectResponse(
                _social_frontend_url(
                    f"social_connected=1&platform={quote(platform.value)}"
                ),
                status_code=303,
            )

        if len(discovered) == 1:
            selected = discovered[0]
            selected_data = dict(token_data)
            selected_data.update(selected.get("token_data") or {})
            await create_account(
                payload["user_id"],
                platform,
                selected_data,
                str(selected["external_account_id"]),
                selected.get("display_name"),
            )
            return RedirectResponse(
                _social_frontend_url(
                    f"social_connected=1&platform={quote(platform.value)}"
                ),
                status_code=303,
            )

        if len(discovered) > 1:
            pending_id = secrets.token_urlsafe(32)
            await cache_set(
                f"social:pending:{pending_id}",
                {
                    "user_id": payload["user_id"],
                    "platform": platform.value,
                    "token_data_enc": encrypt_secret(json.dumps(token_data)),
                    "accounts_enc": encrypt_secret(json.dumps(discovered)),
                },
                ttl=300,
            )
            return RedirectResponse(
                _social_frontend_url(f"social_connect={quote(pending_id)}"),
                status_code=303,
            )

        fallback_id = requested
        if not fallback_id:
            raise ValueError("The platform did not return a connectable account.")
        await create_account(
            payload["user_id"],
            platform,
            token_data,
            fallback_id,
        )
        return RedirectResponse(
            _social_frontend_url(
                f"social_connected=1&platform={quote(platform.value)}"
            ),
            status_code=303,
        )
    except (SocialProviderError, ValueError) as exc:
        message = quote(str(exc), safe="")
        return RedirectResponse(
            _social_frontend_url(f"social_error={message}"),
            status_code=303,
        )


@router.get("/oauth/pending/{pending_id}")
async def oauth_pending(
    pending_id: str,
    current_user: CurrentUser,
) -> dict:
    payload = await cache_get(f"social:pending:{pending_id}")
    if not payload or payload.get("user_id") != current_user["user_id"]:
        raise HTTPException(
            status_code=404,
            detail="Social connection request not found or expired.",
        )
    accounts = json.loads(decrypt_secret(payload["accounts_enc"]))
    return {
        "pending_id": pending_id,
        "platform": payload["platform"],
        "accounts": [
            {
                "external_account_id": item.get("external_account_id"),
                "display_name": item.get("display_name"),
            }
            for item in accounts
            if item.get("external_account_id")
        ],
    }


@router.post("/oauth/pending/{pending_id}/complete")
async def oauth_pending_complete(
    pending_id: str,
    body: OAuthAccountSelection,
    current_user: CurrentUser,
) -> dict:
    payload = await cache_get(f"social:pending:{pending_id}")
    if not payload or payload.get("user_id") != current_user["user_id"]:
        raise HTTPException(
            status_code=404,
            detail="Social connection request not found or expired.",
        )

    accounts = json.loads(decrypt_secret(payload["accounts_enc"]))
    selected = next(
        (
            item
            for item in accounts
            if item.get("external_account_id") == body.external_account_id
        ),
        None,
    )
    if not selected:
        raise HTTPException(
            status_code=422,
            detail="Selected account is not part of this connection request.",
        )

    payload = await cache_pop(f"social:pending:{pending_id}")
    if not payload or payload.get("user_id") != current_user["user_id"]:
        raise HTTPException(
            status_code=404,
            detail="Social connection request expired during completion.",
        )

    token_data = json.loads(decrypt_secret(payload["token_data_enc"]))
    token_data.update(selected.get("token_data") or {})
    account = await create_account(
        current_user["user_id"],
        Platform(payload["platform"]),
        token_data,
        body.external_account_id,
        selected.get("display_name"),
    )
    return {"status": "connected", "account": account}


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


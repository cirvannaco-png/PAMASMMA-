"""Concrete REST adapters for supported social platforms.

Provider-specific SDKs and API payloads belong here. The rest of PAMASMMA
depends only on the provider-neutral contracts.
"""
import base64
import hashlib
import os
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.social.contracts import (
    Capability,
    Platform,
    PublishCommand,
    ReplyCommand,
    SocialProviderError,
)
from app.social.providers.base import SocialProvider
from app.social.providers.http import HttpProvider


def _env(name: str) -> str:
    """Read a social setting without exposing secrets to logs or responses."""
    field = name.lower()
    value = getattr(get_settings(), field, None)
    if value is None:
        return os.getenv(name, "").strip()
    if hasattr(value, "get_secret_value"):
        value = value.get_secret_value()
    return str(value).strip()


def _provider_error(
    platform: Platform,
    code: str,
    message: str,
    status_code: int = 502,
) -> SocialProviderError:
    return SocialProviderError(platform, code, message, status_code)


class OAuthRestProvider(SocialProvider, HttpProvider):
    """Shared OAuth 2.0 transport for providers using conventional flows."""

    auth_url: str = ""
    token_url: str = ""
    client_id_env: str = ""
    client_secret_env: str = ""
    redirect_env: str = ""
    scope_env: str = ""

    def __init__(self) -> None:
        HttpProvider.__init__(self, self.platform)

    def authorization_url(self, state: str) -> str:
        client_id = _env(self.client_id_env)
        redirect_uri = _env(self.redirect_env)
        if not client_id or not redirect_uri:
            raise _provider_error(
                self.platform,
                "oauth_not_configured",
                f"{self.platform.value} OAuth is not configured.",
                503,
            )

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        scopes = _env(self.scope_env)
        if scopes:
            params["scope"] = scopes
        query = urlencode(params)
        return f"{self.auth_url}{'&' if '?' in self.auth_url else '?'}{query}"

    async def exchange_code(
        self,
        code: str,
        state: str | None = None,
    ) -> dict[str, Any]:
        del state
        client_id = _env(self.client_id_env)
        secret = _env(self.client_secret_env)
        redirect_uri = _env(self.redirect_env)
        if not all((client_id, secret, redirect_uri)):
            raise _provider_error(
                self.platform,
                "oauth_not_configured",
                f"{self.platform.value} OAuth is not configured.",
                503,
            )

        return await self.request(
            "POST",
            self.token_url,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        client_id = _env(self.client_id_env)
        secret = _env(self.client_secret_env)
        return await self.request(
            "POST",
            self.token_url,
            data={
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": secret,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )


class XProvider(OAuthRestProvider):
    """X API adapter using OAuth 2.0 with PKCE."""

    platform = Platform.X
    capabilities = frozenset(
        {
            Capability.PUBLISH,
            Capability.COMMENTS_READ,
            Capability.COMMENTS_WRITE,
            Capability.MENTIONS_READ,
        }
    )
    auth_url = "https://x.com/i/oauth2/authorize"
    token_url = "https://api.x.com/2/oauth2/token"
    client_id_env = "SOCIAL_X_CLIENT_ID"
    client_secret_env = "SOCIAL_X_CLIENT_SECRET"
    redirect_env = "SOCIAL_X_REDIRECT_URI"
    scope_env = "SOCIAL_X_SCOPES"

    def _pkce_verifier(self, state: str) -> str:
        return base64.urlsafe_b64encode(
            hashlib.sha256(state.encode()).digest()
        ).decode().rstrip("=")

    def authorization_url(self, state: str) -> str:
        verifier = self._pkce_verifier(state)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")
        url = super().authorization_url(state)
        return f"{url}&code_challenge={challenge}&code_challenge_method=S256"

    async def exchange_code(
        self,
        code: str,
        state: str | None = None,
    ) -> dict[str, Any]:
        client_id = _env(self.client_id_env)
        secret = _env(self.client_secret_env)
        redirect_uri = _env(self.redirect_env)
        if not all((client_id, secret, redirect_uri)):
            raise _provider_error(
                self.platform,
                "oauth_not_configured",
                f"{self.platform.value} OAuth is not configured.",
                503,
            )

        verifier = self._pkce_verifier(state or "")
        return await self.request(
            "POST",
            self.token_url,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        self.require(Capability.PUBLISH)
        body: dict[str, Any] = {"text": command.text}
        if command.reply_to_id:
            body["reply"] = {"in_reply_to_tweet_id": command.reply_to_id}
        return await self.request(
            "POST",
            "https://api.x.com/2/tweets",
            token=token,
            json_body=body,
        )

    async def reply(
        self,
        token: str,
        command: ReplyCommand,
    ) -> dict[str, Any]:
        return await self.publish(
            token,
            PublishCommand(
                account_id=command.account_id,
                text=command.text,
                reply_to_id=command.item_id,
            ),
            command.external_account_id or "",
        )

    async def list_engagement(
        self,
        token: str,
        external_account_id: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        query = f"to:{external_account_id} OR @{external_account_id}"
        params: dict[str, Any] = {
            "query": query,
            "tweet.fields": "created_at,author_id,public_metrics",
            "max_results": 100,
        }
        if cursor:
            params["next_token"] = cursor
        return await self.request(
            "GET",
            "https://api.x.com/2/tweets/search/recent",
            token=token,
            params=params,
        )


class LinkedInProvider(OAuthRestProvider):
    """LinkedIn posts and comment actions adapter."""

    platform = Platform.LINKEDIN
    capabilities = frozenset(
        {
            Capability.PUBLISH,
            Capability.COMMENTS_READ,
            Capability.COMMENTS_WRITE,
        }
    )
    auth_url = "https://www.linkedin.com/oauth/v2/authorization"
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    client_id_env = "SOCIAL_LINKEDIN_CLIENT_ID"
    client_secret_env = "SOCIAL_LINKEDIN_CLIENT_SECRET"
    redirect_env = "SOCIAL_LINKEDIN_REDIRECT_URI"
    scope_env = "SOCIAL_LINKEDIN_SCOPES"

    def _headers(self) -> dict[str, str]:
        return {
            "Linkedin-Version": _env("SOCIAL_LINKEDIN_VERSION") or "202603",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        body = {
            "author": external_account_id,
            "commentary": command.text,
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED"},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        return await self.request(
            "POST",
            "https://api.linkedin.com/rest/posts",
            token=token,
            json_body=body,
            headers=self._headers(),
        )

    async def reply(
        self,
        token: str,
        command: ReplyCommand,
    ) -> dict[str, Any]:
        body = {
            "actor": command.external_account_id or "",
            "object": command.item_id,
            "message": {"text": command.text},
        }
        return await self.request(
            "POST",
            f"https://api.linkedin.com/rest/socialActions/{command.item_id}/comments",
            token=token,
            json_body=body,
            headers=self._headers(),
        )

    async def list_engagement(
        self,
        token: str,
        external_account_id: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        del cursor
        return await self.request(
            "GET",
            f"https://api.linkedin.com/rest/socialActions/{external_account_id}/comments",
            token=token,
            headers=self._headers(),
        )


class YouTubeProvider(OAuthRestProvider):
    """YouTube Data API and Analytics API adapter."""

    platform = Platform.YOUTUBE
    capabilities = frozenset(
        {
            Capability.PUBLISH,
            Capability.COMMENTS_READ,
            Capability.COMMENTS_WRITE,
            Capability.ANALYTICS,
        }
    )
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    client_id_env = "SOCIAL_YOUTUBE_CLIENT_ID"
    client_secret_env = "SOCIAL_YOUTUBE_CLIENT_SECRET"
    redirect_env = "SOCIAL_YOUTUBE_REDIRECT_URI"
    scope_env = "SOCIAL_YOUTUBE_SCOPES"

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        del external_account_id
        video_path = command.platform_options.get("video_path")
        if not video_path:
            raise _provider_error(
                self.platform,
                "media_required",
                "YouTube publishing requires platform_options.video_path.",
                422,
            )

        path = __import__("pathlib").Path(str(video_path))
        if not path.is_file():
            raise _provider_error(
                self.platform,
                "media_not_found",
                "Video file was not found on the server.",
                422,
            )

        metadata = {
            "snippet": {
                "title": command.title or command.text[:100],
                "description": command.text,
            },
            "status": {
                "privacyStatus": command.platform_options.get(
                    "privacy_status",
                    "private",
                )
            },
        }
        upload_type = command.media_type or "video/mp4"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Upload-Content-Type": upload_type,
            "Content-Type": "application/json; charset=UTF-8",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://www.googleapis.com/upload/youtube/v3/videos"
                "?part=snippet,status&uploadType=resumable",
                headers=headers,
                json=metadata,
            )
            if response.status_code >= 400:
                raise _provider_error(
                    self.platform,
                    "provider_error",
                    response.text[:1000],
                    response.status_code,
                )

            upload_url = response.headers.get("location")
            if not upload_url:
                raise _provider_error(
                    self.platform,
                    "provider_error",
                    "YouTube did not return an upload URL.",
                )

            upload = await client.put(
                upload_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": upload_type,
                },
                content=path.read_bytes(),
            )
            if upload.status_code >= 400:
                raise _provider_error(
                    self.platform,
                    "provider_error",
                    upload.text[:1000],
                    upload.status_code,
                )
            return upload.json()

    async def reply(
        self,
        token: str,
        command: ReplyCommand,
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            "https://www.googleapis.com/youtube/v3/comments?part=snippet",
            token=token,
            json_body={
                "snippet": {
                    "parentId": command.item_id,
                    "textOriginal": command.text,
                }
            },
        )

    async def list_engagement(
        self,
        token: str,
        external_account_id: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "part": "snippet,replies",
            "allThreadsRelatedToChannelId": external_account_id,
            "maxResults": 100,
        }
        if cursor:
            params["pageToken"] = cursor
        return await self.request(
            "GET",
            "https://www.googleapis.com/youtube/v3/commentThreads",
            token=token,
            params=params,
        )

    async def analytics(
        self,
        token: str,
        external_account_id: str,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            "https://youtubeanalytics.googleapis.com/v2/reports",
            token=token,
            params={
                "ids": f"channel=={external_account_id}",
                "startDate": start or "2000-01-01",
                "endDate": end or "2100-01-01",
                "metrics": (
                    "views,likes,comments,shares,"
                    "subscribersGained,subscribersLost"
                ),
                "dimensions": "day",
            },
        )


class PinterestProvider(OAuthRestProvider):
    """Pinterest organic content adapter."""

    platform = Platform.PINTEREST
    capabilities = frozenset({Capability.PUBLISH, Capability.ANALYTICS})
    auth_url = "https://www.pinterest.com/oauth/"
    token_url = "https://api.pinterest.com/v5/oauth/token"
    client_id_env = "SOCIAL_PINTEREST_APP_ID"
    client_secret_env = "SOCIAL_PINTEREST_APP_SECRET"
    redirect_env = "SOCIAL_PINTEREST_REDIRECT_URI"
    scope_env = "SOCIAL_PINTEREST_SCOPES"

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        del external_account_id
        if not command.media_url:
            raise _provider_error(
                self.platform,
                "media_required",
                "Pinterest Pins require media_url.",
                422,
            )
        return await self.request(
            "POST",
            "https://api.pinterest.com/v5/pins",
            token=token,
            json_body={
                "board_id": command.platform_options.get("board_id"),
                "title": command.title,
                "description": command.text,
                "alt_text": command.platform_options.get("alt_text"),
                "link": str(command.link_url) if command.link_url else None,
                "media_source": {
                    "source_type": "image_url",
                    "url": str(command.media_url),
                },
            },
        )


class MetaProvider(OAuthRestProvider):
    """Facebook Pages / Meta Graph API adapter."""

    platform = Platform.FACEBOOK
    capabilities = frozenset(
        {
            Capability.PUBLISH,
            Capability.COMMENTS_READ,
            Capability.COMMENTS_WRITE,
            Capability.MENTIONS_READ,
            Capability.ANALYTICS,
            Capability.ADS_READ,
            Capability.ADS_WRITE,
        }
    )
    auth_url = "https://www.facebook.com/v{version}/dialog/oauth"
    token_url = "https://graph.facebook.com/v{version}/oauth/access_token"
    client_id_env = "SOCIAL_META_CLIENT_ID"
    client_secret_env = "SOCIAL_META_CLIENT_SECRET"
    redirect_env = "SOCIAL_META_REDIRECT_URI"
    scope_env = "SOCIAL_META_SCOPES"

    def _version(self) -> str:
        version = _env("SOCIAL_META_GRAPH_VERSION")
        if not version:
            raise _provider_error(
                self.platform,
                "api_version_not_configured",
                "SOCIAL_META_GRAPH_VERSION must be configured.",
                503,
            )
        return version

    def _base(self) -> str:
        return f"https://graph.facebook.com/{self._version()}"

    def authorization_url(self, state: str) -> str:
        self.auth_url = f"https://www.facebook.com/{self._version()}/dialog/oauth"
        return super().authorization_url(state)

    async def exchange_code(
        self,
        code: str,
        state: str | None = None,
    ) -> dict[str, Any]:
        self.token_url = f"{self._base()}/oauth/access_token"
        return await super().exchange_code(code, state)

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"message": command.text}
        if command.link_url:
            body["link"] = str(command.link_url)
        return await self.request(
            "POST",
            f"{self._base()}/{external_account_id}/feed",
            token=token,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def reply(
        self,
        token: str,
        command: ReplyCommand,
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            f"{self._base()}/{command.item_id}/comments",
            token=token,
            data={"message": command.text},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def list_engagement(
        self,
        token: str,
        external_account_id: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "fields": "id,message,comments.limit(100){message,from,created_time}",
            "limit": 100,
        }
        if cursor:
            params["after"] = cursor
        return await self.request(
            "GET",
            f"{self._base()}/{external_account_id}/feed",
            token=token,
            params=params,
        )

    async def analytics(
        self,
        token: str,
        external_account_id: str,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        del start, end
        return await self.request(
            "GET",
            f"{self._base()}/{external_account_id}/insights",
            token=token,
            params={
                "metric": (
                    "page_impressions,page_engaged_users,"
                    "page_post_engagements"
                )
            },
        )

    async def create_campaign(
        self,
        token: str,
        account_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        data = {
            key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in payload.items()
        }
        return await self.request(
            "POST",
            f"{self._base()}/act_{account_id}/campaigns",
            token=token,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )


class InstagramProvider(MetaProvider):
    """Instagram professional account content adapter via Meta Graph."""

    platform = Platform.INSTAGRAM
    capabilities = frozenset(
        {
            Capability.PUBLISH,
            Capability.COMMENTS_READ,
            Capability.COMMENTS_WRITE,
            Capability.MENTIONS_READ,
            Capability.ANALYTICS,
        }
    )

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        if not command.media_url:
            raise _provider_error(
                self.platform,
                "media_required",
                "Instagram publishing requires media_url.",
                422,
            )

        if (command.media_type or "").startswith("video"):
            container = {
                "video_url": str(command.media_url),
                "caption": command.text,
                "media_type": "REELS",
            }
        else:
            container = {
                "image_url": str(command.media_url),
                "caption": command.text,
            }

        created = await self.request(
            "POST",
            f"{self._base()}/{external_account_id}/media",
            token=token,
            data=container,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return await self.request(
            "POST",
            f"{self._base()}/{external_account_id}/media_publish",
            token=token,
            data={"creation_id": created.get("id", "")},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )


class ThreadsProvider(OAuthRestProvider):
    """Threads publishing and reply adapter."""

    platform = Platform.THREADS
    capabilities = frozenset(
        {
            Capability.PUBLISH,
            Capability.COMMENTS_READ,
            Capability.COMMENTS_WRITE,
        }
    )
    auth_url = "https://threads.net/oauth/authorize"
    token_url = "https://graph.threads.net/oauth/access_token"
    client_id_env = "SOCIAL_THREADS_CLIENT_ID"
    client_secret_env = "SOCIAL_THREADS_CLIENT_SECRET"
    redirect_env = "SOCIAL_THREADS_REDIRECT_URI"
    scope_env = "SOCIAL_THREADS_SCOPES"

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        created = await self.request(
            "POST",
            f"https://graph.threads.net/v1.0/{external_account_id}/threads",
            token=token,
            data={"media_type": "TEXT", "text": command.text},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return await self.request(
            "POST",
            f"https://graph.threads.net/v1.0/{external_account_id}/threads_publish",
            token=token,
            data={"creation_id": created.get("id", "")},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def reply(
        self,
        token: str,
        command: ReplyCommand,
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            f"https://graph.threads.net/v1.0/{command.item_id}/replies",
            token=token,
            data={"text": command.text},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )


class TikTokProvider(OAuthRestProvider):
    """TikTok Content Posting API adapter."""

    platform = Platform.TIKTOK
    capabilities = frozenset({Capability.PUBLISH})
    auth_url = "https://www.tiktok.com/v2/auth/authorize/"
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    client_id_env = "SOCIAL_TIKTOK_CLIENT_KEY"
    client_secret_env = "SOCIAL_TIKTOK_CLIENT_SECRET"
    redirect_env = "SOCIAL_TIKTOK_REDIRECT_URI"
    scope_env = "SOCIAL_TIKTOK_SCOPES"

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        del external_account_id

        creator = await self.request(
            "POST",
            "https://open.tiktokapis.com/v2/post/publish/creator_info/query/",
            token=token,
            json_body={},
        )
        info = creator.get("data") or {}
        allowed_privacy = info.get("privacy_level_options") or ["SELF_ONLY"]
        privacy = command.platform_options.get(
            "privacy_level",
            allowed_privacy[0],
        )
        if privacy not in allowed_privacy:
            raise _provider_error(
                self.platform,
                "invalid_privacy_level",
                "Requested TikTok privacy level is not allowed for this creator.",
                422,
            )

        is_photo = (command.media_type or "").startswith("image")
        if is_photo:
            body = {
                "post_info": {
                    "title": command.text,
                    "privacy_level": privacy,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "photo_cover_index": 0,
                    "photo_images": [str(command.media_url)],
                },
            }
            endpoint = (
                "https://open.tiktokapis.com/v2/"
                "post/publish/content/init/"
            )
        else:
            body = {
                "post_info": {
                    "title": command.text,
                    "privacy_level": privacy,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": str(command.media_url),
                },
            }
            endpoint = (
                "https://open.tiktokapis.com/v2/"
                "post/publish/video/init/"
            )

        if not command.media_url:
            raise _provider_error(
                self.platform,
                "media_required",
                "TikTok publishing requires media_url.",
                422,
            )
        return await self.request(
            "POST",
            endpoint,
            token=token,
            json_body=body,
        )


class RedditProvider(OAuthRestProvider):
    """Reddit submissions and comment adapter."""

    platform = Platform.REDDIT
    capabilities = frozenset(
        {
            Capability.PUBLISH,
            Capability.COMMENTS_READ,
            Capability.COMMENTS_WRITE,
            Capability.MENTIONS_READ,
        }
    )
    auth_url = "https://www.reddit.com/api/v1/authorize"
    token_url = "https://www.reddit.com/api/v1/access_token"
    client_id_env = "SOCIAL_REDDIT_CLIENT_ID"
    client_secret_env = "SOCIAL_REDDIT_CLIENT_SECRET"
    redirect_env = "SOCIAL_REDDIT_REDIRECT_URI"
    scope_env = "SOCIAL_REDDIT_SCOPES"

    async def exchange_code(
        self,
        code: str,
        state: str | None = None,
    ) -> dict[str, Any]:
        del state
        client_id = _env(self.client_id_env)
        secret = _env(self.client_secret_env)
        redirect_uri = _env(self.redirect_env)
        basic = base64.b64encode(
            f"{client_id}:{secret}".encode()
        ).decode()
        return await self.request(
            "POST",
            self.token_url,
            data={
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "PAMASMMA/1.0",
            },
        )

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        del external_account_id
        subreddit = command.platform_options.get("subreddit")
        if not subreddit:
            raise _provider_error(
                self.platform,
                "subreddit_required",
                "Reddit publishing requires platform_options.subreddit.",
                422,
            )
        return await self.request(
            "POST",
            "https://oauth.reddit.com/api/submit",
            token=token,
            data={
                "sr": subreddit,
                "title": command.title or command.text[:300],
                "text": command.text,
                "kind": "self",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "PAMASMMA/1.0",
            },
        )

    async def reply(
        self,
        token: str,
        command: ReplyCommand,
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            "https://oauth.reddit.com/api/comment",
            token=token,
            data={"thing_id": command.item_id, "text": command.text},
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "PAMASMMA/1.0",
            },
        )

    async def list_engagement(
        self,
        token: str,
        external_account_id: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": 100}
        if cursor:
            params["after"] = cursor
        return await self.request(
            "GET",
            f"https://oauth.reddit.com/user/{external_account_id}/comments",
            token=token,
            params=params,
            headers={"User-Agent": "PAMASMMA/1.0"},
        )


class TelegramProvider(SocialProvider):
    """Telegram Bot API messaging adapter."""

    platform = Platform.TELEGRAM
    capabilities = frozenset({Capability.PUBLISH, Capability.COMMENTS_READ, Capability.COMMENTS_WRITE})

    def authorization_url(self, state: str) -> str:
        del state
        raise _provider_error(
            self.platform,
            "oauth_not_applicable",
            "Telegram uses a bot token rather than user OAuth.",
            422,
        )

    async def exchange_code(
        self,
        code: str,
        state: str | None = None,
    ) -> dict[str, Any]:
        del code, state
        raise _provider_error(
            self.platform,
            "oauth_not_applicable",
            "Telegram uses a bot token rather than user OAuth.",
            422,
        )

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            f"https://api.telegram.org/bot{token}/sendMessage",
            json_body={
                "chat_id": external_account_id,
                "text": command.text,
            },
        )


class WhatsAppProvider(SocialProvider):
    """WhatsApp Cloud API text messaging adapter."""

    platform = Platform.WHATSAPP
    capabilities = frozenset({Capability.PUBLISH, Capability.COMMENTS_WRITE})

    def authorization_url(self, state: str) -> str:
        del state
        raise _provider_error(
            self.platform,
            "oauth_not_applicable",
            "WhatsApp Business uses Meta business configuration.",
            422,
        )

    async def exchange_code(
        self,
        code: str,
        state: str | None = None,
    ) -> dict[str, Any]:
        del code, state
        raise _provider_error(
            self.platform,
            "oauth_not_applicable",
            "Use Meta Business configuration for WhatsApp.",
            422,
        )

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        version = _env("SOCIAL_META_GRAPH_VERSION")
        if not version:
            raise _provider_error(
                self.platform,
                "api_version_not_configured",
                "SOCIAL_META_GRAPH_VERSION must be configured.",
                503,
            )
        recipient = command.platform_options.get("to")
        if not recipient:
            raise _provider_error(
                self.platform,
                "recipient_required",
                "WhatsApp publishing requires platform_options.to.",
                422,
            )
        return await self.request(
            "POST",
            f"https://graph.facebook.com/{version}/{external_account_id}/messages",
            token=token,
            json_body={
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"body": command.text},
            },
        )


PROVIDERS: dict[Platform, SocialProvider] = {
    Platform.FACEBOOK: MetaProvider(),
    Platform.INSTAGRAM: InstagramProvider(),
    Platform.TIKTOK: TikTokProvider(),
    Platform.YOUTUBE: YouTubeProvider(),
    Platform.LINKEDIN: LinkedInProvider(),
    Platform.X: XProvider(),
    Platform.THREADS: ThreadsProvider(),
    Platform.PINTEREST: PinterestProvider(),
    Platform.REDDIT: RedditProvider(),
    Platform.TELEGRAM: TelegramProvider(),
    Platform.WHATSAPP: WhatsAppProvider(),
}


def get_provider(platform: Platform) -> SocialProvider:
    return PROVIDERS[platform]

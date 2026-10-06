"""Meta and Instagram platform adapters."""
import asyncio
from typing import Any

from app.social.contracts import Capability, Platform, PublishCommand, ReplyCommand
from app.social.providers.common import _env
from app.social.providers.common import provider_error as _provider_error
from app.social.providers.oauth import OAuthRestProvider


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

    async def discover_accounts(self, token: str) -> list[dict[str, Any]]:
        """Discover Facebook Pages the authorized user can manage."""
        response = await self.request(
            "GET",
            f"{self._base()}/me/accounts",
            token=token,
            params={"fields": "id,name,access_token", "limit": 100},
        )
        accounts = []
        for item in response.get("data", []):
            page_token = item.get("access_token")
            page_id = item.get("id")
            if page_id and page_token:
                accounts.append(
                    {
                        "external_account_id": str(page_id),
                        "display_name": item.get("name"),
                        "token_data": {
                            "access_token": page_token,
                            "name": item.get("name"),
                            "scope": _env(self.scope_env),
                            "metadata": {"page_id": str(page_id)},
                        },
                    }
                )
        return accounts

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

    async def discover_accounts(self, token: str) -> list[dict[str, Any]]:
        """Discover Instagram professional accounts linked to managed Pages."""
        response = await self.request(
            "GET",
            f"{self._base()}/me/accounts",
            token=token,
            params={
                "fields": "id,name,access_token,instagram_business_account",
                "limit": 100,
            },
        )
        accounts = []
        for page in response.get("data", []):
            instagram = page.get("instagram_business_account") or {}
            instagram_id = instagram.get("id")
            page_token = page.get("access_token")
            if instagram_id and page_token:
                accounts.append(
                    {
                        "external_account_id": str(instagram_id),
                        "display_name": page.get("name"),
                        "token_data": {
                            "access_token": page_token,
                            "name": page.get("name"),
                            "scope": _env(self.scope_env),
                            "metadata": {
                                "page_id": str(page.get("id")),
                                "instagram_account_id": str(instagram_id),
                            },
                        },
                    }
                )
        return accounts

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
        creation_id = created.get("id")
        if not creation_id:
            raise _provider_error(
                self.platform,
                "container_creation_failed",
                "Instagram did not return a media container id.",
                502,
            )

        # Video/Reel containers are processed asynchronously by Meta.
        if (command.media_type or "").startswith("video"):
            status = ""
            for _ in range(20):
                state = await self.request(
                    "GET",
                    f"{self._base()}/{creation_id}",
                    token=token,
                    params={"fields": "status_code,status"},
                )
                status = str(state.get("status_code") or "").upper()
                if status == "FINISHED":
                    break
                if status in {"ERROR", "EXPIRED"}:
                    raise _provider_error(
                        self.platform,
                        "container_processing_failed",
                        state.get("status")
                        or f"Instagram container entered terminal state {status}.",
                        422,
                    )
                await asyncio.sleep(15)
            else:
                raise _provider_error(
                    self.platform,
                    "container_processing_timeout",
                    "Instagram video processing did not finish within 5 minutes.",
                    504,
                )

        return await self.request(
            "POST",
            f"{self._base()}/{external_account_id}/media_publish",
            token=token,
            data={"creation_id": creation_id},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

"""Meta and Instagram platform adapters."""
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

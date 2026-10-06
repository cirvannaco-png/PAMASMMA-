"""TikTok Content Posting API adapter."""
from typing import Any

from app.social.contracts import Capability, Platform, PublishCommand
from app.social.providers.common import provider_error as _provider_error
from app.social.providers.oauth import OAuthRestProvider


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

    async def discover_accounts(self, token: str) -> list[dict[str, Any]]:
        """Discover the TikTok user who authorized PAMASMMA."""
        response = await self.request(
            "GET",
            "https://open.tiktokapis.com/v2/user/info/",
            token=token,
            params={"fields": "open_id,union_id,display_name,avatar_url"},
        )
        user = (response.get("data") or {}).get("user") or response.get("data") or {}
        external_id = user.get("open_id") or user.get("union_id")
        if not external_id:
            return []
        return [{"external_account_id": str(external_id), "display_name": user.get("display_name")}]

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
                    "title": command.title or command.text[:150],
                    "description": command.text,
                    "privacy_level": privacy,
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "photo_cover_index": 0,
                    "photo_images": [str(command.media_url)],
                },
                "post_mode": "DIRECT_POST",
                "media_type": "PHOTO",
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

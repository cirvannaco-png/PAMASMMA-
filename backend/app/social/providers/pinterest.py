"""Pinterest platform adapter."""
from typing import Any
from app.social.contracts import Capability, Platform, PublishCommand
from app.social.providers.oauth import OAuthRestProvider
from app.social.providers.common import provider_error
class PinterestProvider(OAuthRestProvider):
    """Pinterest organic content adapter."""

    platform = Platform.PINTEREST
    capabilities = frozenset({Capability.PUBLISH})
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
"""Pinterest platform adapter."""
import base64
from typing import Any

from app.social.contracts import Capability, Platform, PublishCommand
from app.social.providers.common import _env
from app.social.providers.common import provider_error as _provider_error
from app.social.providers.oauth import OAuthRestProvider


class PinterestProvider(OAuthRestProvider):
    """Pinterest organic content and ads adapter."""

    platform = Platform.PINTEREST
    capabilities = frozenset(
        {
            Capability.PUBLISH,
            Capability.ADS_READ,
            Capability.ADS_WRITE,
        }
    )
    auth_url = "https://www.pinterest.com/oauth/"
    token_url = "https://api.pinterest.com/v5/oauth/token"
    client_id_env = "SOCIAL_PINTEREST_APP_ID"
    client_secret_env = "SOCIAL_PINTEREST_APP_SECRET"
    redirect_env = "SOCIAL_PINTEREST_REDIRECT_URI"
    scope_env = "SOCIAL_PINTEREST_SCOPES"

    def _basic_auth_header(self) -> str:
        client_id = _env(self.client_id_env)
        secret = _env(self.client_secret_env)
        if not client_id or not secret:
            raise _provider_error(
                self.platform,
                "oauth_not_configured",
                "Pinterest OAuth credentials are not configured.",
                503,
            )
        encoded = base64.b64encode(
            f"{client_id}:{secret}".encode()
        ).decode("ascii")
        return f"Basic {encoded}"

    async def exchange_code(
        self,
        code: str,
        state: str | None = None,
    ) -> dict[str, Any]:
        del state
        redirect_uri = _env(self.redirect_env)
        if not redirect_uri:
            raise _provider_error(
                self.platform,
                "oauth_not_configured",
                "Pinterest OAuth redirect URI is not configured.",
                503,
            )
        return await self.request(
            "POST",
            self.token_url,
            data={
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={
                "Authorization": self._basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        return await self.request(
            "POST",
            self.token_url,
            data={
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={
                "Authorization": self._basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

    async def discover_accounts(self, token: str) -> list[dict[str, Any]]:
        """Discover the Pinterest account represented by the OAuth token."""
        response = await self.request(
            "GET",
            "https://api.pinterest.com/v5/user_account",
            token=token,
        )
        if not response.get("id"):
            return []
        return [
            {
                "external_account_id": str(response["id"]),
                "display_name": response.get("business_name")
                or response.get("username"),
            }
        ]

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
        board_id = command.platform_options.get("board_id")
        if not board_id:
            raise _provider_error(
                self.platform,
                "board_required",
                "Pinterest publishing requires platform_options.board_id.",
                422,
            )
        return await self.request(
            "POST",
            "https://api.pinterest.com/v5/pins",
            token=token,
            json_body={
                "board_id": board_id,
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

    async def create_campaign(
        self,
        token: str,
        account_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        campaign = {
            "name": payload["name"],
            "objective_type": payload["objective"],
            "status": "PAUSED",
        }
        if payload.get("daily_budget") is not None:
            campaign["daily_spend_cap"] = int(
                float(payload["daily_budget"]) * 1_000_000
            )
        provider_options = payload.get("provider_options") or {}
        campaign.update(provider_options)
        return await self.request(
            "POST",
            f"https://api.pinterest.com/v5/ad_accounts/{account_id}/campaigns",
            token=token,
            json_body=[campaign],
        )

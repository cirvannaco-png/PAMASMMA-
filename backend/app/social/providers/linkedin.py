"""LinkedIn platform adapter."""
from typing import Any

from app.social.contracts import Capability, Platform, PublishCommand, ReplyCommand
from app.social.providers.common import _env, provider_error
from app.social.providers.oauth import OAuthRestProvider


class LinkedInProvider(OAuthRestProvider):
    """LinkedIn posts and comment actions adapter."""

    platform = Platform.LINKEDIN
    capabilities = frozenset(
        {
            Capability.PUBLISH,
            Capability.COMMENTS_READ,
            Capability.COMMENTS_WRITE,
            Capability.ADS_READ,
            Capability.ADS_WRITE,
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
            "Linkedin-Version": _env("SOCIAL_LINKEDIN_VERSION"),
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

    async def create_campaign(
        self,
        token: str,
        account_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        version = _env("SOCIAL_LINKEDIN_VERSION")
        if not version:
            raise provider_error(
                self.platform,
                "api_version_not_configured",
                "SOCIAL_LINKEDIN_VERSION must be configured.",
                503,
            )
        provider_options = dict(payload.get("provider_options") or {})
        campaign_group = provider_options.pop("campaign_group", None)
        if not campaign_group:
            raise provider_error(
                self.platform,
                "campaign_group_required",
                "LinkedIn campaigns require provider_options.campaign_group.",
                422,
            )
        budget = payload.get("daily_budget") or payload.get("lifetime_budget")
        body = {
            "account": f"urn:li:sponsoredAccount:{account_id}",
            "name": payload["name"],
            "campaignGroup": campaign_group,
            "type": provider_options.pop("type", "SPONSORED_UPDATES"),
            "costType": provider_options.pop("costType", "CPC"),
            "status": "PAUSED",
        }
        if budget is not None:
            body["dailyBudget"] = {
                "amount": str(budget),
                "currencyCode": payload.get("currency", "USD"),
            }
        body.update(provider_options)
        return await self.request(
            "POST",
            f"https://api.linkedin.com/rest/adAccounts/{account_id}/adCampaigns",
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

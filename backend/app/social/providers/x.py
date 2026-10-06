"""X platform adapter."""
import base64
import hashlib
from typing import Any

from app.social.contracts import Capability, Platform, PublishCommand, ReplyCommand
from app.social.providers.common import _env
from app.social.providers.common import provider_error as _provider_error
from app.social.providers.oauth import OAuthRestProvider


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

    async def discover_accounts(self, token: str) -> list[dict[str, Any]]:
        """Discover the X user who authorized PAMASMMA."""
        response = await self.request(
            "GET",
            "https://api.x.com/2/users/me",
            token=token,
            params={"user.fields": "name,username,profile_image_url"},
        )
        user = response.get("data") or {}
        if not user.get("id"):
            return []
        return [{"external_account_id": str(user["id"]), "display_name": user.get("name") or user.get("username")}]

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

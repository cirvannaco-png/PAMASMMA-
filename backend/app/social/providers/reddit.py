"""Reddit platform adapter."""
import base64
from typing import Any

from app.social.contracts import Capability, Platform, PublishCommand, ReplyCommand
from app.social.providers.common import _env
from app.social.providers.common import provider_error as _provider_error
from app.social.providers.oauth import OAuthRestProvider


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

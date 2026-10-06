"""Threads platform adapter."""
from typing import Any

from app.social.contracts import Capability, Platform, PublishCommand, ReplyCommand
from app.social.providers.oauth import OAuthRestProvider


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

    async def discover_accounts(self, token: str) -> list[dict[str, Any]]:
        """Discover the Threads profile that authorized PAMASMMA."""
        response = await self.request(
            "GET",
            "https://graph.threads.net/v1.0/me",
            token=token,
            params={"fields": "id,username,name"},
        )
        if not response.get("id"):
            return []
        return [{"external_account_id": str(response["id"]), "display_name": response.get("name") or response.get("username")}]

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

"""Provider-neutral social execution contract."""
from typing import Any

from app.social.contracts import (
    Capability,
    Platform,
    PublishCommand,
    ReplyCommand,
    SocialProviderError,
    UnsupportedCapability,
)


class SocialProvider:
    """Stable interface implemented by each external platform adapter."""

    platform: Platform
    capabilities: frozenset[Capability] = frozenset()
    timeout: float = 30.0

    def require(self, capability: Capability) -> None:
        if capability not in self.capabilities:
            raise UnsupportedCapability(self.platform, capability)

    def authorization_url(
        self,
        state: str,
        *,
        code_challenge: str | None = None,
    ) -> str:
        del code_challenge
        raise NotImplementedError

    async def exchange_code(
        self,
        code: str,
        state: str | None = None,
        *,
        code_verifier: str | None = None,
    ) -> dict[str, Any]:
        del state, code_verifier
        raise NotImplementedError

    async def discover_accounts(self, token: str) -> list[dict[str, Any]]:
        """Return accounts the authorized user can connect on this platform."""
        del token
        raise SocialProviderError(
            self.platform,
            "account_discovery_not_supported",
            "This provider cannot discover connectable accounts automatically.",
            422,
        )

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        raise SocialProviderError(
            self.platform,
            "refresh_not_supported",
            "Token refresh is not supported by this adapter.",
            422,
        )

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        self.require(Capability.PUBLISH)
        raise NotImplementedError

    async def reply(
        self,
        token: str,
        command: ReplyCommand,
    ) -> dict[str, Any]:
        self.require(Capability.COMMENTS_WRITE)
        raise NotImplementedError

    async def list_engagement(
        self,
        token: str,
        external_account_id: str,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        self.require(Capability.COMMENTS_READ)
        raise NotImplementedError

    async def analytics(
        self,
        token: str,
        external_account_id: str,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        self.require(Capability.ANALYTICS)
        raise NotImplementedError

    async def create_campaign(
        self,
        token: str,
        account_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self.require(Capability.ADS_WRITE)
        raise NotImplementedError

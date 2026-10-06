"""Telegram and WhatsApp messaging adapters."""
from app.social.contracts import Capability, Platform, PublishCommand
from app.social.providers.base import SocialProvider
from app.social.providers.common import _env, provider_error
from app.social.providers.http import HttpProvider
class TelegramProvider(SocialProvider, HttpProvider):
    def __init__(self) -> None:
        HttpProvider.__init__(self, self.platform)
    """Telegram Bot API messaging adapter."""

    platform = Platform.TELEGRAM
    capabilities = frozenset({Capability.PUBLISH, Capability.COMMENTS_READ, Capability.COMMENTS_WRITE})

    def authorization_url(self, state: str) -> str:
        del state
        raise _provider_error(
            self.platform,
            "oauth_not_applicable",
            "Telegram uses a bot token rather than user OAuth.",
            422,
        )

    async def exchange_code(
        self,
        code: str,
        state: str | None = None,
    ) -> dict[str, Any]:
        del code, state
        raise _provider_error(
            self.platform,
            "oauth_not_applicable",
            "Telegram uses a bot token rather than user OAuth.",
            422,
        )

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            f"https://api.telegram.org/bot{token}/sendMessage",
            json_body={
                "chat_id": external_account_id,
                "text": command.text,
            },
        )

class WhatsAppProvider(SocialProvider, HttpProvider):
    def __init__(self) -> None:
        HttpProvider.__init__(self, self.platform)
    """WhatsApp Cloud API text messaging adapter."""

    platform = Platform.WHATSAPP
    capabilities = frozenset({Capability.PUBLISH, Capability.COMMENTS_WRITE})

    def authorization_url(self, state: str) -> str:
        del state
        raise _provider_error(
            self.platform,
            "oauth_not_applicable",
            "WhatsApp Business uses Meta business configuration.",
            422,
        )

    async def exchange_code(
        self,
        code: str,
        state: str | None = None,
    ) -> dict[str, Any]:
        del code, state
        raise _provider_error(
            self.platform,
            "oauth_not_applicable",
            "Use Meta Business configuration for WhatsApp.",
            422,
        )

    async def publish(
        self,
        token: str,
        command: PublishCommand,
        external_account_id: str,
    ) -> dict[str, Any]:
        version = _env("SOCIAL_META_GRAPH_VERSION")
        if not version:
            raise _provider_error(
                self.platform,
                "api_version_not_configured",
                "SOCIAL_META_GRAPH_VERSION must be configured.",
                503,
            )
        recipient = command.platform_options.get("to")
        if not recipient:
            raise _provider_error(
                self.platform,
                "recipient_required",
                "WhatsApp publishing requires platform_options.to.",
                422,
            )
        return await self.request(
            "POST",
            f"https://graph.facebook.com/{version}/{external_account_id}/messages",
            token=token,
            json_body={
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"body": command.text},
            },
        )


PROVIDERS: dict[Platform, SocialProvider] = {
    Platform.FACEBOOK: MetaProvider(),
    Platform.INSTAGRAM: InstagramProvider(),
    Platform.TIKTOK: TikTokProvider(),
    Platform.YOUTUBE: YouTubeProvider(),
    Platform.LINKEDIN: LinkedInProvider(),
    Platform.X: XProvider(),
    Platform.THREADS: ThreadsProvider(),
    Platform.PINTEREST: PinterestProvider(),
    Platform.REDDIT: RedditProvider(),
    Platform.TELEGRAM: TelegramProvider(),
    Platform.WHATSAPP: WhatsAppProvider(),
}


def get_provider(platform: Platform) -> SocialProvider:
    return PROVIDERS[platform]
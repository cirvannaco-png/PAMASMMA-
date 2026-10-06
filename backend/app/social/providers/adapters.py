"""Provider registry and compatibility boundary."""
from app.social.contracts import Platform
from app.social.providers.linkedin import LinkedInProvider
from app.social.providers.messaging import TelegramProvider, WhatsAppProvider
from app.social.providers.meta import InstagramProvider, MetaProvider
from app.social.providers.pinterest import PinterestProvider
from app.social.providers.reddit import RedditProvider
from app.social.providers.threads import ThreadsProvider
from app.social.providers.tiktok import TikTokProvider
from app.social.providers.x import XProvider
from app.social.providers.youtube import YouTubeProvider

PROVIDERS = {
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


def get_provider(platform: Platform):
    return PROVIDERS[platform]

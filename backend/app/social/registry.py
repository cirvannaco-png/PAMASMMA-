"""Platform registry and capability discovery."""
from app.social.contracts import Platform
from app.social.providers.base import SocialProvider

class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[Platform, SocialProvider] = {}
    def register(self, provider: SocialProvider) -> None:
        self._providers[provider.platform] = provider
    def get(self, platform: Platform) -> SocialProvider:
        try: return self._providers[platform]
        except KeyError as exc: raise KeyError(f"Unsupported platform: {platform.value}") from exc
    def describe(self) -> list[dict]:
        return [{"platform": p.value, "capabilities": sorted(c.value for c in provider.capabilities)} for p, provider in self._providers.items()]

"""Provider selection and failover policy."""
import logging

from app.config import get_settings
from app.intelligence.providers.kernel import KernelProvider
from app.intelligence.providers.openai_compatible import OpenAICompatibleProvider

log = logging.getLogger(__name__)


def get_model_provider():
    settings = get_settings()
    provider = settings.model_provider.lower()

    if provider in {"kernel", "local"}:
        return KernelProvider()

    if provider in {"openai-compatible", "ollama"}:
        return OpenAICompatibleProvider()

    if provider == "anthropic":
        from app.intelligence.providers.anthropic import AnthropicProvider
        return AnthropicProvider()

    if provider == "hybrid":
        if settings.model_api_base_url:
            try:
                return OpenAICompatibleProvider()
            except Exception:
                log.exception("OpenAI-compatible provider unavailable; using kernel")
        return KernelProvider()

    raise ValueError(f"Unsupported MODEL_PROVIDER: {settings.model_provider!r}")

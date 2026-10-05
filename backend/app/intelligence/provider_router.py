"""Task-aware model provider routing with deterministic failover."""
from dataclasses import dataclass

from app.config import get_settings
from app.intelligence.contracts import Sensitivity, TaskComplexity
from app.intelligence.providers.kernel import KernelProvider


@dataclass(frozen=True)
class ProviderSelection:
    name: str
    provider: object


class ProviderRouter:
    def select(
        self,
        complexity: TaskComplexity,
        sensitivity: Sensitivity,
    ) -> ProviderSelection:
        settings = get_settings()
        configured = settings.model_provider.lower()

        # Sensitive requests stay in-process unless an explicitly local provider is chosen.
        if sensitivity == Sensitivity.SENSITIVE and configured not in {"kernel", "local", "ollama"}:
            return ProviderSelection("kernel", KernelProvider())

        if configured == "hybrid":
            candidates = (
                ["anthropic", "openai-compatible", "kernel"]
                if complexity in {TaskComplexity.COMPLEX, TaskComplexity.STRATEGIC}
                else ["openai-compatible", "kernel"]
            )
        elif configured in {"local", "kernel"}:
            candidates = ["kernel"]
        else:
            candidates = [configured, "kernel"]

        for candidate in candidates:
            try:
                provider = self._instantiate(candidate)
                return ProviderSelection(candidate, provider)
            except Exception:
                continue
        return ProviderSelection("kernel", KernelProvider())

    @staticmethod
    def _instantiate(name: str):
        if name in {"kernel", "local"}:
            return KernelProvider()
        if name in {"openai-compatible", "ollama"}:
            from app.intelligence.providers.openai_compatible import OpenAICompatibleProvider
            return OpenAICompatibleProvider()
        if name == "anthropic":
            from app.intelligence.providers.anthropic import AnthropicProvider
            return AnthropicProvider()
        raise ValueError(f"Unsupported provider {name!r}")

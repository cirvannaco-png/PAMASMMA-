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

        if (
            sensitivity == Sensitivity.SENSITIVE
            and not settings.intelligence_cloud_for_sensitive
            and configured not in {"kernel", "local", "ollama"}
        ):
            return ProviderSelection("kernel", KernelProvider())

        if configured == "hybrid":
            candidates = (
                ["anthropic", "openai-compatible", "kernel"]
                if complexity in {
                    TaskComplexity.COMPLEX,
                    TaskComplexity.STRATEGIC,
                }
                else ["openai-compatible", "kernel"]
            )
        elif configured in {"local", "kernel"}:
            candidates = ["kernel"]
        else:
            candidates = [configured, "kernel"]

        for candidate in candidates:
            try:
                return ProviderSelection(
                    candidate,
                    self._instantiate(candidate),
                )
            except Exception:
                continue

        return ProviderSelection(
            "kernel",
            KernelProvider(),
        )

    async def generate(
        self,
        selection: ProviderSelection,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int,
    ) -> tuple[ProviderSelection, str]:
        """Generate with runtime failover.

        Provider construction and provider availability are different failure
        classes. A configured remote provider can still fail at request time,
        so generation falls back to the deterministic kernel.
        """
        try:
            response = await selection.provider.generate(
                system_prompt,
                messages,
                max_tokens,
            )
            return selection, response
        except Exception:
            if selection.name == "kernel":
                raise
            fallback = ProviderSelection(
                "kernel",
                KernelProvider(),
            )
            response = await fallback.provider.generate(
                system_prompt,
                messages,
                max_tokens,
            )
            return fallback, response

    @staticmethod
    def _instantiate(name: str):
        if name in {"kernel", "local"}:
            return KernelProvider()
        if name in {"openai-compatible", "ollama"}:
            from app.intelligence.providers.openai_compatible import (
                OpenAICompatibleProvider,
            )
            return OpenAICompatibleProvider()
        if name == "anthropic":
            from app.intelligence.providers.anthropic import AnthropicProvider
            return AnthropicProvider()
        raise ValueError(f"Unsupported provider {name!r}")

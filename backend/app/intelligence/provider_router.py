"""Task-aware model provider routing with deterministic ordered failover."""
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from typing import Protocol

from app.config import get_settings
from app.intelligence.contracts import Sensitivity, TaskComplexity
from app.intelligence.providers.kernel import KernelProvider


class Provider(Protocol):
    async def generate(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int,
    ) -> str: ...


@dataclass(frozen=True)
class ProviderSelection:
    name: str
    provider: Provider
    # Remote candidates to try next if this provider errors at request time.
    # If all remote candidates fail, the deterministic kernel is last.
    fallbacks: tuple["ProviderSelection", ...] = field(default=())


def _split_models(raw: str | None) -> list[str]:
    """Parse a comma-separated model list, removing blanks and duplicates."""
    result: list[str] = []
    seen: set[str] = set()
    for value in (raw or "").split(","):
        model = value.strip()
        if model and model not in seen:
            seen.add(model)
            result.append(model)
    return result


class ProviderRouter:
    def select(
        self,
        complexity: TaskComplexity,
        sensitivity: Sensitivity,
    ) -> ProviderSelection:
        settings = get_settings()
        configured = settings.model_provider.strip().lower()
        heavy = complexity in {TaskComplexity.COMPLEX, TaskComplexity.STRATEGIC}

        # Sensitive material must never leave the app unless the explicit
        # opt-in setting is enabled. This applies to every remote provider,
        # including the multi-model pool.
        if (
            sensitivity == Sensitivity.SENSITIVE
            and not settings.intelligence_cloud_for_sensitive
            and configured not in {"kernel", "local", "ollama"}
        ):
            return ProviderSelection("kernel", KernelProvider())

        candidates: list[tuple[str, Callable[[], Provider]]] = []
        if configured == "pool":
            fast = _split_models(getattr(settings, "model_pool_fast", ""))
            deep = _split_models(getattr(settings, "model_pool_deep", ""))
            ordered = [*deep, *fast] if heavy else [*fast, *deep]
            candidates = [
                (f"pool:{model}", partial(self._instantiate_pool, model))
                for model in ordered
            ]
        elif configured == "hybrid":
            names = (
                ["anthropic", "openai-compatible"]
                if heavy
                else ["openai-compatible", "anthropic"]
            )
            candidates = [(name, partial(self._instantiate, name)) for name in names]
        elif configured in {"kernel", "local"}:
            return ProviderSelection("kernel", KernelProvider())
        else:
            candidates = [(configured, partial(self._instantiate, configured))]

        built: list[ProviderSelection] = []
        for name, factory in candidates:
            try:
                built.append(ProviderSelection(name, factory()))
            except Exception:
                # A missing SDK/configuration for one provider must not block
                # the next provider in the deterministic priority order.
                continue

        if not built:
            return ProviderSelection("kernel", KernelProvider())
        return ProviderSelection(
            built[0].name,
            built[0].provider,
            tuple(built[1:]),
        )

    async def generate(
        self,
        selection: ProviderSelection,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int,
    ) -> tuple[ProviderSelection, str]:
        """Try selected provider, ordered fallbacks, then the local kernel."""
        chain = [
            ProviderSelection(selection.name, selection.provider),
            *selection.fallbacks,
        ]
        for index, candidate in enumerate(chain):
            try:
                response = await candidate.provider.generate(
                    system_prompt,
                    messages,
                    max_tokens,
                )
            except Exception:
                # A kernel failure is not silently swallowed or retried forever.
                if candidate.name == "kernel":
                    raise
                continue

            if index == 0:
                return selection, response

            # Return the successful provider plus only the still-untried
            # providers. The next call performs fresh task-aware selection.
            return (
                ProviderSelection(
                    candidate.name,
                    candidate.provider,
                    tuple(chain[index + 1:]),
                ),
                response,
            )

        kernel = ProviderSelection("kernel", KernelProvider())
        response = await kernel.provider.generate(
            system_prompt,
            messages,
            max_tokens,
        )
        return kernel, response

    @staticmethod
    def _instantiate_pool(model: str) -> Provider:
        from app.intelligence.providers.openai_compatible import (
            OpenAICompatibleProvider,
        )
        # Avoid SDK-level retries: trying the next model is the router's retry.
        return OpenAICompatibleProvider(model=model, max_retries=0)

    @staticmethod
    def _instantiate(name: str) -> Provider:
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

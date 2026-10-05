"""
Provider-neutral model contract.
Cognitive systems depend on this interface, never on a model vendor SDK.
"""
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class ModelProvider(ABC):
    """Contract for text-generation providers."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int,
    ) -> str:
        ...

    @abstractmethod
    async def stream(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        yield ""

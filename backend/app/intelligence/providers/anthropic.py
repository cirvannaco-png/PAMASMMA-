"""Optional Anthropic adapter. Imported only when selected."""
from collections.abc import AsyncGenerator
from typing import Any, cast

import anthropic

from app.config import get_settings


class AnthropicProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.anthropic_timeout_seconds,
        )
        self.model = settings.anthropic_model

    async def generate(self, system_prompt: str, messages: list[dict], max_tokens: int) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=cast(Any, messages),
        )
        return next((block.text for block in response.content if hasattr(block, "text")), "")

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        async with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=cast(Any, messages),
        ) as stream:
            async for text in stream.text_stream:
                yield text

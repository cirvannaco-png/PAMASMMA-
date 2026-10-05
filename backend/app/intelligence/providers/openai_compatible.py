"""Optional OpenAI-compatible adapter for Ollama/local or hosted endpoints."""
from collections.abc import AsyncGenerator
from typing import Any, AsyncIterator, cast

from openai import AsyncOpenAI

from app.config import get_settings


class OpenAICompatibleProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.model_api_base_url:
            raise RuntimeError("MODEL_API_BASE_URL is not configured.")
        self.client = AsyncOpenAI(
            api_key=(settings.model_api_key.get_secret_value() if settings.model_api_key else "local"),
            base_url=settings.model_api_base_url.rstrip("/") + "/",
        )
        self.model = settings.model_name

    async def generate(self, system_prompt: str, messages: list[dict], max_tokens: int) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        return response.choices[0].message.content or ""

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system_prompt}, *messages],
            stream=True,
        )
        async for event in cast(AsyncIterator[Any], stream):
            chunk = event.choices[0].delta.content if event.choices else None
            if chunk:
                yield chunk

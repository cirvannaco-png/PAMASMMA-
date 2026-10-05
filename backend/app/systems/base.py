"""
PAMASMMA v4.0.1 — Cognitive System Base
All 10 systems inherit from CognitiveSystem.
Handles Anthropic calls, memory retrieval, event emission, personality and
token budgeting.
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import AsyncGenerator

import anthropic

from app.config import get_settings
from app.database import pg_event_bus
from app.embeddings.service import retrieve_relevant_memories

log = logging.getLogger(__name__)
settings = get_settings()

_anthropic = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

PERSONALITY_CLAUSE = f"""
PERSONALITY BASELINE (non-negotiable, enforce in every response):
- Assertiveness: {settings.personality_assertiveness} — direct, decisive, no fake certainty
- Verbosity: {settings.personality_verbosity} — dense but not bloated
- Formality: {settings.personality_formality} — professional, not academic
- Strategic Depth: {settings.personality_strategic_depth} — operate above the immediate question

Identity principal: PAMASMMA founder principal.
Operating context: founder operations, marketing, content, customer support and strategy.
""".strip()


class CognitiveSystem(ABC):
    """Base contract for each governed cognitive system."""

    @property
    @abstractmethod
    def system_id(self) -> str:
        ...

    @property
    @abstractmethod
    def system_name(self) -> str:
        ...

    @property
    @abstractmethod
    def directive(self) -> str:
        ...

    def build_system_prompt(self, memory_context: str = "") -> str:
        parts = [
            f"You are PAMASMMA {self.system_id} — {self.system_name}.",
            self.directive,
            PERSONALITY_CLAUSE,
        ]
        if memory_context:
            parts.append(f"\nRELEVANT MEMORY CONTEXT:\n{memory_context}")
        return "\n\n".join(parts)

    async def invoke(
        self,
        messages: list[dict],
        user_id: str,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        start = time.perf_counter()

        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        )
        memory_context = await retrieve_relevant_memories(
            query=last_user_msg,
            user_id=user_id,
            system_id=self.system_id,
            limit=5,
        )

        system_prompt = self.build_system_prompt(memory_context)

        if stream:
            return self._stream(system_prompt, messages, user_id, start)

        response = await _anthropic.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            system=system_prompt,
            messages=messages,
        )
        content = response.content[0].text
        elapsed = (time.perf_counter() - start) * 1000

        await self._post_invoke(user_id, last_user_msg, content, elapsed)
        return content

    async def _stream(
        self,
        system_prompt: str,
        messages: list[dict],
        user_id: str,
        start: float,
    ) -> AsyncGenerator[str, None]:
        full_response: list[str] = []
        async with _anthropic.messages.stream(
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                full_response.append(text)
                yield text

        elapsed = (time.perf_counter() - start) * 1000
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        )
        await self._post_invoke(
            user_id,
            last_user_msg,
            "".join(full_response),
            elapsed,
        )

    async def _post_invoke(
        self,
        user_id: str,
        query: str,
        response: str,
        latency_ms: float,
    ) -> None:
        try:
            await pg_event_bus.publish(
                channel="cognitive_invocation",
                payload={
                    "system_id": self.system_id,
                    "system_name": self.system_name,
                    "user_id": user_id,
                    "query_preview": query[:120],
                    "latency_ms": round(latency_ms, 2),
                },
            )
        except Exception:
            log.exception("Event emission failed for %s", self.system_id)

        try:
            from app.embeddings.service import store_memory

            await store_memory(
                user_id=user_id,
                system_id=self.system_id,
                content=f"Q: {query}\n\nA: {response}",
            )
        except Exception:
            log.exception("Memory storage failed for %s", self.system_id)

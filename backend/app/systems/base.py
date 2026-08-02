"""
PAMASMMA v4 — Cognitive System Base
All 10 systems (S1–S10) inherit from CognitiveSystem.
Handles: Anthropic API calls, pgvector memory retrieval,
         event emission, personality enforcement, token budgeting.
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import AsyncGenerator

import anthropic

from app.config import get_settings
from app.embeddings.service import embed_text, retrieve_relevant_memories
from app.database import pg_event_bus

log = logging.getLogger(__name__)
settings = get_settings()

_anthropic = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

# ── Personality enforcement clause injected into every system prompt ──────────
PERSONALITY_CLAUSE = f"""
PERSONALITY BASELINE (non-negotiable, enforce in every response):
- Assertiveness: {settings.personality_assertiveness}  — direct, unwavering, no hedging
- Verbosity: {settings.personality_verbosity}          — dense but not bloated
- Formality: {settings.personality_formality}          — professional, not academic
- Strategic Depth: {settings.personality_strategic_depth} — always operate two levels above the question

Identity principal: Kelson Mwangi, founder of Cirvanna — "infrastructure of identity"
Location: Nakuru, Kenya. Operating context: fashion-tech, East Africa + global.
""".strip()


class CognitiveSystem(ABC):
    """
    Abstract base for all PAMASMMA cognitive systems.
    Each system defines its own identity, directive, and scope.
    """

    @property
    @abstractmethod
    def system_id(self) -> str:
        """e.g. 'S1', 'S4'"""
        ...

    @property
    @abstractmethod
    def system_name(self) -> str:
        """e.g. 'Executive Operations'"""
        ...

    @property
    @abstractmethod
    def directive(self) -> str:
        """Core system prompt defining the cognitive role."""
        ...

    def build_system_prompt(self, memory_context: str = "") -> str:
        """Assemble final system prompt with personality and memory."""
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
        """
        Invoke the cognitive system with conversation history.
        Retrieves relevant memories from pgvector before calling the LLM.
        Emits a pg_notify event after each invocation.
        """
        start = time.perf_counter()

        # Retrieve relevant memories from pgvector
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
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
        full_response = []
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
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        await self._post_invoke(user_id, last_user_msg, "".join(full_response), elapsed)

    async def _post_invoke(
        self,
        user_id: str,
        query: str,
        response: str,
        latency_ms: float,
    ) -> None:
        """Emit event and store memory asynchronously after each invocation."""
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
        except Exception as exc:
            log.warning(f"Event emission failed for {self.system_id}: {exc}")

        # Store interaction as a memory embedding (non-blocking)
        try:
            from app.embeddings.service import store_memory
            await store_memory(
                user_id=user_id,
                system_id=self.system_id,
                content=f"Q: {query}\n\nA: {response}",
            )
        except Exception as exc:
            log.warning(f"Memory storage failed for {self.system_id}: {exc}")

"""
PAMASMMA v4.1 — Cognitive System Base
Cognitive systems are domain identities; model selection and infrastructure are
owned by the intelligence layer.
"""
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.config import get_settings
from app.database import pg_event_bus
from app.embeddings.service import retrieve_relevant_memories
from app.intelligence.evaluator import ResponseEvaluator
from app.intelligence.registry import get_model_provider

log = logging.getLogger(__name__)
settings = get_settings()
_provider = get_model_provider()

PERSONALITY_CLAUSE = f"""
PERSONALITY BASELINE:
- Assertiveness: {settings.personality_assertiveness}
- Verbosity: {settings.personality_verbosity}
- Formality: {settings.personality_formality}
- Strategic depth: {settings.personality_strategic_depth}
Operate decisively, distinguish facts from assumptions, and expose uncertainty
when evidence is insufficient.
""".strip()


class CognitiveSystem(ABC):
    """Stable domain contract implemented by S1–S10."""

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
            parts.append("RELEVANT MEMORY CONTEXT:\n" + memory_context)
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
            last_user_msg,
            user_id,
            self.system_id,
            limit=5,
        )
        prompt = self.build_system_prompt(memory_context)

        if stream:
            return self._stream(prompt, messages, user_id, start)

        raw_response = await _provider.generate(
            prompt,
            messages,
            settings.model_max_tokens,
        )
        response = ResponseEvaluator.validate(raw_response)
        await self._post_invoke(user_id, last_user_msg, response, (time.perf_counter() - start) * 1000)
        return response

    async def _stream(
        self,
        prompt: str,
        messages: list[dict],
        user_id: str,
        start: float,
    ) -> AsyncGenerator[str, None]:
        chunks: list[str] = []
        async for chunk in _provider.stream(
            prompt,
            messages,
            settings.anthropic_max_tokens,
        ):
            chunks.append(chunk)
            yield chunk

        response = ResponseEvaluator.validate("".join(chunks))
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        )
        await self._post_invoke(
            user_id,
            last_user_msg,
            response,
            (time.perf_counter() - start) * 1000,
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

"""
PAMASMMA v4.2 — Cognitive System Base
Cognitive systems are domain identities; the intelligence engine owns
context, routing, memory, verification and provider selection.
"""
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.config import get_settings
from app.database import pg_event_bus

log = logging.getLogger(__name__)
settings = get_settings()

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

    def build_system_prompt(
        self,
        memory_context: str = "",
    ) -> str:
        """Backward-compatible prompt helper for external integrations."""
        parts = [
            f"You are PAMASMMA {self.system_id} — {self.system_name}.",
            self.directive,
            PERSONALITY_CLAUSE,
        ]
        if memory_context:
            parts.append(
                "RELEVANT MEMORY CONTEXT:\n"
                + memory_context
            )
        return "\n\n".join(parts)

    async def invoke(
        self,
        messages: list[dict],
        user_id: str,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        start = time.perf_counter()
        from app.intelligence.engine import CognitiveEngine

        engine = CognitiveEngine()
        if stream:
            return self._stream(
                engine,
                messages,
                user_id,
                start,
            )

        result = await engine.run(
            self,
            messages,
            user_id,
        )
        await self._post_invoke(
            user_id=user_id,
            query=self._last_user_message(messages),
            response=result.response,
            latency_ms=(
                time.perf_counter() - start
            ) * 1000,
            trace=result.trace.model_dump(
                mode="json"
            ),
        )
        return result.response

    async def _stream(
        self,
        engine,
        messages: list[dict],
        user_id: str,
        start: float,
    ) -> AsyncGenerator[str, None]:
        chunks: list[str] = []
        async for chunk in engine.stream(
            self,
            messages,
            user_id,
        ):
            chunks.append(chunk)
            yield chunk

        response = "".join(chunks).strip()
        trace = (
            engine.last_result.trace.model_dump(
                mode="json"
            )
            if engine.last_result is not None
            else None
        )
        await self._post_invoke(
            user_id=user_id,
            query=self._last_user_message(messages),
            response=response,
            latency_ms=(
                time.perf_counter() - start
            ) * 1000,
            trace=trace,
        )

    async def _post_invoke(
        self,
        user_id: str,
        query: str,
        response: str,
        latency_ms: float,
        trace: dict | None = None,
    ) -> None:
        payload = {
            "system_id": self.system_id,
            "system_name": self.system_name,
            "user_id": user_id,
            "query_preview": query[:120],
            "latency_ms": round(
                latency_ms,
                2,
            ),
        }

        if trace:
            verification = (
                trace.get("verification")
                if isinstance(trace, dict)
                else None
            )
            payload.update(
                {
                    "decision_id": trace.get(
                        "decision_id"
                    ),
                    "confidence": trace.get(
                        "confidence"
                    ),
                    "provider": trace.get(
                        "provider"
                    ),
                    "routed_systems": trace.get(
                        "routed_systems",
                        [],
                    ),
                    "verification_score": (
                        verification.get("score")
                        if isinstance(
                            verification,
                            dict,
                        )
                        else None
                    ),
                    "evidence_status": trace.get(
                        "evidence_status"
                    ),
                }
            )

        try:
            await pg_event_bus.publish(
                channel="cognitive_invocation",
                payload=payload,
            )
        except Exception:
            log.exception(
                "Event emission failed for %s",
                self.system_id,
            )

        try:
            from app.embeddings.service import store_memory

            await store_memory(
                user_id=user_id,
                system_id=self.system_id,
                content=(
                    f"Q: {query}\n\n"
                    f"A: {response}"
                ),
                metadata={
                    "memory_type": "episodic",
                    "importance": 0.7,
                    "reliability": (
                        trace.get(
                            "verification",
                            {},
                        ).get("score", 0.8)
                        if trace
                        else 0.8
                    ),
                    "outcome_relevance": 0.8,
                    "decision_id": (
                        trace.get("decision_id")
                        if trace
                        else None
                    ),
                    "confidence": (
                        trace.get("confidence")
                        if trace
                        else 0.5
                    ),
                },
            )
        except Exception:
            log.exception(
                "Memory storage failed for %s",
                self.system_id,
            )

    @staticmethod
    def _last_user_message(
        messages: list[dict],
    ) -> str:
        return next(
            (
                m["content"]
                for m in reversed(messages)
                if m["role"] == "user"
            ),
            "",
        )

"""
PAMASMMA Intelligence Kernel.

Deterministic fallback used when no external model is configured. It performs
intent extraction, prioritization, constraint detection and response synthesis.
It is deliberately transparent: no hidden network dependency exists.
"""
import re
from collections.abc import AsyncGenerator


class IntelligenceKernel:
    """Small, deterministic reasoning engine for no-key deployments."""

    _STOPWORDS = {
        "the", "and", "for", "with", "that", "this", "what", "should",
        "would", "could", "from", "into", "your", "have", "about", "there",
        "which", "when", "where", "why", "how", "are", "you", "can",
    }

    @classmethod
    def _keywords(cls, text: str) -> list[str]:
        words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", text.lower())
        ranked: dict[str, int] = {}
        for word in words:
            if word in cls._STOPWORDS:
                continue
            ranked[word] = ranked.get(word, 0) + 1
        return [
            word for word, _count in
            sorted(ranked.items(), key=lambda item: (-item[1], item[0]))
        ][:8]

    @classmethod
    def reason(
        cls,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int,
    ) -> str:
        user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        ).strip()
        previous = next(
            (m["content"] for m in reversed(messages) if m["role"] == "assistant"),
            "",
        ).strip()
        keywords = cls._keywords(user)

        if not user:
            return "No actionable user objective was supplied. State the decision or outcome required."

        system_name = system_prompt.split("\n", 1)[0]
        memory_hint = (
            "Prior conversational context is available and should be treated as evidence, "
            "not authority."
            if previous
            else
            "No prior assistant context is available; establish the operating baseline first."
        )

        lines = [
            f"DECISION FRAME — {system_name}",
            "",
            f"Objective: {user}",
            "",
            "Assessment:",
            f"- Primary intent: {cls._classify(user)}",
            f"- Decision keywords: {', '.join(keywords) if keywords else 'none extracted'}",
            f"- Context state: {memory_hint}",
            "",
            "Recommended action:",
            cls._recommend(user),
            "",
            "Constraints:",
            "- Separate facts from assumptions before committing resources.",
            "- Prefer the smallest reversible action that produces new evidence.",
            "- Define an owner, measurable outcome, and review point.",
            "",
            "Next checkpoint:",
            "Run the recommendation, record the observed result, then update PAMASMMA memory.",
        ]
        return "\n".join(lines)[: max_tokens * 4]

    @staticmethod
    def _classify(text: str) -> str:
        lower = text.lower()
        if any(x in lower for x in ("how do", "build", "implement", "fix", "code")):
            return "implementation / problem solving"
        if any(x in lower for x in ("should", "decide", "priority", "choose")):
            return "decision / prioritization"
        if any(x in lower for x in ("plan", "strategy", "roadmap", "next")):
            return "planning / strategy"
        if any(x in lower for x in ("write", "post", "caption", "content")):
            return "content / communication"
        return "analysis / synthesis"

    @staticmethod
    def _recommend(text: str) -> str:
        lower = text.lower()
        if "fix" in lower or "bug" in lower or "error" in lower:
            return (
                "Isolate the smallest reproducible failure, identify the violated contract, "
                "patch the root cause, then add a regression test."
            )
        if any(x in lower for x in ("choose", "should", "priority", "decide")):
            return (
                "Rank options by expected impact, reversibility, cost and evidence quality. "
                "Commit to the highest-value reversible option."
            )
        if any(x in lower for x in ("plan", "strategy", "roadmap")):
            return (
                "Convert the objective into milestones with measurable acceptance criteria; "
                "sequence dependencies before adding surface area."
            )
        return (
            "Convert the request into an explicit outcome, inspect the relevant constraints, "
            "and take the next action that maximizes useful evidence."
        )


class KernelProvider:
    """ModelProvider-compatible wrapper around the deterministic kernel."""

    async def generate(self, system_prompt: str, messages: list[dict], max_tokens: int) -> str:
        return IntelligenceKernel.reason(system_prompt, messages, max_tokens)

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        text = await self.generate(system_prompt, messages, max_tokens)
        for chunk in text.splitlines(keepends=True):
            yield chunk

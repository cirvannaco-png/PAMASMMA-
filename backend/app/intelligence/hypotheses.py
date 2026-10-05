"""Structured hypothesis formation for the cognitive loop."""
from app.intelligence.contracts import CognitiveContext, CognitivePlan, MemoryItem
from app.intelligence.contracts import IntentType, EvidenceType


class Hypothesis:
    def __init__(
        self,
        statement: str,
        basis: str,
        test: str,
        confidence: float,
    ) -> None:
        self.statement = statement
        self.basis = basis
        self.test = test
        self.confidence = confidence


class HypothesisEngine:
    def generate(
        self,
        context: CognitiveContext,
        plan: CognitivePlan,
        memories: list[MemoryItem],
    ) -> list[Hypothesis]:
        evidence_hint = (
            "existing relevant memory supports this direction"
            if memories
            else "no strong prior memory supports this direction"
        )

        hypotheses = [
            Hypothesis(
                statement=(
                    "The stated objective can be advanced by the smallest "
                    "reversible step that produces decision-relevant evidence."
                ),
                basis=evidence_hint,
                test=(
                    "Execute a bounded experiment and compare the observed result "
                    "with the expected outcome."
                ),
                confidence=0.62 if memories else 0.50,
            )
        ]

        if context.intent in {IntentType.DECISION, IntentType.PLANNING}:
            hypotheses.append(
                Hypothesis(
                    statement=(
                        "A clearly defined option with measurable acceptance criteria "
                        "will outperform an action selected from intuition alone."
                    ),
                    basis="decision/planning intent detected",
                    test="Rank options against impact, reversibility, cost, evidence quality and risk.",
                    confidence=0.65,
                )
            )

        if context.intent == IntentType.IMPLEMENTATION:
            hypotheses.append(
                Hypothesis(
                    statement=(
                        "The implementation outcome depends more on preserving "
                        "the violated contract than on adding surface-area."
                    ),
                    basis="implementation intent detected",
                    test="Identify the smallest reproducible failure and add a regression test.",
                    confidence=0.68,
                )
            )

        if context.intent == IntentType.RESEARCH:
            hypotheses.append(
                Hypothesis(
                    statement=(
                        "The highest-risk claims in this task are those whose "
                        "truth can change over time."
                    ),
                    basis="research/current-information signal detected",
                    test="Verify time-sensitive claims against authoritative external evidence.",
                    confidence=0.74,
                )
            )

        return hypotheses[:4]

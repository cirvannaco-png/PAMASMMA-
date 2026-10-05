"""Outcome learning and confidence calibration."""
from app.embeddings.service import store_memory
from app.intelligence.contracts import FailureDomain, OutcomeRecord
from app.intelligence.persistence import update_decision_outcome


def infer_failure_domain(observed_outcome: str) -> FailureDomain:
    text = observed_outcome.lower()
    rules = (
        (
            FailureDomain.EVIDENCE,
            ("evidence", "source", "stale", "unverified", "data was wrong"),
        ),
        (
            FailureDomain.REASONING,
            ("logic", "reasoning", "judgment", "analysis"),
        ),
        (
            FailureDomain.EXECUTION,
            ("execution", "implementation", "operator error", "deploy"),
        ),
        (
            FailureDomain.ENVIRONMENT,
            ("environment", "market changed", "external condition", "timing"),
        ),
        (
            FailureDomain.ASSUMPTION,
            ("assumption", "assumed", "premise was wrong"),
        ),
    )
    for domain, markers in rules:
        if any(marker in text for marker in markers):
            return domain
    return FailureDomain.UNKNOWN


class OutcomeLearningEngine:
    async def learn(self, outcome: OutcomeRecord) -> str:
        lesson = (
            outcome.lesson.strip()
            or self._derive_lesson(outcome)
        )

        await update_decision_outcome(
            decision_id=outcome.decision_id,
            user_id=outcome.user_id,
            observed_outcome=outcome.observed_outcome,
            prediction_error=outcome.prediction_error,
        )

        reliability = (
            0.9 if outcome.success_score is not None else 0.7
        )
        common_metadata = {
            "importance": 0.95,
            "reliability": reliability,
            "outcome_relevance": 1.0,
            "failure_domain": outcome.failure_domain.value,
            "success_score": outcome.success_score,
            "decision_id": outcome.decision_id,
        }

        await store_memory(
            user_id=outcome.user_id,
            system_id="S1",
            content=(
                f"OUTCOME LEARNING\n"
                f"Decision: {outcome.decision_id}\n"
                f"Expected: {outcome.expected_outcome}\n"
                f"Observed: {outcome.observed_outcome}\n"
                f"Lesson: {lesson}"
            ),
            metadata={
                "memory_type": "outcome",
                **common_metadata,
            },
        )

        await store_memory(
            user_id=outcome.user_id,
            system_id="S1",
            content=(
                "PROCEDURAL LESSON\n"
                "Trigger: comparable decision conditions\n"
                f"Rule: {lesson}"
            ),
            metadata={
                "memory_type": "procedural",
                "importance": 0.90,
                "reliability": reliability,
                "outcome_relevance": 1.0,
                "failure_domain": outcome.failure_domain.value,
                "decision_id": outcome.decision_id,
            },
        )
        return lesson

    @staticmethod
    def _derive_lesson(outcome: OutcomeRecord) -> str:
        if outcome.success_score is not None and outcome.success_score >= 0.8:
            return (
                "Preserve the successful mechanism and test it under "
                "the next comparable condition."
            )
        if outcome.failure_domain == FailureDomain.EVIDENCE:
            return "Require stronger evidence before repeating the decision."
        if outcome.failure_domain == FailureDomain.ASSUMPTION:
            return "Convert the failed assumption into an explicit precondition."
        if outcome.failure_domain == FailureDomain.REASONING:
            return "Re-examine the reasoning chain and add a verification gate."
        if outcome.failure_domain == FailureDomain.EXECUTION:
            return (
                "Separate decision quality from execution controls "
                "and harden the failed step."
            )
        if outcome.failure_domain == FailureDomain.ENVIRONMENT:
            return (
                "Add environment detection before repeating the strategy."
            )
        if outcome.success_score is not None and outcome.success_score <= 0.3:
            return (
                "Do not repeat the decision unchanged without a "
                "new evidence basis."
            )
        return (
            "Treat the result as inconclusive and collect another "
            "observation before generalizing."
        )


def estimate_prediction_error(
    success_score: float | None,
    confidence: float,
) -> float | None:
    if success_score is None:
        return None
    return round(abs(confidence - success_score), 4)

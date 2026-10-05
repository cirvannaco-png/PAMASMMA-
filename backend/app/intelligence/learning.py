"""Outcome learning: convert observed results into calibrated memory."""
from __future__ import annotations

import re

from app.embeddings.service import store_memory
from app.intelligence.contracts import FailureDomain, OutcomeRecord
from app.intelligence.persistence import update_decision_outcome


class OutcomeLearningEngine:
    async def learn(self, outcome: OutcomeRecord) -> str:
        lesson = outcome.lesson.strip()
        if not lesson:
            lesson = self._derive_lesson(outcome)

        await update_decision_outcome(
            decision_id=outcome.decision_id,
            user_id=outcome.user_id,
            observed_outcome=outcome.observed_outcome,
            prediction_error=outcome.prediction_error,
        )
        await store_memory(
            user_id=outcome.user_id,
            system_id="S1",
            content=(
                f"OUTCOME LEARNING\nDecision: {outcome.decision_id}\n"
                f"Expected: {outcome.expected_outcome}\nObserved: {outcome.observed_outcome}\n"
                f"Lesson: {lesson}"
            ),
            metadata={
                "memory_type": "outcome",
                "importance": 0.95,
                "reliability": 0.9 if outcome.success_score is not None else 0.7,
                "outcome_relevance": 1.0,
                "failure_domain": outcome.failure_domain.value,
                "success_score": outcome.success_score,
            },
        )
        return lesson

    @staticmethod
    def _derive_lesson(outcome: OutcomeRecord) -> str:
        if outcome.success_score is not None and outcome.success_score >= 0.8:
            return "The decision was directionally validated; preserve the successful mechanism and test it under the next comparable condition."
        if outcome.failure_domain == FailureDomain.EVIDENCE:
            return "The decision failed because evidence quality was insufficient; require stronger external or primary evidence before repeating it."
        if outcome.failure_domain == FailureDomain.ASSUMPTION:
            return "A planning assumption was wrong; convert the assumption into an explicit precondition for future decisions."
        if outcome.failure_domain == FailureDomain.EXECUTION:
            return "The decision logic may be sound but execution failed; separate execution controls from reasoning quality."
        if outcome.failure_domain == FailureDomain.ENVIRONMENT:
            return "Environmental conditions changed the result; preserve the strategy but make environment detection an explicit gate."
        if outcome.success_score is not None and outcome.success_score <= 0.3:
            return "The decision underperformed materially; do not repeat it unchanged without a new evidence basis."
        return "The result was inconclusive; preserve the uncertainty and collect another observation before generalizing."


def estimate_prediction_error(success_score: float | None, confidence: float) -> float | None:
    if success_score is None:
        return None
    return round(abs(confidence - success_score), 4)

"""Confidence scoring and certainty-band calibration."""
from app.intelligence.contracts import CognitiveContext, CognitivePlan


class ConfidenceEngine:
    def score(
        self,
        context: CognitiveContext,
        plan: CognitivePlan,
        verification_score: float,
        specialist_count: int,
        hypothesis_count: int,
        contradiction_count: int,
        evidence_status: str,
    ) -> float:
        score = 0.45
        score += min(0.15, 0.03 * len(context.memories))
        score += min(0.08, 0.02 * hypothesis_count)
        score += min(0.08, 0.04 * specialist_count)
        score += 0.06 if plan.steps else 0.0
        score += (verification_score - 0.8) * 0.45
        score -= min(0.28, 0.14 * contradiction_count)
        if evidence_status == "requires_external_evidence":
            score -= 0.10
        return round(max(0.05, min(0.95, score)), 3)

    @staticmethod
    def certainty_band(confidence: float) -> str:
        if confidence >= 0.85:
            return "high"
        if confidence >= 0.68:
            return "moderate-high"
        if confidence >= 0.50:
            return "moderate"
        return "low"

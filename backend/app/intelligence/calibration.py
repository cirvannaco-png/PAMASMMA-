"""Adaptive confidence calibration from observed decision outcomes."""
from __future__ import annotations


class ConfidenceCalibrator:
    """Adjust confidence using recent signed prediction errors.

    A positive calibration delta means the system has historically been
    underconfident for comparable decisions; a negative delta means it has
    been overconfident. The adjustment is deliberately bounded.
    """

    def adjust(
        self,
        confidence: float,
        outcomes: list[dict],
        limit: int = 20,
    ) -> float:
        deltas = []
        for outcome in outcomes[:limit]:
            metadata = outcome.get("metadata") or {}
            delta = metadata.get("calibration_delta")
            if delta is None:
                continue
            try:
                deltas.append(float(delta))
            except (TypeError, ValueError):
                continue

        if not deltas:
            return round(confidence, 3)

        mean_delta = sum(deltas) / len(deltas)
        # Past calibration is informative, not authoritative.
        adjustment = max(-0.10, min(0.10, 0.45 * mean_delta))
        return round(max(0.05, min(0.95, confidence + adjustment)), 3)

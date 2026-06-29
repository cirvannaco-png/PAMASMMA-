from typing import Any, Dict, List


class SystemCalibrationLayer:
    """
    Pamasmma Prime System-Wide Calibration Layer

    This module prevents feedback loop collapse by:

    - Normalizing reward signals across time
    - Dampening unstable objective drift
    - Weighting causal signals by confidence
    - Introducing uncertainty into world model assumptions
    - Managing memory pressure via graceful degradation

    It ensures learning remains stable under recursive feedback.
    """

    def __init__(self):
        self.reward_history: List[float] = []
        self.drift_window: List[float] = []
        self.memory_pressure_threshold = 0.8

    # -----------------------------
    # Reward normalization
    # -----------------------------
    def normalize_reward(self, reward: float) -> float:
        self.reward_history.append(reward)

        if len(self.reward_history) < 2:
            return reward

        mean = sum(self.reward_history) / len(self.reward_history)
        variance = sum((r - mean) ** 2 for r in self.reward_history) / len(self.reward_history)
        std = max(1e-6, variance ** 0.5)

        return (reward - mean) / std

    # -----------------------------
    # Objective damping
    # -----------------------------
    def damp_objectives(self, objectives: Dict[str, float], drift: float) -> Dict[str, float]:
        self.drift_window.append(drift)

        avg_drift = sum(self.drift_window[-10:]) / min(len(self.drift_window), 10)

        damped = {}

        for k, v in objectives.items():
            damp_factor = 1.0 - min(0.5, avg_drift)
            damped[k] = v * damp_factor

        return damped

    # -----------------------------
    # Causal weighting
    # -----------------------------
    def weight_causal_links(self, links: List[tuple], confidence: float = 0.5) -> List[tuple]:
        weighted = []

        for a, b in links:
            if confidence > 0.5:
                weighted.append((a, b, confidence))

        return weighted

    # -----------------------------
    # World model uncertainty injection
    # -----------------------------
    def inject_uncertainty(self, state: Dict[str, Any], factor: float = 0.1) -> Dict[str, Any]:
        noisy = dict(state)

        if "complexity" in noisy:
            noisy["complexity"] *= (1.0 + factor)

        if "stability" in noisy:
            noisy["stability"] *= (1.0 - factor)

        return noisy

    # -----------------------------
    # Graceful memory degradation
    # -----------------------------
    def memory_degrade(self, memory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Reduce memory load by filtering low-salience events.
        """

        if len(memory) < 10:
            return memory

        # naive salience heuristic: keep recent + structured events
        retained = []

        for i, event in enumerate(memory):
            if i > len(memory) - 5:
                retained.append(event)
            elif event.get("important", False):
                retained.append(event)

        return retained

    # -----------------------------
    # System stability score
    # -----------------------------
    def stability_score(self, drift: float) -> float:
        self.drift_window.append(drift)

        avg = sum(self.drift_window[-20:]) / min(len(self.drift_window), 20)

        return max(0.0, 1.0 - avg)

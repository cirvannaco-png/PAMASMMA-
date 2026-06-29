from typing import Dict, Any, List


class AdaptiveObjectiveSystem:
    """
    Pamasmma Prime Adaptive Objective Layer

    Evolves objective weights based on system experience.
    Bridges static objectives with learned preference drift.
    """

    def __init__(self):
        # baseline objectives (initial priors)
        self.objectives = {
            "system_coherence": 0.4,
            "task_completion": 0.3,
            "resource_efficiency": 0.2,
            "learning_progression": 0.1
        }

        self.learning_rate = 0.05
        self.history: List[Dict[str, Any]] = []

    def update(self, outcome: Dict[str, Any]) -> None:
        """
        Adjust objective weights based on observed outcomes.
        """

        self.history.append(outcome)

        score = outcome.get("score", 0)
        success = outcome.get("success", True)

        # simplistic reinforcement update
        delta = self.learning_rate * (1.0 if success else -1.0) * score

        # adjust task completion bias as primary proxy
        self.objectives["task_completion"] += delta

        # normalize
        self._normalize()

    def evaluate(self, state: Dict[str, Any], action: Dict[str, Any]) -> float:
        """
        Compute adaptive utility score.
        """

        score = 0.0

        if action.get("valid", True):
            score += self.objectives["task_completion"]

        if state.get("stability", 1.0) < 0.5:
            score -= 0.5

        if not action.get("traceable", True):
            score -= 0.3

        return score

    def _normalize(self) -> None:
        total = sum(self.objectives.values())
        if total <= 0:
            return
        for k in self.objectives:
            self.objectives[k] /= total

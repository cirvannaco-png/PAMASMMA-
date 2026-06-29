class ObjectiveFunctionSystem:
    """
    Pamasmma Prime Objective Function System

    Defines system-wide optimization targets and scoring logic.
    This is the 'why' layer of the architecture.
    """

    def __init__(self):
        self.primary_objectives = {
            "system_coherence": 0.4,
            "task_completion": 0.3,
            "resource_efficiency": 0.2,
            "learning_progression": 0.1
        }

        self.penalties = {
            "constraint_violation": -1.0,
            "unstable_state": -0.7,
            "untraceable_action": -0.5
        }

    def evaluate(self, state: dict, action: dict) -> float:
        """
        Compute utility score for a given action in a given state.
        """

        score = 0.0

        # Simplified scoring baseline
        if action.get("valid", True):
            score += self.primary_objectives["task_completion"]

        if state.get("stability", 1.0) < 0.5:
            score += self.penalties["unstable_state"]

        if not action.get("traceable", True):
            score += self.penalties["untraceable_action"]

        return score

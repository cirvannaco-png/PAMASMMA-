from typing import Any, Dict


class WorldModel:
    """
    Pamasmma Prime World Model

    Simulates environment state transitions based on actions.
    Provides predictive structure for planning and reasoning.
    """

    def __init__(self):
        self.state_history = []

    def predict(self, state: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict next state given current state and action.
        """

        next_state = dict(state)

        # minimal deterministic transition model
        action_type = action.get("type")

        if action_type == "execute":
            next_state["progress"] = state.get("progress", 0) + 1

        elif action_type == "analyze":
            next_state["insight"] = True

        elif action_type == "refine":
            next_state["complexity"] = state.get("complexity", 0) + 1

        # generic trace
        next_state["last_action"] = action

        self.state_history.append(next_state)

        return next_state

    def reset(self) -> None:
        """
        Reset internal simulation history.
        """
        self.state_history.clear()

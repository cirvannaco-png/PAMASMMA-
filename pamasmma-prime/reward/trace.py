from typing import Any, Dict, List


class RewardTraceSystem:
    """
    Pamasmma Prime Reward Trace System

    Assigns long-term credit to actions based on delayed outcomes.
    Implements simplified temporal credit assignment using decay.
    """

    def __init__(self, gamma: float = 0.95):
        # discount factor for long-term reward propagation
        self.gamma = gamma

        # stored trajectory of (state, action, reward)
        self.trajectory: List[Dict[str, Any]] = []

        # computed credit assignments
        self.credits: List[Dict[str, Any]] = []

    def record(self, state: Dict[str, Any], action: Dict[str, Any], reward: float) -> None:
        """
        Store experience tuple.
        """
        self.trajectory.append({
            "state": state,
            "action": action,
            "reward": reward
        })

    def compute_returns(self) -> List[float]:
        """
        Compute discounted returns for each step (reverse accumulation).
        """
        returns = []
        G = 0.0

        for step in reversed(self.trajectory):
            G = step.get("reward", 0.0) + self.gamma * G
            returns.insert(0, G)

        return returns

    def assign_credit(self) -> List[Dict[str, Any]]:
        """
        Attach long-term credit values to actions.
        """
        returns = self.compute_returns()

        self.credits = []

        for i, step in enumerate(self.trajectory):
            self.credits.append({
                "state": step["state"],
                "action": step["action"],
                "reward": step["reward"],
                "return": returns[i]
            })

        return self.credits

    def reset(self) -> None:
        """
        Clear episode memory.
        """
        self.trajectory.clear()
        self.credits.clear()

from typing import Any, Dict


class LearningLoop:
    """
    Pamasmma Prime Learning Loop

    This module connects experience → reward → adaptation.

    It binds together:
    - Reward Trace System
    - Calibration Layer
    - Adaptive Objectives
    - Runtime feedback signals

    It is responsible for incremental behavioral learning.
    """

    def __init__(self, runtime, reward, calibration, objectives):
        self.runtime = runtime
        self.reward = reward
        self.calibration = calibration
        self.objectives = objectives

    def step(self, state: Dict[str, Any], action: Dict[str, Any], reward_signal: float) -> Dict[str, Any]:
        """
        Execute one learning iteration.
        """

        norm_reward = self.calibration.normalize_reward(reward_signal)

        self.reward.record(state, action, norm_reward)

        self.objectives.update({
            "score": norm_reward,
            "success": norm_reward > 0
        })

        if hasattr(self.runtime, "observe_learning"):
            self.runtime.observe_learning({
                "state": state,
                "action": action,
                "reward": norm_reward
            })

        return {
            "normalized_reward": norm_reward,
            "status": "learned"
        }

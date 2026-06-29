from typing import Any, Dict


class UnifiedCalibratedRuntime:
    """
    Pamasmma Prime Unified Calibrated Runtime

    This layer binds together:
    - Core cognitive runtime
    - Calibration system (signal stabilization)
    - Stabilization loop (feedback homeostasis)

    It is the final integration layer ensuring:
    - stable learning
    - controlled feedback propagation
    - graceful degradation under memory pressure
    - drift-resistant cognition
    """

    def __init__(self, runtime, calibration, stabilizer):
        self.runtime = runtime
        self.calibration = calibration
        self.stabilizer = stabilizer

    def step(self, input_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a fully stabilized cognition cycle.
        """

        reward = input_event.get("reward", 0.0)
        norm_reward = self.calibration.normalize_reward(reward)
        input_event["reward"] = norm_reward

        state = input_event.get("state", {"stability": 1.0, "complexity": 0.0})
        input_event["state"] = self.calibration.inject_uncertainty(state)

        if hasattr(self.runtime.memory, "episodic_memory"):
            self.runtime.memory.episodic_memory = self.calibration.memory_degrade(
                self.runtime.memory.episodic_memory
            )

        core_output = self.runtime.step(input_event)

        plan = core_output.get("plan", [])
        action = plan[-1] if plan else {"type": "noop"}

        stability_report = self.stabilizer.step(
            input_event.get("state", {}),
            action,
            norm_reward
        )

        drift = stability_report.get("drift", 0.0)
        stability_score = self.calibration.stability_score(drift)

        return {
            "core": core_output,
            "stability": stability_report,
            "stability_score": stability_score,
            "reward_normalized": norm_reward,
            "drift": drift
        }

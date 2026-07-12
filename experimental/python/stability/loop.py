from typing import Any, Dict


class StabilizationLoop:
    """
    Pamasmma Prime Stabilization Loop

    This module binds all subsystems into a feedback alignment mechanism:

    - Aligns reward signals with objective adaptation
    - Stabilizes memory compression cycles
    - Detects drift via governance hardening
    - Ensures causal + world model consistency over time

    This is the system's self-correcting homeostasis layer.
    """

    def __init__(
        self,
        memory,
        objectives,
        reward,
        causal_engine,
        world_model,
        governance,
        hardening
    ):
        self.memory = memory
        self.objectives = objectives
        self.reward = reward
        self.causal_engine = causal_engine
        self.world_model = world_model
        self.governance = governance
        self.hardening = hardening

        self.drift_accumulator = 0.0

    def step(self, state: Dict[str, Any], action: Dict[str, Any], reward_signal: float) -> Dict[str, Any]:
        self.reward.record(state, action, reward_signal)

        self.objectives.update({"score": reward_signal, "success": reward_signal > 0})

        if len(self.memory.episodic_memory) > 15:
            compression_report = self.memory.compress()
        else:
            compression_report = {"status": "skipped"}

        self.causal_engine.observe({"type": action.get("type", "unknown")})
        causal_links = self.causal_engine.infer()

        predicted_state = self.world_model.predict(state, action)

        governance_eval = self.governance.evaluate(action)

        drift = self.hardening._compute_drift({
            "stability": state.get("stability", 1.0),
            "complexity": state.get("complexity", 0.0)
        })

        self.drift_accumulator += drift

        stability_score = max(0.0, 1.0 - self.drift_accumulator)

        return {
            "predicted_state": predicted_state,
            "causal_links": causal_links,
            "governance": governance_eval,
            "compression": compression_report,
            "stability_score": stability_score,
            "drift": drift
        }

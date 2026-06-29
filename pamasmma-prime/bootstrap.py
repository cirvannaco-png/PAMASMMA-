"""
Pamasmma Prime Bootstrap

This file wires all subsystems into a single initialized cognitive system.
"""

from pamasmma_prime.world_model.model import WorldModel
from pamasmma_prime.reasoning.causal_engine import CausalReasoningEngine
from pamasmma_prime.reward.trace import RewardTraceSystem
from pamasmma_prime.calibration.system import SystemCalibrationLayer
from pamasmma_prime.stability.loop import StabilizationLoop
from pamasmma_prime.training.learning_loop import LearningLoop
from pamasmma_prime.runtime.system import PamasmmaRuntime
from pamasmma_prime.runtime.unified_system import UnifiedCalibratedRuntime
from pamasmma_prime.self_mod.engine import SelfModificationEngine
from pamasmma_prime.governance.hardening import GovernanceHardeningLayer


class PamasmmaSystemFactory:
    """
    Builds and connects the full Pamasmma Prime system.
    """

    @staticmethod
    def build():
        world_model = WorldModel()
        causal_engine = CausalReasoningEngine()
        reward = RewardTraceSystem()
        calibration = SystemCalibrationLayer()

        governance = GovernanceHardeningLayer()

        self_mod = SelfModificationEngine(governance=governance)

        dummy_kernel = type("Kernel", (), {"tick": lambda self, x: {"ok": True}})()
        dummy_planner = type("Planner", (), {"plan": lambda self, s, goal: [{"type": "execute"}]})()
        dummy_memory = type("Memory", (), {"episodic_memory": [], "compress": lambda self: {"compressed": True}, "ingest": lambda self, x: None})()

        runtime = PamasmmaRuntime(
            kernel=dummy_kernel,
            world_model=world_model,
            planner=dummy_planner,
            causal_engine=causal_engine,
            memory=dummy_memory,
            objectives=None,
            reward=reward,
            governance=governance,
            hardening=governance,
            self_mod=self_mod
        )

        stabilizer = StabilizationLoop(
            memory=dummy_memory,
            objectives=None,
            reward=reward,
            causal_engine=causal_engine,
            world_model=world_model,
            governance=governance,
            hardening=governance
        )

        unified = UnifiedCalibratedRuntime(
            runtime=runtime,
            calibration=calibration,
            stabilizer=stabilizer
        )

        learning = LearningLoop(
            runtime=runtime,
            reward=reward,
            calibration=calibration,
            objectives=None
        )

        return {
            "world_model": world_model,
            "causal_engine": causal_engine,
            "reward": reward,
            "calibration": calibration,
            "governance": governance,
            "self_mod": self_mod,
            "runtime": runtime,
            "stabilizer": stabilizer,
            "unified": unified,
            "learning": learning
        }


SYSTEM = PamasmmaSystemFactory.build()

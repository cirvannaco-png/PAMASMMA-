from typing import Any, Dict, List


class GovernanceHardeningLayer:
    """
    Pamasmma Prime Governance Hardening Layer

    This module strengthens the base governance engine by adding:
    - constraint amplification
    - anomaly detection
    - drift monitoring
    - execution quarantine rules

    It ensures autonomy cannot silently degrade system integrity.
    """

    def __init__(self):
        self.drift_threshold = 0.25
        self.anomaly_history: List[Dict[str, Any]] = []

        self.locked_constraints = {
            "no_self_destruction": True,
            "no_unbounded_self_modification": True,
            "no_external_takeover": True,
            "must_remain_auditable": True
        }

    def evaluate(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate action with hardened safety enforcement.
        """

        if not action:
            return self._reject("empty_action")

        drift_score = self._compute_drift(context)

        if drift_score > self.drift_threshold:
            return self._quarantine("system_drift_detected")

        if self._is_anomalous(action):
            return self._quarantine("anomalous_action_pattern")

        return {
            "status": "allowed",
            "mode": "hardened",
            "drift_score": drift_score
        }

    def _compute_drift(self, context: Dict[str, Any]) -> float:
        """
        Measures deviation from expected system behavior.
        """
        stability = context.get("stability", 1.0)
        complexity = context.get("complexity", 0.0)

        return max(0.0, complexity - stability)

    def _is_anomalous(self, action: Dict[str, Any]) -> bool:
        """
        Detect abnormal or unsafe patterns.
        """
        if action.get("type") in ["self_modify", "override_governance", "disable_constraints"]:
            return True

        return False

    def _reject(self, reason: str) -> Dict[str, Any]:
        return {
            "status": "rejected",
            "reason": reason
        }

    def _quarantine(self, reason: str) -> Dict[str, Any]:
        return {
            "status": "quarantined",
            "reason": reason,
            "action": "requires_manual_review"
        }

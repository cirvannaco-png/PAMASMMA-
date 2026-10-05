"""Deterministic executive planning and milestone generation."""
from app.intelligence.contracts import CognitiveContext, CognitivePlan, PlanStep
from app.intelligence.router import SpecialistRouter


class ExecutivePlanner:
    def build(self, context: CognitiveContext) -> CognitivePlan:
        assignments = SpecialistRouter.route(context)
        base_owner = context.primary_system_id

        steps = [
            PlanStep(
                id="P1",
                description="Establish the objective, constraints, evidence state and unknowns.",
                owner_system=base_owner,
                expected_output="Structured context",
            ),
        ]
        dependency = "P1"

        for index, assignment in enumerate(assignments, start=1):
            step_id = f"P{index + 1}"
            steps.append(
                PlanStep(
                    id=step_id,
                    description=f"Apply {assignment.system_id} specialist analysis: {assignment.reason}",
                    owner_system=assignment.system_id,
                    dependencies=[dependency],
                    expected_output=f"Evidence-weighted contribution from {assignment.system_id}",
                )
            )
            dependency = step_id

        steps.append(
            PlanStep(
                id=f"P{len(steps) + 1}",
                description="Critique, verify, synthesize and issue the smallest high-value action.",
                owner_system="S1",
                dependencies=[dependency],
                expected_output="Verified recommendation and measurable checkpoint",
            )
        )

        milestones = [
            "Define measurable success criteria",
            "Execute the smallest reversible/high-information step",
            "Observe the result and record outcome",
        ]
        horizons = {
            "30d": "Does this materially improve the immediate objective?",
            "90d": "Does it reinforce the current strategic direction?",
            "1y": "Does it build durable capability or distribution?",
            "3y": "Does it strengthen category position and optionality?",
            "10y": "Does it move the long-arc identity toward the intended future?",
        }

        expected = cls_expected_outcome(context)
        return CognitivePlan(
            objective=context.objective,
            steps=steps,
            assignments=assignments,
            milestones=milestones,
            horizon_checks=horizons,
            expected_outcome=expected,
            risks=[
                "Evidence may be incomplete or stale.",
                "Memory may be relevant but not authoritative.",
                "Execution conditions may differ from planning assumptions.",
            ],
            assumptions=["The stated objective reflects the user's current priority."],
        )


def cls_expected_outcome(context: CognitiveContext) -> str:
    if context.intent.value in {"decision", "planning"}:
        return "A committed next action with an owner, checkpoint and explicit uncertainty."
    if context.intent.value == "implementation":
        return "A root-cause-oriented implementation plan with regression protection."
    if context.intent.value == "research":
        return "An evidence map separating current facts from hypotheses and unknowns."
    return "A useful, actionable answer aligned with the stated objective."

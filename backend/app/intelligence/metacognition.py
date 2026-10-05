"""Metacognitive governance for consistency, evidence and uncertainty."""
from app.intelligence.contracts import CognitiveContext, VerificationIssue, VerificationReport


class MetacognitiveGovernor:
    def inspect(
        self,
        context: CognitiveContext,
        verification: VerificationReport,
    ) -> VerificationReport:
        issues = list(verification.issues)

        if context.contradictions:
            issues.append(
                VerificationIssue(
                    "medium",
                    "belief_conflict",
                    "Conflicting beliefs are present; the answer must surface them instead of silently resolving them.",
                )
            )

        if not context.memories and context.complexity.value in {"complex", "strategic"}:
            issues.append(
                VerificationIssue(
                    "low",
                    "context_depth",
                    "A complex task has little historical context; preserve uncertainty rather than inferring a strong personalized conclusion.",
                )
            )

        if verification.score < 0.78:
            requires_revision = True
        else:
            requires_revision = any(
                issue.severity == "high" for issue in issues
            )

        score = max(
            0.0,
            min(
                1.0,
                verification.score
                - sum(
                    0.08 if issue.severity == "medium" else 0.15 if issue.severity == "high" else 0.02
                    for issue in issues
                    if issue not in verification.issues
                ),
            ),
        )

        return VerificationReport(
            score=round(score, 3),
            issues=issues,
            requires_revision=requires_revision,
            evidence_status=verification.evidence_status,
            confidence_adjustment=(score - 0.8) * 0.5,
        )

"""Critic stage for generated cognitive output."""
from app.intelligence.contracts import (
    CognitiveContext,
    CognitivePlan,
    VerificationIssue,
    VerificationReport,
)


class CognitiveCritic:
    """Checks answer quality without owning evidence-policy decisions."""

    def evaluate(
        self,
        response: str,
        context: CognitiveContext,
        plan: CognitivePlan,
    ) -> VerificationReport:
        issues: list[VerificationIssue] = []
        clean = response.strip()

        if len(clean) < 80:
            issues.append(
                VerificationIssue(
                    "high",
                    "completeness",
                    "Response is too short to carry a strategic "
                    "or decision-grade conclusion.",
                )
            )

        lower = clean.lower()

        if context.constraints and not any(
            constraint.lower().split()[0] in lower
            for constraint in context.constraints
            if constraint.strip()
        ):
            issues.append(
                VerificationIssue(
                    "medium",
                    "constraint_alignment",
                    "Response does not visibly address the extracted constraints.",
                )
            )

        if (
            context.intent.value
            in {"decision", "planning", "implementation"}
            and not any(
                token in lower
                for token in (
                    "recommend",
                    "next",
                    "action",
                    "do ",
                    "build",
                    "choose",
                    "priorit",
                )
            )
        ):
            issues.append(
                VerificationIssue(
                    "medium",
                    "actionability",
                    "Decision-oriented output lacks an explicit next action.",
                )
            )

        certainty_markers = (
            "definitely",
            "guaranteed",
            "certainly",
            "always",
            "never",
        )
        if (
            any(
                marker in lower
                for marker in certainty_markers
            )
            and context.sensitivity.value == "sensitive"
        ):
            issues.append(
                VerificationIssue(
                    "high",
                    "overconfidence",
                    "Sensitive-context output contains absolute certainty language.",
                )
            )

        score = 1.0
        penalties = {
            "high": 0.2,
            "medium": 0.1,
            "low": 0.04,
        }
        for issue in issues:
            score -= penalties.get(
                issue.severity,
                0.05,
            )

        score = max(
            0.0,
            min(1.0, score),
        )
        return VerificationReport(
            score=score,
            issues=issues,
            requires_revision=score < 0.78,
            evidence_status="structural_only",
            confidence_adjustment=(score - 0.8) * 0.5,
        )


class ContradictionChecker:
    _NEGATION = __import__("re").compile(
        r"\b(?:not|never|no|without|cannot|can't|isn't|doesn't|won't)\b",
        __import__("re").IGNORECASE,
    )

    @classmethod
    def text_contradiction(
        cls,
        left: str,
        right: str,
    ) -> bool:
        import re

        left_words = set(
            re.findall(
                r"[a-z0-9-]{4,}",
                left.lower(),
            )
        )
        right_words = set(
            re.findall(
                r"[a-z0-9-]{4,}",
                right.lower(),
            )
        )
        overlap = len(left_words & right_words)
        if overlap < 3:
            return False

        left_negated = cls._NEGATION.search(left) is not None
        right_negated = cls._NEGATION.search(right) is not None
        return left_negated != right_negated

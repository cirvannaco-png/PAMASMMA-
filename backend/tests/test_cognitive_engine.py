"""Regression tests for PAMASMMA's cognitive operating system."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.intelligence.context import ContextAssembler
from app.intelligence.contracts import (
    FailureDomain,
    IntentType,
    MemoryItem,
    MemoryType,
    Sensitivity,
    TaskComplexity,
)
from app.intelligence.critic import ContradictionChecker
from app.intelligence.engine import CognitiveEngine
from app.intelligence.provider_router import ProviderRouter, ProviderSelection
from app.intelligence.learning import (
    estimate_prediction_error,
    infer_failure_domain,
)
from app.intelligence.router import SpecialistRouter
from app.systems.s1_executive import s1_executive_system


def test_context_assembly_extracts_intent_constraints_and_entities():
    context = ContextAssembler.assemble(
        [
            {
                "role": "user",
                "content": (
                    "Plan how to improve PAMASMMA. "
                    "It must preserve the current API and avoid unnecessary "
                    "dependencies."
                ),
            }
        ],
        user_id="test-user",
        primary_system_id="S1",
    )

    assert context.intent == IntentType.PLANNING
    assert context.complexity == TaskComplexity.STRATEGIC
    assert "PAMASMMA" in {item.name for item in context.entities}
    assert any("must preserve" in item.lower() for item in context.constraints)


def test_context_marks_sensitive_requests():
    context = ContextAssembler.assemble(
        [{"role": "user", "content": "Store my API key securely."}],
        "test-user",
        "S1",
    )
    assert context.sensitivity == Sensitivity.SENSITIVE


def test_specialist_router_routes_by_domain_signals():
    context = ContextAssembler.assemble(
        [
            {
                "role": "user",
                "content": "Plan a brand pitch for investors with a strong narrative and 10-year vision.",
            }
        ],
        "test-user",
        "S1",
    )
    assignments = SpecialistRouter.route(context)
    routed = {item.system_id for item in assignments}
    assert {"S1", "S3", "S5", "S8", "S10"} & routed
    assert "S1" in routed


def test_memory_score_prioritizes_reliable_recent_outcome():
    from app.embeddings.service import _score_memory

    now = datetime.now(UTC)
    high_score, _ = _score_memory(
        similarity=0.82,
        created_at=now - timedelta(days=2),
        metadata={
            "importance": 0.95,
            "reliability": 0.95,
            "outcome_relevance": 1.0,
        },
        query="deployment lesson",
        content="deployment lesson for production",
    )
    low_score, _ = _score_memory(
        similarity=0.82,
        created_at=now - timedelta(days=80),
        metadata={
            "importance": 0.2,
            "reliability": 0.2,
            "outcome_relevance": 0.1,
        },
        query="deployment lesson",
        content="unrelated note",
    )
    assert high_score > low_score


def test_contradiction_checker_detects_negated_claim():
    assert ContradictionChecker.text_contradiction(
        "PAMASMMA is production ready and stable.",
        "PAMASMMA is not production ready and stable.",
    )


def test_provider_router_keeps_sensitive_request_local_by_default(monkeypatch):
    monkeypatch.setattr(
        "app.intelligence.provider_router.get_settings",
        lambda: SimpleNamespace(
            model_provider="anthropic",
            intelligence_cloud_for_sensitive=False,
        ),
    )
    selection = ProviderRouter().select(
        TaskComplexity.STRATEGIC,
        Sensitivity.SENSITIVE,
    )
    assert selection.name == "kernel"


def test_outcome_calibration_helpers():
    assert infer_failure_domain("The assumption was wrong.") == FailureDomain.ASSUMPTION
    assert infer_failure_domain("The deployment failed during execution.") == FailureDomain.EXECUTION
    assert estimate_prediction_error(0.7, 0.85) == 0.15


@pytest.mark.asyncio
async def test_engine_runs_context_plan_specialists_verification_and_decision(monkeypatch):
    class FakeProvider:
        async def generate(self, system_prompt, messages, max_tokens):
            return (
                "Recommendation: implement the smallest reversible validation step. "
                "This directly addresses the objective and establishes a measurable "
                "checkpoint while keeping evidence and assumptions explicit."
            )

    engine = CognitiveEngine()
    engine.provider_router.select = lambda *_args: ProviderSelection(
        "test-provider",
        FakeProvider(),
    )
    engine.world_model.observe = AsyncMock()
    engine.world_model.hydrate = AsyncMock(return_value=[])

    monkeypatch.setattr(
        "app.intelligence.engine.list_beliefs",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.intelligence.engine.upsert_belief",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.intelligence.engine.create_decision",
        AsyncMock(return_value="decision"),
    )
    monkeypatch.setattr(
        "app.embeddings.service.retrieve_memory_items",
        AsyncMock(
            return_value=[
                MemoryItem(
                    content="Prior validation succeeded.",
                    memory_type=MemoryType.OUTCOME,
                    similarity=0.9,
                    recency=1.0,
                    importance=0.9,
                    reliability=0.9,
                    outcome_relevance=1.0,
                    contextual_fit=0.8,
                    score=0.92,
                )
            ]
        ),
    )

    result = await engine.run(
        s1_executive_system,
        [
            {
                "role": "user",
                "content": (
                    "Plan how to improve PAMASMMA architecture while preserving "
                    "the current API and minimizing unnecessary changes."
                ),
            }
        ],
        "test-user",
    )

    assert result.response.startswith("Recommendation:")
    assert result.decision.id
    assert 0.0 <= result.decision.confidence <= 1.0
    assert result.trace.provider == "test-provider"
    assert result.trace.memory_count == 1
    assert result.trace.routed_systems
    assert result.trace.verification.score >= 0.78
    assert result.trace.evidence_status == "structural_only"
    assert result.decision.context["hypotheses"]


def test_planner_marks_specialists_parallel_after_context():
    from app.intelligence.planner import ExecutivePlanner

    context = ContextAssembler.assemble(
        [{"role": "user", "content": "Plan a brand strategy for investors."}],
        "test-user",
        "S1",
    )
    plan = ExecutivePlanner().build(context)
    specialist_steps = [
        step for step in plan.steps
        if step.id != "P1" and step.owner_system != "S1"
    ]
    assert specialist_steps
    assert all(step.dependencies == ["P1"] for step in specialist_steps)


def test_evidence_gate_marks_research_as_external_evidence_required():
    from app.intelligence.evidence import EvidenceGate

    context = ContextAssembler.assemble(
        [{"role": "user", "content": "Research the latest market position."}],
        "test-user",
        "S1",
    )
    status, issues = EvidenceGate().assess(context, "Here is the analysis.")
    assert status == "requires_external_evidence"
    assert issues


@pytest.mark.asyncio
async def test_provider_runtime_failure_falls_back_to_kernel():
    class BrokenProvider:
        async def generate(self, system_prompt, messages, max_tokens):
            raise RuntimeError("provider unavailable")

    selection = ProviderSelection("broken", BrokenProvider())
    routed, response = await ProviderRouter().generate(
        selection,
        "Answer deterministically.",
        [{"role": "user", "content": "Test"}],
        256,
    )
    assert routed.name == "kernel"
    assert response

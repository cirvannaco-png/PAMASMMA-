"""Typed contracts for the PAMASMMA cognitive operating system."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class MemoryType(StrEnum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    RELATIONSHIP = "relationship"
    OUTCOME = "outcome"


class EvidenceType(StrEnum):
    FACT = "fact"
    INFERENCE = "inference"
    ASSUMPTION = "assumption"
    PREDICTION = "prediction"
    OPINION = "opinion"
    UNKNOWN = "unknown"


class IntentType(StrEnum):
    IMPLEMENTATION = "implementation"
    DECISION = "decision"
    PLANNING = "planning"
    ANALYSIS = "analysis"
    COMMUNICATION = "communication"
    RESEARCH = "research"
    REVIEW = "review"
    GENERAL = "general"


class Sensitivity(StrEnum):
    LOW = "low"
    STANDARD = "standard"
    SENSITIVE = "sensitive"


class TaskComplexity(StrEnum):
    ROUTINE = "routine"
    MODERATE = "moderate"
    COMPLEX = "complex"
    STRATEGIC = "strategic"


class FailureDomain(StrEnum):
    EVIDENCE = "evidence"
    REASONING = "reasoning"
    EXECUTION = "execution"
    ENVIRONMENT = "environment"
    ASSUMPTION = "assumption"
    UNKNOWN = "unknown"


class MemoryItem(BaseModel):
    content: str
    memory_type: MemoryType = MemoryType.SEMANTIC
    similarity: float = 0.0
    recency: float = 0.0
    importance: float = 0.5
    reliability: float = 0.5
    outcome_relevance: float = 0.5
    contextual_fit: float = 0.5
    score: float = 0.0
    created_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class Belief(BaseModel):
    statement: str
    evidence_type: EvidenceType = EvidenceType.UNKNOWN
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reliability: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = "inference"
    subject: str | None = None
    predicate: str | None = None
    object: str | None = None
    status: str = "active"


class Hypothesis(BaseModel):
    statement: str
    basis: str
    test: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class WorldEntity(BaseModel):
    name: str
    entity_type: str = "concept"
    attributes: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class Relationship(BaseModel):
    subject: str
    relation: str
    object: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class CognitiveContext(BaseModel):
    user_id: str
    primary_system_id: str
    query: str
    recent_messages: list[dict]
    objective: str
    intent: IntentType
    sensitivity: Sensitivity
    complexity: TaskComplexity
    constraints: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    entities: list[WorldEntity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    memories: list[MemoryItem] = Field(default_factory=list)
    beliefs: list[Belief] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)


class PlanStep(BaseModel):
    id: str
    description: str
    owner_system: str
    dependencies: list[str] = Field(default_factory=list)
    expected_output: str
    reversible: bool = True


class SpecialistAssignment(BaseModel):
    system_id: str
    reason: str
    weight: float = Field(ge=0.0, le=1.0)
    required: bool = False


class CognitivePlan(BaseModel):
    objective: str
    steps: list[PlanStep]
    assignments: list[SpecialistAssignment]
    milestones: list[str] = Field(default_factory=list)
    horizon_checks: dict[str, str] = Field(default_factory=dict)
    expected_outcome: str = ""
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class VerificationIssue(BaseModel):
    severity: str
    category: str
    message: str


class VerificationReport(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    issues: list[VerificationIssue] = Field(default_factory=list)
    requires_revision: bool = False
    evidence_status: str = "structural_only"
    confidence_adjustment: float = 0.0


class DecisionRecord(BaseModel):
    id: str
    user_id: str
    primary_system_id: str
    objective: str
    context: dict = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    memories: list[str] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    certainty_band: str = "moderate"
    selected_action: str
    alternatives_rejected: list[str] = Field(default_factory=list)
    owner: str = "PAMASMMA"
    expected_outcome: str = ""
    deadline: str | None = None
    horizon_checks: dict[str, str] = Field(default_factory=dict)
    status: str = "open"
    created_at: datetime | None = None


class OutcomeRecord(BaseModel):
    id: str
    decision_id: str
    user_id: str
    expected_outcome: str
    observed_outcome: str
    success_score: float | None = Field(default=None, ge=0.0, le=1.0)
    prediction_error: float | None = None
    failure_domain: FailureDomain = FailureDomain.UNKNOWN
    lesson: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class CognitiveTrace(BaseModel):
    intent: IntentType
    complexity: TaskComplexity
    sensitivity: Sensitivity
    memory_count: int = 0
    contradiction_count: int = 0
    routed_systems: list[str] = Field(default_factory=list)
    provider: str = "kernel"
    verification: VerificationReport
    decision_id: str | None = None
    confidence: float = 0.5
    uncertainty: list[str] = Field(default_factory=list)
    evidence_status: str = "structural_only"


class CognitiveResult(BaseModel):
    response: str
    decision: DecisionRecord
    trace: CognitiveTrace

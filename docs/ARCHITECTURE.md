# PAMASMMA v4.2 — Cognitive Operating System Architecture

## Purpose

PAMASMMA is a provider-neutral assistant platform whose intelligence is implemented as a governed cognitive pipeline rather than a single model call.

The architecture separates model capability from cognitive control, memory from truth, response generation from verification, and application code from deployment infrastructure.

Nakima remains a separate repository and is not embedded into PAMASMMA.

## Cognitive lifecycle

~~~text
OBSERVE
  ↓
INTERPRET
  ↓
CONTEXTUALIZE
  ↓
RETRIEVE MEMORY
  ↓
FORM HYPOTHESES
  ↓
PLAN
  ↓
DELIBERATE
  ↓
GENERATE
  ↓
VERIFY
  ↓
METACOGNITIVE GOVERNANCE
  ↓
DECIDE
  ↓
ACT / HAND OFF
  ↓
OBSERVE OUTCOME
  ↓
LEARN
  ↓
UPDATE MEMORY + WORLD MODEL
~~~

The HTTP request ends after a response and structured decision. Real-world action remains external unless an authorized action tool exists. Outcomes can later be recorded to close the learning loop.

## Runtime architecture

~~~text
Frontend / API clients
        │
        ▼
FastAPI transport
  ├─ authentication
  ├─ rate limits
  └─ request validation
        │
        ▼
CognitiveSystem S1–S10
  └─ stable domain identity/directive
        │
        ▼
CognitiveEngine
  ├─ ContextAssembler
  ├─ BeliefResolver
  ├─ Memory Fabric
  ├─ WorldModel
  ├─ HypothesisEngine
  ├─ ExecutivePlanner
  ├─ SpecialistRouter
  ├─ ProviderRouter
  ├─ CognitiveCritic
  ├─ EvidenceGate
  ├─ MetacognitiveGovernor
  └─ ConfidenceEngine
        │
        ├─ KernelProvider
        ├─ Local/OpenAI-compatible provider
        └─ Optional Anthropic provider
        │
        ▼
DecisionRecord + audit events
~~~

## Memory fabric

Six memory classes are recognized:

| Type | Purpose |
|---|---|
| Working | Current task state |
| Episodic | What happened in prior interaction |
| Semantic | Durable facts and generalized knowledge |
| Procedural | Reusable lessons and operating rules |
| Relationship | Entities and relationship context |
| Outcome | Decision result and prediction error |

Memory retrieval is scored from similarity, recency, importance, reliability, outcome relevance, and contextual fit.

The dependency-free local embedding mode remains available for CI and no-key deployments. A semantic external embedding adapter can be enabled separately.

## Belief and contradiction governance

Beliefs are represented with:

- evidence type
- confidence
- reliability
- source
- subject
- predicate
- object
- active/inactive status

Evidence types are FACT, INFERENCE, ASSUMPTION, PREDICTION, OPINION and UNKNOWN.

The contradiction resolver detects conflicting claims about the same subject and predicate. Historical state is not silently overwritten.

## Hypothesis and evidence stages

HypothesisEngine produces explicit candidate expectations with a basis, confidence and test.

EvidenceGate marks research and time-sensitive claims as requiring external evidence. It does not fabricate sources or claim that external verification happened.

## Executive planning and specialist routing

S1 is the executive orchestrator. S2–S10 remain specialist domain systems.

Routing is evidence-weighted and intent-aware. The system does not force every specialist to vote on every query.

Specialist prompts are independent and are synthesized by the primary system without recursive S1 invocation.

## Verification and metacognition

The generated answer passes through:

~~~text
CognitiveCritic
      ↓
EvidenceGate
      ↓
MetacognitiveGovernor
      ↓
Optional revision
      ↓
Final verification
~~~

The critic checks completeness, constraints, actionability and inappropriate certainty.

The metacognitive governor adds belief-conflict and context-depth checks.

## Confidence

Confidence is an explicit numeric output with a certainty band.

It incorporates:

- retrieved memory
- hypothesis coverage
- specialist participation
- plan completeness
- verification quality
- contradiction burden
- evidence requirements

Confidence never substitutes for external evidence.

## World model

The world model persists entities and relationships in:

~~~text
pamasmma_world_entities
pamasmma_world_relationships
~~~

This creates durable user/project context rather than relying only on raw conversation history.

## Outcome learning

Each decision can later receive an outcome.

~~~text
EXPECTED OUTCOME
      ↓
OBSERVED OUTCOME
      ↓
PREDICTION ERROR
      ↓
FAILURE DOMAIN
      ↓
LESSON
      ↓
OUTCOME MEMORY
      ↓
PROCEDURAL MEMORY
~~~

Failure domains distinguish evidence, reasoning, execution, environment, assumptions and unknown causes.

## Provider governance

Provider selection considers task complexity and sensitivity.

Sensitive requests remain in-process by default. Cloud processing requires the explicit sensitive-cloud configuration control.

The deterministic kernel is a governance/fallback control plane. It is not presented as equivalent to a frontier generative model.

## Durable persistence

Migration 002 adds:

~~~text
pamasmma_decisions
pamasmma_beliefs
pamasmma_outcomes
pamasmma_world_entities
pamasmma_world_relationships
~~~

Existing durable infrastructure remains PostgreSQL, pgvector, PostgreSQL LISTEN/NOTIFY and Redis-compatible Key Value storage.

The in-memory persistence mode is bounded and intended for tests, demos and validation.

## Eventing

Cognitive events include:

| Event | Purpose |
|---|---|
| cognitive_invocation | audit/telemetry |
| cognitive_outcome | outcome learning telemetry |
| override_queue | governed override workflow |
| scheduler_event | scheduled-system telemetry |

User-scoped events are filtered before SSE delivery.

## API additions

Existing cognitive invocation routes remain compatible. New state surfaces are:

~~~text
GET  /api/v1/cognitive/decisions
GET  /api/v1/cognitive/decisions/{decision_id}
POST /api/v1/cognitive/decisions/{decision_id}/outcome
GET  /api/v1/cognitive/outcomes
~~~

POST /api/v1/cognitive/invoke now returns the user response together with a cognitive trace and structured decision.

## Production boundary

Application readiness and infrastructure readiness are separate.

PAMASMMA must use isolated production PostgreSQL and persistent Redis-compatible storage. Midas Touch2 storage must not be reused, and a free/ephemeral cache must not be classified as durable production storage.

The Render deployment contract already models this isolation; infrastructure billing remains an activation gate.

# PAMASMMA v4.1 — Current Architecture

## System boundary

PAMASMMA owns the assistant-facing cognitive platform:

- intent and context handling
- memory and retrieval
- reasoning and planning
- provider routing
- tool and knowledge orchestration
- response validation
- authentication and session security
- audit events and action history
- outcome persistence and evaluation

Nakima is a separate repository and is not embedded in PAMASMMA.

## System overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           PAMASMMA v4.1                                   │
│                 Governed Synthetic Executive Intelligence                 │
├──────────────────┬──────────────────────┬──────────────────────────────────┤
│ Frontend         │ Backend              │ Runtime / Infrastructure          │
│ Next.js 16       │ FastAPI              │ Render                            │
│ React 19         │ Python 3.11          │ PostgreSQL + pgvector             │
│ TypeScript       │ SQLAlchemy async     │ Redis-compatible Key Value        │
│ Tailwind         │ structlog            │ GitHub Actions                     │
│ Zustand          │ SSE / auth / events  │ Kernel + optional model adapters  │
└──────────────────┴──────────────────────┴──────────────────────────────────┘
```

## Request lifecycle

```
Client
  │
  ▼
LoggingMiddleware
  │  request ID + structured logs
  ▼
RateLimitMiddleware
  │  global/API/auth/cognitive limits
  ▼
CORS
  ▼
Route Handler
  ├─ /api/v1/auth/*
  │    └─ TOTP / WebAuthn / JWT session services
  │
  ├─ /api/v1/cognitive/*
  │    └─ current-user dependency
  │         └─ cognitive system
  │              ├─ relevant-memory retrieval
  │              ├─ provider-neutral model invocation
  │              ├─ response evaluation
  │              ├─ action/event persistence
  │              └─ memory persistence
  │
  └─ /api/v1/events/stream
       └─ authenticated SSE subscribers
```

## Intelligence architecture

```
USER
  │
  ▼
ORCHESTRATOR
  │
  ├─ intent classification
  ├─ context assembly
  ├─ memory retrieval
  ├─ reasoning / planning
  ├─ provider routing
  └─ policy / validation
  │
  ▼
MODEL PROVIDER BOUNDARY
  ├─ Intelligence Kernel (deterministic, zero model key)
  ├─ OpenAI-compatible / local model
  └─ Optional Anthropic adapter
  │
  ▼
RESPONSE EVALUATOR
  │
  ▼
RESPONSE + OUTCOME MEMORY
```

Every cognitive system depends on the provider-neutral `ModelProvider` interface. Vendor SDKs
are isolated inside adapter modules.

The Intelligence Kernel is PAMASMMA's deterministic fallback and orchestration substrate.
It is intentionally not represented as equivalent to a frontier generative model.

## Persistence modes

### Durable

`PERSISTENCE_MODE=postgres` uses:

- PostgreSQL + Alembic for application persistence
- PostgreSQL LISTEN/NOTIFY for the event bus
- pgvector-backed memory storage
- Redis-compatible Key Value for sessions, WebAuthn state, rate limits, replay protection, and cache

### Ephemeral

`PERSISTENCE_MODE=memory` uses bounded in-process state.

This mode is appropriate for CI, demos, and validation. It is not durable production
storage and must not be treated as such.

## Event bus

The event bus is provider-neutral:

```
Cognitive / Override / Scheduler event
        │
        ▼
      PGEventBus
        ├─ PostgreSQL LISTEN/NOTIFY (durable mode)
        └─ in-process dispatch       (memory mode)
        │
        ├─ action/override handlers
        └─ authenticated SSE broadcast
```

| Channel | Producers | Consumers |
|---|---|---|
| cognitive_invocation | S1–S10 | action log + SSE |
| override_queue | cognitive override endpoint | override handler + SSE |
| scheduler_event | scheduled jobs | event handlers + SSE |

## Authentication architecture

### TOTP

1. Founder enrollment is protected by `PAMASMMA_BOOTSTRAP_TOKEN`.
2. The server generates the TOTP secret.
3. The secret is encrypted with AES-256-GCM before persistence.
4. Verification accepts only the user identifier and current code.
5. Replay prevention is enforced server-side.

The client never supplies the authoritative stored TOTP secret during verification.

### WebAuthn

- registration requires an authenticated founder session
- fresh challenges are stored server-side
- credential state is persisted server-side
- authentication creates a new server-bound session

### JWT sessions

- access tokens are short-lived
- refresh tokens are tied to live server-side sessions
- refresh rotates session state and token pairs
- versioned authentication namespaces permit deliberate invalidation

## Memory architecture

```
User message
   │
   ▼
Embedding service
   ├─ local deterministic 1536-dim embedding
   └─ optional OpenAI embedding adapter
   │
   ▼
Relevant-memory retrieval
   ├─ user isolation
   ├─ system isolation
   ├─ freshness policy
   └─ similarity threshold
   │
   ▼
Cognitive system
   │
   ▼
Validated response
   │
   ▼
Persist memory + action outcome
```

Durable memory uses PostgreSQL/pgvector. Ephemeral mode uses a bounded in-process store.

## Repository layout

```
backend/
  app/
    auth/
    embeddings/
    events/
    intelligence/
    middleware/
    models/
    routers/
    runtime/
    security/
    services/
    systems/
  migrations/
  tests/

frontend/
  src/
    app/
    components/
    hooks/
    lib/

docs/
render.yaml
```

Architectural boundaries:

- routers own HTTP transport
- application services own use cases
- infrastructure modules own external systems
- cognitive systems own system-specific directives and behavior
- provider adapters own vendor SDK integration
- runtime mode selects durable or ephemeral infrastructure explicitly

## Observability

Structured JSON logs carry:

- request ID
- HTTP method and path
- client information
- status
- latency
- lifecycle events
- exception summaries

Render logs and metrics are the primary deployment observability surface.

## Scheduler

Scheduled jobs run in `Africa/Nairobi` timezone.

Scheduler startup is explicit and disabled in staging/CI. Durable production enables it
on the single API instance defined by the production deployment contract.

## Production deployment contract

The canonical target is Render.

The root `render.yaml` declares:

- PAMASMMA-specific PostgreSQL
- PAMASMMA-specific persistent Key Value
- FastAPI API service
- Next.js standalone web service
- pre-deploy Alembic migrations
- readiness-gated API rollout
- kernel/local-embedding baseline with optional external model providers

PAMASMMA must not reuse another repository's database or classify a non-persistent free
Key Value instance as durable production storage.

## Quality gates

```
Backend:
  ruff
  mypy
  pytest + coverage
  durable PostgreSQL + Valkey integration

Frontend:
  TypeScript
  ESLint
  production build

Release:
  Docker image build on main
```

All gates must pass before a release is classified as production-ready.

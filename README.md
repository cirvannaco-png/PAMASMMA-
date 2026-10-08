# PAMASMMA v4.2.1

**Governed Synthetic Executive Intelligence**  
Provider-neutral cognitive infrastructure for the PAMASMMA assistant platform.

## System boundary

PAMASMMA owns the assistant-facing cognitive platform: intent handling, context, memory, reasoning/planning, model routing, tool orchestration, validation, authentication, audit events, and outcome persistence.

Nakima is a separate repository and must not be embedded into PAMASMMA.

## Architecture

```
USER
  ↓
PAMASMMA COGNITIVE ENGINE
  ↓
OBSERVE → INTERPRET → CONTEXTUALIZE
  ↓
MEMORY + BELIEFS + WORLD MODEL
  ↓
HYPOTHESES → PLAN → SPECIALIST ROUTING
  ↓
PROVIDER ROUTER
  ├── Intelligence Kernel (no model key)
  ├── Local / OpenAI-compatible model
  └── Optional Anthropic model
  ↓
CRITIC → EVIDENCE GATE → METACOGNITIVE GOVERNOR
  ↓
CONFIDENCE → DECISION RECORD
  ↓
RESPONSE + ACTION HANDOFF
  ↓
OUTCOME → LEARNING → PROCEDURAL MEMORY
```

### Provider boundary

All cognitive systems depend on the provider-neutral `ModelProvider` interface. Vendor SDKs are isolated inside adapter modules, so changing model providers does not require rewriting the cognitive systems.

### Intelligence governance

The engine explicitly separates:
- **FACT** — directly supported information
- **INFERENCE** — reasoned conclusion from available evidence
- **ASSUMPTION** — premise that has not been established
- **PREDICTION** — forward-looking expectation
- **OPINION** — value judgment or preference
- **UNKNOWN** — information that is currently unavailable

Memory is treated as evidence, not unquestionable truth. Conflicting beliefs are surfaced for resolution, hypotheses can be tested, and decision records preserve assumptions, risks, confidence, alternatives, expected outcomes, and later observed outcomes.

The verification pipeline is:

`GENERATION → CRITIC → EVIDENCE GATE → METACOGNITIVE GOVERNOR → CONFIDENCE → DECISION`

The confidence engine provides a certainty band rather than pretending heuristic confidence is a calibrated probability.

### No-key intelligence

The deterministic **PAMASMMA Intelligence Kernel** can operate without Anthropic or OpenAI credentials. Local hashing embeddings provide semantic-memory behavior without an embedding API key.

This is an orchestration and reasoning layer, not a claim that a deterministic kernel is equivalent to a frontier generative model.

## Cognitive systems

PAMASMMA exposes ten governed cognitive systems. They are domain identities inside the cognitive engine—not ten independent agents.

| System | Responsibility |
|---|---|
| **S1 — Executive Operations** | Orchestration, prioritization, decision synthesis, consequence analysis |
| **S2 — Marketing Intelligence** | Market signals, positioning, campaigns, growth intelligence |
| **S3 — Relationship Management** | Stakeholders, trust, relationship health, influence networks |
| **S4 — Creator Economy** | Content strategy, creator leverage, distribution and network effects |
| **S5 — Narrative Governance** | Brand narrative, identity coherence, messaging and symbolic architecture |
| **S6 — Audience Psychology** | Segmentation, behavioral patterns, sentiment and resonance |
| **S7 — Behavioral Consistency** | Metacognition, behavioral drift detection, governance and recalibration |
| **S8 — Persuasion Governance** | Ethical persuasion, conversion psychology and influence-risk auditing |
| **S9 — Voice & Presence** | Tone, communication style, cadence, scripts and presence |
| **S10 — Strategic Narrative** | Long-horizon strategy across 30-day, 90-day, 1-year, 3-year and 10-year horizons |

All cognitive endpoints require an authenticated session. S1 acts as the executive orchestrator while the other systems contribute specialist perspectives when the task requires them.

## Runtime modes

### Durable production

Set:

```text
PERSISTENCE_MODE=postgres
DATABASE_URL=<PostgreSQL connection string>
REDIS_URL=<Redis-compatible connection string>
```

Durable mode uses:
- PostgreSQL + Alembic for application persistence
- PostgreSQL LISTEN/NOTIFY for the event bus
- Redis-compatible storage for sessions, WebAuthn challenges/credentials, rate limits, replay protection, and cache
- pgvector-backed semantic memory when the database schema provides the vector extension

### Ephemeral validation

Set:

```text
PERSISTENCE_MODE=memory
MODEL_PROVIDER=kernel
EMBEDDING_PROVIDER=local
SCHEDULER_ENABLED=false
```

Memory mode is explicitly bounded and single-instance. It is appropriate for demos, CI, and integration validation, not durable production data.

## Security model

- Production requires an explicitly injected `SECRET_KEY` with at least 32 characters.
- Non-production environments generate an ephemeral signing secret at process startup.
- First-time founder enrollment requires `PAMASMMA_BOOTSTRAP_TOKEN`.
- TOTP secrets are encrypted at rest with AES-256-GCM.
- TOTP verification reads the secret from server-side persistence; clients cannot supply it.
- WebAuthn registration requires an authenticated founder session.
- Refresh tokens are bound to live server-side sessions and rotated.
- Authentication state uses versioned namespaces so legacy state can be invalidated deliberately.
- Rate limiting applies at global, API, authentication, and cognitive boundaries.

## Repository layout

```text
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

Routers own HTTP transport only. Application services own use-case logic and persistence access. Infrastructure modules own database, Redis, provider SDK, and event-bus boundaries.

## Local development

Prerequisites: Python 3.11+, Node.js 20+.

```bash
cp .env.example .env

cd backend
python -m pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Quality gates

Backend:

```bash
cd backend
ruff check app/ tests/
mypy app/ --ignore-missing-imports --no-strict-optional
pytest tests/ -v --cov=app
```

Frontend:

```bash
cd frontend
npm run type-check
npm run lint
npm run build
```

GitHub Actions enforces the backend and frontend gates. Docker build validation runs on `main`.

## Render deployment

The root `render.yaml` defines the Render deployment contract and pins the backend runtime to Python 3.11.9.

The API health endpoint is:

```text
GET /health
```

The frontend uses the API configured through `NEXT_PUBLIC_API_URL`.

The production `render.yaml` now declares isolated PAMASMMA PostgreSQL and persistent Key Value resources, wires them into the API, runs Alembic before rollout, and uses `/health/ready` for traffic admission. It deliberately uses the kernel/local-embedding path so baseline production does not require an external model API key.

Render billing is required before those durable resources can be provisioned. The existing Midas Touch2 PostgreSQL instance must not be reused, and the free `pamasmma-cache` Key Value instance must not be classified as durable production storage. The current `pamasmma-api-staging` and `pamasmma-web-staging` services are validation environments running the hardening branch.

## Database migrations

Alembic owns schema evolution. Application startup verifies connectivity but does not mutate production schema.

Before starting a durable environment:

```bash
cd backend
alembic upgrade head
```

The current migration chain is linear:

```text
001_initial
  ↓
002_auth_hardening
  ↓
003_cognitive_state
  ↓
004_cognitive_audit
  ↓
005_knowledge_training
  ↓
006_knowledge_training_integrity
  ↓
007_social_growth
  ↓
008_social_integrity
  ↓
009_social_delivery_resilience
```

The cognitive migrations add durable decision records, beliefs, outcomes, world-model entities/relationships, and cognitive audit state. The knowledge migrations add provenance-aware training sources/chunks and active-source deduplication/chunk-order integrity.

## Environment variables

See [`.env.example`](.env.example) for the complete template.

Core settings include:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing and application security |
| `PAMASMMA_BOOTSTRAP_TOKEN` | Founder enrollment protection |
| `PERSISTENCE_MODE` | `postgres` or `memory` |
| `DATABASE_URL` | Durable PostgreSQL connection |
| `REDIS_URL` | Durable Redis-compatible connection |
| `MODEL_PROVIDER` | `kernel`, `anthropic`, `openai-compatible`, or `hybrid` |
| `MODEL_NAME` | Local/OpenAI-compatible model identifier |
| `MODEL_MAX_TOKENS` | Maximum generation budget |
| `MODEL_API_BASE_URL` | OpenAI-compatible provider endpoint |
| `MODEL_API_KEY` | OpenAI-compatible provider credential |
| `INTELLIGENCE_MEMORY_LIMIT` | Maximum memories considered per cognitive invocation |
| `INTELLIGENCE_MAX_SPECIALISTS` | Maximum specialist systems routed per invocation |
| `INTELLIGENCE_REVISION_ENABLED` | Enables critic-driven revision |
| `INTELLIGENCE_CLOUD_FOR_SENSITIVE` | Whether sensitive requests may use cloud providers |
| `EMBEDDING_PROVIDER` | `local` or `openai` |
| `WEBAUTHN_RP_ID` | WebAuthn relying-party domain |
| `WEBAUTHN_ORIGIN` | WebAuthn browser origin |
| `ALLOWED_ORIGINS` | CORS allow-list |
| `NEXT_PUBLIC_API_URL` | Frontend API base URL |

## Release status

**v4.2 is integrated on `main`.** The cognitive operating system expansion has passed backend lint/type/tests, frontend type-check/lint/build, durable Postgres + Valkey integration, and Docker build validation.

v4.2 cognitive architecture includes:
- provider-neutral cognitive engine
- deterministic no-key intelligence kernel
- six-class memory fabric with weighted retrieval
- belief/contradiction governance
- hypothesis, planning and specialist-routing stages
- evidence gate, verification and metacognitive governance
- explicit confidence and structured decision records
- outcome learning with procedural lessons
- durable world model and relationship graph
- explicit durable and ephemeral runtime modes
- TOTP/WebAuthn/JWT authentication hardening
- user-isolated SSE events
- Alembic-owned schema migrations
- Render deployment configuration
- backend/frontend CI gates
- production-oriented logging and rate limiting
- structured cognitive traces and decision telemetry
- runtime provider failover
- explicit evidence and uncertainty governance

The application code, durable migration path, scheduled-delivery resilience, and CI gates are production-hardened. Final launch still depends on external infrastructure provisioning and platform-side credentials/approvals: isolated durable PostgreSQL + Redis-compatible storage, real OAuth app credentials, redirect URIs, verified domains where required, platform scopes/app review, and ad-account permissions. Those controls cannot be bypassed by application code.


## Knowledge Training
PAMASMMA includes a governed Knowledge Training subsystem for importing books, notes, documents, subtitles, audio and video. Sources are parsed, chunked, embedded and retrieved as provenance-aware cognitive context; uploads do not silently modify model weights. See `docs/KNOWLEDGE_TRAINING.md` for supported formats, API endpoints and governance.
## Social Growth

PAMASMMA now includes a governed social execution layer at `/social`. It provides provider-neutral account connections, publishing and scheduling, engagement synchronization and replies, analytics adapters, campaign planning, an explicit campaign approval gate, and resilient scheduled delivery with bounded retries and worker leasing. Platform adapters remain isolated from the cognitive engine. See [docs/SOCIAL_GROWTH.md](docs/SOCIAL_GROWTH.md).

## MCP Connection Catalog

PAMASMMA includes a curated MCP capability catalog and UI discovery layer for high-value integrations spanning executive operations, personal assistance, marketing, customer support, content creation, knowledge and observability.

Core candidates include GitHub, GitLab, Google Workspace expansion, Notion, Slack, Linear, Sentry, HubSpot, Figma, Canva, Google Analytics 4 and Google Search Console. Optional candidates include Jira, Grafana and Apify.

The catalog does not auto-install or trust a server. MCP Registry entries are discovery metadata; endpoint selection, credentials, scopes and enablement remain operator-controlled.

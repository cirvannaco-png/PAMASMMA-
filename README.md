# PAMASMMA v4.1

**Governed Synthetic Executive Intelligence**  
Provider-neutral cognitive infrastructure for the PAMASMMA assistant platform.

## System boundary

PAMASMMA owns the assistant-facing cognitive platform: intent handling, context, memory, reasoning/planning, model routing, tool orchestration, validation, authentication, audit events, and outcome persistence.

Nakima is a separate repository and must not be embedded into PAMASMMA.

## Architecture

```
USER
  ↓
PAMASMMA ORCHESTRATOR
  ↓
INTENT + CONTEXT
  ↓
MEMORY
  ↓
REASONING / PLANNING
  ↓
PROVIDER ROUTER
  ├── Intelligence Kernel (no model key)
  ├── Local / OpenAI-compatible model
  └── Optional Anthropic model
  ↓
TOOLS / KNOWLEDGE
  ↓
RESPONSE VALIDATION
  ↓
RESPONSE
  ↓
ACTION LOG + MEMORY
```

### Provider boundary

All cognitive systems depend on the provider-neutral `ModelProvider` interface. Vendor SDKs are isolated inside adapter modules, so changing model providers does not require rewriting the cognitive systems.

### No-key intelligence

The deterministic **PAMASMMA Intelligence Kernel** can operate without Anthropic or OpenAI credentials. Local hashing embeddings provide semantic-memory behavior without an embedding API key.

This is an orchestration and reasoning layer, not a claim that a deterministic kernel is equivalent to a frontier generative model.

## Cognitive systems

PAMASMMA currently exposes ten governed cognitive systems, S1–S10. All cognitive endpoints require an authenticated session.

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

The repository currently contains a zero-key, ephemeral Render blueprint because the Render workspace does not have a second free PostgreSQL allocation available for PAMASMMA. The existing free PostgreSQL instance is owned by another project and is not reused.

A production durable deployment must provision a PAMASMMA-specific PostgreSQL database and durable Redis-compatible storage, then set `PERSISTENCE_MODE=postgres` and wire `DATABASE_URL` and `REDIS_URL` into the API service. Do not share another repository's database.

## Database migrations

Alembic owns schema evolution. Application startup verifies connectivity but does not mutate production schema.

Before starting a durable environment:

```bash
cd backend
alembic upgrade head
```

Migration `002_auth_hardening` introduces the stable `user_key` identity key and its unique index.

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
| `EMBEDDING_PROVIDER` | `local` or `openai` |
| `WEBAUTHN_RP_ID` | WebAuthn relying-party domain |
| `WEBAUTHN_ORIGIN` | WebAuthn browser origin |
| `ALLOWED_ORIGINS` | CORS allow-list |
| `NEXT_PUBLIC_API_URL` | Frontend API base URL |

## Release status

v4.1 hardening includes:
- provider-neutral intelligence architecture
- deterministic no-key intelligence kernel
- local semantic embeddings
- explicit durable and ephemeral runtime modes
- TOTP/WebAuthn/JWT authentication hardening
- user-isolated SSE events
- Alembic-owned schema migrations
- Render deployment configuration
- backend/frontend CI gates
- production-oriented logging and rate limiting

The remaining production gate is infrastructure: PAMASMMA needs isolated durable PostgreSQL and Redis-compatible storage before the deployment can truthfully be classified as durable production.

# PAMASMMA v4.1 — Deployment Guide

PAMASMMA is deployed as two independently deployable services:

- **API:** FastAPI
- **Web:** Next.js

The canonical deployment target is Render. PAMASMMA does not depend on Railway,
Supabase, Upstash, Anthropic, or OpenAI for its baseline no-key deployment.

## 1. Deployment modes

### Durable production

Use this mode for real production data.

Required infrastructure:

- PAMASMMA-specific PostgreSQL database with pgvector support
- PAMASMMA-specific durable Redis-compatible Key Value store
- Isolated from other repositories and applications
- API environment: `PERSISTENCE_MODE=postgres`

Required API variables:

```text
APP_ENV=production
DEBUG=false
SECRET_KEY=<generated secret, at least 32 characters>
PAMASMMA_BOOTSTRAP_TOKEN=<separate enrollment secret>
PERSISTENCE_MODE=postgres
DATABASE_URL=<PAMASMMA PostgreSQL connection string>
REDIS_URL=<PAMASMMA Redis-compatible connection string>
MODEL_PROVIDER=kernel
EMBEDDING_PROVIDER=local
SCHEDULER_ENABLED=false
WEBAUTHN_RP_ID=<production web domain>
WEBAUTHN_RP_NAME=PAMASMMA
WEBAUTHN_ORIGIN=https://<production web domain>
ALLOWED_ORIGINS=["https://<production web domain>"]
```

Anthropic and OpenAI credentials are optional provider integrations. They are not
required when the kernel and local embeddings are selected.

### Ephemeral validation

Use this mode for demonstrations, CI, and staging:

```text
APP_ENV=staging
PERSISTENCE_MODE=memory
MODEL_PROVIDER=kernel
EMBEDDING_PROVIDER=local
SCHEDULER_ENABLED=false
```

The application uses bounded in-process state and deliberately does not claim
durability.

## 2. Render services

The repository root contains `render.yaml`.

It defines:

- `pamasmma-api`
- `pamasmma-web`

The API is a Python 3.11.9 deployment and exposes `/health`.
The frontend uses Next.js standalone output.

The production web command uses the standalone server directly:

```text
node .next/standalone/server.js
```

Do not change this back to `next start` while `output: standalone` is enabled.

## 3. Database migrations

Alembic owns all schema evolution.

Before a durable production API is started:

```bash
cd backend
alembic upgrade head
```

Application startup verifies connectivity only. It does not mutate the production
schema.

Migration `002_auth_hardening` creates the stable `user_key` identity column,
backfills it from the existing username, and adds uniqueness.

On Render free compute, automatic `preDeployCommand` migrations are not available;
use a controlled migration execution path or paid compute with a pre-deploy migration
command.

## 4. Security

Production secrets must be supplied through the deployment platform's secret
configuration. Never commit real credentials.

Required controls:

- `SECRET_KEY` is mandatory in production.
- `PAMASMMA_BOOTSTRAP_TOKEN` is mandatory for founder enrollment.
- TOTP secrets are encrypted with AES-256-GCM.
- TOTP verification reads the server-side secret.
- WebAuthn registration requires an authenticated session.
- Refresh tokens are bound to live server-side sessions and rotate on refresh.
- Rate limiting applies globally and at authentication/API/cognitive boundaries.
- CORS is an explicit allow-list.

## 5. Health and observability

The API exposes:

```text
GET /health
```

Durable production health should report:

```json
{
  "status": "healthy",
  "database": true,
  "redis": true,
  "persistence": "postgres",
  "intelligence": "kernel",
  "embeddings": "local"
}
```

The structured logger emits JSON request/start/end and lifecycle events.

Render logs and metrics are the first-line runtime observability surface.

## 6. Verification gates

Before release:

```bash
cd backend
ruff check app/ tests/
mypy app/ --ignore-missing-imports --no-strict-optional
pytest tests/ -v --cov=app

cd ../frontend
npm run type-check
npm run lint
npm run build
```

GitHub Actions must finish successfully for the release head.

After deployment:

1. Confirm the deployment is `live`.
2. Confirm `/health` is healthy.
3. Confirm there are no new runtime error logs.
4. Verify authentication and founder enrollment.
5. Verify authenticated cognitive system listing.
6. Invoke S1 using the kernel provider.
7. Verify SSE streaming.
8. Verify user-isolated action logs.
9. Verify token refresh and logout.
10. Verify persistent memory/action-log behavior in durable mode.

## 7. Staging validation completed

A Render staging deployment of the PAMASMMA branch has been exercised with:

- Python 3.11.9
- Kernel intelligence
- Local embeddings
- Ephemeral memory mode
- Next.js standalone frontend
- Structured startup/shutdown logging

The API and web staging services reached `live` state and the application startup
completed successfully.

## 8. Current infrastructure constraint

The current Render workspace already has one active free PostgreSQL instance owned
by another project. PAMASMMA must not reuse that database.

The workspace's free Key Value resource does not provide the persistence guarantees
required for durable production. A separate PAMASMMA PostgreSQL database and durable
Redis-compatible resource must therefore be provisioned before PAMASMMA is declared
durable production.

Do not bypass this requirement by sharing another repository's database or by
pretending memory-mode persistence is durable.

## 9. Rollback

Rollback the Render service to the last known-good deployment after preserving
application logs and identifying the triggering commit.

For database changes, use an explicit backward-compatible migration strategy.
Do not rely on application startup to reverse schema changes.

## 10. Repository boundary

PAMASMMA owns the assistant platform and its cognitive infrastructure.

Nakima is a separate repository and must remain outside the PAMASMMA deployment
boundary.

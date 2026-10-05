# PAMASMMA v4.1 Migration Notes

## Authentication

TOTP verification no longer accepts a client-supplied secret. The backend stores
the TOTP secret encrypted with AES-256-GCM and verifies only the supplied code
against the server-side secret.

WebAuthn registration requires an authenticated founder session.

Refresh-token rotation checks the live server-side session before revoking it.

## Runtime persistence

Two explicit modes now exist:

- \`postgres\`: durable PostgreSQL/pgvector plus Redis-compatible session storage.
- \`memory\`: bounded, ephemeral in-process storage for CI, demos and zero-datastore
  Render deployments.

Do not treat memory mode as durable production persistence.

## Intelligence providers

The cognitive systems now depend on the provider-neutral intelligence layer.

Default no-key path:

- \`MODEL_PROVIDER=kernel\`
- \`EMBEDDING_PROVIDER=local\`

Optional adapters:

- \`MODEL_PROVIDER=anthropic\`
- \`MODEL_PROVIDER=openai-compatible\` for Ollama or another compatible endpoint
- \`EMBEDDING_PROVIDER=openai\`

No Anthropic or OpenAI API key is required in kernel/local mode.

## Database migration

Durable mode requires:

\`\`\`bash
cd backend
alembic upgrade head
\`\`\`

Migration \`002_auth_hardening\` adds the stable \`user_key\` used by the
authentication service and backfills it from existing usernames.

## Render

The root \`render.yaml\` defines a two-service zero-key deployment:

- \`pamasmma-api\`
- \`pamasmma-web\`

The default Render blueprint intentionally uses memory persistence because the
workspace already has an active free Postgres database and a second database
requires billing.

For durable production, provision PostgreSQL and persistent Redis-compatible
storage and set:

\`\`\`text
PERSISTENCE_MODE=postgres
SCHEDULER_ENABLED=true
EMBEDDING_PROVIDER=local
MODEL_PROVIDER=kernel
\`\`\`

Then attach the generated database and Redis connection strings.

## Rollback

Rollback the application by reverting the merge commit. Before rollback of the
authentication changes, rotate any credentials issued during the hardened
deployment and review active sessions because the Redis namespace was versioned
to invalidate legacy auth state.

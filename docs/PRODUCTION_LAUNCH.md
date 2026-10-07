# PAMASMMA Production Launch Contract

This document separates controls PAMASMMA can enforce in code from controls owned by external platforms or the production environment.

## 1. Backend callback URLs

For the default Render deployment, the OAuth callback pattern is:

`https://pamasmma-api.onrender.com/api/v1/social/oauth/{platform}/callback`

Use the exact URL for each OAuth provider:

- Meta / Instagram: `https://pamasmma-api.onrender.com/api/v1/social/oauth/facebook/callback` and `.../instagram/callback`
- TikTok: `https://pamasmma-api.onrender.com/api/v1/social/oauth/tiktok/callback`
- YouTube: `https://pamasmma-api.onrender.com/api/v1/social/oauth/youtube/callback`
- LinkedIn: `https://pamasmma-api.onrender.com/api/v1/social/oauth/linkedin/callback`
- X: `https://pamasmma-api.onrender.com/api/v1/social/oauth/x/callback`
- Threads: `https://pamasmma-api.onrender.com/api/v1/social/oauth/threads/callback`
- Pinterest: `https://pamasmma-api.onrender.com/api/v1/social/oauth/pinterest/callback`
- Reddit: `https://pamasmma-api.onrender.com/api/v1/social/oauth/reddit/callback`

Telegram and WhatsApp do not use this user-OAuth callback flow in the current adapter boundary; they require bot/business credentials and provider-specific configuration.

If a custom API domain is introduced, replace the host everywhere and register the exact resulting callback URI with each provider. Do not use wildcard callback URLs.

## 2. Required secret variables

Inject secrets through the production secret store. Never commit them.

### Meta / Instagram
`SOCIAL_META_CLIENT_ID`
`SOCIAL_META_CLIENT_SECRET`
`SOCIAL_META_REDIRECT_URI`
`SOCIAL_META_SCOPES`
`SOCIAL_META_GRAPH_VERSION`

### TikTok
`SOCIAL_TIKTOK_CLIENT_KEY`
`SOCIAL_TIKTOK_CLIENT_SECRET`
`SOCIAL_TIKTOK_REDIRECT_URI`
`SOCIAL_TIKTOK_SCOPES`

### YouTube / Google
`SOCIAL_YOUTUBE_CLIENT_ID`
`SOCIAL_YOUTUBE_CLIENT_SECRET`
`SOCIAL_YOUTUBE_REDIRECT_URI`
`SOCIAL_YOUTUBE_SCOPES`

### LinkedIn
`SOCIAL_LINKEDIN_CLIENT_ID`
`SOCIAL_LINKEDIN_CLIENT_SECRET`
`SOCIAL_LINKEDIN_REDIRECT_URI`
`SOCIAL_LINKEDIN_SCOPES`
`SOCIAL_LINKEDIN_VERSION`

The default scope includes `rw_ads` because PAMASMMA exposes LinkedIn advertising capability.

### X
`SOCIAL_X_CLIENT_ID`
`SOCIAL_X_CLIENT_SECRET`
`SOCIAL_X_REDIRECT_URI`
`SOCIAL_X_SCOPES`

X uses a server-held PKCE verifier per OAuth transaction.

### Threads
`SOCIAL_THREADS_CLIENT_ID`
`SOCIAL_THREADS_CLIENT_SECRET`
`SOCIAL_THREADS_REDIRECT_URI`
`SOCIAL_THREADS_SCOPES`

### Pinterest
`SOCIAL_PINTEREST_APP_ID`
`SOCIAL_PINTEREST_APP_SECRET`
`SOCIAL_PINTEREST_REDIRECT_URI`
`SOCIAL_PINTEREST_SCOPES`

### Reddit
`SOCIAL_REDDIT_CLIENT_ID`
`SOCIAL_REDDIT_CLIENT_SECRET`
`SOCIAL_REDDIT_REDIRECT_URI`
`SOCIAL_REDDIT_SCOPES`

### Telegram / WhatsApp
`SOCIAL_TELEGRAM_BOT_TOKEN`
`SOCIAL_WHATSAPP_ACCESS_TOKEN`

Use additional provider-specific identifiers through the account metadata / platform options boundary rather than hard-coding a single account.

## 3. Provider approval requirements

PAMASMMA does not and cannot bypass external approval.

Before public operation, obtain the provider-side permissions required by the chosen capability set. TikTok's Direct Post integration in this repository is designed around the `video.publish` scope and creator-info flow. Public visibility can remain restricted until the provider-side review/audit requirements for the client are satisfied.

LinkedIn Marketing API campaign management requires the appropriate advertising permission, including `rw_ads` for the campaign-management boundary, and the target ad account must be authorized for the application.

Pinterest advertising endpoints require the corresponding ads scopes/access, while organic Pin operations use the Pin/board permissions.

## 4. Account linking behavior

PAMASMMA supports multiple authorized accounts on the same platform.

The flow is:

`OAuth authorization → provider account discovery → explicit account selection when multiple accounts exist → encrypted server-side token storage`

The browser receives account identity metadata, not access or refresh tokens.

## 5. Advertising safety boundary

PAMASMMA can plan campaigns and persist an approval state. Campaign execution remains explicitly gated. Autonomous ad spending stays disabled unless the operator deliberately enables it and the external ad account grants the corresponding permission.

## 6. Process topology

Production is split into two application processes:

- **API** (`pamasmma-api`) — HTTP, OAuth callbacks, authenticated commands, liveness/readiness.
- **Worker** (`pamasmma-worker`) — APScheduler, scheduled social delivery, engagement sync, health reports, and recurring intelligence jobs.

Keep `SCHEDULER_ENABLED=false` on the API and `SCHEDULER_ENABLED=true` on exactly one worker instance. This prevents scheduler duplication when the HTTP service is scaled.

Start the worker with:

`cd backend && python -m app.worker`

## 7. Production database and cache

Required:

`PERSISTENCE_MODE=postgres`
`DATABASE_URL=<isolated PAMASMMA PostgreSQL>`
`REDIS_URL=<isolated PAMASMMA Key Value / Redis-compatible instance>`

The current schema head is migration `009`.

Run:

`cd backend && alembic upgrade head`

before traffic admission.

## 8. Scheduled delivery guarantees

Scheduled social posts use:

`queued → processing → published`

Transient failures use bounded exponential backoff and a worker lease. Stale leases are recoverable. The scheduler is intentionally at-least-once across external APIs; exactly-once cannot be guaranteed generically when a provider may accept a request but the network fails before PAMASMMA records the response.

## 9. Final production verification

The codebase must pass:

- backend Ruff
- backend mypy
- backend pytest
- durable PostgreSQL + Valkey migration/smoke tests
- frontend type-check
- frontend lint
- frontend production build
- Docker backend build
- Docker frontend build

Then run live provider tests for every platform whose credentials are configured:

`authorize → callback → discovery → selection → encrypted persistence → token refresh → publish → provider response → persisted outcome`

For scheduled delivery:

`queue → scheduler claim → provider publish → persisted success`

For failure handling:

`provider transient error → retry state → backoff → retry → terminal success/failed state`

For observability:

`/health` for liveness and `/health/ready` for durable dependency readiness.


## 10. Render infrastructure contract

The committed `render.yaml` defines isolated production PostgreSQL, Valkey/Key Value, API, worker, and frontend services in Frankfurt. OAuth client credentials, callback URIs, bot tokens, and advertising credentials are deliberately `sync: false` and must be entered in the Render secret store.

The production API runs the migration command before deploy admission:

`cd backend && alembic upgrade head`

The frontend uses `NEXT_PUBLIC_API_URL` and never receives provider OAuth secrets or access tokens.

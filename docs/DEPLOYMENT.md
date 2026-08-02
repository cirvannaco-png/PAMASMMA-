# PAMASMMA v4 — Deployment Guide

Stack: **Railway** (compute) + **Supabase** (Postgres + pgvector) + **Upstash** (Redis)  
Estimated setup time: ~30 minutes.

---

## 1. Supabase — Postgres + pgvector

1. Create project at [supabase.com](https://supabase.com)
2. **Enable pgvector**: Dashboard → Database → Extensions → search `vector` → enable
3. Copy connection string: Settings → Database → Connection string → URI
   - Use **Transaction mode** (port `6543`) for Railway compatibility
   - Format: `postgresql+asyncpg://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres`
4. Keep the `anon` key for future frontend-direct reads if needed

---

## 2. Upstash — Redis

1. Create database at [upstash.com](https://upstash.com) → Select **Redis**
2. Region: closest to Railway region (e.g. `us-east-1` if using Railway US East)
3. **TLS must be enabled** — use the `rediss://` URL (note double-s)
4. Copy the `.env` connection string from the Upstash dashboard

---

## 3. Anthropic + OpenAI Keys

- **Anthropic API key**: [console.anthropic.com](https://console.anthropic.com) → API Keys → Create
- **OpenAI API key** (embeddings): [platform.openai.com](https://platform.openai.com) → API keys → Create
  - Only `text-embedding-3-small` is used — cheapest tier

---

## 4. Railway — Backend (FastAPI)

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login

# From repo root
railway init
# Select: "Deploy from source" → choose your GitHub repo

# Create backend service
railway service create pamasmma-api
railway service up --source=backend

# Set environment variables
railway variables set \
  DATABASE_URL="postgresql+asyncpg://..." \
  REDIS_URL="rediss://..." \
  ANTHROPIC_API_KEY="sk-ant-..." \
  OPENAI_API_KEY="sk-..." \
  SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(64))')" \
  APP_ENV="production" \
  WEBAUTHN_RP_ID="your-domain.app" \
  WEBAUTHN_ORIGIN="https://your-domain.app" \
  ALLOWED_ORIGINS='["https://your-domain.app"]'

# Run migrations
railway run alembic -c backend/alembic.ini upgrade head

# Deploy
railway up --service pamasmma-api
```

---

## 5. Railway — Frontend (Next.js)

```bash
railway service create pamasmma-web
railway service up --source=frontend

railway variables set \
  NEXT_PUBLIC_API_URL="https://pamasmma-api.up.railway.app/api/v1"

railway up --service pamasmma-web
```

---

## 6. GitHub Actions Secrets

Set these in: `github.com/<org>/<repo>` → Settings → Secrets → Actions

| Secret | Value |
|--------|-------|
| `SECRET_KEY` | 64-char hex string |
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `RAILWAY_TOKEN` | From Railway → Account Settings → Tokens |

---

## 7. Custom Domain (optional)

Railway → Service → Settings → Custom Domains:
- `api.pamasmma.app` → pamasmma-api service
- `pamasmma.app` → pamasmma-web service

Update environment variables:
```bash
railway variables set \
  WEBAUTHN_RP_ID="pamasmma.app" \
  WEBAUTHN_ORIGIN="https://pamasmma.app" \
  ALLOWED_ORIGINS='["https://pamasmma.app"]' \
  --service pamasmma-api
```

---

## 8. Verify Deployment

```bash
# Health check
curl https://api.pamasmma.app/health
# Expected: {"status":"healthy","database":true,"redis":true,"version":"4.0.0"}

# TOTP setup test
curl -X POST https://api.pamasmma.app/api/v1/auth/totp/setup \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","username":"test@test.com"}'
# Expected: {"secret":"...","uri":"otpauth://..."}
```

---

## Local Development

```bash
# Full stack via Docker
docker compose -f infrastructure/docker-compose.dev.yml up

# API only
cd backend
pip install -r requirements.txt
cp ../../.env.example .env  # fill in values
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend only
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run dev
```

---

## Rollback

```bash
# Railway keeps last 5 deployments
railway deployments list --service pamasmma-api
railway rollback --deployment <deployment-id> --service pamasmma-api
```

---

## Monitoring

Railway provides:
- Build + runtime logs: `railway logs --service pamasmma-api`
- Metrics dashboard in Railway UI
- Upstash dashboard shows Redis memory + ops/sec
- Supabase dashboard shows DB size + query performance

All API requests are structured-logged (JSON via structlog) and visible in Railway's log drain.

# ⬡ PAMASMMA v4
**Governed Synthetic Executive Intelligence**  
*Principal cognitive infrastructure for Kelson Mwangi · Cirvanna · Nakuru, Kenya*

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PAMASMMA v4                          │
│              Governed Synthetic Executive AI            │
├────────────────┬────────────────┬───────────────────────┤
│   Frontend     │    Backend     │    Infrastructure     │
│   Next.js 15   │   FastAPI      │   Supabase (Postgres) │
│   TypeScript   │   Python 3.11  │   Upstash (Redis)     │
│   Tailwind CSS │   Async/await  │   Railway (Deploy)    │
└────────────────┴────────────────┴───────────────────────┘
```

## Cognitive Systems (S1–S10)

| ID  | System                | Color     | Role                                    |
|-----|-----------------------|-----------|-----------------------------------------|
| S1  | Executive Operations  | `#6B3FFB` | Decision core · priority synthesis      |
| S2  | Marketing Intelligence| `#00D4FF` | Brand positioning · market signals      |
| S3  | Relationship Mgmt     | `#D4AF37` | Stakeholder mapping · trust calibration |
| S4  | Creator Economy       | `#3BFFA0` | Content strategy · distribution intel   |
| S5  | Narrative Governance  | `#FF5B8B` | Story coherence · message sovereignty   |
| S6  | Audience Psychology   | `#FF8C42` | Behavioral modeling · identity resonance|
| S7  | Behavioral Consistency| `#A97FFF` | Pattern enforcement · persona integrity |
| S8  | Persuasion Governance | `#FF4D6D` | Ethical influence · conversion intel    |
| S9  | Voice & Presence      | `#5BFFD0` | Tone synthesis · presence amplification |
| S10 | Strategic Narrative   | `#FFD700` | Long-arc positioning · vision crystalize|

## Personality Baseline

| Trait           | Value | Description                    |
|-----------------|-------|--------------------------------|
| Assertiveness   | 0.84  | Direct · unwavering · decisive |
| Verbosity       | 0.72  | Dense but not bloated          |
| Formality       | 0.61  | Professional · not academic    |
| Strategic Depth | 0.91  | Operate two levels above       |

## Tech Stack

**Backend**
- FastAPI + Uvicorn (async, uvloop)
- SQLAlchemy 2.0 async + asyncpg
- Postgres LISTEN/NOTIFY event bus (replaces Kafka)
- pgvector for semantic memory retrieval
- TOTP (pyotp) + WebAuthn/FIDO2 (py_webauthn)
- APScheduler — 6 background jobs
- Redis (Upstash) — sessions, WebAuthn challenges, rate limiting
- OpenAI `text-embedding-3-small` for pgvector memory embeddings
- Anthropic Claude for all 10 cognitive system responses

**Frontend**
- Next.js 15 (App Router, standalone output)
- TypeScript 5 + Tailwind CSS
- Zustand state management (ESM-safe static imports)
- SSE streaming for cognitive system responses
- Design system: Obsidian / Gold / Silver / Magenta

**Infrastructure**
- Supabase (Postgres + pgvector hosting)
- Upstash (Redis, serverless)
- Railway (API + Web deployment)
- GitHub Actions (CI + deploy)

## Local Development

**Prerequisites:** Docker Desktop, Python 3.11+, Node 20+

```bash
# 1. Clone and configure
git clone https://github.com/cirvannaco-png/PAMASMMA-.git
cd PAMASMMA-
cp .env.example .env
# Edit .env with your actual credentials — see Environment Variables below

# 2. Start full stack with Docker
docker compose -f infrastructure/docker-compose.dev.yml up

# OR run services individually:

# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Testing

```bash
cd backend
pytest tests/ -v --cov=app
```

## Deployment (Railway)

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login

# Link to your project
railway link

# Run migrations
railway run alembic -c backend/alembic.ini upgrade head

# Deploy
railway up
```

Or push to `main` — GitHub Actions handles the rest automatically.

## Environment Variables

See `.env.example` for all required variables.

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | 64-char hex — generate with `python -c "import secrets; print(secrets.token_hex(64))"` |
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://...` — Supabase connection string |
| `REDIS_URL` | ✅ | `rediss://...` — Upstash Redis URL |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic API key for all 10 cognitive systems |
| `OPENAI_API_KEY` | ✅ | OpenAI API key for `text-embedding-3-small` pgvector embeddings |
| `WEBAUTHN_RP_ID` | ✅ | Relying party domain (e.g. `pamasmma.app`) |
| `WEBAUTHN_ORIGIN` | ✅ | Full origin URL (e.g. `https://pamasmma.app`) |
| `ALLOWED_ORIGINS` | ✅ | JSON list of allowed CORS origins |
| `NEXT_PUBLIC_API_URL` | ✅ | Frontend → API URL (e.g. `https://api.pamasmma.app/api/v1`) |

**GitHub Secrets required for CI/CD:**
- `SECRET_KEY` — 64-char hex secret
- `ANTHROPIC_API_KEY` — Anthropic API key
- `OPENAI_API_KEY` — OpenAI API key (for embeddings)
- `RAILWAY_TOKEN` — Railway deploy token

## Changelog

### v4.0.0 (current)
- Initial release: 10 cognitive systems (S1–S10)
- TOTP + WebAuthn/FIDO2 dual-factor auth
- pgvector semantic memory with 90-day freshness policy
- Postgres LISTEN/NOTIFY event bus (zero external message broker)
- APScheduler — 6 background jobs (purge, sessions, audit, digest, coherence, health)
- SSE streaming for real-time cognitive system responses

### Bug Fixes Applied
- **`config.py`** — Added missing `openai_api_key` field to `Settings` (required for embeddings service)
- **`embeddings/service.py`** — `AsyncOpenAI` now receives `api_key` from Settings explicitly
- **`database.py`** — Removed unused `asynccontextmanager` and `sa_event` imports
- **`migrations/001_initial.py`** — Added missing columns to `pamasmma_users` table: `totp_enabled`, `is_active`, `updated_at`, `last_login_at` (ORM model and migration were out of sync)
- **`store.ts`** — Replaced CommonJS `require()` calls inside Zustand actions with ESM-safe static imports
- **`ci.yml`** — Fixed `npm ci` → `npm install` (no lock file in repo) and corrected `cache-dependency-path` to `frontend/package.json`; added `OPENAI_API_KEY` to CI environment

---

*"Infrastructure of identity."*  
Cirvanna · Nakuru, Kenya · 2025

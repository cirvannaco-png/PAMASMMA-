# PAMASMMA v4 — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PAMASMMA v4                                   │
│                  Governed Synthetic Executive Intelligence               │
├──────────────────┬──────────────────────────┬───────────────────────────┤
│   Frontend       │       Backend            │     Infrastructure        │
│   Next.js 15     │       FastAPI            │     Supabase (Postgres)   │
│   TypeScript     │       Python 3.11+       │     Upstash (Redis)       │
│   Tailwind CSS   │       Async/uvloop       │     Railway (Deploy)      │
│   Zustand        │       structlog          │     GitHub Actions (CI)   │
└──────────────────┴──────────────────────────┴───────────────────────────┘
```

## Request Lifecycle

```
Client Request
    │
    ▼
LoggingMiddleware          ← attaches X-Request-ID, structured log
    │
    ▼
RateLimitMiddleware        ← Redis sliding window (IP + route)
    │
    ▼
CORSMiddleware
    │
    ▼
Route Handler
    │
    ├─ /api/v1/auth/*      → Auth Router (TOTP / WebAuthn / JWT)
    │
    ├─ /api/v1/cognitive/* → Cognitive Router
    │       │
    │       ▼
    │   get_current_user() → decode JWT → verify Redis session
    │       │
    │       ▼
    │   CognitiveSystem.invoke()
    │       │
    │       ├─ retrieve_relevant_memories() → pgvector cosine search
    │       ├─ anthropic.messages.create()  → Anthropic API
    │       ├─ pg_notify('cognitive_invocation') → PGEventBus
    │       └─ store_memory()              → pgvector embed + insert
    │
    └─ /api/v1/events/stream → SSE fan-out from PGEventBus
```

## Event Bus

Postgres LISTEN/NOTIFY replaces Kafka. Zero external dependencies.

```
CognitiveSystem._post_invoke()
    │
    └─ pg_notify('cognitive_invocation', payload_json)
            │
            ▼
    PGEventBus._dispatch()
            │
            ├─ handle_cognitive_invocation() → INSERT pamasmma_action_log
            └─ broadcast() → SSE fan-out to all connected clients
```

**Channels:**
| Channel | Producer | Consumer |
|---|---|---|
| `cognitive_invocation` | S1–S10 systems | action log + SSE |
| `override_queue` | POST /cognitive/override | override_queue table + SSE |
| `scheduler_event` | APScheduler jobs | structured log + SSE |

## Authentication Flow

```
1. TOTP Setup
   POST /auth/totp/setup
   └─ Returns: { secret, uri }
   └─ Frontend: render QR code from uri

2. TOTP Verify
   POST /auth/totp/verify { user_id, secret, code }
   └─ pyotp.verify(code, valid_window=1)
   └─ Redis: mark_totp_used() → replay prevention
   └─ Returns: { access_token, refresh_token }

3. Authenticated Requests
   Authorization: Bearer <access_token>
   └─ decode_token() → validate JWT
   └─ get_session(session_id) → confirm Redis session live
   └─ inject current_user into route handler

4. Token Refresh
   POST /auth/token/refresh { refresh_token }
   └─ revoke old session
   └─ create new session
   └─ issue new token pair

5. WebAuthn (optional hardware key)
   POST /auth/webauthn/register/begin  → challenge stored in Redis (120s TTL)
   POST /auth/webauthn/register/complete → verify + store credential in Redis
   POST /auth/webauthn/authenticate/begin → fresh challenge
   POST /auth/webauthn/authenticate/complete → verify + update sign_count
```

## Memory Architecture

```
User Message
    │
    ▼
embed_text(message)           ← text-embedding-3-small, 1536 dims
    │
    ▼
retrieve_relevant_memories()
    SELECT ... FROM pamasmma_memories
    WHERE user_id = ? AND system_id = ?
      AND created_at > NOW() - 90 days
      AND 1 - (embedding <=> query_vec) > 0.78
    ORDER BY embedding <=> query_vec
    LIMIT 5
    │
    ▼
Inject into system prompt as "RELEVANT MEMORY CONTEXT"
    │
    ▼
Anthropic API call
    │
    ▼
store_memory(response)        ← embed + INSERT INTO pamasmma_memories
```

**Indexes:**
- `ivfflat` cosine index on `embedding` (lists=100) — sub-10ms retrieval
- B-tree indexes on `user_id`, `system_id`, `created_at`

## Scheduler Jobs

All jobs run in `Africa/Nairobi` timezone (EAT, UTC+3).

| ID | Name | Schedule | Purpose |
|----|------|----------|---------|
| J1 | memory_purge | Daily 02:00 | Delete memories > 180 days |
| J2 | session_cleanup | Every 30 min | Reconcile orphaned Redis sessions |
| J3 | behavioral_audit | Daily 06:00 | S7 personality drift check |
| J4 | market_digest | Daily 07:00 | S2 market signal compilation |
| J5 | narrative_coherence | Monday 08:00 | S5 brand coherence scan |
| J6 | health_report | Every 15 min | DB + Redis health emit |

## Data Models

```
pamasmma_users
├─ id (UUID PK)
├─ username (unique)
├─ totp_secret_enc (AES-GCM encrypted)
├─ totp_enabled (bool)
├─ webauthn_registered (bool)
└─ created_at, updated_at, last_login_at

pamasmma_memories
├─ id (UUID PK)
├─ user_id, system_id (indexed)
├─ content (text)
├─ embedding (vector(1536)) ← ivfflat indexed
├─ metadata (text/JSON)
└─ created_at (indexed)

pamasmma_action_log
├─ id (UUID PK)
├─ system_id, system_name
├─ user_id (indexed)
├─ query_preview (500 chars)
├─ latency_ms
└─ created_at (indexed)

pamasmma_override_queue
├─ id (UUID PK)
├─ system_id (indexed)
├─ directive, reason
├─ user_id
├─ status (pending/applied/rejected)
└─ created_at, applied_at
```

## Personality Baseline

Enforced at the `CognitiveSystem.build_system_prompt()` level — injected into every LLM call. Cannot be overridden at the API layer.

| Trait | Value | Effect |
|---|---|---|
| Assertiveness (ASS) | 0.84 | Direct, no hedging, no passive voice |
| Verbosity (VBY) | 0.72 | Dense but not bloated — 2–4 paragraphs |
| Formality (FML) | 0.61 | Professional but not academic |
| Strategic Depth (SDT) | 0.91 | Always operate two levels above the question |

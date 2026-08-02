# PAMASMMA v4 — API Reference

Base URL: `https://api.pamasmma.app/api/v1`  
Auth: `Authorization: Bearer <access_token>` (all `/cognitive/*` routes)

---

## Authentication

### POST `/auth/totp/setup`
Generate a TOTP secret for a user.

**Request**
```json
{ "user_id": "kelson-mwangi", "username": "kelson@cirvanna.co" }
```
**Response**
```json
{ "secret": "JBSWY3DPEHPK3PXP", "uri": "otpauth://...", "issuer": "PAMASMMA" }
```

---

### POST `/auth/totp/verify`
Verify a TOTP code and receive JWT tokens.

**Request**
```json
{ "user_id": "kelson-mwangi", "secret": "JBSWY3DPEHPK3PXP", "code": "123456" }
```
**Response**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```
**Errors**
- `401` — Invalid or expired TOTP code
- `429` — Rate limit exceeded (5/min per IP)

---

### POST `/auth/token/refresh`
Silently refresh tokens. Old session is revoked.

**Request**
```json
{ "refresh_token": "eyJ..." }
```
**Response** — same shape as `/auth/totp/verify`

---

### POST `/auth/logout`
Revoke current session. Requires auth header.

**Response**
```json
{ "status": "logged_out" }
```

---

### POST `/auth/webauthn/register/begin`
Start WebAuthn hardware key registration.

**Request** `{ "user_id": "...", "username": "..." }`  
**Response** — WebAuthn `PublicKeyCredentialCreationOptions` JSON

---

### POST `/auth/webauthn/register/complete`
Complete WebAuthn registration. Stores credential in Redis.

**Request** `{ "user_id": "...", "credential": { /* WebAuthn response */ } }`  
**Response** `{ "status": "registered" }`

---

### POST `/auth/webauthn/authenticate/begin`
Start WebAuthn authentication challenge.

**Request** `{ "user_id": "..." }`  
**Response** — WebAuthn `PublicKeyCredentialRequestOptions` JSON

---

### POST `/auth/webauthn/authenticate/complete`
Complete WebAuthn auth. Returns JWT tokens on success.

**Request** `{ "user_id": "...", "credential": { /* WebAuthn response */ } }`  
**Response** — same as `/auth/totp/verify`

---

## Cognitive Systems

All cognitive endpoints require `Authorization: Bearer <access_token>`.

### GET `/cognitive/systems`
List all 10 cognitive systems.

**Response**
```json
{
  "systems": [
    { "id": "S1", "name": "Executive Operations", "color": "#6B3FFB" },
    ...
  ],
  "count": 10
}
```

---

### POST `/cognitive/invoke`
Invoke a cognitive system with conversation history.

**Request**
```json
{
  "system_id": "S1",
  "messages": [
    { "role": "user", "content": "What should I prioritize this quarter?" }
  ],
  "stream": false
}
```
**Response (stream: false)**
```json
{
  "system_id": "S1",
  "system_name": "Executive Operations",
  "response": "Execute the following three priorities..."
}
```
**Response (stream: true)** — `Content-Type: text/event-stream`
```
data: Execute the
data:  following three
data:  priorities...
data: [DONE]
```

**Validation**
- `system_id` must match `^S([1-9]|10)$`
- `messages` max 50 items, each content max 32,000 chars
- Rate limit: 20 requests/min per IP

---

### GET `/cognitive/action-log`
Retrieve invocation history.

**Query params**
- `system_id` (optional) — filter by system, e.g. `S1`
- `limit` (default 50, max 200)

**Response**
```json
{
  "entries": [
    {
      "id": "uuid",
      "system_id": "S1",
      "system_name": "Executive Operations",
      "query_preview": "What should I prioritize...",
      "latency_ms": 1243.5,
      "created_at": "2025-06-14T07:32:11+03:00"
    }
  ],
  "count": 1
}
```

---

### POST `/cognitive/override`
Queue a behavioral override directive for a system.

**Request**
```json
{
  "system_id": "S7",
  "directive": "Increase assertiveness weighting to 0.92 for the next 48 hours.",
  "reason": "Preparing for investor pitch — need sharper tonality."
}
```
**Response** `{ "status": "queued", "system_id": "S7" }`

---

## Events (SSE)

### GET `/events/stream?token=<access_token>`
Real-time event stream. Uses EventSource (browser native).

**Note:** Auth via query param because `EventSource` doesn't support headers.

**Event shape**
```json
{ "type": "cognitive_invocation", "data": { "system_id": "S1", "latency_ms": 890 } }
{ "type": "override_queue",       "data": { "system_id": "S7", "status": "queued" } }
{ "type": "scheduler_event",      "data": { "job": "J3", "name": "behavioral_audit" } }
{ "type": "heartbeat" }
```

Heartbeat sent every 30s to keep connection alive.

---

## Health

### GET `/health`
Infrastructure health check. No auth required.

**Response**
```json
{ "status": "healthy", "database": true, "redis": true, "version": "4.0.0" }
```
`status` is `"degraded"` if any service is unreachable.

---

## Error Format

All errors follow the same shape:
```json
{ "detail": "Human-readable error message.", "path": "/api/v1/..." }
```

**Common status codes**
| Code | Meaning |
|------|---------|
| 401 | Missing, invalid, or expired token |
| 403 | Forbidden (no bearer token provided) |
| 404 | Resource not found |
| 422 | Validation error (Pydantic) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

# PAMASMMA JARVIS — Voice Architecture

**Status:** Initial GPT-Live WebRTC voice path implemented; production hardening remains open.  
**Scope:** PAMASMMA only.

## Architecture decision

Use GPT-Live as the low-latency speech interface, not as PAMASMMA's independent reasoning authority. Configure client delegation. The browser handles microphone/speaker WebRTC and transcript events; PAMASMMA authenticates the delegated transcript, persists it in the JARVIS conversation, runs the existing CognitiveEngine, and returns the verified result for spoken delivery.

This preserves one reasoning and evidence-governance authority across text and voice.

## Session startup

1. The user explicitly presses MIC in the authenticated JARVIS workspace.
2. The browser requests microphone permission and creates a WebRTC peer connection plus the `oai-events` data channel.
3. The browser creates an SDP offer and sends it to `POST /api/v1/jarvis/conversations/{conversation_id}/voice-sessions`.
4. The PAMASMMA backend verifies conversation ownership and sends the offer to `POST /v1/live/sessions` using the server-side `OPENAI_API_KEY`.
5. The Live session is configured with `gpt-live-1.1`, client delegation, `vesper` voice, bounded recent text history and `store: false`. The backend sends a stable privacy-preserving JARVIS user hash in `OpenAI-Safety-Identifier` and restricts the untrusted browser data channel to transcript/delegation events, commentary append and session close.
6. Before exposing the SDP answer, the backend registers the provider session ID, owner, conversation, model, status and a one-hour server-side expiry in PostgreSQL. A matching usage-ledger row is created in `awaiting_provider` state. If registration fails, the SDP answer is not exposed to the browser. The API key never reaches the browser.

## Client delegation lifecycle

1. Browser receives `session.input_transcript.delta` events and retains timestamped transcript fragments in memory.
2. On `session.delegation.created`, the browser uses the delegation offset to assemble the matching utterance.
3. The browser sends the delegation ID and transcript to the authenticated PAMASMMA voice-delegation endpoint.
4. PAMASMMA verifies conversation ownership and requires an active, unexpired server-registered voice session. It claims the delegation ID in PostgreSQL before cognitive work, hashing the transcript rather than retaining a second copy. A duplicate with the same transcript returns the cached completed response; reuse with a different transcript is rejected; concurrent processing is rejected. Stale processing claims can be recovered after the five-minute lease window. The same database-backed turn lease used by text protects the conversation.
5. The CognitiveEngine's decision, scoped memory/beliefs/world model and evidence governance remain authoritative.
6. PAMASMMA persists the assistant response with modality `voice`. The assistant message and completed delegation response cache are committed in one database transaction, so a completed retry cannot run cognition a second time.
7. The browser sends `session.commentary.append` with the matching delegation ID so GPT-Live can speak the backend result.
8. On user stop, the browser sends `session.close`, waits for `session.closed` where possible, then calls the authenticated session-close endpoint and releases the peer connection and microphone tracks. If the data channel or browser disappears first, the server-side one-hour expiry prevents the stale session from authorizing new delegations indefinitely.

## Privacy and security

- Microphone access starts only after an explicit user action.
- No always-on background capture or wake-word listener is implemented.
- The browser never receives the OpenAI API key.
- GPT-Live session storage is explicitly disabled (`store: false`).
- PAMASMMA does not upload/store raw audio in its own object storage in this phase.
- Voice transcripts and assistant text responses are persisted in the authenticated JARVIS conversation.
- Conversation ownership is checked before session creation and before each delegated turn.
- Voice requests have the same cognitive API rate limit as text.
- The voice model is instructed to delegate substantive requests and not invent completed actions.
- `vesper` is a supported natural British masculine voice; it is not an imitation or clone of a film actor.

## Current limitations and production blockers

The first voice path is functional code, but it is not yet production-certified:

1. Durable session registration and owner-scoped close are implemented. Server expiry is one hour; provider-side expiry and revocation semantics still need live-account verification.
2. Durable delegation idempotency is implemented with transcript-hash conflict detection, cached completed responses, concurrent-request rejection, stale-claim recovery, and atomic assistant-message/cache commit.
3. The PostgreSQL usage ledger creates one row per voice session, but rows remain `awaiting_provider`. Trusted final provider usage capture, token reconciliation and cost calculation are not implemented; do not infer costs from browser telemetry.
4. Provider outage, interrupted WebRTC, delayed transcript and concurrent duplicate delegation need live-provider integration tests.
5. Physical Android microphone, speaker, Bluetooth, screen-lock and network-handoff QA remains required.
6. The voice provider account must have GPT-Live access and a valid server-side `OPENAI_API_KEY`.
7. The browser's client-delegation event bridge is acceptable only while JARVIS has no external action tools. Before governed tools are introduced, move delegation handling to a server-side sideband connection so tool execution never depends on a client event handler.

## Acceptance criteria

- Unauthenticated or cross-owner requests cannot create a session or submit a transcript.
- Missing API key returns 503 without leaking secrets.
- Malformed or oversized SDP is rejected before provider submission.
- Provider errors return a sanitized error and do not expose provider payloads or keys.
- Microphone permission denial leaves text chat usable.
- Voice transcripts and assistant results survive page reloads.
- Repeated completed delegation IDs with the same transcript return the original stored result; different transcript reuse is rejected; concurrent processing is rejected.
- Session close releases microphone tracks and the peer connection.
- No raw audio is persisted by PAMASMMA or stored by the Live session.
- A trusted provider usage source populates the usage ledger before cost reporting; Android device QA passes before production enablement.

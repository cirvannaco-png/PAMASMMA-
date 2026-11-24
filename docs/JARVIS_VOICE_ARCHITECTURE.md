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
6. The backend returns only the Live session ID and SDP answer. The API key never reaches the browser.

## Client delegation lifecycle

1. Browser receives `session.input_transcript.delta` events and retains timestamped transcript fragments in memory.
2. On `session.delegation.created`, the browser uses the delegation offset to assemble the matching utterance.
3. The browser sends the delegation ID and transcript to the authenticated PAMASMMA voice-delegation endpoint.
4. PAMASMMA verifies conversation ownership, acquires the same database-backed turn lease used by text, stores the user message with modality `voice`, and invokes the JARVIS adapter over the existing CognitiveEngine.
5. The CognitiveEngine's decision, scoped memory/beliefs/world model and evidence governance remain authoritative.
6. PAMASMMA persists the assistant response with modality `voice` and returns it to the browser.
7. The browser sends `session.commentary.append` with the matching delegation ID so GPT-Live can speak the backend result.
8. On user stop, the browser sends `session.close`, waits for `session.closed` where possible, then releases the peer connection and microphone tracks. If the data channel closes before the final event, usage is unconfirmed.

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

1. Live session IDs are currently held by the browser and are not registered in a durable PAMASMMA voice-session table.
2. Delegation IDs are deduplicated in the active browser session but are not yet protected by a durable server-side idempotency record.
3. Final Live session usage and cost are not yet recorded in PAMASMMA's usage ledger.
4. Provider outage, interrupted WebRTC, delayed transcript and duplicate delegation behaviour need automated integration tests.
5. Physical Android microphone, speaker, Bluetooth, screen-lock and network-handoff QA remains required.
6. The voice provider account must have GPT-Live access and a valid server-side `OPENAI_API_KEY`.
7. The browser's client-delegation event bridge is appropriate while JARVIS has no external action tools. When governed tools are introduced, move delegation handling to a server-side sideband connection so tool execution never depends on a client event handler.

## Acceptance criteria

- Unauthenticated or cross-owner requests cannot create a session or submit a transcript.
- Missing API key returns 503 without leaking secrets.
- Malformed or oversized SDP is rejected before provider submission.
- Provider errors return a sanitized error and do not expose provider payloads or keys.
- Microphone permission denial leaves text chat usable.
- Voice transcripts and assistant results survive page reloads.
- Duplicate/late delegation events cannot create duplicate actions; durable idempotency must be implemented before tool execution.
- Session close releases microphone tracks and the peer connection.
- No raw audio is persisted by PAMASMMA or stored by the Live session.
- Android device QA and usage/cost telemetry pass before production enablement.

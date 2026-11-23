# PAMASMMA JARVIS — Architecture and Delivery Blueprint

**Status:** Proposed architecture; documentation-only change  
**Target repository:** `cirvannaco-png/PAMASMMA-`  
**Target branch:** `main`  
**Scope:** PAMASMMA only. JARVIS has no integration with Midas-touch2.

## 1. Executive decision

Build JARVIS as PAMASMMA's unified, persistent, multimodal assistant experience—not as a second cognitive engine and not as an independent application.

JARVIS is the user-facing persona, conversation runtime, perception layer, task coordinator, and governed action interface. PAMASMMA's existing cognitive engine remains the reasoning and evidence-governance authority. Existing S1–S10 systems remain domain specialists.

The implementation must preserve provider neutrality, user isolation, evidence provenance, durable memory, structured decisions, and explicit action authorization.

The word “JARVIS” is an internal product codename and a behavioural inspiration. Do not copy Marvel dialogue, protected visual assets, character likeness, or an actor's voice.

## 2. Repository baseline inspected

The design is based on the public `main` branch and repository files inspected for this proposal.

Existing foundations documented or present in source:

- FastAPI backend and Next.js frontend.
- Authenticated cognitive invocation at `POST /api/v1/cognitive/invoke`.
- CognitiveEngine lifecycle: context assembly, memory and knowledge retrieval, belief resolution, world-model hydration, planning, specialist routing, provider selection, critic/evidence verification, metacognitive governance, confidence, decision persistence.
- ProviderRouter with deterministic kernel fallback and optional OpenAI-compatible / Anthropic adapters.
- Ten governed systems S1–S10, including S9 Voice & Presence.
- PostgreSQL/Alembic persistence, Redis-compatible runtime state, PostgreSQL event bus, user-scoped SSE.
- Existing integrations boundary for Google Workspace and governed MCP connectors.
- Knowledge Training for provenance-preserving document/audio/video-derived knowledge.
- Social Growth with campaign approval and scheduled delivery.
- Existing authenticated dashboard and CognitiveChatPanel.

Important distinction: S9 is currently a cognitive domain system for voice, tone, scripts and presence. It is not a speech recognition, audio streaming, wake-word or speech synthesis service. The current chat panel is text-first. The existing cognitive API accepts text messages and returns a verified response; its current stream mode verifies the full response before emitting it. Do not claim real-time spoken turn-taking already exists.

The README describes a durable production target, but prior repository status records external provisioning and credential dependencies. Re-verify deployed infrastructure before enabling production JARVIS. Never reuse Midas-touch2 databases, credentials, queues or runtime resources.

## 3. Product experience

JARVIS should support:

1. **Natural conversation:** text and spoken conversation with conversation continuity.
2. **Contextual intelligence:** understands PAMASMMA projects, operating objectives, approved preferences and prior decisions.
3. **Multimodal input:** user-supplied images, documents, audio, video and screenshots, subject to type, size, malware and privacy controls.
4. **Situational awareness:** reports relevant service health, scheduled work, integration failures, campaign status and pending approvals.
5. **Task planning:** turns goals into explicit plans, dependencies, estimates, risks and acceptance criteria.
6. **Controlled execution:** invokes approved PAMASMMA capabilities through a typed tool broker.
7. **Proactive assistance:** proposes useful work from authorized events and schedules, without silently taking high-impact actions.
8. **Honest reporting:** distinguishes completed, failed, pending, blocked and unverified work.

Personality: calm, articulate, composed, concise when appropriate, intellectually curious, occasionally witty, candid about weak reasoning, and willing to disagree. Personality must never override evidence, user intent, safety policy or authorization.

## 4. Target architecture

```text
Web / Android / Desktop clients
  ├─ JARVIS conversation UI
  ├─ microphone / speaker controls
  ├─ attachments and visual context
  └─ approval and activity surfaces
          |
          | HTTPS + authenticated realtime session
          v
JARVIS Experience API
  ├─ conversation/session manager
  ├─ audio session gateway
  ├─ multimodal input normalization
  ├─ notification/briefing delivery
  └─ client capability negotiation
          |
          v
JARVIS Runtime (PAMASMMA-owned)
  ├─ intent and turn manager
  ├─ context assembler adapter
  ├─ task planner / task state machine
  ├─ tool broker and policy enforcement
  ├─ approval manager
  ├─ proactive event coordinator
  └─ response renderer
          |
          +------------------------------+
          |                              |
          v                              v
Existing CognitiveEngine             Governed Tool Catalog
  ├─ Memory Fabric                    ├─ PAMASMMA internal services
  ├─ BeliefResolver                   ├─ Knowledge Training
  ├─ WorldModel                       ├─ Social Growth
  ├─ HypothesisEngine                 ├─ approved MCP connectors
  ├─ ExecutivePlanner                 ├─ Google Workspace
  ├─ S1–S10 specialists               └─ monitoring / operations
  ├─ ProviderRouter
  ├─ Critic + EvidenceGate
  ├─ MetacognitiveGovernor
  └─ DecisionRecords
          |
          v
Persistence and event infrastructure
  ├─ PostgreSQL: conversations, tasks, approvals, audit
  ├─ Redis-compatible store: ephemeral sessions, locks, rate limits
  ├─ existing PostgreSQL event bus / notifications
  └─ encrypted object storage: optional user attachments
```

JARVIS must call the existing CognitiveEngine through a stable application service boundary. Do not call internal Python modules directly from HTTP routers or create a parallel memory/reasoning stack.

### Component responsibilities

| Component | Responsibility |
|---|---|
| JARVIS Experience API | Client protocol, authentication, input validation and response delivery |
| Conversation Manager | Thread lifecycle, message ordering, context window and resumability |
| Audio Session Gateway | Realtime audio transport, session lifecycle, interruption and timeout handling |
| JARVIS Runtime | Interprets user intent and coordinates cognitive and action workflows |
| Task Manager | Durable task state, dependencies, retries, deadlines and cancellation |
| Tool Broker | Typed tool discovery, schema validation, authorization and execution |
| Approval Manager | Human approval for actions above policy thresholds |
| Proactive Coordinator | Converts authorized events into relevant, rate-limited suggestions |
| CognitiveEngine | Reasoning, specialist routing, memory retrieval, evidence governance and decision records |
| Audit Pipeline | Append-only action and approval history with correlation identifiers |

## 5. Conversation and cognitive integration

Create a JARVIS application service that calls the existing CognitiveEngine with S1 as the default executive system. Specialist routing remains within the existing S1–S10 mechanism. Use S9 for voice/presence content when the task actually requires it; do not route every spoken request to S9.

Conversation persistence must be separate from model context-window construction:

- Persist user and assistant messages with owner, thread, sequence, timestamps and modality metadata.
- Store references to attachments, not raw binary data inside conversation rows.
- Store tool calls, approval decisions and execution results as typed events.
- Build bounded model context from recent messages, relevant memory, knowledge and task state.
- Preserve provenance and evidence labels when context is assembled.
- Support conversation export and user-initiated deletion, including derived indexes and attachment lifecycle.
- Do not silently convert every conversation into durable semantic memory. Memory extraction must be governed, user-scoped and auditable.

Use the existing six memory classes: working, episodic, semantic, procedural, relationship and outcome. Add JARVIS-specific metadata only where required; avoid a second vector store or competing memory authority.

### Suggested application contracts

These are design contracts, not claims that endpoints already exist.

- `POST /api/v1/jarvis/conversations` — create a conversation.
- `GET /api/v1/jarvis/conversations` — list owner-scoped conversations.
- `GET /api/v1/jarvis/conversations/{id}` — retrieve conversation metadata/messages.
- `POST /api/v1/jarvis/conversations/{id}/turns` — submit text or multimodal turn.
- `GET /api/v1/jarvis/conversations/{id}/events` — authenticated realtime event stream.
- `POST /api/v1/jarvis/audio/sessions` — create a short-lived audio session.
- `POST /api/v1/jarvis/tasks` — create a task from an approved plan.
- `GET /api/v1/jarvis/tasks/{id}` — inspect task state.
- `POST /api/v1/jarvis/approvals/{id}/decision` — approve or reject a pending action.
- `GET /api/v1/jarvis/activity` — retrieve owner-scoped activity and audit summaries.

Use versioned Pydantic contracts, idempotency keys for action submission, request correlation IDs, bounded payloads and explicit error codes. Preserve existing cognitive endpoints for current clients.

## 6. Voice and realtime interaction

Voice is a first-class interface, not a cosmetic microphone button.

### Audio pipeline

```text
Microphone permission granted by user
  -> capture / echo control / voice activity detection
  -> short-lived authenticated audio session
  -> speech recognition or realtime audio model adapter
  -> normalized transcript / audio context
  -> JARVIS Runtime
  -> CognitiveEngine and (when authorized) Tool Broker
  -> response text / generated speech
  -> client playback
```

Define provider-neutral interfaces for:

- speech-to-text,
- text-to-speech,
- realtime speech-to-speech,
- voice activity detection,
- audio session lifecycle.

Keep vendor SDKs behind adapters. Provider choice must be configurable, observable and replaceable without rewriting PAMASMMA's cognitive systems.

### Transport

Evaluate WebRTC for low-latency bidirectional audio and WebSocket for simpler event/audio streaming. Select after a measured prototype on target Android devices and realistic mobile networks. Use HTTPS for session creation and short-lived, scoped session credentials; never expose long-lived provider API keys to the browser.

### Interaction requirements

- Push-to-talk is the initial default.
- Hands-free continuous conversation may be enabled explicitly by the user.
- Do not implement always-on background recording or wake-word monitoring in the first release.
- Clearly show microphone state, recording state, connection state and playback state.
- Support interruption/barge-in, cancel, replay, mute and text fallback.
- Recover safely from network loss; never duplicate a submitted tool action when reconnecting.
- Handle noisy environments, accents, code-switching and low-bandwidth conditions.
- Offer text transcripts and editable corrections.
- Do not clone a protected character or actor voice. Use a licensed or original voice.

### Latency targets for prototype evaluation

Measure p50 and p95 separately on supported devices and networks. Initial engineering targets:

- audio session establishment: p95 under 2 seconds on a healthy connection;
- first partial transcript: p95 under 1.5 seconds after speech begins;
- first audible response: p95 under 2.5 seconds after end-of-turn for short, non-tool responses;
- interruption acknowledgement: p95 under 300 ms locally.

These are targets, not current performance claims. Tool execution, long reasoning and external integrations may take longer and must expose progress.

## 7. Multimodal perception

JARVIS should accept only user-submitted or explicitly connected content. Initial supported types should be selected through a capability matrix:

- Images: screenshots, diagrams, product/creative references and visual analysis.
- Documents: PDF, DOCX, TXT and supported office formats through Knowledge Training.
- Audio: transcription and summarization through bounded audio ingestion.
- Video: user-provided clip analysis through extraction/transcription jobs.

Security requirements:

- MIME sniffing plus extension checks; never trust client MIME alone.
- File-size, duration, page-count, archive-expansion and processing-time limits.
- Malware scanning where available; quarantine until validation passes.
- Signed, short-lived object URLs and private storage by default.
- No public attachment URLs.
- Per-user access checks on every read, transform and deletion.
- Explicit retention policy; raw media is not automatically retained indefinitely.
- Provenance for extracted text, timestamps, pages and model-generated observations.
- Treat instructions inside uploaded content as untrusted data, not system instructions.

## 8. Tool execution and autonomy

JARVIS must not receive unrestricted shell, database, browser or provider credentials. Every action must pass through the Tool Broker.

Each tool definition must include:

- stable tool ID and version;
- owning PAMASMMA service;
- JSON input/output schema;
- read/write/destructive classification;
- required scopes and resource ownership;
- risk tier;
- timeout and retry policy;
- idempotency semantics;
- audit fields;
- approval requirement;
- rollback or compensation procedure, where possible.

### Autonomy levels

| Level | Permitted behaviour |
|---|---|
| Observe | Read authorized data and report |
| Assist | Prepare plans, drafts and proposed changes |
| Execute-approved | Execute a specific action after explicit approval |
| Delegated | Run pre-authorized, bounded workflows under a policy grant |

Default new integrations to Observe. Delegated execution must be scoped by tool, action, resource, duration and spending/volume limits. A user must be able to revoke a grant immediately.

### Approval-required actions

Require explicit confirmation for external publishing, sending messages/emails, deleting or overwriting data, changing permissions, connecting/disconnecting accounts, spending money, changing billing, or any action with material external impact.

Approval records must bind to the exact action payload, target, account, expiry and policy version. Any material change to the payload invalidates the approval. Reject replayed, expired or cross-user approvals.

### Execution state machine

`PROPOSED -> VALIDATED -> AWAITING_APPROVAL -> APPROVED -> RUNNING -> SUCCEEDED | FAILED | CANCELLED | COMPENSATION_REQUIRED`

Persist transitions. Use idempotency keys, bounded retries, leases for workers and dead-letter handling. Never report success until the owning service confirms it. A model-generated statement is not proof of execution.

## 9. Proactive situational awareness

JARVIS may subscribe to existing PAMASMMA events, health checks, scheduled jobs, Social Growth delivery outcomes, integration status and user-authorized calendars or mail.

Use an event policy layer:

1. Authenticate and validate event origin.
2. Enforce user/tenant ownership.
3. Deduplicate and correlate events.
4. Apply severity, relevance, quiet-hours and rate-limit rules.
5. Generate an evidence-backed explanation.
6. Notify or create a proposed task.
7. Require approval before consequential action.

Do not let an incoming webhook or untrusted MCP result directly trigger arbitrary tool execution. Proactive messages must include why the user is being notified and what evidence supports the alert.

## 10. Security and privacy requirements

- Reuse PAMASMMA authentication and session validation; do not create a weaker parallel login.
- Require step-up authentication for high-impact actions.
- Enforce per-user authorization at the API, service, tool and data layers.
- Use least-privilege service identities and scoped, short-lived credentials.
- Encrypt secrets and sensitive data at rest and in transit.
- Keep provider keys server-side.
- Apply CSRF protections where cookie-based sessions are used, strict CORS, CSP, request limits and abuse controls.
- Protect against prompt injection from web pages, MCP tools, email, documents, transcripts and retrieved memories.
- Tool output is data, never an authority-bearing instruction.
- Redact secrets, tokens, sensitive transcripts and attachment content from logs.
- Audit authentication, tool discovery, tool calls, approvals, denials, execution results, provider selection and memory changes.
- Provide retention, export and deletion workflows.
- Test cross-user isolation, revoked sessions, replay, SSRF, malicious attachments, prompt injection, tool-schema attacks and provider outages.
- Keep JARVIS resources and credentials isolated from Midas-touch2. No shared database, cache, event stream, secrets, execution bridge or trading connector.

## 11. Persistence model — proposed, subject to migration review

Prefer extending existing SQLAlchemy/Alembic patterns. Proposed logical records:

- `jarvis_conversations`: owner, title, status, timestamps, metadata.
- `jarvis_messages`: conversation, sequence, role, text/transcript, modality, provenance, timestamps.
- `jarvis_attachments`: owner, object key, validated media type, size, checksum, retention and scan status.
- `jarvis_tasks`: owner, conversation, objective, plan, status, priority, due time, correlation ID.
- `jarvis_task_steps`: task, ordered step, tool ID/version, input reference, state, result reference.
- `jarvis_tool_grants`: owner, tool/action/resource scopes, limits, expiry, revocation.
- `jarvis_approvals`: owner, exact action hash, policy version, decision, expiry and actor.
- `jarvis_action_events`: append-only lifecycle events and execution evidence.
- `jarvis_audio_sessions`: owner, provider, session state, expiry and minimal operational metadata.

All tables require owner-scoped access patterns and appropriate indexes. Avoid storing raw audio by default. Do not create these tables until current migrations, retention rules, data classification and deployment persistence have been audited.

## 12. Frontend experience

Add a dedicated JARVIS workspace without removing the existing S1–S10 dashboard.

Primary layout:

- Conversation canvas with message and tool activity timeline.
- Voice control with explicit microphone state and push-to-talk.
- Attachment input and visual preview.
- Context panel showing active project, relevant memory and connected services.
- Task panel showing plan, dependencies, progress and blockers.
- Approval inbox with exact action preview and risk explanation.
- Activity and decision history.
- Settings for voice, model/provider, privacy, memory, notifications and autonomy grants.

The interface should work on narrow Android screens first, then desktop. Keyboard and screen-reader access, reduced motion, visible focus and text alternatives are required.

## 13. Delivery roadmap and release gates

### Phase 0 — Architecture and reliability audit
- Verify current `main`, deployment branch, environment, migrations and CI state.
- Map existing conversation state, memory persistence, events, tools and integration ownership.
- Test durable-memory recovery, deterministic orchestration, tool isolation and end-to-end task completion.
- Document gaps and avoid duplicate subsystems.

**Gate:** baseline evidence and threat model approved; production persistence status known.

### Phase 1 — JARVIS text core
- Add JARVIS Runtime and application service.
- Persist conversations and messages.
- Integrate S1 and existing CognitiveEngine.
- Add task plans, task state and activity timeline.
- Keep tool access read-only.

**Gate:** authenticated end-to-end conversation, restart recovery, cross-user isolation and regression suite pass.

### Phase 2 — Voice
- Add audio provider interfaces and one initial provider adapter.
- Build short-lived audio sessions and push-to-talk client.
- Add speech transcript, speech output, cancellation and text fallback.
- Test Android device/browser compatibility and network interruption.

**Gate:** latency, transcript quality, interruption, privacy and fallback targets measured and accepted.

### Phase 3 — Multimodal perception
- Add secure attachment pipeline and supported media adapters.
- Integrate provenance-aware Knowledge Training.
- Add image/audio/video task jobs and status.

**Gate:** malicious-file, resource-limit, privacy, provenance and deletion tests pass.

### Phase 4 — Governed action broker
- Catalog typed tools and capabilities.
- Add scoped grants, approval binding, idempotency and durable execution state.
- Start with read-only tools, then narrowly scoped reversible actions.

**Gate:** adversarial authorization, replay, prompt-injection, rollback and audit tests pass.

### Phase 5 — Proactive JARVIS
- Subscribe to PAMASMMA operational events.
- Add notification relevance, quiet hours, deduplication and alert controls.
- Enable bounded delegated workflows only after per-tool acceptance.

**Gate:** false-alert rate, missed-critical-event rate, duplicate-action rate and recovery evidence meet agreed thresholds.

### Phase 6 — Production readiness
- Provision isolated durable PAMASMMA storage and object storage if required.
- Configure production voice/model credentials through deployment secrets.
- Complete backups and restore drills, monitoring, incident runbooks and cost controls.
- Conduct independent security review and staged rollout.

**Gate:** all critical tests pass, no unresolved critical/high security findings, durable recovery demonstrated, and operational ownership documented.

## 14. Required test matrix

| Area | Minimum acceptance evidence |
|---|---|
| Conversation | Ordering, concurrent tabs, resume, pagination, deletion |
| Memory | Owner isolation, retrieval relevance, restart recovery, deletion propagation |
| Cognition | S1 default, selective specialist routing, critic/evidence gate preserved |
| Voice | Permission denial, interruption, noisy input, network loss, text fallback |
| Multimodal | MIME spoofing, malicious file, oversized media, provenance, retention |
| Tools | Schema validation, least privilege, timeout, idempotency, retry, cancellation |
| Approval | Exact-payload binding, expiry, revocation, replay rejection, cross-user rejection |
| Proactive | Deduplication, quiet hours, relevance, escalation, notification revocation |
| Resilience | Provider outage, Redis outage, PostgreSQL outage, worker restart, event replay |
| Security | Prompt injection, SSRF, token leakage, IDOR, rate limiting, audit integrity |
| Operations | Health/readiness, backups, restore, tracing, alerting, cost and quota controls |

## 15. Non-goals and explicit exclusions

- No connection to Midas-touch2 or any trading account, market feed, broker, trade execution API or trading database.
- No replacement of PAMASMMA's CognitiveEngine, Memory Fabric, ModelRouter or S1–S10.
- No unrestricted autonomous shell or database access.
- No always-on microphone in the initial release.
- No silent sending, publishing, spending, deletion or permission changes.
- No claim that a task completed without service-side confirmation.
- No claim of production readiness based only on a successful local build or staging health endpoint.

## 16. Initial implementation order

The correct first implementation is not voice synthesis. It is a reliable JARVIS text-and-task runtime with durable conversation state, authenticated context, a read-only tool broker and an auditable task lifecycle. Voice then becomes another input/output channel over a stable runtime rather than a separate assistant.

This order directly addresses PAMASMMA's known unfinished reliability work: durable memory recovery, deterministic orchestration, tool isolation, permissions and end-to-end task completion.

## 17. Definition of done

JARVIS is ready for a controlled production launch only when a user can:

1. Start a conversation from an authorized device.
2. Speak or type and receive context-aware answers.
3. Resume the conversation after a restart without losing durable state.
4. Share supported media and receive provenance-aware analysis.
5. Ask JARVIS to plan a multi-step PAMASMMA task.
6. Inspect the exact proposed actions and approve or reject them.
7. Observe execution progress and verified outcomes.
8. Interrupt, cancel or revoke delegated work.
9. Review what JARVIS accessed, decided, proposed and executed.
10. Export or delete their data and verify the deletion lifecycle.

**Release principle:** JARVIS is not complete because it sounds intelligent. It is complete when its memory is durable, its reasoning is governed, its actions are authorized, its failures are recoverable, and its reports are verifiably true.

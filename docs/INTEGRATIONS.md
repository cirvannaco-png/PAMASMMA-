# PAMASMMA Integrations

## Google Workspace

PAMASMMA supports a user-authorized Google connection with Gmail and Drive read/write operations. OAuth tokens are encrypted at rest and refresh tokens remain server-side.

The configured OAuth request uses Gmail gmail.modify and Drive drive scopes, plus OpenID identity scopes. Google documents gmail.modify as allowing reading, composing and sending mail; Drive drive permits full Drive file management. These are sensitive/restricted permissions and public deployments may require Google's OAuth verification and, for restricted data handling, additional security assessment.

Endpoints:
- GET /api/v1/integrations/google/start
- GET /api/v1/integrations/google/callback
- Gmail list/get/send under /api/v1/integrations/google/{account_id}/gmail/...
- Drive list/get/upload/delete under /api/v1/integrations/google/{account_id}/drive/...

## MCP connector fabric

PAMASMMA can register authorized MCP Streamable HTTP servers per user, discover their tools, search the official MCP Registry, and invoke selected tools. Bearer credentials are encrypted at rest and never returned by list endpoints.

High-impact MCP tool names (for example send, create, update, delete, publish, deploy or execute) require explicit confirmation before invocation. PAMASMMA does not treat registry presence as a security approval: a registry entry is discovery metadata, not proof that a server is safe. The official registry exposes an unauthenticated, read-only discovery API under /v0.1/servers.

The connector uses the official MCP Python SDK v2 and Streamable HTTP transport. The SDK supports modern 2026-07-28 MCP plus compatibility with earlier protocol-era servers.

PAMASMMA remains model-provider neutral: OpenAI-compatible, Anthropic and local providers can consume the normalized MCP capability layer.

## Curated MCP connection catalog

PAMASMMA now exposes a curated discovery catalog at /api/v1/integrations/mcp/recommended. The initial catalog covers GitHub, GitLab, Google Workspace, Notion, Slack, Linear, Jira, Sentry, Grafana, HubSpot, Figma, Canva, Google Analytics 4, Google Search Console and Apify.

The catalog is not an auto-installer. Registry presence is discovery metadata only. A user or operator must still select the server endpoint, authenticate it, satisfy provider scopes and approvals, and explicitly enable the resulting connector.

The catalog prioritizes integrations that fit PAMASMMA's operating surface: personal assistant, executive operations, marketing, customer support, content creation, relationship management, knowledge and observability.

Google Workspace is already implemented natively for Gmail and Drive. The Google Workspace MCP profile is an optional expansion path for Calendar, Docs and Sheets. Avoid enabling duplicate permission surfaces without a deliberate reason.

The official MCP Registry supports remote Streamable HTTP servers through the remotes property. PAMASMMA remains compatible with that transport, while treating every remote endpoint and credential as independently governed.

## Registry-verified MCP profiles — October 2026

The following requested connections are represented as governed discovery profiles. Registry identity is recorded for operator review; it is not an authorization grant.

| Service | MCP Registry server | Verified version |
|---|---|---:|
| Google Workspace expansion | `com.proscendia/google-workspace` | 1.0.0 |
| Notion | `com.notion/mcp` | 1.0.1 |
| Slack | `com.mcparmory/slack` | 1.0.1 |
| Linear | `app.linear/linear` | 1.0.1 |
| Sentry | `io.github.getsentry/sentry-mcp` | 0.41.0 |
| HubSpot | `io.github.mindstone/mcp-server-hubspot` | 0.4.1 |
| Figma | `com.figma.mcp/mcp` | 1.0.3 |
| Canva | `com.canva.mcp/mcp` | 1.0.0 |
| Google Analytics 4 | `com.getmcpads/google-analytics` | 2.0.1 |
| Google Search Console | `com.getmcpads/google-search-console` | 2.0.1 |
| Jira | `io.github.proprock/jira-mini-mcp` | 1.3.0 |
| Grafana | `io.github.grafana/mcp-grafana` | 1.6.0 |
| Apify | `com.apify/apify-mcp-server` | 0.17.4 |

Google Workspace already has a native PAMASMMA OAuth path for Gmail and Drive. The MCP profile is therefore treated as an expansion path for broader Workspace services, rather than an instruction to duplicate existing credential surfaces.

The catalog intentionally separates **discoverable**, **connected**, and **enabled** states. No listed MCP server is automatically connected, trusted, or granted write access.


## MCP OAuth lifecycle and egress policy

PAMASMMA now offers two authentication modes per MCP connector:

- **Bearer token** for an operator-supplied token or a public endpoint.
- **MCP OAuth** through the official MCP Python SDK `OAuthClientProvider`. It uses protected-resource and authorization-server discovery, PKCE/state handling, authorization-code exchange, persisted client registration metadata, token refresh and issuer checks provided by the SDK.

OAuth access/refresh token data and OAuth client registration information are encrypted at rest with PAMASMMA's existing secret-encryption boundary. Plain credentials are never returned by connector-list APIs. The transient authorization code, SDK state, issuer and connector/user association are stored in the Redis-backed single-use callback flow with a bounded expiry. In multi-instance production the API and OAuth flow workers must share the configured Redis-compatible store.

Endpoints:

- `POST /api/v1/integrations/mcp/{connector_id}/oauth/start` — initiate an OAuth flow and return an authorization URL.
- `GET /api/v1/integrations/mcp/oauth/callback` — receive the authorization-server callback, validated against the SDK-generated state and issuer.
- `POST /api/v1/integrations/mcp/{connector_id}/oauth/disconnect` — clear PAMASMMA's locally stored OAuth tokens while retaining encrypted OAuth client-registration metadata for reconnect. This does not revoke the remote authorization-server grant; use the provider's account-security page for remote grant revocation where available.

Configure `MCP_OAUTH_REDIRECT_URI` to the exact public callback URL registered/advertised to the authorization server. Production must use HTTPS. The MCP Python SDK currently handles dynamic client registration when supported; MCP servers that require pre-registration or a provider-specific OAuth client configuration may need additional operator configuration.

### Outbound MCP endpoint controls

MCP registration and every MCP tool invocation validate the target endpoint. PAMASMMA requires HTTPS on port 443, rejects embedded URL credentials/fragments and non-canonical IPv4 literals, and blocks localhost, internal hostnames, and private/loopback/link-local/reserved IP literals. **Production also requires a non-empty exact-host allowlist in `MCP_ALLOWED_HOSTS`.** Only add hosts that operators have reviewed. This is a deliberate production gate; leave an unknown endpoint disconnected rather than weakening egress restrictions. The same host validation is applied to each request made through the MCP SDK HTTP client, including OAuth metadata discovery and token exchange. OAuth connectors must allowlist the MCP host and any separate, reviewed authorization-server/token hosts advertised during discovery; unlisted destinations are rejected.

MCP tool invocation is fail-closed: tools explicitly annotated read-only can run without an extra confirmation, destructive/open-world tools require confirmation, and tools without trustworthy read-only metadata require explicit confirmation. Tool names are not treated as a sufficient security boundary by themselves.


## Provider endpoint profiles

The Integrations page exposes an explicit **Configure** action for known Streamable HTTP endpoints. Selecting an endpoint only pre-fills the connection form; it does not connect or authorize it. The operator must confirm the hostname allowlist, select the appropriate auth mode, provide registered OAuth credentials when required, add the connector, and then explicitly start authorization.

| Service | Remote endpoint profile | Auth / prerequisites |
|---|---|---|
| Google Workspace expansion | Google Calendar `https://calendarmcp.googleapis.com/mcp/v1`; Docs `https://docsmcp.googleapis.com/mcp/v1`; Sheets `https://sheetsmcp.googleapis.com/mcp/v1`; Slides `https://slidesmcp.googleapis.com/mcp/v1`; Chat `https://chatmcp.googleapis.com/mcp/v1`; People `https://people.googleapis.com/mcp/v1` | Google requires Workspace API enablement and a registered OAuth client ID/secret. Gmail and Drive remain available through PAMASMMA's existing native integration, so don't connect duplicate paths without a reason. |
| Notion | `https://mcp.notion.com/mcp` | Authorize the specific workspace and required pages. Confirm the currently supported OAuth registration mode for the Notion account. |
| Slack | `https://mcp.slack.com/mcp` | Pre-register a Slack OAuth app/client; Slack remote MCP does not support dynamic client registration. Use the exact redirect URI and minimum scopes. |
| Linear | `https://mcp.linear.app/mcp` | OAuth authorization is required; server behavior determines whether dynamic registration can be used or pre-registered client information is needed. |
| Sentry | `https://mcp.sentry.dev/mcp` | Authorize the intended Sentry organization/project and restrict tool permissions. |
| HubSpot | `https://mcp.hubspot.com` | Create a HubSpot MCP Auth App with client ID/secret. HubSpot requires OAuth with PKCE. |
| Figma | `https://mcp.figma.com/mcp` | Sign in to Figma and confirm the organization's account/client access eligibility before rollout. |
| Canva | `https://api.canva.com/connect/v1/mcp` or, for access-approved clients, `https://mcp.canva.com/mcp` | Requires an approved Canva app/client, OAuth configuration and applicable platform permissions. Only use the endpoint assigned to that app. |
| Jira / Atlassian | `https://mcp.atlassian.com/v2/mcp` | Authorize the intended Atlassian site(s) and Jira product; use least privilege. |
| Grafana Cloud | `https://mcp.grafana.com/mcp/<YOUR-STACK>.grafana.net` | Hosted Grafana Cloud endpoint with OAuth 2.1. Replace the placeholder with the real stack host. Self-hosted Grafana needs its own MCP server deployed behind an approved HTTPS endpoint. |
| Apify | `https://mcp.apify.com` | Supports OAuth or an Apify API token. Enforce execution, data-volume and spend limits for Actors. |
| Google Analytics 4 | No first-party Google-hosted remote MCP endpoint confirmed in this catalog. | Select an independently reviewed third-party MCP server or deploy a PAMASMMA-managed adapter using Google Analytics APIs. Verify its source and permissions before use. |
| Google Search Console | No first-party Google-hosted remote MCP endpoint confirmed in this catalog. | Select an independently reviewed third-party MCP server or deploy a PAMASMMA-managed adapter using Search Console APIs. Verify its source and permissions before use. |

Provider endpoints and auth requirements change independently of PAMASMMA. The table is an operational starting point; verify the current provider registration and access requirements before production enablement.

### Registered OAuth client fields

When adding an OAuth connector, PAMASMMA accepts a pre-registered `oauth_client_id`, an optional provider-issued `oauth_client_secret`, and the token-endpoint authentication method (`none`, `client_secret_post`, or `client_secret_basic`). Client information and tokens are encrypted at rest. These fields support servers that do not offer dynamic client registration; leaving the client ID blank delegates registration to the MCP SDK/server only when that server explicitly supports it.

### Production allowlist

Configure only the hosts PAMASMMA will actually use in `MCP_ALLOWED_HOSTS`. The example file includes a starter list as a comment; copy only approved hosts into the deployment secret/environment variable. Every MCP registration and every tool request re-validates the HTTPS URL against the exact host allowlist. Redirects are disabled on MCP HTTP clients. Production registration remains disabled when the allowlist is empty.

### Operational status

A profile in the catalog means only that PAMASMMA has a reviewed discovery record. A service is **not connected** until the user's connector has been registered; it is **not authenticated** until the provider's OAuth or token exchange succeeds; and it is **not production-ready** until scopes, provider-side approval, allowlisting, tool-level policy and end-to-end tests are complete. In particular, Google Analytics 4 and Search Console remain provider-adapter choices rather than claimed official hosted integrations.


## MCP Tool Audit

Each tool execution creates a durable audit record before a tool capable of side effects is invoked. The audit records the authenticated PAMASMMA user, connector, tool name, status, whether confirmation was required/provided, timing, error class, and SHA-256 fingerprints of arguments/results. It does **not** persist raw tool arguments, raw tool results, or connector tokens.

- `GET /api/v1/integrations/mcp/audit?limit=50` returns audit entries for the current authenticated user; optional `connector_id` narrows the view.
- `POST /api/v1/integrations/mcp/{connector_id}/health-check` performs live tool discovery and reports healthy, authorization-required, or unhealthy status without exposing provider response bodies.
- `DELETE /api/v1/integrations/mcp/{connector_id}` removes the user's connector and encrypted credentials. Audit history is retained; the connector foreign key is nulled on deletion.

Tool calls are fail-closed for authorization: unless the tool explicitly advertises read-only annotations and does not advertise destructive/open-world behavior, PAMASMMA requires explicit confirmation. A tool name such as `search` or `get` is not sufficient evidence of read-only behavior. Tool arguments are validated against the latest discovered JSON Schema before execution. External MCP tool output is returned with `source="mcp_external"` and `trusted=false` so downstream cognitive systems can handle it as untrusted evidence.

The audit row is persisted in `pamasmma_mcp_tool_audit` before an external call. If the provider action succeeds but final audit update fails, the tool result is still returned with `audit_status="completion_pending_reconciliation"` to avoid prompting unsafe duplicate retries; the stale `started` row remains available for operator reconciliation.

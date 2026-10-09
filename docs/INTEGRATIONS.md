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
- `POST /api/v1/integrations/mcp/{connector_id}/oauth/disconnect` — clear PAMASMMA's stored OAuth client data and tokens. This does not promise that the remote authorization server revokes its grant; use the provider's account-security page for remote grant revocation where available.

Configure `MCP_OAUTH_REDIRECT_URI` to the exact public callback URL registered/advertised to the authorization server. Production must use HTTPS. The MCP Python SDK currently handles dynamic client registration when supported; MCP servers that require pre-registration or a provider-specific OAuth client configuration may need additional operator configuration.

### Outbound MCP endpoint controls

MCP registration and every MCP tool invocation validate the target endpoint. PAMASMMA requires HTTPS on port 443, rejects embedded URL credentials/fragments, and blocks localhost, internal hostnames, and private/loopback/link-local/reserved IP literals. **Production also requires a non-empty exact-host allowlist in `MCP_ALLOWED_HOSTS`.** Only add hosts that operators have reviewed. This is a deliberate production gate; leave an unknown endpoint disconnected rather than weakening egress restrictions.

MCP tool invocation is fail-closed: tools explicitly annotated read-only can run without an extra confirmation, destructive/open-world tools require confirmation, and tools without trustworthy read-only metadata require explicit confirmation. Tool names are not treated as a sufficient security boundary by themselves.

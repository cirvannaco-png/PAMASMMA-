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

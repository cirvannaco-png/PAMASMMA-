"use client";

/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { integrations } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

export default function IntegrationsPage() {
  const router = useRouter();
  const { isAuthenticated, isRestoring } = useAuth();
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [mcp, setMcp] = useState<Array<Record<string, unknown>>>([]);
  const [auditEntries, setAuditEntries] = useState<Array<Record<string, unknown>>>([]);
  const [healthStatuses, setHealthStatuses] = useState<Record<string, string>>({});
  const [recommended, setRecommended] = useState<Array<Record<string, unknown>>>([]);
  const [selectedProfile, setSelectedProfile] = useState<Record<string, unknown> | null>(null);
  const [selectedEndpointNotes, setSelectedEndpointNotes] = useState("");
  const [name, setName] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [token, setToken] = useState("");
  const [authMode, setAuthMode] = useState<"bearer" | "oauth">("bearer");
  const [oauthClientId, setOauthClientId] = useState("");
  const [oauthClientSecret, setOauthClientSecret] = useState("");
  const [oauthTokenMethod, setOauthTokenMethod] = useState<"none" | "client_secret_post" | "client_secret_basic">("client_secret_post");

  const load = async () => {
    const data = await integrations.list();
    setItems(data.integrations);
    setMcp(data.mcp);
    const catalog = await integrations.mcpRecommended();
    setRecommended(catalog.connections);
    const audit = await integrations.mcpAudit(20).catch(() => ({ entries: [] as Array<Record<string, unknown>>, count: 0 }));
    setAuditEntries(audit.entries);
  };

  useEffect(() => {
    if (!isRestoring && !isAuthenticated) router.replace("/auth");
  }, [isAuthenticated, isRestoring, router]);

  useEffect(() => {
    if (isAuthenticated) void load().catch((error) => toast.error(error instanceof Error ? error.message : "Integration load failed."));
  }, [isAuthenticated]);

  if (isRestoring || !isAuthenticated) return null;

  const connectGoogle = async () => {
    try {
      const result = await integrations.googleStart();
      window.location.assign(result.authorization_url);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Google connection failed.");
    }
  };

  const addMcp = async () => {
    if (!name.trim() || !endpoint.trim()) return;
    try {
      await integrations.mcpAdd({ name: name.trim(), endpoint: endpoint.trim(), auth_mode: authMode, bearer_token: authMode === "bearer" ? token || undefined : undefined, oauth_client_id: authMode === "oauth" ? oauthClientId.trim() || undefined : undefined, oauth_client_secret: authMode === "oauth" ? oauthClientSecret || undefined : undefined, oauth_token_endpoint_auth_method: oauthTokenMethod, enabled: true });
      setName(""); setEndpoint(""); setToken(""); setAuthMode("bearer"); setOauthClientId(""); setOauthClientSecret(""); setOauthTokenMethod("client_secret_post");
      await load();
      toast.success("MCP connector registered.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "MCP registration failed.");
    }
  };

  return (
    <main style={{ minHeight: "100vh", background: "#04040D", color: "#D0D0EC", padding: 28 }}>
      <div style={{ maxWidth: 980, margin: "0 auto" }}>
        <button onClick={() => router.push("/dashboard")} style={{ background: "none", border: 0, color: "#8E80D8", cursor: "pointer", marginBottom: 18 }}>← Dashboard</button>
        <h1 style={{ fontSize: 24, marginBottom: 8 }}>Integrations</h1>
        <p style={{ color: "#77779A", marginBottom: 26 }}>Connect Google Workspace and governed MCP application/AI capabilities to PAMASMMA.</p>

        <section style={{ border: "1px solid #202040", borderRadius: 12, padding: 20, marginBottom: 18 }}>
          <h2 style={{ fontSize: 16 }}>Google Workspace</h2>
          <p style={{ color: "#77779A", fontSize: 13 }}>Gmail read/compose/send and Drive file read/write are requested through Google OAuth. Tokens remain encrypted server-side.</p>
          <button onClick={connectGoogle} style={{ padding: "10px 14px", borderRadius: 8, border: "1px solid #4C3F88", background: "#17132E", color: "#D8D0FF", cursor: "pointer" }}>Connect Google</button>
          <div style={{ marginTop: 16 }}>
            {items.filter((item) => item.provider === "google").map((item) => (
              <div key={String(item.id)} style={{ padding: 10, background: "#0A0A18", borderRadius: 8, marginTop: 8 }}>
                <strong>{String(item.display_name ?? "Google account")}</strong>
                <div style={{ color: "#68688A", fontSize: 12 }}>{String(item.external_account_id)}</div>
                <div style={{ color: "#55C8A0", fontSize: 11 }}>Gmail + Drive connected</div>
              </div>
            ))}
          </div>
        </section>

        <section style={{ border: "1px solid #202040", borderRadius: 12, padding: 20 }}>
          <h2 style={{ fontSize: 16 }}>MCP application + AI connector fabric</h2>
          <p style={{ color: "#77779A", fontSize: 13 }}>Register authorized Streamable HTTP MCP servers. PAMASMMA discovers their tools and keeps credentials encrypted.</p>
          <div id="mcp-connect-form" style={{ display: "grid", gap: 8 }}>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Connector name" style={{ padding: 10, background: "#0A0A18", border: "1px solid #29294A", color: "#D0D0EC", borderRadius: 8 }} />
            <input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="https://example.com/mcp" style={{ padding: 10, background: "#0A0A18", border: "1px solid #29294A", color: "#D0D0EC", borderRadius: 8 }} />
            <label style={{ display: "grid", gap: 6, fontSize: 12, color: "#77779A" }}>
              Authentication mode
              <select value={authMode} onChange={(e) => setAuthMode(e.target.value as "bearer" | "oauth")} style={{ padding: 10, background: "#0A0A18", border: "1px solid #29294A", color: "#D0D0EC", borderRadius: 8 }}>
                <option value="oauth">OAuth 2.1 / MCP authorization</option>
                <option value="bearer">Bearer token / public server</option>
              </select>
            </label>
            {authMode === "bearer" && (
              <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="Bearer token (optional)" style={{ padding: 10, background: "#0A0A18", border: "1px solid #29294A", color: "#D0D0EC", borderRadius: 8 }} />
            )}
            {authMode === "oauth" && (
              <>
                <input value={oauthClientId} onChange={(e) => setOauthClientId(e.target.value)} placeholder="OAuth client ID (blank if server supports dynamic registration)" style={{ padding: 10, background: "#0A0A18", border: "1px solid #29294A", color: "#D0D0EC", borderRadius: 8 }} autoComplete="off" />
                <input type="password" value={oauthClientSecret} onChange={(e) => setOauthClientSecret(e.target.value)} placeholder="OAuth client secret (if provider issues one)" style={{ padding: 10, background: "#0A0A18", border: "1px solid #29294A", color: "#D0D0EC", borderRadius: 8 }} autoComplete="new-password" />
                <label style={{ display: "grid", gap: 6, fontSize: 12, color: "#77779A" }}>
                  OAuth token endpoint authentication
                  <select value={oauthTokenMethod} onChange={(e) => setOauthTokenMethod(e.target.value as "none" | "client_secret_post" | "client_secret_basic")} style={{ padding: 10, background: "#0A0A18", border: "1px solid #29294A", color: "#D0D0EC", borderRadius: 8 }}>
                    <option value="client_secret_post">Client secret in POST body</option>
                    <option value="client_secret_basic">HTTP Basic client authentication</option>
                    <option value="none">Public client / no client secret</option>
                  </select>
                </label>
                <p style={{ color: "#77779A", fontSize: 11, margin: 0 }}>
                  OAuth credentials are encrypted at rest. Leave client ID blank only when the MCP authorization server supports dynamic registration. The redirect URI must be registered exactly with the provider.
                </p>
              </>
            )}
            <button onClick={() => void addMcp()} style={{ padding: "10px 14px", borderRadius: 8, border: "1px solid #315F72", background: "#10202A", color: "#AEEBFF", cursor: "pointer" }}>Add MCP connector</button>
          </div>
          <div style={{ marginTop: 16 }}>
            {mcp.map((item) => {
              const connectorId = String(item.id);
              const connectorAuthMode = String(item.auth_mode ?? "bearer");
              const authStatus = String(item.auth_status ?? "configured");
              return (
                <div key={connectorId} style={{ padding: 10, background: "#0A0A18", borderRadius: 8, marginTop: 8 }}>
                  <strong>{String(item.name)}</strong>
                  <div style={{ color: "#68688A", fontSize: 11 }}>{String(item.endpoint)}</div>
                  <div style={{ color: authStatus === "connected" ? "#55C8A0" : "#BBAEFF", fontSize: 11, marginTop: 4 }}>
                    {connectorAuthMode.toUpperCase()} · {authStatus}
                  </div>
                  {connectorAuthMode === "oauth" && authStatus !== "connected" && (
                    <button
                      type="button"
                      onClick={() => void integrations.mcpOAuthStart(connectorId).then((result) => {
                        if (result.authorization_url) {
                          window.location.assign(result.authorization_url);
                        } else if (result.status === "connected") {
                          toast.success("MCP OAuth connection completed.");
                          void load();
                        } else {
                          toast.error(`MCP OAuth status: ${result.status}`);
                        }
                      }).catch((error) => toast.error(error instanceof Error ? error.message : "MCP OAuth start failed."))}
                      style={{ marginTop: 8, padding: "7px 10px", borderRadius: 7, border: "1px solid #315F72", background: "#10202A", color: "#AEEBFF", cursor: "pointer", fontSize: 11 }}
                    >
                      Authorize connection
                    </button>
                  )}
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 7, marginTop: 8 }}>
                    <button
                      type="button"
                      onClick={() => void integrations.mcpHealthCheck(connectorId).then((result) => {
                        setHealthStatuses((current) => ({ ...current, [connectorId]: result.status }));
                        if (result.status === "healthy") toast.success(`MCP healthy · ${result.tool_count ?? 0} tools`);
                        else if (result.status === "authorization_required") toast("Authorize this connector to continue.");
                        else toast.error(`MCP health: ${result.status}`);
                      }).catch((error) => toast.error(error instanceof Error ? error.message : "Health check failed."))}
                      style={{ padding: "7px 10px", borderRadius: 7, border: "1px solid #25254A", background: "#0D0D1B", color: "#A7A2D8", cursor: "pointer", fontSize: 11 }}
                    >
                      Check connection
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (!window.confirm(`Remove ${String(item.name)} and delete its saved credentials?`)) return;
                        void integrations.mcpRemove(connectorId).then(() => load()).then(() => toast.success("MCP connector removed.")).catch((error) => toast.error(error instanceof Error ? error.message : "Could not remove connector."));
                      }}
                      style={{ padding: "7px 10px", borderRadius: 7, border: "1px solid #543939", background: "#211010", color: "#F0B4B4", cursor: "pointer", fontSize: 11 }}
                    >
                      Remove connector
                    </button>
                  </div>
                  {healthStatuses[connectorId] && (
                    <div style={{ color: healthStatuses[connectorId] === "healthy" ? "#55C8A0" : "#D5B46D", fontSize: 11, marginTop: 5 }}>
                      Health: {healthStatuses[connectorId]}
                    </div>
                  )}
                  {connectorAuthMode === "oauth" && authStatus === "connected" && (
                    <button
                      type="button"
                      onClick={() => void integrations.mcpOAuthDisconnect(connectorId).then(() => load()).then(() => toast.success("Saved MCP authorization cleared.")).catch((error) => toast.error(error instanceof Error ? error.message : "Could not clear authorization."))}
                      style={{ marginTop: 8, padding: "7px 10px", borderRadius: 7, border: "1px solid #543939", background: "#211010", color: "#F0B4B4", cursor: "pointer", fontSize: 11 }}
                    >
                      Clear saved authorization
                    </button>
                  )}
                </div>
              );
            })}
          </div>
          <div style={{ marginTop: 22, borderTop: "1px solid #202040", paddingTop: 18 }}>
            <h3 style={{ fontSize: 14, marginBottom: 6 }}>Recent MCP tool audit</h3>
            <p style={{ color: "#77779A", fontSize: 12, marginBottom: 10 }}>
              Records include operation metadata and content hashes only. Raw tool arguments and results are not stored in this audit view.
            </p>
            {auditEntries.length === 0 ? (
              <div style={{ color: "#68688A", fontSize: 12 }}>No audited tool calls yet.</div>
            ) : (
              <div style={{ display: "grid", gap: 7 }}>
                {auditEntries.slice(0, 20).map((entry) => {
                  const status = String(entry.status ?? "unknown");
                  const duration = typeof entry.duration_ms === "number" ? `${entry.duration_ms} ms` : "duration pending";
                  return (
                    <div key={String(entry.id)} style={{ padding: 10, background: "#070713", borderRadius: 8, border: "1px solid #18182F" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                        <strong style={{ fontSize: 12 }}>{String(entry.connector_name)} · {String(entry.tool_name)}</strong>
                        <span style={{ color: status === "succeeded" ? "#55C8A0" : status === "failed" || status === "blocked" ? "#F0B4B4" : "#D5B46D", fontSize: 11 }}>{status}</span>
                      </div>
                      <div style={{ color: "#68688A", fontSize: 10, marginTop: 4 }}>
                        {String(entry.created_at ?? "")} · {duration} · confirmed: {String(entry.confirmed ?? false)}
                      </div>
                      {typeof entry.error_type === "string" && entry.error_type.length > 0 && (
                        <div style={{ color: "#D5B46D", fontSize: 10, marginTop: 4 }}>Error class: {entry.error_type}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          <div style={{ marginTop: 22, borderTop: "1px solid #202040", paddingTop: 18 }}>
            <h3 style={{ fontSize: 14, marginBottom: 6 }}>Recommended MCP connections</h3>
            <p style={{ color: "#77779A", fontSize: 12, marginBottom: 10 }}>
              Discovery profiles are shown here. A connection is not auto-installed; you still choose the endpoint, credentials and scopes.
            </p>
            <div style={{ display: "grid", gap: 8 }}>
              {recommended.map((item) => (
                <div key={String(item.id)} style={{ padding: 11, background: "#070713", borderRadius: 8, border: "1px solid #18182F" }}>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{String(item.name)} <span style={{ color: "#68688A", fontSize: 10 }}>· {String(item.priority)}</span></div>
                  <div style={{ color: "#7E7E9E", fontSize: 11, marginTop: 4 }}>{String(item.reason)}</div>
                  {typeof item.endpoint_status === "string" && (
                    <div style={{ color: "#D5B46D", fontSize: 11, marginTop: 5 }}>{item.endpoint_status}</div>
                  )}
                  <div style={{ color: "#52526E", fontSize: 10, marginTop: 5 }}>
                    Registry: {String(item.registry_server)}{item.registry_version ? ` · v${String(item.registry_version)}` : ""}
                  </div>
                  {Array.isArray(item.remote_endpoints) && item.remote_endpoints.map((candidate) => {
                    if (!candidate || typeof candidate !== "object") return null;
                    const option = candidate as Record<string, unknown>;
                    const optionName = String(option.label ?? item.name);
                    const optionEndpoint = String(option.endpoint ?? "");
                    if (!optionEndpoint) return null;
                    return (
                      <button
                        key={optionEndpoint}
                        type="button"
                        onClick={() => {
                          setName(optionName);
                          setEndpoint(optionEndpoint);
                          setAuthMode(option.auth_mode === "bearer" ? "bearer" : "oauth");
                          setToken("");
                          setOauthClientId("");
                          setOauthClientSecret("");
                          setSelectedProfile(item);
                          setSelectedEndpointNotes(String(option.notes ?? ""));
                          document.getElementById("mcp-connect-form")?.scrollIntoView({ behavior: "smooth", block: "center" });
                          toast.success("Endpoint selected. Review auth settings and register to continue.");
                        }}
                        style={{ marginTop: 7, marginRight: 6, padding: "7px 10px", borderRadius: 7, border: "1px solid #315F72", background: "#10202A", color: "#AEEBFF", cursor: "pointer", fontSize: 10 }}
                      >
                        Configure {optionName}
                      </button>
                    );
                  })}
                  <button
                    type="button"
                    onClick={() =>
                      void integrations.mcpProfile(String(item.id))
                        .then((result) => setSelectedProfile(result.connection))
                        .catch((error) =>
                          toast.error(error instanceof Error ? error.message : "Profile lookup failed."),
                        )
                    }
                    style={{
                      marginTop: 8,
                      padding: "7px 10px",
                      borderRadius: 7,
                      border: "1px solid #25254A",
                      background: "#0D0D1B",
                      color: "#A7A2D8",
                      cursor: "pointer",
                      fontSize: 10,
                    }}
                  >
                    View connection profile
                  </button>
                </div>
              ))}
            </div>
          {selectedProfile && (
            <div style={{ marginTop: 16, padding: 12, border: "1px solid #2A2850", borderRadius: 8, background: "#09091A" }}>
              <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6 }}>Selected connection profile</div>
              <div style={{ color: "#77779A", fontSize: 11 }}>
                {String(selectedProfile.name)} · risk {String(selectedProfile.risk)} · {String(selectedProfile.connection_state)}
              </div>
              <div style={{ color: "#55556E", fontSize: 10, marginTop: 5 }}>
                Auth: {Array.isArray(selectedProfile.auth) ? selectedProfile.auth.join(", ") : String(selectedProfile.auth)}
              </div>
              <div style={{ color: "#55556E", fontSize: 10, marginTop: 5 }}>
                Capabilities: {Array.isArray(selectedProfile.capabilities) ? selectedProfile.capabilities.join(", ") : String(selectedProfile.capabilities)}
              </div>
              {selectedEndpointNotes && (
                <div style={{ color: "#BBAEFF", fontSize: 11, lineHeight: 1.5, marginTop: 8 }}>
                  {selectedEndpointNotes}
                </div>
              )}
              {typeof selectedProfile.endpoint_status === "string" && (
                <div style={{ color: "#D5B46D", fontSize: 11, lineHeight: 1.5, marginTop: 8 }}>
                  {selectedProfile.endpoint_status}
                </div>
              )}
            </div>
          )}
          </div>
        </section>
      </div>
    </main>
  );
}

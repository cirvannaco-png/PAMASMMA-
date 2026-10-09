"use client";

/* eslint-disable react-hooks/set-state-in-effect */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { integrations, mcp as mcpApi } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

export default function IntegrationsPage() {
  const router = useRouter();
  const { isAuthenticated, isRestoring } = useAuth();
  const [items, setItems] = useState<Array<Record<string, unknown>>>([]);
  const [mcp, setMcp] = useState<Array<Record<string, unknown>>>([]);
  const [auditEntries, setAuditEntries] = useState<Array<Record<string, unknown>>>([]);
  const [healthStatuses, setHealthStatuses] = useState<Record<string, string>>({});
  const [toolLists, setToolLists] = useState<Record<string, Array<Record<string, unknown>>>>({});
  const [toolArguments, setToolArguments] = useState<Record<string, string>>({});
  const [toolResults, setToolResults] = useState<Record<string, string>>({});
  const [toolBusy, setToolBusy] = useState<Record<string, boolean>>({});
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

  const getToolKey = (connectorId: string, toolName: string) => `${connectorId}::${toolName}`;

  const toggleMcpTools = async (connectorId: string) => {
    if (Object.prototype.hasOwnProperty.call(toolLists, connectorId)) {
      setToolLists((current) => {
        const next = { ...current };
        delete next[connectorId];
        return next;
      });
      return;
    }

    const busyKey = `discover:${connectorId}`;
    setToolBusy((current) => ({ ...current, [busyKey]: true }));
    try {
      const data = await integrations.mcpTools(connectorId);
      setToolLists((current) => ({ ...current, [connectorId]: data.tools }));
      setToolArguments((current) => {
        const next = { ...current };
        for (const tool of data.tools) {
          if (typeof tool.name !== "string") continue;
          const key = getToolKey(connectorId, tool.name);
          if (!(key in next)) next[key] = "{}";
        }
        return next;
      });
      toast.success(`Discovered ${data.tools.length} MCP tools.`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "MCP tool discovery failed.");
    } finally {
      setToolBusy((current) => ({ ...current, [busyKey]: false }));
    }
  };

  const runMcpTool = async (connectorId: string, connectorName: string, toolName: string) => {
    const key = getToolKey(connectorId, toolName);
    let args: Record<string, unknown>;
    try {
      const parsed: unknown = JSON.parse(toolArguments[key] ?? "{}");
      if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("Tool arguments must be a JSON object.");
      }
      args = parsed as Record<string, unknown>;
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Enter valid JSON arguments.");
      return;
    }

    const argumentPreview = JSON.stringify(args, null, 2);
    const visiblePreview = argumentPreview.length > 1200
      ? `${argumentPreview.slice(0, 1200)}\n… confirmation preview truncated`
      : argumentPreview;
    const approved = window.confirm(
      `Review external MCP action\n\nConnector: ${connectorName}\nTool: ${toolName}\n\nArguments:\n${visiblePreview}\n\nRemote tool behavior is not guaranteed. This may modify external systems; treat the result as untrusted.\n\nRun this tool?`,
    );
    if (!approved) return;

    setToolBusy((current) => ({ ...current, [key]: true }));
    try {
      const result = await mcpApi.call(connectorId, toolName, args, true);
      const resultText = JSON.stringify(result, null, 2) ?? String(result);
      setToolResults((current) => ({
        ...current,
        [key]: resultText.length > 20000
          ? `${resultText.slice(0, 20000)}\n… display truncated at 20,000 characters`
          : resultText,
      }));
      if (result.is_error === true) {
        toast.error(`${toolName} returned an MCP error. Inspect the result.`);
      } else {
        toast.success(`MCP tool ${toolName} invoked.`);
      }
      void integrations.mcpAudit(20)
        .then((audit) => setAuditEntries(audit.entries))
        .catch(() => toast("Tool completed, but the audit view could not be refreshed."));
    } catch (error) {
      const message = error instanceof Error ? error.message : "MCP tool invocation failed.";
      setToolResults((current) => ({ ...current, [key]: JSON.stringify({ error: message }, null, 2) }));
      toast.error(message);
    } finally {
      setToolBusy((current) => ({ ...current, [key]: false }));
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
                  <div style={{ marginTop: 12, borderTop: "1px solid #18182F", paddingTop: 10 }}>
                    <button
                      type="button"
                      disabled={Boolean(toolBusy[`discover:${connectorId}`] || (connectorAuthMode === "oauth" && authStatus !== "connected"))}
                      onClick={() => void toggleMcpTools(connectorId)}
                      style={{ padding: "7px 10px", borderRadius: 7, border: "1px solid #315F72", background: "#10202A", color: "#AEEBFF", cursor: "pointer", fontSize: 11, opacity: connectorAuthMode === "oauth" && authStatus !== "connected" ? 0.55 : 1 }}
                    >
                      {toolBusy[`discover:${connectorId}`] ? "Discovering tools…" : Object.prototype.hasOwnProperty.call(toolLists, connectorId) ? "Hide tools" : "Discover tools"}
                    </button>
                    {connectorAuthMode === "oauth" && authStatus !== "connected" && (
                      <span style={{ marginLeft: 8, color: "#68688A", fontSize: 11 }}>Authorize this connector first.</span>
                    )}
                    {Object.prototype.hasOwnProperty.call(toolLists, connectorId) && (
                      <div style={{ display: "grid", gap: 10, marginTop: 10 }}>
                        {toolLists[connectorId].length === 0 ? (
                          <div style={{ color: "#68688A", fontSize: 12 }}>This MCP server returned no tools.</div>
                        ) : toolLists[connectorId].map((tool) => {
                          const toolName = typeof tool.name === "string" ? tool.name : "unnamed-tool";
                          const toolKey = getToolKey(connectorId, toolName);
                          return (
                            <div key={toolKey} style={{ background: "#070713", border: "1px solid #202040", borderRadius: 9, padding: 12 }}>
                              <strong style={{ fontSize: 12 }}>{toolName}</strong>
                              <p style={{ color: "#77779A", fontSize: 11, lineHeight: 1.5, margin: "5px 0 8px", whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                                {String(tool.description ?? "No description provided by this MCP server.")}
                              </p>
                              <details style={{ marginBottom: 8, color: "#A7A2D8", fontSize: 11 }}>
                                <summary style={{ cursor: "pointer" }}>Input schema</summary>
                                <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: 220, overflow: "auto", background: "#04040D", padding: 8, borderRadius: 6 }}>
                                  {JSON.stringify(tool.input_schema ?? {}, null, 2)}
                                </pre>
                              </details>
                              <label style={{ display: "grid", gap: 5, color: "#A7A2D8", fontSize: 11 }}>
                                Arguments (JSON object)
                                <textarea
                                  aria-label={`JSON arguments for ${toolName}`}
                                  value={toolArguments[toolKey] ?? "{}"}
                                  onChange={(event) => setToolArguments((current) => ({ ...current, [toolKey]: event.target.value }))}
                                  spellCheck={false}
                                  rows={5}
                                  style={{ width: "100%", boxSizing: "border-box", resize: "vertical", padding: 9, background: "#04040D", border: "1px solid #29294A", color: "#D0D0EC", borderRadius: 6, fontFamily: "monospace", fontSize: 11 }}
                                />
                              </label>
                              <button
                                type="button"
                                disabled={Boolean(toolBusy[toolKey])}
                                onClick={() => void runMcpTool(connectorId, String(item.name ?? connectorId), toolName)}
                                style={{ marginTop: 8, padding: "7px 10px", borderRadius: 7, border: "1px solid #5E4C28", background: "#211A0D", color: "#E7C98C", cursor: "pointer", fontSize: 11, opacity: toolBusy[toolKey] ? 0.6 : 1 }}
                              >
                                {toolBusy[toolKey] ? "Running…" : "Review & run"}
                              </button>
                              {toolResults[toolKey] && (
                                <details open style={{ marginTop: 9, color: "#D5B46D", fontSize: 11 }}>
                                  <summary style={{ cursor: "pointer" }}>Latest result · untrusted external output</summary>
                                  <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: 300, overflow: "auto", background: "#04040D", padding: 8, borderRadius: 6, color: "#D0D0EC" }}>
                                    {toolResults[toolKey]}
                                  </pre>
                                </details>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
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

"use client";

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
  const [name, setName] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [token, setToken] = useState("");

  const load = async () => {
    const data = await integrations.list();
    setItems(data.integrations);
    setMcp(data.mcp);
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
      await integrations.mcpAdd({ name: name.trim(), endpoint: endpoint.trim(), bearer_token: token || undefined, enabled: true });
      setName(""); setEndpoint(""); setToken("");
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
          <div style={{ display: "grid", gap: 8 }}>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Connector name" style={{ padding: 10, background: "#0A0A18", border: "1px solid #29294A", color: "#D0D0EC", borderRadius: 8 }} />
            <input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="https://example.com/mcp" style={{ padding: 10, background: "#0A0A18", border: "1px solid #29294A", color: "#D0D0EC", borderRadius: 8 }} />
            <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="Bearer token (optional)" style={{ padding: 10, background: "#0A0A18", border: "1px solid #29294A", color: "#D0D0EC", borderRadius: 8 }} />
            <button onClick={() => void addMcp()} style={{ padding: "10px 14px", borderRadius: 8, border: "1px solid #315F72", background: "#10202A", color: "#AEEBFF", cursor: "pointer" }}>Add MCP connector</button>
          </div>
          <div style={{ marginTop: 16 }}>
            {mcp.map((item) => <div key={String(item.id)} style={{ padding: 10, background: "#0A0A18", borderRadius: 8, marginTop: 8 }}>{String(item.name)} <span style={{ color: "#55C8A0", fontSize: 11 }}>· governed</span><div style={{ color: "#68688A", fontSize: 11 }}>{String(item.endpoint)}</div></div>)}
          </div>
        </section>
      </div>
    </main>
  );
}

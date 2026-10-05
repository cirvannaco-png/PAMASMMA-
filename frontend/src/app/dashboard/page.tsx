"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useCognitiveStore } from "@/lib/store";
import { cognitive, auth } from "@/lib/api";
import { SYSTEMS, PERSONALITY } from "@/lib/constants";
import type { SystemId, Message } from "@/types";
import toast from "react-hot-toast";

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, userId, clearAuth } = useAuthStore();
  const {
    activeSystemId, threads, loading,
    setActiveSystem, addMessage, appendToLastMessage,
    setLoading, setActionLog,
  } = useCognitiveStore();

  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<"chat" | "log">("chat");

  const activeSystem = SYSTEMS.find(s => s.id === activeSystemId)!;
  const thread: Message[] = threads[activeSystemId] ?? [];

  useEffect(() => {
    if (!isAuthenticated) router.replace("/auth");
  }, [isAuthenticated]);

  useEffect(() => {
    const el = document.getElementById("chat-bottom");
    el?.scrollIntoView({ behavior: "smooth" });
  }, [threads, loading]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const userMsg: Message = {
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };
    addMessage(activeSystemId, userMsg);
    setInput("");
    setLoading(true);

    const allMessages = [...thread, userMsg];

    try {
      const res = await cognitive.invokeStream(
        activeSystemId,
        allMessages.map(m => ({ role: m.role, content: m.content })),
      );

      if (!res.ok) {
        throw new Error("Stream failed");
      }
      if (!res.body) {
        throw new Error("Streaming response has no body");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let streamDone = false;
      let assistantSeeded = false;

      const consumeFrame = (line: string): void => {
        if (!line.startsWith("data: ")) return;

        const payload = line.slice(6);
        if (payload === "[DONE]") {
          streamDone = true;
          return;
        }

        let chunk: string;
        try {
          chunk = JSON.parse(payload) as string;
        } catch {
          return;
        }

        if (!assistantSeeded) {
          addMessage(activeSystemId, { role: "assistant", content: "" });
          assistantSeeded = true;
        }
        appendToLastMessage(activeSystemId, chunk);
      };

      while (!streamDone) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          consumeFrame(line);
          if (streamDone) break;
        }
      }

      buffer += decoder.decode();
      if (!streamDone && buffer.startsWith("data: ")) {
        consumeFrame(buffer);
      }
    } catch {
      toast.error(activeSystemId + " system error — check connection");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try { await auth.logout(); } catch {}
    clearAuth();
    router.replace("/auth");
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#04040D]" style={{ color: "#D0D0EC" }}>

      {/* ── SIDEBAR ── */}
      {sidebarOpen && (
        <aside style={{ width: 264, background: "#07071A", borderRight: "1px solid #161630", display: "flex", flexDirection: "column", flexShrink: 0 }}>
          {/* Brand */}
          <div style={{ padding: "18px 16px", borderBottom: "1px solid #161630", display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 22, color: "#6B3FFB" }}>⬡</span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: 3, color: "#E8E8FA" }}>PAMASMMA</div>
              <div style={{ fontSize: 8, color: "#3A3A6A", letterSpacing: 1.5, marginTop: 2 }}>Synthetic Executive Intelligence</div>
            </div>
          </div>

          {/* Personality meters */}
          <div style={{ padding: "12px 14px", borderBottom: "1px solid #111128" }}>
            <div style={{ fontSize: 8, letterSpacing: 2.5, color: "#3A3A6A", fontWeight: 700, marginBottom: 10 }}>PERSONALITY BASELINE</div>
            {PERSONALITY.map(p => (
              <div key={p.key} style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 8 }}>
                <span style={{ fontSize: 9, color: "#6060A0", fontFamily: "monospace", width: 26 }}>{p.key}</span>
                <div style={{ flex: 1, height: 3, background: "#161630", borderRadius: 2, overflow: "hidden" }}>
                  <div style={{ width: `${p.val * 100}%`, height: "100%", background: "linear-gradient(90deg,#6B3FFB,#9B6BFF)", borderRadius: 2 }} />
                </div>
                <span style={{ fontSize: 9, color: "#6B3FFB", fontFamily: "monospace", width: 26, textAlign: "right" }}>{p.val}</span>
              </div>
            ))}
          </div>

          {/* Cognitive systems list */}
          <div style={{ flex: 1, overflowY: "auto", padding: "12px 14px" }}>
            <div style={{ fontSize: 8, letterSpacing: 2.5, color: "#3A3A6A", fontWeight: 700, marginBottom: 10 }}>COGNITIVE SYSTEMS</div>
            {SYSTEMS.map(sys => (
              <button
                key={sys.id}
                onClick={() => setActiveSystem(sys.id as SystemId)}
                style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "7px 8px", borderRadius: 8, width: "100%",
                  marginBottom: 3, cursor: "pointer", textAlign: "left",
                  border: `1px solid ${activeSystemId === sys.id ? sys.color : "transparent"}`,
                  background: activeSystemId === sys.id ? `${sys.color}12` : "transparent",
                  transition: "all 0.12s",
                }}
              >
                <span style={{ fontSize: 8, fontWeight: 800, color: "#06060F", padding: "2px 5px", borderRadius: 4, background: sys.color, minWidth: 30, textAlign: "center", fontFamily: "monospace" }}>{sys.id}</span>
                <span style={{ fontSize: 11, color: "#B0B0D0", fontWeight: 500, flex: 1, lineHeight: 1.3 }}>{sys.name}</span>
                {(threads[sys.id as SystemId]?.length ?? 0) > 0 && (
                  <span style={{ fontSize: 9, color: "#5050A0", background: "#12122A", padding: "1px 5px", borderRadius: 10, fontFamily: "monospace" }}>{threads[sys.id as SystemId]?.length}</span>
                )}
              </button>
            ))}
          </div>

          {/* Footer */}
          <div style={{ padding: "12px 16px", borderTop: "1px solid #111128" }}>
            {[
              { color: "#3BFFA0", label: "MALI v7 · ACTIVE" },
              { color: "#00D4FF", label: "17 MCP · BOUND" },
              { color: "#D4AF37", label: "Cirvanna · Nakuru KE" },
            ].map(f => (
              <div key={f.label} style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 6, fontSize: 9, color: "#3A3A6A", fontFamily: "monospace" }}>
                <span style={{ width: 5, height: 5, borderRadius: "50%", background: f.color, boxShadow: `0 0 5px ${f.color}60`, flexShrink: 0 }} />
                {f.label}
              </div>
            ))}
            <button onClick={handleLogout} style={{ marginTop: 8, fontSize: 9, color: "#3A3A6A", background: "none", border: "none", cursor: "pointer", letterSpacing: 1 }}>
              LOGOUT ↗
            </button>
          </div>
        </aside>
      )}

      {/* ── MAIN ── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", borderBottom: "1px solid #161630", background: "#07071A", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button onClick={() => setSidebarOpen(v => !v)} style={{ background: "none", border: "none", color: "#404080", cursor: "pointer", fontSize: 16 }}>☰</button>
            <span style={{ width: 9, height: 9, borderRadius: "50%", background: activeSystem.color, display: "inline-block", flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#E8E8FA" }}>{activeSystem.name}</div>
              <div style={{ fontSize: 10, color: "#3A3A6A", marginTop: 2 }}>{activeSystem.id} · Cognitive System</div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            {(["chat", "log"] as const).map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)} style={{ fontSize: 9, letterSpacing: 2, color: activeTab === tab ? activeSystem.color : "#3A3A6A", background: "none", border: "none", cursor: "pointer", fontWeight: 700, textTransform: "uppercase" }}>{tab}</button>
            ))}
            <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 9, color: "#00D4FF", letterSpacing: 2, fontFamily: "monospace", fontWeight: 700 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#00D4FF", boxShadow: "0 0 6px #00D4FF" }} className="animate-pulse-dot" />
              {activeSystemId} · ONLINE
            </div>
          </div>
        </div>

        {/* Chat Area */}
        {activeTab === "chat" && (
          <>
            <div style={{ flex: 1, overflowY: "auto", padding: "24px 20px", display: "flex", flexDirection: "column", gap: 16 }}>
              {thread.length === 0 && (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, textAlign: "center", paddingTop: 80, opacity: 0.65 }}>
                  <div style={{ fontSize: 46, color: activeSystem.color }} className="animate-float">⬡</div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#C0C0E0", marginTop: 10 }}>{activeSystem.name}</div>
                  <div style={{ fontSize: 11, color: "#3A3A6A", maxWidth: 320, lineHeight: 1.6, marginTop: 6 }}>Address this cognitive system to engage its intelligence</div>
                </div>
              )}
              {thread.map((msg, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-end", gap: 10, justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
                  {msg.role === "assistant" && (
                    <div style={{ width: 32, height: 32, borderRadius: 8, background: activeSystem.color, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 8, fontWeight: 800, color: "#06060F", fontFamily: "monospace", flexShrink: 0 }}>{activeSystem.id}</div>
                  )}
                  <div style={{
                    padding: "12px 16px", maxWidth: "70%", fontSize: 13, lineHeight: 1.7, whiteSpace: "pre-wrap", wordBreak: "break-word",
                    background: msg.role === "user" ? "#6B3FFB" : "#0C0C22",
                    borderRadius: msg.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                    border: msg.role === "assistant" ? `1px solid ${activeSystem.color}30` : "none",
                    color: msg.role === "user" ? "#E8E8FA" : "#D0D0EC",
                  }}>
                    {msg.content}
                  </div>
                  {msg.role === "user" && (
                    <div style={{ width: 32, height: 32, borderRadius: 8, background: "#1A1A3A", border: "1px solid #4040A0", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, color: "#A0A0D0", fontFamily: "monospace", flexShrink: 0 }}>KM</div>
                  )}
                </div>
              ))}
              {loading && (
                <div style={{ display: "flex", alignItems: "flex-end", gap: 10 }}>
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: activeSystem.color, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 8, fontWeight: 800, color: "#06060F", fontFamily: "monospace" }}>{activeSystem.id}</div>
                  <div style={{ padding: "16px 18px", background: "#0C0C22", border: `1px solid ${activeSystem.color}30`, borderRadius: "16px 16px 16px 4px", display: "flex", gap: 5, alignItems: "center" }}>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#3A3A7A", display: "inline-block" }} className="animate-bounce-dot" />
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#3A3A7A", display: "inline-block" }} className="animate-bounce-dot-2" />
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#3A3A7A", display: "inline-block" }} className="animate-bounce-dot-3" />
                  </div>
                </div>
              )}
              <div id="chat-bottom" />
            </div>

            {/* Input */}
            <div style={{ padding: "14px 20px 16px", borderTop: "1px solid #161630", background: "#07071A", flexShrink: 0 }}>
              <div style={{ display: "flex", gap: 10, marginBottom: 8 }}>
                <textarea
                  rows={1}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                  placeholder={`Address ${activeSystem.name}…`}
                  style={{
                    flex: 1, background: "#0C0C22", border: "1px solid #1E1E40",
                    borderRadius: 12, padding: "12px 16px", color: "#DDE0F0",
                    fontSize: 13, fontFamily: "inherit", outline: "none",
                    resize: "none", lineHeight: 1.5,
                  }}
                />
                <button
                  onClick={handleSend}
                  disabled={loading || !input.trim()}
                  style={{
                    width: 46, height: 46, borderRadius: 12, border: "none",
                    background: input.trim() && !loading ? activeSystem.color : "#1A1A3A",
                    color: "#E8E8FA", fontSize: 18, fontWeight: 700,
                    cursor: input.trim() && !loading ? "pointer" : "not-allowed",
                    flexShrink: 0, opacity: loading || !input.trim() ? 0.4 : 1,
                  }}
                >↑</button>
              </div>
              <div style={{ fontSize: 9, color: "#22224A", letterSpacing: 1.5, fontFamily: "monospace" }}>
                PAMASMMA · {activeSystemId} · MALI v7 · {thread.length} exchanges · Enter to send
              </div>
            </div>
          </>
        )}

        {/* Action Log Tab */}
        {activeTab === "log" && <ActionLogPanel systemId={activeSystemId} />}
      </div>
    </div>
  );
}

function ActionLogPanel({ systemId }: { systemId: SystemId }) {
  const [entries, setEntries] = useState<any[]>([]);
  const activeSystem = SYSTEMS.find(s => s.id === systemId)!;

  useEffect(() => {
    cognitive.getActionLog(systemId, 100)
      .then(d => setEntries(d.entries))
      .catch(() => {});
  }, [systemId]);

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
      <div style={{ fontSize: 10, letterSpacing: 2, color: "#3A3A6A", marginBottom: 16, fontFamily: "monospace" }}>
        ACTION LOG — {systemId} — {entries.length} entries
      </div>
      {entries.length === 0 && (
        <div style={{ color: "#2A2A5A", fontSize: 12 }}>No invocations logged yet.</div>
      )}
      {entries.map(e => (
        <div key={e.id} style={{ background: "#0C0C22", border: "1px solid #161630", borderRadius: 8, padding: "10px 14px", marginBottom: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span style={{ fontSize: 9, color: activeSystem.color, fontFamily: "monospace", fontWeight: 700 }}>{e.system_id}</span>
            <span style={{ fontSize: 9, color: "#3A3A6A", fontFamily: "monospace" }}>{e.latency_ms}ms · {new Date(e.created_at).toLocaleTimeString()}</span>
          </div>
          <div style={{ fontSize: 12, color: "#8080C0", lineHeight: 1.5 }}>{e.query_preview}</div>
        </div>
      ))}
    </div>
  );
}

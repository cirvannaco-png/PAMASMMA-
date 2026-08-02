/**
 * PAMASMMA v4 — Cognitive Chat Panel
 * Handles message display and input for any cognitive system.
 */
"use client";
import { useEffect, useRef, useState } from "react";
import { SYSTEM_MAP } from "@/lib/constants";
import type { Message, SystemId } from "@/types";

interface ChatPanelProps {
  systemId: SystemId;
  messages: Message[];
  loading: boolean;
  onSend: (content: string) => void;
}

export function CognitiveChatPanel({ systemId, messages, loading, onSend }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const sys = SYSTEM_MAP[systemId];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = () => {
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
  };

  return (
    <>
      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "24px 20px", display: "flex", flexDirection: "column", gap: 16 }}>

        {messages.length === 0 && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, textAlign: "center", paddingTop: 80, opacity: 0.65 }}>
            <div style={{ fontSize: 46, color: sys.color, marginBottom: 12 }} className="animate-float">⬡</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#C0C0E0" }}>{sys.name}</div>
            <div style={{ fontSize: 11, color: "#3A3A6A", maxWidth: 320, lineHeight: 1.6, marginTop: 6 }}>
              Address this cognitive system to engage its intelligence
            </div>
            <div style={{ fontSize: 9, color: "#2A2A5A", letterSpacing: 1.5, marginTop: 10, fontFamily: "monospace" }}>
              {systemId} · MALI v7 · READY
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "flex-end", gap: 10,
            justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
          }}>
            {msg.role === "assistant" && (
              <Avatar id={sys.id} color={sys.color} />
            )}
            <div style={{
              padding: "12px 16px",
              maxWidth: "70%",
              fontSize: 13,
              lineHeight: 1.7,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              background: msg.role === "user" ? "#6B3FFB" : "#0C0C22",
              borderRadius: msg.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
              border: msg.role === "assistant" ? `1px solid ${sys.color}30` : "none",
              color: msg.role === "user" ? "#E8E8FA" : "#D0D0EC",
            }}>
              {msg.content}
            </div>
            {msg.role === "user" && <UserAvatar />}
          </div>
        ))}

        {loading && (
          <div style={{ display: "flex", alignItems: "flex-end", gap: 10 }}>
            <Avatar id={sys.id} color={sys.color} />
            <div style={{ padding: "16px 18px", background: "#0C0C22", border: `1px solid ${sys.color}30`, borderRadius: "16px 16px 16px 4px", display: "flex", gap: 5, alignItems: "center" }}>
              <Dot delay={0} />
              <Dot delay={0.18} />
              <Dot delay={0.36} />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ padding: "14px 20px 16px", borderTop: "1px solid #161630", background: "#07071A", flexShrink: 0 }}>
        <div style={{ display: "flex", gap: 10, marginBottom: 8 }}>
          <textarea
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder={`Address ${sys.name}…`}
            style={{
              flex: 1, background: "#0C0C22",
              border: `1px solid ${input ? "#3A3AFB" : "#1E1E40"}`,
              borderRadius: 12, padding: "12px 16px",
              color: "#DDE0F0", fontSize: 13,
              fontFamily: "inherit", outline: "none",
              resize: "none", lineHeight: 1.5,
              transition: "border-color 0.15s",
            }}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            style={{
              width: 46, height: 46, borderRadius: 12, border: "none",
              background: input.trim() && !loading ? sys.color : "#1A1A3A",
              color: "#E8E8FA", fontSize: 18, fontWeight: 700,
              cursor: input.trim() && !loading ? "pointer" : "not-allowed",
              flexShrink: 0,
              opacity: !input.trim() || loading ? 0.4 : 1,
              transition: "background 0.15s",
            }}
          >↑</button>
        </div>
        <div style={{ fontSize: 9, color: "#22224A", letterSpacing: 1.5, fontFamily: "monospace" }}>
          PAMASMMA · {sys.id} · MALI v7 · {messages.length} exchanges · Enter to send · Shift+Enter for newline
        </div>
      </div>
    </>
  );
}

function Avatar({ id, color }: { id: string; color: string }) {
  return (
    <div style={{
      width: 32, height: 32, borderRadius: 8,
      background: color, display: "flex",
      alignItems: "center", justifyContent: "center",
      fontSize: 8, fontWeight: 800, color: "#06060F",
      fontFamily: "monospace", flexShrink: 0,
    }}>
      {id}
    </div>
  );
}

function UserAvatar() {
  return (
    <div style={{
      width: 32, height: 32, borderRadius: 8,
      background: "#1A1A3A", border: "1px solid #4040A0",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 9, color: "#A0A0D0", fontFamily: "monospace", flexShrink: 0,
    }}>
      KM
    </div>
  );
}

function Dot({ delay }: { delay: number }) {
  return (
    <span style={{
      width: 7, height: 7, borderRadius: "50%",
      background: "#3A3A7A", display: "inline-block",
      animation: `bounce-dot 1.1s ease-in-out ${delay}s infinite`,
    }} />
  );
}

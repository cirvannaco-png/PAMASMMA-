/**
 * PAMASMMA v4 — Cognitive Chat Panel
 * Handles message display and input for any cognitive system.
 */
"use client";
import { useEffect, useRef, useState } from "react";
import { SYSTEM_MAP } from "@/lib/constants";
import type { CognitiveMetadataEvent, Message, SystemId } from "@/types";

interface ChatPanelProps {
  systemId: SystemId;
  messages: Message[];
  loading: boolean;
  cognition: CognitiveMetadataEvent | null;
  onSend: (content: string) => void;
}

export function CognitiveChatPanel({ systemId, messages, loading, cognition, onSend }: ChatPanelProps) {
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

        {cognition && <CognitionPanel cognition={cognition} systemColor={sys.color} />}

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

function CognitionPanel({
  cognition,
  systemColor,
}: {
  cognition: CognitiveMetadataEvent;
  systemColor: string;
}) {
  const trace = cognition.cognition;
  const decision = cognition.decision;
  const confidence = Math.round(trace.confidence * 100);

  return (
    <div
      style={{
        width: "100%",
        maxWidth: 760,
        border: `1px solid ${systemColor}24`,
        background: "#08081B",
        borderRadius: 14,
        padding: 14,
      }}
      aria-label="Cognitive decision trace"
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 12,
          flexWrap: "wrap",
          alignItems: "center",
          marginBottom: 10,
        }}
      >
        <span style={{ fontSize: 9, fontFamily: "monospace", letterSpacing: 1.5, color: "#64649A" }}>
          VERIFIED COGNITION
        </span>
        <span style={{ fontSize: 11, fontFamily: "monospace", color: systemColor }}>
          CONFIDENCE {confidence}%
        </span>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
        <TraceChip label="Intent" value={trace.intent} />
        <TraceChip label="Complexity" value={trace.complexity} />
        <TraceChip label="Provider" value={trace.provider} />
        <TraceChip label="Verification" value={`${Math.round(trace.verification.score * 100)}%`} />
        <TraceChip label="Evidence" value={trace.evidence_status} />
      </div>

      <div style={{ fontSize: 11, color: "#9090C0", lineHeight: 1.6, marginBottom: 10 }}>
        Routed: <span style={{ color: "#C5C5E8" }}>{trace.routed_systems.join(" · ")}</span>
      </div>

      <div style={{ fontSize: 11, color: "#7070A0", lineHeight: 1.6 }}>
        <strong style={{ color: "#B8B8DE" }}>Next action:</strong>{" "}
        {decision.selected_action}
      </div>

      {trace.uncertainty.length > 0 && (
        <div style={{ marginTop: 10, fontSize: 10, color: "#8585A8", lineHeight: 1.6 }}>
          <strong style={{ color: "#A7A7C4" }}>Uncertainty:</strong>{" "}
          {trace.uncertainty.join(" · ")}
        </div>
      )}
    </div>
  );
}

function TraceChip({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <span
      style={{
        display: "inline-flex",
        gap: 5,
        alignItems: "center",
        border: "1px solid #1E1E40",
        borderRadius: 999,
        padding: "5px 8px",
        fontSize: 9,
        fontFamily: "monospace",
        color: "#8585B0",
      }}
    >
      <span style={{ color: "#46466C" }}>{label}</span>
      <span style={{ color: "#B0B0D4" }}>{value}</span>
    </span>
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

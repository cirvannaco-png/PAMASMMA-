/**
 * PAMASMMA — Cognitive navigation sidebar.
 */
"use client";

import { useRouter } from "next/navigation";
import { useCognitiveStore } from "@/lib/store";
import { SYSTEMS, PERSONALITY } from "@/lib/constants";
import { SectionLabel, StatusDot } from "@/components/ui";
import type { SystemId } from "@/types";
import { KnowledgeTrainingPanel } from "@/components/knowledge/KnowledgeTrainingPanel";

interface SidebarProps {
  onLogout: () => void;
  onSystemSelect?: (systemId: SystemId) => void;
}

export function Sidebar({ onLogout, onSystemSelect }: SidebarProps) {
  const router = useRouter();
  const { activeSystemId, threads, setActiveSystem } = useCognitiveStore();

  return (
    <aside
      className="pamasmma-sidebar"
      aria-label="Cognitive system navigation"
      style={{
        width: 264,
        flexShrink: 0,
        background: "#07071A",
        borderRight: "1px solid #161630",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div style={{ padding: "18px 16px", borderBottom: "1px solid #161630", display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 22, color: "#6B3FFB", flexShrink: 0 }} aria-hidden="true">⬡</span>
        <div>
          <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: 3, color: "#E8E8FA" }}>PAMASMMA</div>
          <div style={{ fontSize: 8, color: "#3A3A6A", letterSpacing: 1.5, marginTop: 2 }}>Synthetic Executive Intelligence</div>
        </div>
      </div>

      <div style={{ padding: "12px 14px", borderBottom: "1px solid #111128" }}>
        <SectionLabel>Personality Baseline</SectionLabel>
        {PERSONALITY.map((p) => (
          <div key={p.key} style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 8 }}>
            <span style={{ fontSize: 9, color: "#6060A0", fontFamily: "monospace", width: 26 }}>{p.key}</span>
            <div style={{ flex: 1, height: 3, background: "#161630", borderRadius: 2, overflow: "hidden" }}>
              <div style={{ width: `${p.val * 100}%`, height: "100%", background: "linear-gradient(90deg,#6B3FFB,#9B6BFF)", borderRadius: 2 }} />
            </div>
            <span style={{ fontSize: 9, color: "#6B3FFB", fontFamily: "monospace", width: 28, textAlign: "right" }}>{p.val}</span>
          </div>
        ))}
      </div>

      <div style={{ padding: "8px 14px", borderBottom: "1px solid #111128" }}>
        <button
          type="button"
          onClick={() => router.push("/social")}
          style={{
            width: "100%",
            padding: "9px 10px",
            borderRadius: 8,
            border: "1px solid #2B2450",
            background: "#141128",
            color: "#BBAEFF",
            textAlign: "left",
            cursor: "pointer",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: 1,
          }}
        >
          SOCIAL GROWTH →
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "12px 14px" }}>
        <SectionLabel>Knowledge Training</SectionLabel>
        <div style={{ marginBottom: 12 }}>
          <KnowledgeTrainingPanel />
        </div>
        <SectionLabel>Cognitive Systems</SectionLabel>
        {SYSTEMS.map((sys) => {
          const msgCount = threads[sys.id as SystemId]?.length ?? 0;
          const isActive = activeSystemId === sys.id;
          return (
            <button
              key={sys.id}
              type="button"
              aria-pressed={isActive}
              onClick={() => {
                const id = sys.id as SystemId;
                setActiveSystem(id);
                onSystemSelect?.(id);
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "7px 8px",
                borderRadius: 8,
                width: "100%",
                marginBottom: 3,
                cursor: "pointer",
                textAlign: "left",
                border: `1px solid ${isActive ? sys.color : "transparent"}`,
                background: isActive ? `${sys.color}12` : "transparent",
                transition: "all 0.12s",
              }}
            >
              <span
                style={{
                  fontSize: 8,
                  fontWeight: 800,
                  color: "#06060F",
                  padding: "2px 5px",
                  borderRadius: 4,
                  background: sys.color,
                  minWidth: 30,
                  textAlign: "center",
                  fontFamily: "monospace",
                  flexShrink: 0,
                }}
              >
                {sys.id}
              </span>
              <span style={{ fontSize: 11, color: isActive ? "#E8E8FA" : "#B0B0D0", fontWeight: 500, flex: 1, lineHeight: 1.3 }}>
                {sys.name}
              </span>
              {msgCount > 0 && (
                <span style={{ fontSize: 9, color: "#5050A0", background: "#12122A", padding: "1px 5px", borderRadius: 10, fontFamily: "monospace" }}>
                  {msgCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div style={{ padding: "12px 16px", borderTop: "1px solid #111128" }}>
        {[
          { color: "#3BFFA0", label: "MALI v7 · ACTIVE" },
          { color: "#00D4FF", label: "17 MCP · BOUND" },
          { color: "#D4AF37", label: "Cirvanna · Nakuru KE" },
        ].map((f) => (
          <div key={f.label} style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 6, fontSize: 9, color: "#3A3A6A", fontFamily: "monospace" }}>
            <StatusDot color={f.color} />
            {f.label}
          </div>
        ))}
        <button
          type="button"
          onClick={onLogout}
          style={{ marginTop: 8, fontSize: 9, color: "#2A2A5A", background: "none", border: "none", cursor: "pointer", letterSpacing: 1, padding: 0 }}
        >
          LOGOUT ↗
        </button>
      </div>
    </aside>
  );
}

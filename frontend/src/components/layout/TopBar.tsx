/**
 * PAMASMMA v4 — TopBar Component
 */
"use client";
import { StatusDot } from "@/components/ui";
import { SYSTEM_MAP } from "@/lib/constants";
import type { SystemId } from "@/types";

interface TopBarProps {
  activeSystemId: SystemId;
  activeTab: "chat" | "log" | "override";
  onTabChange: (tab: "chat" | "log" | "override") => void;
  onToggleSidebar: () => void;
}

export function TopBar({ activeSystemId, activeTab, onTabChange, onToggleSidebar }: TopBarProps) {
  const sys = SYSTEM_MAP[activeSystemId];

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "14px 20px", borderBottom: "1px solid #161630",
      background: "#07071A", flexShrink: 0,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button
          onClick={onToggleSidebar}
          style={{ background: "none", border: "none", color: "#404080", cursor: "pointer", fontSize: 16, lineHeight: 1 }}
        >
          ☰
        </button>
        <span style={{ width: 9, height: 9, borderRadius: "50%", background: sys.color, display: "inline-block", flexShrink: 0 }} />
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#E8E8FA" }}>{sys.name}</div>
          <div style={{ fontSize: 10, color: "#3A3A6A", marginTop: 2 }}>
            {activeSystemId} · Cognitive System
          </div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        {(["chat", "log", "override"] as const).map(tab => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            style={{
              fontSize: 9, letterSpacing: 2, fontWeight: 700,
              textTransform: "uppercase", background: "none", border: "none",
              cursor: "pointer",
              color: activeTab === tab ? sys.color : "#3A3A6A",
              borderBottom: activeTab === tab ? `1px solid ${sys.color}` : "1px solid transparent",
              paddingBottom: 2,
              transition: "color 0.15s",
            }}
          >
            {tab}
          </button>
        ))}

        <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 9, color: "#00D4FF", letterSpacing: 2, fontFamily: "monospace", fontWeight: 700 }}>
          <StatusDot color="#00D4FF" />
          {activeSystemId} · ONLINE
        </div>
      </div>
    </div>
  );
}

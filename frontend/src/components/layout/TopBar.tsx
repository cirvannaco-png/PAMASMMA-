/**
 * PAMASMMA — Console top bar.
 */
"use client";

import { StatusDot } from "@/components/ui";
import { SYSTEM_MAP } from "@/lib/constants";
import type { SystemId } from "@/types";

interface TopBarProps {
  activeSystemId: SystemId;
  activeTab: "chat" | "knowledge" | "log" | "override";
  onTabChange: (tab: "chat" | "knowledge" | "log" | "override") => void;
  onToggleSidebar: () => void;
}

export function TopBar({ activeSystemId, activeTab, onTabChange, onToggleSidebar }: TopBarProps) {
  const sys = SYSTEM_MAP[activeSystemId];

  return (
    <div
      className="pamasmma-header"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "14px 20px",
        borderBottom: "1px solid #161630",
        background: "#07071A",
        flexShrink: 0,
        gap: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
        <button
          type="button"
          aria-label="Toggle navigation"
          onClick={onToggleSidebar}
          style={{ background: "none", border: "none", color: "#404080", cursor: "pointer", fontSize: 16, lineHeight: 1, flexShrink: 0 }}
        >
          ☰
        </button>
        <span style={{ width: 9, height: 9, borderRadius: "50%", background: sys.color, display: "inline-block", flexShrink: 0 }} aria-hidden="true" />
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#E8E8FA", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{sys.name}</div>
          <div style={{ fontSize: 10, color: "#3A3A6A", marginTop: 2 }}>{activeSystemId} · Cognitive System</div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 14, flexShrink: 0 }}>
        <div className="pamasmma-header-tabs" style={{ display: "flex", alignItems: "center", gap: 18 }}>
          {(["chat", "knowledge", "log", "override"] as const).map((tab) => (
            <button
              type="button"
              key={tab === "knowledge" ? "learn" : tab}
              aria-pressed={activeTab === tab}
              onClick={() => onTabChange(tab)}
              style={{
                fontSize: 9,
                letterSpacing: 2,
                fontWeight: 700,
                textTransform: "uppercase",
                background: "none",
                border: "none",
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
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 9, color: "#00D4FF", letterSpacing: 2, fontFamily: "monospace", fontWeight: 700 }}>
          <StatusDot color="#00D4FF" />
          <span className="pamasmma-status-label">{activeSystemId} · ONLINE</span>
          <span className="pamasmma-status-short">{activeSystemId}</span>
        </div>
      </div>
    </div>
  );
}

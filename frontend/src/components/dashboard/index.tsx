/**
 * PAMASMMA v4 — Dashboard Components
 * ActionLog: invocation history with latency.
 * OverrideQueue: S7 behavioral override submission + history.
 */
"use client";
import { useEffect, useState } from "react";
import { cognitive } from "@/lib/api";
import { SYSTEM_MAP } from "@/lib/constants";
import { Card, Badge, SectionLabel, Button } from "@/components/ui";
import type { ActionLogEntry, SystemId } from "@/types";
import toast from "react-hot-toast";

// ── Action Log ────────────────────────────────────────────────────────────────

interface ActionLogProps {
  systemId?: SystemId;
}

export function ActionLog({ systemId }: ActionLogProps) {
  const [entries, setEntries] = useState<ActionLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const sys = systemId ? SYSTEM_MAP[systemId] : null;

  useEffect(() => {
    setLoading(true);
    cognitive.getActionLog(systemId, 100)
      .then(d => setEntries(d.entries))
      .catch(() => toast.error("Failed to load action log"))
      .finally(() => setLoading(false));
  }, [systemId]);

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
      <SectionLabel>
        Action Log{systemId ? ` — ${systemId}` : " — All Systems"} · {entries.length} entries
      </SectionLabel>

      {loading && (
        <div style={{ color: "#3A3A6A", fontSize: 12, fontFamily: "monospace" }}>Loading…</div>
      )}

      {!loading && entries.length === 0 && (
        <div style={{ color: "#2A2A5A", fontSize: 12 }}>No invocations logged yet.</div>
      )}

      {entries.map(e => {
        const entryColor = SYSTEM_MAP[e.system_id as SystemId]?.color ?? "#6B3FFB";
        return (
          <Card key={e.id} accent={entryColor} style={{ marginBottom: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <Badge color={entryColor}>{e.system_id}</Badge>
                <span style={{ fontSize: 11, color: "#6060A0" }}>{e.system_name}</span>
              </div>
              <div style={{ display: "flex", gap: 12, fontSize: 9, color: "#3A3A6A", fontFamily: "monospace" }}>
                <span>{e.latency_ms.toFixed(0)}ms</span>
                <span>{new Date(e.created_at).toLocaleString("en-KE", { timeZone: "Africa/Nairobi" })}</span>
              </div>
            </div>
            <div style={{ fontSize: 12, color: "#8080C0", lineHeight: 1.5 }}>{e.query_preview}</div>
          </Card>
        );
      })}
    </div>
  );
}

// ── Override Queue ────────────────────────────────────────────────────────────

interface OverrideQueueProps {
  systemId: SystemId;
}

export function OverrideQueue({ systemId }: OverrideQueueProps) {
  const [directive, setDirective] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const sys = SYSTEM_MAP[systemId];

  const handleSubmit = async () => {
    if (!directive.trim() || !reason.trim()) {
      toast.error("Both directive and reason are required");
      return;
    }
    setSubmitting(true);
    try {
      await cognitive.queueOverride(systemId, directive.trim(), reason.trim());
      toast.success(`Override queued for ${systemId}`);
      setDirective("");
      setReason("");
    } catch (e: any) {
      toast.error(e.message ?? "Failed to queue override");
    } finally {
      setSubmitting(false);
    }
  };

  const textareaStyle: React.CSSProperties = {
    width: "100%",
    background: "#0C0C22",
    border: "1px solid #1E1E40",
    borderRadius: 10,
    padding: "12px 14px",
    color: "#DDE0F0",
    fontSize: 12,
    fontFamily: "inherit",
    outline: "none",
    resize: "vertical",
    lineHeight: 1.6,
    marginBottom: 12,
  };

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: 24, maxWidth: 640 }}>
      <SectionLabel>Override Queue — {systemId}</SectionLabel>
      <div style={{ fontSize: 11, color: "#3A3A6A", lineHeight: 1.6, marginBottom: 20 }}>
        Queue a behavioral override directive for the {sys.name} system.
        Overrides are processed by S7 Behavioral Consistency and logged to the action log.
      </div>

      <Card accent={sys.color} style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 10, color: "#3A3A6A", marginBottom: 6, fontFamily: "monospace", letterSpacing: 1 }}>DIRECTIVE</div>
        <textarea
          rows={4}
          value={directive}
          onChange={e => setDirective(e.target.value)}
          placeholder="Enter the behavioral override directive…"
          style={textareaStyle}
        />

        <div style={{ fontSize: 10, color: "#3A3A6A", marginBottom: 6, fontFamily: "monospace", letterSpacing: 1 }}>REASON</div>
        <textarea
          rows={2}
          value={reason}
          onChange={e => setReason(e.target.value)}
          placeholder="Explain the reason for this override…"
          style={textareaStyle}
        />

        <Button
          onClick={handleSubmit}
          loading={submitting}
          disabled={!directive.trim() || !reason.trim()}
          style={{ background: sys.color }}
        >
          Queue Override →
        </Button>
      </Card>

      <div style={{ fontSize: 9, color: "#2A2A5A", fontFamily: "monospace", lineHeight: 1.8 }}>
        ⚠ Overrides are governed by S7 Behavioral Consistency.<br />
        All overrides are logged and auditable.<br />
        Personality baseline cannot be permanently overridden.
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";

import { knowledge } from "@/lib/api";
import { Badge, Button, Card, SectionLabel } from "@/components/ui";
import type { KnowledgeSource, KnowledgeTrainingMode, SystemId } from "@/types";

interface Props {
  activeSystemId: SystemId;
}

const MODES: Array<{
  value: KnowledgeTrainingMode;
  label: string;
  description: string;
}> = [
  { value: "reference", label: "Reference", description: "Facts and reference material." },
  { value: "behavioral", label: "Behavioral", description: "Preferences, methods and procedures." },
  { value: "domain_playbook", label: "Domain playbook", description: "Specialized rules and repeatable playbooks." },
];

const STATUS_LABEL: Record<string, string> = {
  processing: "PROCESSING",
  ready: "READY",
  awaiting_transcription: "AWAITING TRANSCRIPTION",
  failed: "FAILED",
};

export function KnowledgeTraining({ activeSystemId }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [title, setTitle] = useState("");
  const [mode, setMode] = useState<KnowledgeTrainingMode>("reference");
  const [scope, setScope] = useState<"global" | SystemId>("global");
  const [transcript, setTranscript] = useState("");
  const [uploading, setUploading] = useState(false);

  const loadSources = useCallback(async () => {
    try {
      const data = await knowledge.list();
      setSources(data.sources);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to load knowledge sources.",
      );
    }
  }, []);

  useEffect(() => {
    void loadSources();
  }, [loadSources]);

  const handleUpload = async () => {
    if (!files.length || uploading) return;
    setUploading(true);
    try {
      for (const file of files) {
        await knowledge.upload({
          file,
          title: title.trim() || undefined,
          training_mode: mode,
          scope_system_id: scope === "global" ? undefined : scope,
          transcript: transcript.trim() || undefined,
        });
      }
      toast.success(
        files.length === 1
          ? "Source trained into PAMASMMA."
          : files.length + " sources trained into PAMASMMA.",
      );
      setFiles([]);
      setTitle("");
      setTranscript("");
      if (inputRef.current) inputRef.current.value = "";
      await loadSources();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Knowledge ingestion failed.",
      );
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (sourceId: string) => {
    try {
      await knowledge.remove(sourceId);
      setSources((current) =>
        current.filter((source) => source.id !== sourceId),
      );
      toast.success("Knowledge source removed.");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to remove source.",
      );
    }
  };

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: 24 }}>
      <div style={{ maxWidth: 960 }}>
        <SectionLabel>Knowledge Training · {sources.length} sources</SectionLabel>
        <div style={{ color: "#6060A0", fontSize: 11, lineHeight: 1.7, marginBottom: 18, maxWidth: 760 }}>
          Upload books, notes, transcripts, audio or video. PAMASMMA extracts and indexes source-backed knowledge with provenance instead of blindly changing model weights.
        </div>

        <Card accent="#D4AF37" style={{ marginBottom: 20 }}>
          <div style={{ display: "grid", gap: 14 }}>
            <div>
              <div style={{ fontSize: 10, color: "#3A3A6A", fontFamily: "monospace", letterSpacing: 1, marginBottom: 6 }}>SOURCE FILES</div>
              <input
                ref={inputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.epub,.txt,.md,.markdown,.rst,.log,.srt,.vtt,.mp3,.wav,.m4a,.aac,.flac,.ogg,.mp4,.mov,.mkv,.webm,.avi,.m4v"
                onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
                style={{ width: "100%", color: "#B0B0D0", fontSize: 12 }}
              />
              {files.length > 0 && (
                <div style={{ marginTop: 8, fontSize: 10, color: "#6060A0", overflowWrap: "anywhere" }}>
                  {files.map((file) => file.name).join(" · ")}
                </div>
              )}
            </div>

            <div>
              <div style={{ fontSize: 10, color: "#3A3A6A", fontFamily: "monospace", letterSpacing: 1, marginBottom: 6 }}>TITLE (OPTIONAL)</div>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="e.g. The Intelligent Investor — chapters 1–5"
                style={{ width: "100%", background: "#0C0C22", border: "1px solid #1E1E40", borderRadius: 9, padding: "10px 12px", color: "#DDE0F0", fontSize: 12, outline: "none" }}
              />
            </div>

            <div>
              <div style={{ fontSize: 10, color: "#3A3A6A", fontFamily: "monospace", letterSpacing: 1, marginBottom: 8 }}>TRAINING MODE</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8 }}>
                {MODES.map((item) => (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => setMode(item.value)}
                    style={{
                      textAlign: "left",
                      padding: 11,
                      borderRadius: 9,
                      border: "1px solid " + (mode === item.value ? "#D4AF37" : "#1E1E40"),
                      background: mode === item.value ? "#17152A" : "#0C0C22",
                      color: "#DDE0F0",
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ fontSize: 11, fontWeight: 700 }}>{item.label}</div>
                    <div style={{ fontSize: 9, color: "#6060A0", marginTop: 4, lineHeight: 1.4 }}>{item.description}</div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 10, color: "#3A3A6A", fontFamily: "monospace", letterSpacing: 1, marginBottom: 6 }}>KNOWLEDGE SCOPE</div>
              <select
                value={scope}
                onChange={(event) => setScope(event.target.value as "global" | SystemId)}
                style={{ width: "100%", background: "#0C0C22", border: "1px solid #1E1E40", borderRadius: 9, padding: "10px 12px", color: "#DDE0F0", fontSize: 12 }}
              >
                <option value="global">Global PAMASMMA knowledge</option>
                <option value={activeSystemId}>{activeSystemId} only</option>
              </select>
            </div>

            <div>
              <div style={{ fontSize: 10, color: "#3A3A6A", fontFamily: "monospace", letterSpacing: 1, marginBottom: 6 }}>VIDEO / AUDIO TRANSCRIPT (OPTIONAL)</div>
              <textarea
                value={transcript}
                onChange={(event) => setTranscript(event.target.value)}
                rows={3}
                placeholder="Paste a transcript when media has no embedded subtitles or transcription provider."
                style={{ width: "100%", background: "#0C0C22", border: "1px solid #1E1E40", borderRadius: 9, padding: "10px 12px", color: "#DDE0F0", fontSize: 12, outline: "none", resize: "vertical" }}
              />
            </div>

            <Button
              onClick={handleUpload}
              loading={uploading}
              disabled={!files.length}
              style={{ background: "#D4AF37", color: "#08080F" }}
            >
              Train Sources →
            </Button>
          </div>
        </Card>

        <div style={{ display: "grid", gap: 8 }}>
          {sources.map((source) => (
            <Card key={source.id} style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center" }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  <Badge color="#D4AF37">{STATUS_LABEL[source.status] ?? source.status.toUpperCase()}</Badge>
                  <Badge color="#6B3FFB">{source.training_mode.replace("_", " ")}</Badge>
                  <span style={{ fontSize: 11, color: "#C0C0D8", fontWeight: 700 }}>{source.title}</span>
                </div>
                <div style={{ marginTop: 5, color: "#6060A0", fontSize: 10, overflowWrap: "anywhere" }}>
                  {source.filename} · {source.chunk_count} chunks · {source.extraction_method}
                </div>
                {source.error && (
                  <div style={{ marginTop: 5, color: "#FF7A9D", fontSize: 10, lineHeight: 1.5 }}>
                    {source.error}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => void handleDelete(source.id)}
                style={{ border: "1px solid #2A2A5A", background: "transparent", color: "#7070A0", borderRadius: 8, padding: "7px 10px", cursor: "pointer", fontSize: 10, flexShrink: 0 }}
              >
                Remove
              </button>
            </Card>
          ))}
          {sources.length === 0 && (
            <div style={{ color: "#3A3A6A", fontSize: 11, padding: "24px 4px" }}>
              No training sources yet. Your first uploaded book, note or lecture will appear here.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

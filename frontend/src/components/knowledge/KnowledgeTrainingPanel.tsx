/**
 * PAMASMMA — Knowledge Training panel.
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { knowledge, type KnowledgeSource } from "@/lib/api";

const ACCEPT =
  ".pdf,.epub,.docx,.txt,.md,.csv,.json,.srt,.vtt,.mp3,.wav,.m4a,.aac,.ogg,.flac,.mp4,.mov,.mkv,.avi,.m4v,.webm";

export function KnowledgeTrainingPanel() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [training, setTraining] = useState(false);
  const [mode, setMode] = useState<"knowledge" | "procedure">("knowledge");
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const result = await knowledge.listSources(20);
      setSources(result.sources);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load knowledge sources.");
    }
  });

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const uploadFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setTraining(true);
    setError(null);

    const selected = Array.from(files);
    let completed = 0;

    try {
      for (const file of selected) {
        setProgress(`${completed + 1}/${selected.length} · ${file.name}`);
        await knowledge.upload(file, mode);
        completed += 1;
      }
      setProgress(`${completed} source${completed === 1 ? "" : "s"} ingested`);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Knowledge ingestion failed.");
    } finally {
      setTraining(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const remove = async (source: KnowledgeSource) => {
    if (!window.confirm(`Remove ${source.filename} from PAMASMMA knowledge?`)) {
      return;
    }

    try {
      setError(null);
      await knowledge.remove(source.id);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to remove source.");
    }
  };

  return (
    <section aria-label="Knowledge Training">
      <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
        <select
          value={mode}
          onChange={(event) =>
            setMode(event.target.value as "knowledge" | "procedure")
          }
          disabled={training}
          aria-label="Training mode"
          style={{
            flex: 1,
            minWidth: 0,
            padding: "7px 8px",
            border: "1px solid #2A2455",
            borderRadius: 7,
            background: "#0E0E25",
            color: "#AFAFD0",
            fontSize: 9,
          }}
        >
          <option value="knowledge">Knowledge</option>
          <option value="procedure">Procedure / Rules</option>
        </select>
        <button
          type="button"
          disabled={training}
          onClick={() => inputRef.current?.click()}
          style={{
            flex: 1.35,
            padding: "7px 8px",
            border: "1px solid #2A2455",
            borderRadius: 7,
            background: "#10102A",
            color: "#B9A8FF",
            cursor: training ? "wait" : "pointer",
            fontSize: 9,
            fontWeight: 700,
          }}
        >
          {training ? "INGESTING…" : "＋ ADD SOURCES"}
        </button>
      </div>

      <input
        ref={inputRef}
        hidden
        multiple
        type="file"
        accept={ACCEPT}
        onChange={(event) => void uploadFiles(event.target.files)}
      />

      {progress && (
        <div style={{ marginBottom: 7, color: "#7474A8", fontSize: 8 }}>
          {progress}
        </div>
      )}

      {error && (
        <div
          role="alert"
          style={{
            marginBottom: 8,
            padding: "6px 7px",
            borderRadius: 6,
            border: "1px solid #5A2B45",
            background: "#211020",
            color: "#FF9AB8",
            fontSize: 8,
            lineHeight: 1.35,
          }}
        >
          {error}
        </div>
      )}

      <div style={{ display: "grid", gap: 5 }}>
        {sources.slice(0, 4).map((source) => (
          <div
            key={source.id}
            style={{
              display: "flex",
              gap: 7,
              alignItems: "center",
              padding: "6px 7px",
              border: "1px solid #17172F",
              borderRadius: 7,
              background: "#0B0B20",
            }}
          >
            <span style={{ fontSize: 9, color: "#6B3FFB" }}>●</span>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div
                title={source.filename}
                style={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  color: "#BDBDD8",
                  fontSize: 8,
                }}
              >
                {source.filename}
              </div>
              <div style={{ color: "#56567D", fontSize: 7, marginTop: 2 }}>
                {source.status} · {source.chunk_count ?? 0} chunks · {source.training_mode}
              </div>
            </div>
            <button
              type="button"
              onClick={() => void remove(source)}
              aria-label={`Remove ${source.filename}`}
              style={{
                border: 0,
                background: "transparent",
                color: "#5A5A86",
                cursor: "pointer",
                fontSize: 10,
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

/**
 * PAMASMMA v4 — useCognitive hook
 * Encapsulates streaming invocation logic for any cognitive system.
 */
"use client";
import { useCallback } from "react";
import toast from "react-hot-toast";
import { cognitive } from "@/lib/api";
import { useCognitiveStore } from "@/lib/store";
import type { SystemId } from "@/types";

export function useCognitive() {
  const {
    activeSystemId,
    threads,
    loading,
    addMessage,
    appendToLastMessage,
    setLoading,
    setActionLog,
  } = useCognitiveStore();

  const sendMessage = useCallback(
    async (systemId: SystemId, content: string) => {
      if (!content.trim() || loading) return;

      const thread = threads[systemId] ?? [];
      const userMsg = {
        role: "user" as const,
        content: content.trim(),
        timestamp: new Date().toISOString(),
      };
      addMessage(systemId, userMsg);
      setLoading(true);

      const allMessages = [...thread, userMsg].map(m => ({
        role: m.role,
        content: m.content,
      }));

      try {
        const res = await cognitive.invokeStream(systemId, allMessages);
        if (!res.ok) throw new Error(`Stream error: ${res.status}`);

        // Add empty assistant message to accumulate chunks into
        addMessage(systemId, { role: "assistant", content: "", timestamp: new Date().toISOString() });

        const reader = res.body!.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const raw = decoder.decode(value, { stream: true });
          for (const line of raw.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            const chunk = line.slice(6);
            if (chunk === "[DONE]") break;
            appendToLastMessage(systemId, chunk);
          }
        }
      } catch (err: any) {
        toast.error(`${systemId} system error — ${err.message ?? "check connection"}`);
      } finally {
        setLoading(false);
      }
    },
    [loading, threads, addMessage, appendToLastMessage, setLoading],
  );

  const fetchActionLog = useCallback(
    async (systemId?: SystemId) => {
      try {
        const data = await cognitive.getActionLog(systemId, 100);
        setActionLog(data.entries);
      } catch {
        toast.error("Failed to load action log");
      }
    },
    [setActionLog],
  );

  return { activeSystemId, threads, loading, sendMessage, fetchActionLog };
}

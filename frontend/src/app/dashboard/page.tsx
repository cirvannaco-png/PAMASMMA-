"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

import { cognitive } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { useCognitiveStore } from "@/lib/store";
import { SYSTEMS } from "@/lib/constants";
import type {
  CognitiveMetadataEvent,
  Message,
  SystemId,
} from "@/types";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { CognitiveChatPanel } from "@/components/cognitive/CognitiveChatPanel";
import { ActionLog, OverrideQueue } from "@/components/dashboard";

type ConsoleTab = "chat" | "log" | "override";

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, isRestoring, logout } = useAuth();
  const {
    activeSystemId,
    threads,
    loading,
    setLoading,
    addMessage,
    appendToLastMessage,
  } = useCognitiveStore();

  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<ConsoleTab>("chat");
  const [cognition, setCognition] = useState<CognitiveMetadataEvent | null>(null);

  const activeSystem = SYSTEMS.find((system) => system.id === activeSystemId)!;
  const thread: Message[] = threads[activeSystemId] ?? [];

  useEffect(() => {
    if (!isRestoring && !isAuthenticated) {
      router.replace("/auth");
    }
  }, [isAuthenticated, isRestoring, router]);

  useEffect(() => {
    setCognition(null);
  }, [activeSystemId]);

  useEffect(() => {
    const handleResize = () => {
      setSidebarOpen(window.innerWidth > 820);
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const handleSend = async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || loading) return;

    const userMsg: Message = {
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    addMessage(activeSystemId, userMsg);
    setLoading(true);

    try {
      const allMessages = [...thread, userMsg];
      const res = await cognitive.invokeStream(
        activeSystemId,
        allMessages.map((message) => ({
          role: message.role,
          content: message.content,
        })),
      );

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail ?? "Cognitive stream failed.");
      }

      if (!res.body) {
        throw new Error("Streaming response has no body.");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let streamDone = false;
      let assistantSeeded = false;

      const consumeFrame = (line: string) => {
        if (!line.startsWith("data: ")) return;

        const payload = line.slice(6);
        if (payload === "[DONE]") {
          streamDone = true;
          return;
        }

        let chunk: unknown;
        try {
          chunk = JSON.parse(payload);
        } catch {
          return;
        }

        if (
          typeof chunk === "object" &&
          chunk !== null &&
          (chunk as { type?: unknown }).type === "cognition"
        ) {
          setCognition(chunk as CognitiveMetadataEvent);
          return;
        }

        if (typeof chunk !== "string") return;

        if (!assistantSeeded) {
          addMessage(activeSystemId, {
            role: "assistant",
            content: "",
            timestamp: new Date().toISOString(),
          });
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

      if (!assistantSeeded) {
        throw new Error("The cognitive system returned no content.");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Cognitive system unavailable.");
    } finally {
      setLoading(false);
    }
  };

  if (isRestoring || !isAuthenticated) {
    return (
      <main className="grid h-screen place-items-center bg-[#04040D] px-6 text-[#6D6DA0]">
        <div className="text-center">
          <div className="font-mono text-xs tracking-[0.24em]">RESTORING SECURE SESSION…</div>
          <div className="mt-3 text-[11px] text-[#3A3A6A]">
            Access is held until the server session is confirmed.
          </div>
        </div>
      </main>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#04040D]" style={{ color: "#D0D0EC" }}>
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
          className="pamasmma-sidebar-backdrop"
        />
      )}

      {sidebarOpen && (
        <Sidebar
          onLogout={logout}
          onSystemSelect={() => {
            if (window.innerWidth <= 820) setSidebarOpen(false);
          }}
        />
      )}

      <div className="pamasmma-main" style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <TopBar
          activeSystemId={activeSystemId as SystemId}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onToggleSidebar={() => setSidebarOpen((open) => !open)}
        />

        {activeTab === "chat" && (
          <CognitiveChatPanel
            systemId={activeSystemId as SystemId}
            messages={thread}
            loading={loading}
            cognition={cognition}
            onSend={(content) => {
              void handleSend(content);
            }}
          />
        )}

        {activeTab === "log" && <ActionLog systemId={activeSystemId as SystemId} />}

        {activeTab === "override" && <OverrideQueue systemId={activeSystemId as SystemId} />}
      </div>
    </div>
  );
}

/**
 * PAMASMMA v4 — useWebSocket hook
 * Real-time event feed from the backend via Server-Sent Events (SSE).
 * Connects to /api/v1/events/stream and dispatches typed events.
 * Auto-reconnects with exponential backoff on disconnect.
 */
"use client";
import { useEffect, useRef, useCallback } from "react";

type EventType = "cognitive_invocation" | "override_queue" | "scheduler_event" | "health";
type EventHandler = (data: Record<string, unknown>) => void;

interface UseEventStreamOptions {
  enabled?: boolean;
  onEvent?: (type: EventType, data: Record<string, unknown>) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

const BASE_URL = process.env.NEXT_PUBLIC_API_URL?.replace("/api/v1", "") ?? "http://localhost:8000";
const MAX_RETRIES = 6;
const BASE_DELAY_MS = 1000;

export function useEventStream({
  enabled = true,
  onEvent,
  onConnect,
  onDisconnect,
}: UseEventStreamOptions = {}) {
  const esRef       = useRef<EventSource | null>(null);
  const retryCount  = useRef(0);
  const retryTimer  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMounted   = useRef(true);

  const connect = useCallback(() => {
    if (!enabled || !isMounted.current) return;

    // Get access token from localStorage (set by api.ts setTokens)
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("pamasmma_access") ?? ""
        : "";

    const url = `${BASE_URL}/api/v1/events/stream${token ? `?token=${token}` : ""}`;
    const es = new EventSource(url, { withCredentials: true });
    esRef.current = es;

    es.onopen = () => {
      retryCount.current = 0;
      onConnect?.();
    };

    es.onmessage = (evt) => {
      try {
        const parsed = JSON.parse(evt.data) as { type: EventType; data: Record<string, unknown> };
        onEvent?.(parsed.type, parsed.data);
      } catch {
        // Non-JSON heartbeat — ignore
      }
    };

    es.onerror = () => {
      es.close();
      esRef.current = null;
      onDisconnect?.();

      if (!isMounted.current) return;
      if (retryCount.current >= MAX_RETRIES) return;

      const delay = BASE_DELAY_MS * Math.pow(2, retryCount.current);
      retryCount.current += 1;
      retryTimer.current = setTimeout(() => connect(), delay);
    };
  }, [enabled, onEvent, onConnect, onDisconnect]);

  useEffect(() => {
    isMounted.current = true;
    if (enabled) connect();

    return () => {
      isMounted.current = false;
      if (retryTimer.current) clearTimeout(retryTimer.current);
      esRef.current?.close();
      esRef.current = null;
    };
  }, [enabled, connect]);

  const disconnect = useCallback(() => {
    if (retryTimer.current) clearTimeout(retryTimer.current);
    esRef.current?.close();
    esRef.current = null;
  }, []);

  return { disconnect, reconnect: connect };
}

/**
 * Simplified hook — subscribe to a specific event type only.
 */
export function useEventSubscription(
  eventType: EventType,
  handler: EventHandler,
  enabled = true,
) {
  const handlerRef = useRef(handler);

  useEffect(() => {
    handlerRef.current = handler;
  }, [handler]);

  useEventStream({
    enabled,
    onEvent: (type, data) => {
      if (type === eventType) handlerRef.current(data);
    },
  });
}

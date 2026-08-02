/**
 * PAMASMMA v4 — Global State (Zustand)
 * Auth store + Cognitive session store.
 */
import { create } from "zustand";
import type { Message, SystemId, AuthTokens, ActionLogEntry } from "@/types";
import { setTokens as _setTokens, clearTokens as _clearTokens } from "@/lib/api";

// ── Auth Store ────────────────────────────────────────────────────────────
interface AuthState {
  userId: string | null;
  isAuthenticated: boolean;
  setAuth: (userId: string, tokens: AuthTokens) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  userId: null,
  isAuthenticated: false,
  setAuth: (userId, tokens) => {
    _setTokens(tokens);
    set({ userId, isAuthenticated: true });
  },
  clearAuth: () => {
    _clearTokens();
    set({ userId: null, isAuthenticated: false });
  },
}));

// ── Cognitive Store ───────────────────────────────────────────────────────
interface CognitiveState {
  activeSystemId: SystemId;
  threads: Record<SystemId, Message[]>;
  loading: boolean;
  actionLog: ActionLogEntry[];

  setActiveSystem: (id: SystemId) => void;
  addMessage: (systemId: SystemId, message: Message) => void;
  appendToLastMessage: (systemId: SystemId, chunk: string) => void;
  setLoading: (v: boolean) => void;
  clearThread: (systemId: SystemId) => void;
  setActionLog: (entries: ActionLogEntry[]) => void;
}

export const useCognitiveStore = create<CognitiveState>((set) => ({
  activeSystemId: "S1",
  threads: {} as Record<SystemId, Message[]>,
  loading: false,
  actionLog: [],

  setActiveSystem: (id) => set({ activeSystemId: id }),

  addMessage: (systemId, message) =>
    set((state) => ({
      threads: {
        ...state.threads,
        [systemId]: [...(state.threads[systemId] ?? []), message],
      },
    })),

  appendToLastMessage: (systemId, chunk) =>
    set((state) => {
      const msgs = [...(state.threads[systemId] ?? [])];
      if (msgs.length === 0) return state;
      const last = msgs[msgs.length - 1];
      if (last.role !== "assistant") return state;
      msgs[msgs.length - 1] = { ...last, content: last.content + chunk };
      return { threads: { ...state.threads, [systemId]: msgs } };
    }),

  setLoading: (v) => set({ loading: v }),

  clearThread: (systemId) =>
    set((state) => ({
      threads: { ...state.threads, [systemId]: [] },
    })),

  setActionLog: (entries) => set({ actionLog: entries }),
}));

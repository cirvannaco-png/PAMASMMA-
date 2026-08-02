/**
 * PAMASMMA v4 — API Client
 * Typed fetch wrapper. Handles auth headers, token refresh, structured errors.
 */

import { AuthTokens, ActionLogEntry, CognitiveSystem, Message } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// ── Token Storage (memory + localStorage for persistence) ─────────────────
let _accessToken: string | null = null;
let _refreshToken: string | null = null;

export function setTokens(tokens: AuthTokens): void {
  _accessToken = tokens.access_token;
  _refreshToken = tokens.refresh_token;
  if (typeof window !== "undefined") {
    localStorage.setItem("pamasmma_refresh", tokens.refresh_token);
  }
}

export function clearTokens(): void {
  _accessToken = null;
  _refreshToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("pamasmma_refresh");
  }
}

export function loadStoredRefreshToken(): void {
  if (typeof window !== "undefined") {
    _refreshToken = localStorage.getItem("pamasmma_refresh");
  }
}

// ── Core Fetch ────────────────────────────────────────────────────────────
async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> ?? {}),
  };

  if (_accessToken) {
    headers["Authorization"] = `Bearer ${_accessToken}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  // Token expired — attempt silent refresh
  if (res.status === 401 && retry && _refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiFetch<T>(path, options, false);
    }
    clearTokens();
    if (typeof window !== "undefined") window.location.href = "/auth";
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw Object.assign(new Error(err.detail ?? "Request failed"), { status: res.status });
  }

  return res.json();
}

async function refreshAccessToken(): Promise<boolean> {
  if (!_refreshToken) return false;
  try {
    const data: AuthTokens = await apiFetch("/auth/token/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: _refreshToken }),
    }, false);
    setTokens(data);
    return true;
  } catch {
    return false;
  }
}

// ── Auth ──────────────────────────────────────────────────────────────────
export const auth = {
  totpSetup: (user_id: string, username: string) =>
    apiFetch<{ secret: string; uri: string }>("/auth/totp/setup", {
      method: "POST",
      body: JSON.stringify({ user_id, username }),
    }),

  totpVerify: (user_id: string, secret: string, code: string) =>
    apiFetch<AuthTokens>("/auth/totp/verify", {
      method: "POST",
      body: JSON.stringify({ user_id, secret, code }),
    }),

  logout: () =>
    apiFetch<{ status: string }>("/auth/logout", { method: "POST" }),

  webauthnRegisterBegin: (user_id: string, username: string) =>
    apiFetch<object>("/auth/webauthn/register/begin", {
      method: "POST",
      body: JSON.stringify({ user_id, username }),
    }),

  webauthnRegisterComplete: (user_id: string, credential: object) =>
    apiFetch<{ status: string }>("/auth/webauthn/register/complete", {
      method: "POST",
      body: JSON.stringify({ user_id, credential }),
    }),

  webauthnAuthBegin: (user_id: string) =>
    apiFetch<object>("/auth/webauthn/authenticate/begin", {
      method: "POST",
      body: JSON.stringify({ user_id }),
    }),

  webauthnAuthComplete: (user_id: string, credential: object) =>
    apiFetch<AuthTokens>("/auth/webauthn/authenticate/complete", {
      method: "POST",
      body: JSON.stringify({ user_id, credential }),
    }),
};

// ── Cognitive Systems ─────────────────────────────────────────────────────
export const cognitive = {
  listSystems: () =>
    apiFetch<{ systems: CognitiveSystem[]; count: number }>("/cognitive/systems"),

  invoke: (system_id: string, messages: Message[]) =>
    apiFetch<{ system_id: string; system_name: string; response: string }>(
      "/cognitive/invoke",
      {
        method: "POST",
        body: JSON.stringify({ system_id, messages, stream: false }),
      },
    ),

  invokeStream: (system_id: string, messages: Message[]): Promise<Response> => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
    };
    if (_accessToken) headers["Authorization"] = `Bearer ${_accessToken}`;
    return fetch(`${API_BASE}/cognitive/invoke`, {
      method: "POST",
      headers,
      body: JSON.stringify({ system_id, messages, stream: true }),
    });
  },

  getActionLog: (system_id?: string, limit = 50) =>
    apiFetch<{ entries: ActionLogEntry[]; count: number }>(
      `/cognitive/action-log?limit=${limit}${system_id ? `&system_id=${system_id}` : ""}`,
    ),

  queueOverride: (system_id: string, directive: string, reason: string) =>
    apiFetch<{ status: string; system_id: string }>("/cognitive/override", {
      method: "POST",
      body: JSON.stringify({ system_id, directive, reason }),
    }),
};

// ── Health ────────────────────────────────────────────────────────────────
export const health = {
  check: () =>
    fetch(`${API_BASE.replace("/api/v1", "")}/health`)
      .then(r => r.json()),
};

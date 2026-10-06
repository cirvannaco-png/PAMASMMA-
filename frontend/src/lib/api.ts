/**
 * PAMASMMA v4.0.1 — Typed API Client
 * In-memory access token + persisted refresh token with safe refresh rotation.
 */

import { AuthTokens, ActionLogEntry, CognitiveSystem, Message, KnowledgeSource, KnowledgeTrainingMode } from "@/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

let _accessToken: string | null = null;
let _refreshToken: string | null = null;
let _refreshPromise: Promise<AuthTokens | null> | null = null;

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

export function loadStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  _refreshToken = localStorage.getItem("pamasmma_refresh");
  return _refreshToken;
}

export async function restoreSession(): Promise<AuthTokens | null> {
  loadStoredRefreshToken();
  return refreshAccessToken();
}

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
    headers.Authorization = "Bearer " + _accessToken;
  }

  const res = await fetch(API_BASE + path, {
    ...options,
    headers,
  });

  if (res.status === 401 && retry && _refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiFetch<T>(path, options, false);
    }

    clearTokens();
    if (typeof window !== "undefined") {
      window.location.replace(new URL("/auth", window.location.origin).toString());
    }
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const err = await res
      .json()
      .catch(() => ({ detail: "Request failed" }));
    throw Object.assign(
      new Error(err.detail ?? "Request failed"),
      { status: res.status },
    );
  }

  return res.json() as Promise<T>;
}

async function multipartFetch<T>(path: string, form: FormData, retry = true): Promise<T> {
  const headers: Record<string, string> = {};
  if (_accessToken) headers.Authorization = "Bearer " + _accessToken;

  const res = await fetch(API_BASE + path, {
    method: "POST",
    headers,
    body: form,
  });

  if (res.status === 401 && retry && _refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return multipartFetch<T>(path, form, false);
    clearTokens();
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw Object.assign(new Error(err.detail ?? "Request failed"), {
      status: res.status,
    });
  }

  return res.json() as Promise<T>;
}

async function invokeStreamRequest(
  system_id: string,
  messages: Message[],
  retry = true,
): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  };

  if (_accessToken) {
    headers.Authorization = "Bearer " + _accessToken;
  }

  const response = await fetch(API_BASE + "/cognitive/invoke", {
    method: "POST",
    headers,
    body: JSON.stringify({
      system_id,
      messages,
      stream: true,
    }),
  });

  if (response.status === 401 && retry && _refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return invokeStreamRequest(system_id, messages, false);
    }
    clearTokens();
    throw new Error("Session expired");
  }

  return response;
}

async function refreshAccessToken(): Promise<AuthTokens | null> {
  if (!_refreshToken) return null;

  if (_refreshPromise) {
    return _refreshPromise;
  }

  _refreshPromise = (async () => {
    try {
      const response = await fetch(API_BASE + "/auth/token/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: _refreshToken }),
      });

      if (!response.ok) {
        clearTokens();
        return null;
      }

      const data = (await response.json()) as AuthTokens;
      setTokens(data);
      return data;
    } catch {
      clearTokens();
      return null;
    } finally {
      _refreshPromise = null;
    }
  })();

  return _refreshPromise;
}

export const auth = {
  status: (user_id: string) =>
    apiFetch<{
      setup_required: boolean;
      totp_enabled: boolean;
      webauthn_registered: boolean;
    }>(`/auth/status?user_id=${encodeURIComponent(user_id)}`),

  totpSetup: (
    user_id: string,
    username: string,
    bootstrapToken: string,
  ) =>
    apiFetch<{ secret: string; uri: string; issuer: string }>(
      "/auth/totp/setup",
      {
        method: "POST",
        headers: { "X-Bootstrap-Token": bootstrapToken },
        body: JSON.stringify({ user_id, username }),
      },
    ),

  totpVerify: (user_id: string, code: string) =>
    apiFetch<AuthTokens>("/auth/totp/verify", {
      method: "POST",
      body: JSON.stringify({ user_id, code }),
    }),

  logout: () =>
    apiFetch<{ status: string }>("/auth/logout", { method: "POST" }),

  webauthnRegisterBegin: () =>
    apiFetch<object>("/auth/webauthn/register/begin", { method: "POST" }),

  webauthnRegisterComplete: (credential: object) =>
    apiFetch<{ status: string }>("/auth/webauthn/register/complete", {
      method: "POST",
      body: JSON.stringify({ credential }),
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

export const cognitive = {
  listSystems: () =>
    apiFetch<{ systems: CognitiveSystem[]; count: number }>(
      "/cognitive/systems",
    ),

  invoke: (system_id: string, messages: Message[]) =>
    apiFetch<{
      system_id: string;
      system_name: string;
      response: string;
    }>("/cognitive/invoke", {
      method: "POST",
      body: JSON.stringify({ system_id, messages, stream: false }),
    }),

  invokeStream: (
    system_id: string,
    messages: Message[],
  ): Promise<Response> => invokeStreamRequest(system_id, messages),

  getActionLog: (system_id?: string, limit = 50) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (system_id) params.set("system_id", system_id);

    return apiFetch<{
      entries: ActionLogEntry[];
      count: number;
    }>("/cognitive/action-log?" + params.toString());
  },

  queueOverride: (
    system_id: string,
    directive: string,
    reason: string,
  ) =>
    apiFetch<{ status: string; system_id: string }>("/cognitive/override", {
      method: "POST",
      body: JSON.stringify({ system_id, directive, reason }),
    }),
};

  knowledge: {
    list: () =>
      apiFetch<{ sources: KnowledgeSource[]; count: number }>("/knowledge"),

    upload: (input: {
      file: File;
      title?: string;
      training_mode: KnowledgeTrainingMode;
      scope_system_id?: string;
      transcript?: string;
    }) => {
      const form = new FormData();
      form.append("file", input.file);
      if (input.title) form.append("title", input.title);
      form.append("training_mode", input.training_mode);
      if (input.scope_system_id) {
        form.append("scope_system_id", input.scope_system_id);
      }
      if (input.transcript) form.append("transcript", input.transcript);

      return multipartFetch<{ status: string; source: KnowledgeSource }>(
        "/knowledge/upload",
        form,
      );
    },

    remove: (source_id: string) =>
      apiFetch<{ status: string; source_id: string }>(
        "/knowledge/" + encodeURIComponent(source_id),
        { method: "DELETE" },
      ),
  },

export const health = {
  check: () =>
    fetch(API_BASE.replace("/api/v1", "") + "/health").then((res) =>
      res.json(),
    ),
};

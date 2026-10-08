/**
 * PAMASMMA v4.0.1 — Typed API Client
 * In-memory access token + persisted refresh token with safe refresh rotation.
 */

import { AuthTokens, ActionLogEntry, CognitiveSystem, Message } from "@/types";

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

export interface KnowledgeSource {
  id: string;
  filename: string;
  media_type?: string;
  status: string;
  content_hash?: string;
  size_bytes?: number;
  chunk_count?: number;
  training_mode: "knowledge" | "procedure";
  metadata?: Record<string, unknown> | string | null;
  error?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface KnowledgeChunk {
  ordinal: number;
  locator: string | null;
  content: string;
  metadata?: Record<string, unknown> | string | null;
}

export const knowledge = {
  listSources: (limit = 100) =>
    apiFetch<{ sources: KnowledgeSource[]; count: number }>(
      `/knowledge/sources?limit=${limit}`,
    ),

  listChunks: (sourceId: string, limit = 100) =>
    apiFetch<{ chunks: KnowledgeChunk[]; count: number; source_id: string }>(
      `/knowledge/sources/${encodeURIComponent(sourceId)}/chunks?limit=${limit}`,
    ),

  upload: async (
    file: File,
    trainingMode: "knowledge" | "procedure" = "knowledge",
    retry = true,
  ): Promise<{
    source_id: string;
    status: string;
    filename: string;
    chunks: number;
    mode: "knowledge" | "procedure";
    content_hash: string;
    deduplicated: boolean;
  }> => {
    const form = new FormData();
    form.append("file", file);

    const headers: Record<string, string> = {};
    if (_accessToken) headers.Authorization = "Bearer " + _accessToken;

    const response = await fetch(
      API_BASE +
        `/knowledge/upload?training_mode=${encodeURIComponent(trainingMode)}`,
      {
        method: "POST",
        headers,
        body: form,
      },
    );

    if (response.status === 401 && retry && _refreshToken) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        return knowledge.upload(file, trainingMode, false);
      }
      clearTokens();
      throw new Error("Session expired");
    }

    if (!response.ok) {
      const err = await response
        .json()
        .catch(() => ({ detail: "Upload failed" }));
      throw Object.assign(
        new Error(err.detail ?? "Upload failed"),
        { status: response.status },
      );
    }

    return response.json() as Promise<{
      source_id: string;
      status: string;
      filename: string;
      chunks: number;
      mode: "knowledge" | "procedure";
      content_hash: string;
      deduplicated: boolean;
    }>;
  },

  remove: (sourceId: string) =>
    apiFetch<{ status: string; source_id: string }>(
      `/knowledge/sources/${encodeURIComponent(sourceId)}`,
      { method: "DELETE" },
    ),
};

export const health = {
  check: () =>
    fetch(API_BASE.replace("/api/v1", "") + "/health").then((res) =>
      res.json(),
    ),
};

export const social = {
  platforms: () => apiFetch<{platforms: {platform:string; capabilities:string[]}[]}>("/social/platforms"),
  oauthStart: (platform: string, externalAccountId?: string) =>
    apiFetch<{ platform: string; authorization_url: string; state: string }>(
      "/social/oauth/" +
        encodeURIComponent(platform) +
        "/start" +
        (externalAccountId
          ? "?external_account_id=" + encodeURIComponent(externalAccountId)
          : ""),
    ),
  oauthPending: (pendingId: string) =>
    apiFetch<{
      pending_id: string;
      platform: string;
      accounts: Array<{
        external_account_id: string;
        display_name?: string | null;
      }>;
    }>(
      "/social/oauth/pending/" + encodeURIComponent(pendingId),
    ),
  oauthComplete: (pendingId: string, externalAccountId: string) =>
    apiFetch<{ status: string; account: Record<string, unknown> }>(
      "/social/oauth/pending/" +
        encodeURIComponent(pendingId) +
        "/complete",
      {
        method: "POST",
        body: JSON.stringify({ external_account_id: externalAccountId }),
      },
    ),
  accounts: () => apiFetch<{accounts: Array<{id:string;platform:string;external_account_id:string;display_name?:string|null;status:string;capabilities:string[]}>;count:number}>("/social/accounts"),
  manualAccount: (body:{platform:string;access_token:string;refresh_token?:string;external_account_id:string;display_name?:string;scopes?:string[];metadata?:Record<string,unknown>}) => apiFetch<{account:Record<string,unknown>}>("/social/accounts/manual", {method:"POST",body:JSON.stringify(body)}),
  disconnect: (accountId:string) => apiFetch<{status:string;account_id:string}>("/social/accounts/" + encodeURIComponent(accountId), {method:"DELETE"}),
  publish: (body:{command:any;scheduled_at?:string}) => apiFetch<{status:string;post_id:string;platform_post_id?:string|null}>("/social/publish", {method:"POST",body:JSON.stringify(body)}),
  engagement: () => apiFetch<{items:Array<Record<string,unknown>>;count:number}>("/social/engagement"),
  analytics: (accountId: string, start?: string, end?: string) => {
    const params = new URLSearchParams();
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    const query = params.toString();
    return apiFetch<Record<string, unknown>>(
      `/social/analytics/${encodeURIComponent(accountId)}${query ? `?${query}` : ""}`,
    );
  },
  sync: (accountId:string) => apiFetch<{count:number;items:any[]}>("/social/engagement/sync/" + encodeURIComponent(accountId), {method:"POST"}),
  reply: (body:{account_id:string;item_id:string;text:string}) => apiFetch<{status:string}>("/social/engagement/reply", {method:"POST",body:JSON.stringify(body)}),
  planCampaign: (body:any) => apiFetch<{campaign_id:string;status:string;approval_required:boolean}>("/social/campaigns", {method:"POST",body:JSON.stringify(body)}),
  approveCampaign: (campaignId:string) => apiFetch<{status:string;campaign_id:string;external_campaign_id?:string|null}>("/social/campaigns/" + encodeURIComponent(campaignId) + "/approve", {method:"POST"}),
};


export const integrations = {
  googleStart: () => apiFetch<{ authorization_url: string; state: string }>("/integrations/google/start"),
  list: () => apiFetch<{ integrations: Array<Record<string, unknown>>; mcp: Array<Record<string, unknown>> }>("/integrations"),
  mcpRecommended: (role?: string, priority?: "core" | "optional") => {
    const params = new URLSearchParams();
    if (role) params.set("role", role);
    if (priority) params.set("priority", priority);
    const query = params.toString();
    return apiFetch<{ connections: Array<Record<string, unknown>> }>(
      "/integrations/mcp/recommended" + (query ? "?" + query : ""),
    );
  },
  gmailMessages: (accountId: string, q?: string) => apiFetch<Record<string, unknown>>(`/integrations/google/${encodeURIComponent(accountId)}/gmail/messages${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  gmailSend: (accountId: string, body: { to: string[]; subject: string; body: string; cc?: string[]; bcc?: string[] }) => apiFetch<Record<string, unknown>>(`/integrations/google/${encodeURIComponent(accountId)}/gmail/send`, { method: "POST", body: JSON.stringify(body) }),
  driveFiles: (accountId: string, q?: string) => apiFetch<Record<string, unknown>>(`/integrations/google/${encodeURIComponent(accountId)}/drive/files${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  driveUpload: (accountId: string, body: { name: string; mime_type: string; content_base64: string; parent_id?: string }) => apiFetch<Record<string, unknown>>(`/integrations/google/${encodeURIComponent(accountId)}/drive/upload`, { method: "POST", body: JSON.stringify(body) }),
  mcpAdd: (body: { name: string; endpoint: string; bearer_token?: string; enabled?: boolean }) => apiFetch<Record<string, unknown>>("/integrations/mcp", { method: "POST", body: JSON.stringify(body) }),
  mcpTools: (connectorId: string) => apiFetch<{ tools: Array<Record<string, unknown>> }>(`/integrations/mcp/${encodeURIComponent(connectorId)}/tools`),
};


export const mcp = {
  registrySearch: (q: string, limit = 20) =>
    apiFetch<{ servers: Array<Record<string, unknown>> }>(`/integrations/mcp/registry/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  call: (connectorId: string, toolName: string, arguments_: Record<string, unknown>, confirmed = false) =>
    apiFetch<Record<string, unknown>>(`/integrations/mcp/${encodeURIComponent(connectorId)}/call`, {
      method: "POST",
      body: JSON.stringify({ tool_name: toolName, arguments: arguments_, confirmed }),
    }),
};

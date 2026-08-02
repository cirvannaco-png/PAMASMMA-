// PAMASMMA v4 — TypeScript Types

export type SystemId = "S1" | "S2" | "S3" | "S4" | "S5" | "S6" | "S7" | "S8" | "S9" | "S10";

export interface CognitiveSystem {
  id: SystemId;
  name: string;
  color: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

export interface PersonalityBaseline {
  assertiveness: number;
  verbosity: number;
  formality: number;
  strategicDepth: number;
}

export interface ActionLogEntry {
  id: string;
  system_id: SystemId;
  system_name: string;
  query_preview: string;
  latency_ms: number;
  created_at: string;
}

export interface OverrideEntry {
  id: string;
  system_id: SystemId;
  directive: string;
  reason: string;
  status: "pending" | "applied" | "rejected";
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiError {
  detail: string;
  status: number;
}

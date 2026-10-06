// PAMASMMA v4.2 — TypeScript Types

export type SystemId =
  | "S1"
  | "S2"
  | "S3"
  | "S4"
  | "S5"
  | "S6"
  | "S7"
  | "S8"
  | "S9"
  | "S10";

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

export type KnowledgeTrainingMode =
  | "reference"
  | "behavioral"
  | "domain_playbook";

export type KnowledgeSourceStatus =
  | "processing"
  | "ready"
  | "awaiting_transcription"
  | "failed";

export interface KnowledgeSource {
  id: string;
  title: string;
  filename: string;
  media_type: string;
  training_mode: KnowledgeTrainingMode;
  status: KnowledgeSourceStatus;
  extraction_method: string;
  size_bytes: number;
  content_hash: string;
  scope_system_id: SystemId | null;
  language: string | null;
  chunk_count: number;
  error: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PersonalityBaseline {
  assertiveness: number;
  verbosity: number;
  formality: number;
  strategicDepth: number;
}

export interface VerificationIssue {
  severity: "low" | "medium" | "high";
  category: string;
  message: string;
}

export interface VerificationReport {
  score: number;
  issues: VerificationIssue[];
  requires_revision: boolean;
  evidence_status: string;
  confidence_adjustment: number;
}

export interface CognitiveTrace {
  intent: string;
  complexity: string;
  sensitivity: string;
  memory_count: number;
  knowledge_count: number;
  contradiction_count: number;
  routed_systems: SystemId[];
  provider: string;
  verification: VerificationReport;
  decision_id: string | null;
  confidence: number;
  uncertainty: string[];
  evidence_status: string;
}

export interface DecisionRecord {
  id: string;
  user_id: string;
  primary_system_id: SystemId;
  objective: string;
  context: Record<string, unknown>;
  constraints: string[];
  evidence: Array<Record<string, unknown>>;
  memories: string[];
  options: string[];
  assumptions: string[];
  risks: string[];
  confidence: number;
  certainty_band: string;
  selected_action: string;
  alternatives_rejected: string[];
  owner: string;
  expected_outcome: string;
  deadline?: string | null;
  horizon_checks: Record<string, string>;
  status: string;
}

export interface CognitiveMetadataEvent {
  type: "cognition";
  cognition: CognitiveTrace;
  decision: DecisionRecord;
}

export interface ActionLogEntry {
  id: string;
  system_id: SystemId;
  system_name: string;
  query_preview: string;
  latency_ms: number;
  decision_id?: string | null;
  confidence?: number | null;
  provider?: string | null;
  verification_score?: number | null;
  evidence_status?: string | null;
  routed_systems?: SystemId[];
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

import { BaseEvent } from './interfaces';

export interface TaskCreatedEvent extends BaseEvent {
  type: 'task.created';
  task_type: 'content' | 'marketing' | 'social' | 'email';
  input: Record<string, unknown>;
}

export interface TaskProcessedEvent extends BaseEvent {
  type: 'task.processed';
  agent: string;
  output: Record<string, unknown>;
  confidence_score: number;
}

export interface TaskApprovedEvent extends BaseEvent {
  type: 'task.approved';
  approved_by: string;
  risk_score: number;
}

export interface AgentContentGeneratedEvent extends BaseEvent {
  type: 'agent.content.generated';
  agent: string;
  content: { caption: string; hashtags: string[] };
}

export interface ToolEmailExecutedEvent extends BaseEvent {
  type: 'tool.email.executed';
  tool: string;
  status: 'success' | 'failed';
  response: Record<string, unknown>;
}

export interface ToolMCPCalledEvent extends BaseEvent {
  type: 'tool.mcp.called';
  mcp_server: string;
  tool_name: string;
  input_hash: string;
  status: 'success' | 'rejected' | 'failed';
  mali_verdict: string;
  latency_ms: number;
  trace_id: string;
}

export interface MaliRiskAssessedEvent extends BaseEvent {
  type: 'mali.risk.assessed';
  risk_score: number;
  failure_modes: string[];
  recommendation: 'approve' | 'reject' | 'revise';
}

export interface MemoryUpdatedEvent extends BaseEvent {
  type: 'memory.updated';
  store_type: 'episodic' | 'semantic';
  operation: 'write' | 'update';
}

export interface AgentDriftDetectedEvent extends BaseEvent {
  type: 'agent.drift.detected';
  agent_id: string;
  drift_score: number;
}

export type SystemEvent =
  | TaskCreatedEvent
  | TaskProcessedEvent
  | TaskApprovedEvent
  | AgentContentGeneratedEvent
  | ToolEmailExecutedEvent
  | ToolMCPCalledEvent
  | MaliRiskAssessedEvent
  | MemoryUpdatedEvent
  | AgentDriftDetectedEvent;
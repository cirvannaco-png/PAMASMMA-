export interface BaseEvent {type: string; schema_version: number; timestamp: string; tenant_id: string; task_id: string;}
export interface TaskCreatedEvent extends BaseEvent {type: 'task.created'; task_type: 'content' | 'marketing' | 'social' | 'email'; input: Record<string, unknown>;}
export interface TaskProcessedEvent extends BaseEvent {type: 'task.processed'; agent: string; output: Record<string, unknown>; confidence_score: number;}
export interface ToolMCPCalledEvent extends BaseEvent {type: 'tool.mcp.called'; mcp_server: string; tool_name: string; input_hash: string; status: 'success' | 'rejected' | 'failed'; mali_verdict: string; latency_ms: number; trace_id: string;}
export interface AgentDriftDetectedEvent extends BaseEvent {type: 'agent.drift.detected'; agent_id: string; drift_score: number;}
export type SystemEvent = TaskCreatedEvent | TaskProcessedEvent | ToolMCPCalledEvent | AgentDriftDetectedEvent;
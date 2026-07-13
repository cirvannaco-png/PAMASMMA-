import Ajv, { ValidateFunction } from 'ajv';
import { SystemEvent } from './events';

const ajv = new Ajv();

// Define schemas for every event type
const baseRequired = ['type', 'schema_version', 'timestamp', 'tenant_id', 'task_id'];

const taskCreatedSchema = {
  type: 'object',
  required: [...baseRequired, 'task_type', 'input'],
};
const taskProcessedSchema = { type: 'object', required: [...baseRequired, 'agent', 'output', 'confidence_score'] };
const taskApprovedSchema = { type: 'object', required: [...baseRequired, 'approved_by', 'risk_score'] };
const agentContentGeneratedSchema = { type: 'object', required: [...baseRequired, 'agent', 'content'] };
const toolEmailExecutedSchema = { type: 'object', required: [...baseRequired, 'tool', 'status', 'response'] };
const toolMCPCalledSchema = { type: 'object', required: [...baseRequired, 'mcp_server', 'tool_name', 'input_hash', 'status', 'mali_verdict', 'latency_ms', 'trace_id'] };
const maliRiskAssessedSchema = { type: 'object', required: [...baseRequired, 'risk_score', 'failure_modes', 'recommendation'] };
const memoryUpdatedSchema = { type: 'object', required: [...baseRequired, 'store_type', 'operation'] };
const agentDriftDetectedSchema = { type: 'object', required: [...baseRequired, 'agent_id', 'drift_score'] };

const validators: Record<string, ValidateFunction> = {
  'task.created': ajv.compile(taskCreatedSchema),
  'task.processed': ajv.compile(taskProcessedSchema),
  'task.approved': ajv.compile(taskApprovedSchema),
  'agent.content.generated': ajv.compile(agentContentGeneratedSchema),
  'tool.email.executed': ajv.compile(toolEmailExecutedSchema),
  'tool.mcp.called': ajv.compile(toolMCPCalledSchema),
  'mali.risk.assessed': ajv.compile(maliRiskAssessedSchema),
  'memory.updated': ajv.compile(memoryUpdatedSchema),
  'agent.drift.detected': ajv.compile(agentDriftDetectedSchema),
};

export function validateEvent(event: SystemEvent): boolean {
  // Extract type before passing event to the AJV validator. AJV's ValidateFunction
  // is typed as a type-guard (data is T) so TypeScript narrows `event` to `never`
  // in the false branch if we access it after the validator call.
  const eventType = event.type;
  const validator = validators[eventType];
  if (!validator) {
    console.error(`No validator for event type: ${eventType}`);
    return false;
  }
  // Cast to unknown: AJV operates on arbitrary JSON; type safety is enforced
  // by the JSON schema, not by TypeScript's structural narrowing.
  const valid = validator(event as unknown);
  if (!valid) {
    console.error(`Event validation failed for ${eventType}:`, validator.errors);
  }
  return valid;
}

import { validateEvent } from '../src/schemaValidator';

describe('validateEvent', () => {
  const base = {
    schema_version: 1,
    timestamp: new Date().toISOString(),
    tenant_id: 't1',
    task_id: 'task-1',
  } as const;

  it('accepts a well-formed task.created event', () => {
    const ok = validateEvent({
      ...base,
      type: 'task.created',
      task_type: 'analysis',
      input: { prompt: 'hello' },
    } as any);
    expect(ok).toBe(true);
  });

  it('rejects a task.created event missing required fields', () => {
    const ok = validateEvent({
      ...base,
      type: 'task.created',
    } as any);
    expect(ok).toBe(false);
  });

  it('rejects an unknown event type', () => {
    const ok = validateEvent({
      ...base,
      type: 'not.a.real.event',
    } as any);
    expect(ok).toBe(false);
  });

  it('accepts a well-formed tool.mcp.called event', () => {
    const ok = validateEvent({
      ...base,
      type: 'tool.mcp.called',
      mcp_server: 'srv',
      tool_name: 'send_email',
      input_hash: 'abc',
      status: 'success',
      mali_verdict: 'approved',
      latency_ms: 12,
      trace_id: 'trace-1',
    } as any);
    expect(ok).toBe(true);
  });
});

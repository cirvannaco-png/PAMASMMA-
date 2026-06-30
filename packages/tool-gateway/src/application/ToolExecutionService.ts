import { ToolRegistry } from '../domain/ToolRegistry';
import { InjectionDetector } from '../domain/InjectionDetector';
import { IMaliService, IMCPClient, IEventBus, AppError, ok, fail, Result } from '@pamasmma/shared';

export class ToolExecutionService {
  constructor(
    private registry: ToolRegistry,
    private injectionDetector: InjectionDetector,
    private maliService: IMaliService,   // interface
    private mcpClient: IMCPClient,       // interface
    private eventBus: IEventBus
  ) {}

  async execute(
    toolName: string,
    inputs: unknown,
    context: { tenant_id: string; task_id: string; trace_id: string }
  ): Promise<Result<unknown>> {
    const tool = this.registry.getTool(toolName);
    if (!tool) return fail(new AppError('Tool not found', 'TOOL_NOT_FOUND', 404));

    if (this.injectionDetector.scan(JSON.stringify(inputs))) {
      await this.eventBus.emit({
        type: 'tool.mcp.called',
        schema_version: 1,
        timestamp: new Date().toISOString(),
        tenant_id: context.tenant_id,
        task_id: context.task_id,
        mcp_server: tool.server,
        tool_name: tool.toolName,
        input_hash: '...',
        status: 'rejected',
        mali_verdict: 'injection_blocked',
        latency_ms: 0,
        trace_id: context.trace_id,
      });
      return fail(new AppError('Injection detected', 'INJECTION_BLOCKED', 400));
    }

    if (tool.maliRequired) {
      const verdict = await this.maliService.evaluate(context.task_id, inputs);
      if (verdict === 'reject') {
        return fail(new AppError('Mali rejected execution', 'MALI_REJECTED', 403));
      }
    }

    try {
      const start = Date.now();
      const result = await this.mcpClient.call(tool.server, tool.toolName, inputs);
      const latency = Date.now() - start;
      
      await this.eventBus.emit({
        type: 'tool.mcp.called',
        schema_version: 1,
        timestamp: new Date().toISOString(),
        tenant_id: context.tenant_id,
        task_id: context.task_id,
        mcp_server: tool.server,
        tool_name: tool.toolName,
        input_hash: JSON.stringify(inputs),
        status: 'success',
        mali_verdict: 'approved',
        latency_ms: latency,
        trace_id: context.trace_id,
      });
      return ok(result);
    } catch (err: any) {
      return fail(new AppError(err.message, 'MCP_CALL_FAILED', 502));
    }
  }
}

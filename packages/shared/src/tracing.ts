import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { trace, context, Span } from '@opentelemetry/api';

// Use the stable string constant directly — SemanticResourceAttributes was
// removed in @opentelemetry/semantic-conventions ≥ 1.0 stable API.
const SERVICE_NAME_ATTR = 'service.name';

let sdk: NodeSDK;

export function initTracing(serviceName: string): void {
  sdk = new NodeSDK({
    resource: new Resource({
      [SERVICE_NAME_ATTR]: serviceName,
    }),
    traceExporter: new OTLPTraceExporter(),
  });
  sdk.start();
}

export function getTracer() {
  return trace.getTracer('pamasmma');
}

export function withTraceContext(
  tenantId: string,
  taskId: string,
  fn: (span: Span) => void
): void {
  const span = getTracer().startSpan('operation');
  span.setAttribute('tenant_id', tenantId);
  span.setAttribute('task_id', taskId);
  context.with(trace.setSpan(context.active(), span), () => fn(span));
  span.end();
}

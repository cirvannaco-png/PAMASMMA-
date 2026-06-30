import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';
import { trace, context, Span } from '@opentelemetry/api';

let sdk: NodeSDK;

export function initTracing(serviceName: string) {
  sdk = new NodeSDK({
    resource: new Resource({
      [SemanticResourceAttributes.SERVICE_NAME]: serviceName,
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
) {
  const span = getTracer().startSpan('operation');
  span.setAttribute('tenant_id', tenantId);
  span.setAttribute('task_id', taskId);
  context.with(trace.setSpan(context.active(), span), () => fn(span));
  span.end();
}
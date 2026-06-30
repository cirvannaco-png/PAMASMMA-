# Deployment Guide

## Prerequisites
- Kubernetes 1.24+
- Docker
- kubectl configured
- Environment secrets configured

## Quick Deploy

```bash
kubectl apply -f infra/kubernetes/namespace.yaml
kubectl apply -f infra/kubernetes/configmap.yaml
kubectl apply -f infra/kubernetes/secrets.yaml
kubectl apply -f infra/kubernetes/
```

## Services

- **Orchestrator**: Port 3000
- **Content Agent**: Port 3002
- **Mali Engine**: Port 3003
- **Personality Engine**: Port 3004
- **Marketing Intel**: Port 3005
- **Tool Gateway**: Port 3001
- **Relationship Graph**: Port 3006

## Observability

- OpenTelemetry traces: `http://localhost:4317` (OTLP gRPC)
- Prometheus metrics: `http://localhost:9090`
- Grafana dashboards: `http://localhost:3000`

## Scaling

```bash
kubectl scale deployment orchestrator --replicas=3
```

## Monitoring

Grafana dashboards:
- System Health (`grafana-dashboards/system-health.json`)
- Agent Behavior (`grafana-dashboards/agent-behavior.json`)
- Mali Threats (`grafana-dashboards/mali-threat.json`)
- Business Intelligence (`grafana-dashboards/business-intelligence.json`)

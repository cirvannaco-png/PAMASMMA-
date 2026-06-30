# PAMASMMA v2.1 Deployment Guide

## Phase 1: Local Development Setup

### 1.1 Prerequisites
- Node.js 18+ (LTS)
- npm 9+
- Docker & Docker Compose
- kubectl 1.28+
- git

### 1.2 Clone & Install
```bash
git clone https://github.com/cirvannaco-png/PAMASMMA-.git
cd PAMASMMA-
npm install
```

### 1.3 Build All Packages
```bash
npm run build
```

Output should show:
```
@pamasmma/shared: tsc [✓]
@pamasmma/memory-core: tsc [✓]
@pamasmma/orchestrator: tsc [✓]
@pamasmma/content-agent: tsc [✓]
@pamasmma/tool-gateway: tsc [✓]
@pamasmma/mali-engine: tsc [✓]
@pamasmma/personality-engine: tsc [✓]
@pamasmma/marketing-intel: tsc [✓]
@pamasmma/self-healing: tsc [✓]
@pamasmma/relationship-graph: tsc [✓]
```

### 1.4 Run Tests
```bash
npm test
```

Expected: All tests pass across all packages.

---

## Phase 2: Local Docker Deployment

### 2.1 Create docker-compose.yml
```yaml
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    ports:
      - "2181:2181"

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  otel-collector:
    image: otel/opentelemetry-collector:latest
    ports:
      - "4317:4317"
      - "4318:4318"
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    command: ["--config=/etc/otel-collector-config.yaml"]

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - ./grafana-dashboards:/etc/grafana/provisioning/dashboards

  orchestrator:
    build: ./packages/orchestrator
    ports:
      - "3001:3000"
    environment:
      KAFKA_BROKERS: kafka:29092
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4318
    depends_on:
      - kafka
      - otel-collector
```

### 2.2 Start Local Stack
```bash
docker-compose up -d
```

### 2.3 Verify Services
```bash
# Check Kafka
docker-compose exec kafka kafka-topics --list --bootstrap-server kafka:9092

# Check Prometheus
curl http://localhost:9090/api/v1/status/config

# Check Grafana
curl http://localhost:3000
```

---

## Phase 3: Kubernetes Deployment

### 3.1 Prerequisites
- Kubernetes cluster (1.28+)
- kubectl configured
- Docker registry access

### 3.2 Build Docker Images
```bash
# Build orchestrator
docker build -t pamasmma/orchestrator:v2.1.0 ./packages/orchestrator

# Build content-agent
docker build -t pamasmma/content-agent:v2.1.0 ./packages/content-agent

# Build tool-gateway
docker build -t pamasmma/tool-gateway:v2.1.0 ./packages/tool-gateway

# Build mali-engine
docker build -t pamasmma/mali-engine:v2.1.0 ./packages/mali-engine

# Push to registry
docker push pamasmma/orchestrator:v2.1.0
docker push pamasmma/content-agent:v2.1.0
docker push pamasmma/tool-gateway:v2.1.0
docker push pamasmma/mali-engine:v2.1.0
```

### 3.3 Create Kubernetes Namespace
```bash
kubectl apply -f infra/kubernetes/namespace.yaml
```

### 3.4 Add ConfigMaps & Secrets
```bash
# Create secrets
kubectl apply -f infra/kubernetes/secrets.yaml

# Create config
kubectl apply -f infra/kubernetes/configmap.yaml
```

### 3.5 Deploy Orchestrator
```bash
kubectl apply -f infra/kubernetes/orchestrator-deployment.yaml
kubectl apply -f infra/kubernetes/services.yaml
```

### 3.6 Verify Deployment
```bash
# Check namespace
kubectl get ns | grep pamasmma

# Check deployments
kubectl get deployments -n pamasmma

# Check pods
kubectl get pods -n pamasmma

# Check services
kubectl get svc -n pamasmma

# View logs
kubectl logs -n pamasmma deployment/orchestrator -f
```

---

## Phase 4: Observability Setup

### 4.1 Configure Prometheus
Create `prometheus.yml`:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'pamasmma'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - pamasmma
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
```

### 4.2 Deploy OpenTelemetry Collector
```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
  namespace: pamasmma
data:
  config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
          http:
            endpoint: 0.0.0.0:4318
    processors:
      batch:
        timeout: 10s
        send_batch_size: 1024
    exporters:
      jaeger:
        endpoint: jaeger-collector:14250
      prometheus:
        endpoint: 0.0.0.0:8888
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [batch]
          exporters: [jaeger]
        metrics:
          receivers: [otlp]
          processors: [batch]
          exporters: [prometheus]
EOF
```

### 4.3 Deploy Grafana Dashboards
```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards
  namespace: pamasmma
data:
  system-health.json: |
$(cat grafana-dashboards/system-health.json | sed 's/^/    /')
  agent-behavior.json: |
$(cat grafana-dashboards/agent-behavior.json | sed 's/^/    /')
  mali-threat.json: |
$(cat grafana-dashboards/mali-threat.json | sed 's/^/    /')
EOF
```

---

## Phase 5: Testing & Validation

### 5.1 Unit Tests
```bash
npm test -- --coverage
```

### 5.2 Integration Tests
```bash
npm test -- packages/orchestrator/__tests__/routes.test.ts
```

### 5.3 Load Testing
```bash
# Using k6 or similar
k6 run load-test.js
```

### 5.4 Health Checks
```bash
# Orchestrator health
curl http://localhost:3001/health

# Prometheus metrics
curl http://localhost:9090/api/v1/targets

# Grafana dashboards
curl http://localhost:3000/api/dashboards
```

---

## Phase 6: Production Hardening

### 6.1 Enable Authentication
```yaml
# Add to secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: pamasmma-auth
  namespace: pamasmma
type: Opaque
stringData:
  jwt-secret: "your-secret-key"
  api-key: "your-api-key"
```

### 6.2 Enable TLS
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: tls-secret
  namespace: pamasmma
type: kubernetes.io/tls
data:
  tls.crt: base64-encoded-cert
  tls.key: base64-encoded-key
```

### 6.3 Resource Limits
```yaml
resources:
  limits:
    memory: "512Mi"
    cpu: "500m"
  requests:
    memory: "256Mi"
    cpu: "250m"
```

### 6.4 Pod Disruption Budget
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: orchestrator-pdb
  namespace: pamasmma
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: orchestrator
```

### 6.5 Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: pamasmma-network-policy
  namespace: pamasmma
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: api
  egress:
  - to:
    - podSelector:
        matchLabels:
          role: database
```

---

## Phase 7: Monitoring & Alerts

### 7.1 Create Prometheus Rules
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-rules
  namespace: pamasmma
data:
  alerts.yml: |
    groups:
    - name: pamasmma
      rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
```

### 7.2 Alert Configuration
```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  group_by: ['alertname', 'cluster']
  routes:
  - match:
      severity: critical
    receiver: 'pagerduty'
    
receivers:
- name: 'default'
  slack_configs:
  - api_url: 'your-slack-webhook'
    channel: '#pamasmma-alerts'
```

---

## Phase 8: Continuous Integration/Deployment

### 8.1 GitHub Actions Workflow
Create `.github/workflows/ci-cd.yml`:
```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-node@v3
      with:
        node-version: '18'
    - run: npm install
    - run: npm run build
    - run: npm test

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build and push Docker images
      run: |
        docker build -t pamasmma/orchestrator:${{ github.sha }} ./packages/orchestrator
        docker push pamasmma/orchestrator:${{ github.sha }}
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/orchestrator orchestrator=pamasmma/orchestrator:${{ github.sha }} -n pamasmma
```

---

## Phase 9: Scaling & Performance Tuning

### 9.1 Horizontal Pod Autoscaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orchestrator-hpa
  namespace: pamasmma
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orchestrator
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 9.2 Vertical Pod Autoscaling
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: orchestrator-vpa
  namespace: pamasmma
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orchestrator
  updatePolicy:
    updateMode: "Auto"
```

---

## Phase 10: Disaster Recovery & Backup

### 10.1 Persistent Volume Setup
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pamasmma-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  storageClassName: fast
  nfs:
    server: nfs-server.example.com
    path: /pamasmma
```

### 10.2 Backup Strategy
```bash
# Backup namespace
kubectl get all -n pamasmma -o yaml > pamasmma-backup.yaml

# Backup secrets
kubectl get secrets -n pamasmma -o yaml > pamasmma-secrets-backup.yaml

# Restore
kubectl apply -f pamasmma-backup.yaml
```

### 10.3 Velero Setup for Disaster Recovery
```bash
velero install \
  --provider aws \
  --bucket pamasmma-backups \
  --secret-file ./credentials-velero
```

---

## Troubleshooting

### Issue: Pods not starting
```bash
kubectl describe pod -n pamasmma <pod-name>
kubectl logs -n pamasmma <pod-name>
```

### Issue: Service not accessible
```bash
kubectl port-forward -n pamasmma svc/orchestrator-service 3001:80
```

### Issue: Memory leaks
```bash
kubectl top pods -n pamasmma
kubectl top nodes
```

### Issue: Connection to Kafka failing
```bash
kubectl exec -it -n pamasmma deployment/orchestrator -- bash
nc -zv kafka.pamasmma.svc.cluster.local 9092
```

---

## Success Criteria

- ✅ All 10 packages build successfully
- ✅ All unit tests pass (>80% coverage)
- ✅ Docker images build and run
- ✅ Kubernetes pods are healthy and running
- ✅ Services are accessible via LoadBalancer
- ✅ Metrics flowing to Prometheus
- ✅ Grafana dashboards rendering
- ✅ Event bus operational (Kafka)
- ✅ Memory access working (episodic/semantic)
- ✅ Mali adversarial simulation active

---

## Support & Documentation

- **Slack**: #pamasmma-dev
- **Docs**: https://pamasmma.dev
- **Issues**: https://github.com/cirvannaco-png/PAMASMMA-/issues
- **PR Reviews**: https://github.com/cirvannaco-png/PAMASMMA-/pulls

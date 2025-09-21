# MemoryOS Deployments

This directory contains deployment configurations for MemoryOS across different environments and platforms.

## Structure

```
deployments/
├── kubernetes/          # Kubernetes manifests
│   ├── base/           # Base configurations
│   ├── overlays/       # Environment-specific overlays
│   └── monitoring/     # ServiceMonitors, Services
├── monitoring/         # Monitoring stack configurations
│   ├── grafana/        # Grafana dashboards and config
│   ├── prometheus/     # Prometheus rules and config
│   └── alerts/         # Alert manager configurations
├── docker/            # Docker and Docker Compose
├── local/             # Local development setup
└── docs/              # Deployment documentation

## Quick Start

### Local Development
```bash
# Start local observability stack
cd local
docker-compose up -d

# Verify metrics endpoint
curl http://localhost:8080/v1/metrics
```

### Kubernetes Development
```bash
# Create namespaces
kubectl create namespace memoryos
kubectl create namespace monitoring

# Deploy monitoring stack
kubectl apply -k kubernetes/base/
```

### Production
See individual environment documentation in `docs/`.

## Observability Integration

The monitoring stack is designed to work with MemoryOS's built-in observability module:

- **Metrics**: Prometheus scrapes `/v1/metrics` endpoint
- **Logs**: JSON structured logs with correlation IDs
- **Traces**: OpenTelemetry spans exported to configured backends
- **Dashboards**: Pre-built Grafana dashboards for all components

## Environment Variables

Key configuration variables for observability:

```bash
# Metrics
PROMETHEUS_URL=http://prometheus:9090
METRICS_ENABLED=true
METRICS_PORT=8081

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_CORRELATION_ENABLED=true

# Tracing
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:14268/api/traces
TRACING_ENABLED=true
TRACING_SAMPLE_RATE=0.1
```

## Support

For deployment issues, check:
1. `docs/troubleshooting.md`
2. Component-specific READMEs
3. GitHub Issues with `deployment` label

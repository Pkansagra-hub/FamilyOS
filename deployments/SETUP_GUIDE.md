# MemoryOS Observability Setup Guide

## Overview

You now have a properly organized observability and deployment structure for MemoryOS! Here's what we've set up:

```
deployments/
├── README.md                    # Main deployment guide
├── bootstrap.py                 # Setup automation script
├── local/                       # Local development
│   ├── docker-compose.yml       # Full stack with monitoring
│   └── prometheus.yml           # Prometheus configuration
├── kubernetes/                  # Kubernetes manifests
│   ├── base/                    # Base configurations
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── configmap.yaml
│   └── overlays/                # Environment-specific overlays
├── monitoring/                  # Monitoring configurations
│   ├── README.md                # Your original Grafana setup guide
│   ├── grafana/                 # Grafana dashboards & config
│   └── prometheus/              # Prometheus rules & alerts
└── docker/
    └── Dockerfile               # MemoryOS container image
```

## Quick Start

### Option 1: Local Development (Recommended)

1. **Install Docker Desktop** (if not already installed)
   - Download from https://www.docker.com/products/docker-desktop/
   - Make sure it's running

2. **Start the observability stack**:
   ```bash
   cd deployments
   python bootstrap.py local
   ```

3. **Access the services**:
   - **Agents Plane**: http://localhost:8080 (agents/tools API)
   - **App Plane**: http://localhost:8081 (frontend API)
   - **Control Plane**: http://localhost:8082 (admin/security API)
   - **Metrics**: http://localhost:9090/v1/metrics
   - **Grafana**: http://localhost:3000 (admin/admin)
   - **Prometheus**: http://localhost:9090
   - **Jaeger Tracing**: http://localhost:16686

### Option 2: Kubernetes (Advanced)

1. **Make sure kubectl is connected to your cluster**:
   ```bash
   kubectl cluster-info
   ```

2. **Deploy to Kubernetes**:
   ```bash
   cd deployments
   python bootstrap.py k8s
   ```

3. **Access services via port-forward**:
   ```bash
   # MemoryOS API
   kubectl port-forward -n memoryos svc/memoryos 8080:8080

   # Grafana (if deployed)
   kubectl port-forward -n monitoring svc/grafana 3000:3000
   ```

## What's Integrated

### 1. Your Existing Observability Module
The setup uses your existing `observability/` module which provides:
- **Structured JSON logging** with PII redaction
- **Prometheus metrics** for APIs, pipelines, storage
- **OpenTelemetry tracing** with spans
- **ASGI middleware** for HTTP instrumentation

### 2. Your Grafana Configuration
We've moved your Grafana files to the proper location:
- Dashboards are in `deployments/monitoring/grafana/dashboards/`
- Provisioning config is in `deployments/monitoring/grafana/provisioning/`
- ServiceMonitor for Prometheus scraping is preserved

### 3. Complete Development Environment
- **Prometheus** automatically scrapes MemoryOS metrics
- **Grafana** has your custom dashboards pre-loaded
- **Jaeger** collects distributed traces
- **Redis** available for caching needs

## Next Steps

### 1. Build MemoryOS Docker Image
```bash
cd deployments/docker
docker build -t memoryos:latest ../..
```

### 2. Implement Health Endpoints
Add these to your main application:
```python
# In your main API router
@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/ready")
async def ready():
    # Check dependencies (database, etc.)
    return {"status": "ready", "timestamp": time.time()}
```

### 3. Enable Metrics in Service.py
Update your `service.py` to expose metrics:
```python
from observability.metrics import registry
from prometheus_client import make_asgi_app

# Add metrics endpoint
metrics_app = make_asgi_app(registry)
app.mount("/v1/metrics", metrics_app)
```

### 4. Test the Setup
```bash
# Start local stack
cd deployments
python bootstrap.py local

# Check if services are running
docker-compose -f local/docker-compose.yml ps

# Test metrics endpoint
curl http://localhost:8081/v1/metrics

# Open Grafana
open http://localhost:3000
```

## Troubleshooting

### Common Issues

1. **Docker not running**: Make sure Docker Desktop is started
2. **Port conflicts**: If ports 3000, 8080, 9090 are in use, stop other services
3. **Memory issues**: Increase Docker memory limit in settings

### Useful Commands

```bash
# Check what's running
docker-compose -f deployments/local/docker-compose.yml ps

# View logs
docker-compose -f deployments/local/docker-compose.yml logs memoryos

# Stop everything
docker-compose -f deployments/local/docker-compose.yml down

# Restart just one service
docker-compose -f deployments/local/docker-compose.yml restart memoryos
```

### Prerequisites Check
```bash
cd deployments
python bootstrap.py check
```

## Integration with VS Code

Since you have the Kubernetes extension installed:

1. **Connect to cluster**: Use Command Palette → "Kubernetes: Set Kubeconfig"
2. **View pods**: Open Kubernetes explorer in VS Code sidebar
3. **Stream logs**: Right-click pods → "Follow Logs"
4. **Port forward**: Right-click service → "Port Forward"

You're all set! The observability layer is now properly organized and ready for development.

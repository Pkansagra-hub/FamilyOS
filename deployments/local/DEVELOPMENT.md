# MemoryOS Local Development Guide

This guide covers the complete development environment setup for MemoryOS, including Kubernetes cluster, hot-reload workflow, and mock external services.

## Prerequisites

- Docker Desktop with Kubernetes enabled
- PowerShell 5.1+ (Windows)
- kubectl CLI tool
- Skaffold (for hot-reload development)

## Quick Start

### 1. Setup Local Kubernetes Cluster

Run the automated setup script:

```powershell
# Navigate to the local deployment directory
cd deployments/local

# Run the setup script
.\setup-local-k8s.ps1
```

This script will:
- ✅ Verify prerequisites (Docker, kubectl)
- ✅ Enable Kubernetes in Docker Desktop
- ✅ Install NGINX Ingress Controller
- ✅ Create memoryos-dev namespace
- ✅ Deploy PostgreSQL, Redis, MinIO
- ✅ Deploy mock external services
- ✅ Deploy MemoryOS application
- ✅ Configure ingress routing
- ✅ Set up monitoring (Prometheus, Grafana, Jaeger)

### 2. Start Hot-Reload Development

```powershell
# Start Skaffold for hot-reload development
skaffold dev

# Or run in background
skaffold dev --port-forward
```

### 3. Access Services

After setup, the following services are available:

| Service | URL | Description |
|---------|-----|-------------|
| MemoryOS API | http://localhost:8080 | Main application API |
| Mock Services | http://localhost:8090 | Mock external services |
| PostgreSQL | localhost:5432 | Database (memoryos/memoryos123) |
| Redis | localhost:6379 | Cache and session store |
| MinIO | http://localhost:9000 | S3-compatible storage |
| Prometheus | http://localhost:9090 | Metrics and monitoring |
| Grafana | http://localhost:3000 | Dashboards (admin/admin) |
| Jaeger | http://localhost:16686 | Distributed tracing |

## Development Workflow

### Hot-Reload Development

The hot-reload system automatically detects changes and updates running containers:

1. **Make code changes** to any Python file
2. **Skaffold detects changes** and syncs files to containers
3. **Application auto-reloads** with new code
4. **No manual restart required**

### File Sync Patterns

The following files are automatically synced:

```yaml
# MemoryOS Application
- api/**/*.py → /app/api
- core/**/*.py → /app/core
- service.py → /app/service.py
- pyproject.toml → /app/pyproject.toml

# Mock Services
- mocks/*.py → /app
- mocks/*.txt → /app
```

### Development Commands

```powershell
# Start development with port forwarding
skaffold dev --port-forward

# Start development in background
skaffold dev --tail=false

# Debug mode with additional logging
skaffold dev --verbosity=debug

# Clean up resources
skaffold delete
```

## Mock External Services

The development environment includes comprehensive mock services for isolated development:

### Available Mock Services

- **🔐 OAuth2/OIDC Provider**: User authentication and authorization
- **🌐 External APIs**: Weather, News, Translation services
- **📨 Message Queue**: Pub/Sub messaging simulation
- **🔗 Webhooks**: Event notification system
- **💾 Storage**: File upload/download simulation
- **📢 Notifications**: Multi-channel messaging

### Mock Service URLs

```bash
# API Documentation
http://localhost:8090/docs

# Health Check
http://localhost:8090/health

# Service Statistics
http://localhost:8090/mock/stats

# Reset Mock Data
curl -X DELETE http://localhost:8090/mock/reset
```

### Using Mock Services

```python
# Example: Using mock OAuth in MemoryOS
import httpx

# Get access token
response = httpx.post("http://mock-services:8090/oauth/token", data={
    "grant_type": "client_credentials",
    "client_id": "memoryos_dev"
})
token = response.json()["access_token"]

# Make authenticated request
headers = {"Authorization": f"Bearer {token}"}
user_info = httpx.get("http://mock-services:8090/oauth/userinfo", headers=headers)
```

## Configuration

### Environment Variables

Set these in your development environment:

```powershell
# MemoryOS Configuration
$env:ENVIRONMENT = "development"
$env:DATABASE_URL = "postgresql://memoryos:memoryos123@localhost:5432/memoryos"
$env:REDIS_URL = "redis://localhost:6379"

# Mock Services Configuration
$env:MOCK_OAUTH_ISSUER = "http://localhost:8090"
$env:EXTERNAL_WEATHER_API = "http://localhost:8090/external/weather"
$env:EXTERNAL_NEWS_API = "http://localhost:8090/external/news"
```

### Kubernetes Configuration

```yaml
# Custom configuration in k8s/memoryos-configmap.yaml
data:
  ENVIRONMENT: "development"
  LOG_LEVEL: "DEBUG"
  DATABASE_URL: "postgresql://memoryos:memoryos123@postgres:5432/memoryos"
  REDIS_URL: "redis://redis:6379"
  EXTERNAL_OAUTH_URL: "http://mock-services:8090"
```

## Debugging

### Application Debugging

1. **Enable Debug Mode**:
   ```yaml
   # In memoryos-deployment.yaml
   env:
   - name: DEBUG
     value: "true"
   ```

2. **Connect Debugger**:
   ```powershell
   # Port forward debug port
   kubectl port-forward -n memoryos-dev svc/memoryos 5678:5678

   # Connect VS Code debugger to localhost:5678
   ```

### Database Access

```powershell
# Connect to PostgreSQL
kubectl exec -it -n memoryos-dev postgres-0 -- psql -U memoryos -d memoryos

# Redis CLI
kubectl exec -it -n memoryos-dev redis-0 -- redis-cli
```

### Log Access

```powershell
# MemoryOS logs
kubectl logs -n memoryos-dev deployment/memoryos -f

# Mock services logs
kubectl logs -n memoryos-dev deployment/mock-services -f

# All services logs
kubectl logs -n memoryos-dev --all-containers=true -f
```

## Monitoring and Observability

### Metrics (Prometheus)

Access Prometheus at http://localhost:9090

Common queries:
```promql
# API request rate
rate(http_requests_total[5m])

# Memory usage
process_memory_bytes

# Database connections
postgresql_connections_active
```

### Dashboards (Grafana)

Access Grafana at http://localhost:3000 (admin/admin)

Pre-configured dashboards:
- MemoryOS Application Metrics
- PostgreSQL Database Metrics
- Redis Cache Metrics
- Kubernetes Cluster Overview

### Tracing (Jaeger)

Access Jaeger at http://localhost:16686

Trace your requests across services:
- API → Database queries
- Cache operations
- External service calls
- Async task processing

## Testing

### Unit Tests

```powershell
# Run unit tests
kubectl exec -n memoryos-dev deployment/memoryos -- python -m pytest tests/unit -v

# Run with coverage
kubectl exec -n memoryos-dev deployment/memoryos -- python -m pytest tests/unit --cov=memoryos
```

### Integration Tests

```powershell
# Run integration tests against local environment
kubectl exec -n memoryos-dev deployment/memoryos -- python -m pytest tests/integration -v

# Test with mock services
kubectl exec -n memoryos-dev deployment/memoryos -- python -m pytest tests/integration --mock-services
```

### Load Testing

```powershell
# Simple load test
kubectl run load-test --image=alpine/curl --rm -it -- \
  /bin/sh -c "for i in \$(seq 1 100); do curl http://memoryos:8080/health; done"
```

## Troubleshooting

### Common Issues

1. **Services Not Starting**:
   ```powershell
   # Check pod status
   kubectl get pods -n memoryos-dev

   # Check events
   kubectl get events -n memoryos-dev --sort-by='.lastTimestamp'
   ```

2. **Database Connection Issues**:
   ```powershell
   # Check PostgreSQL status
   kubectl exec -n memoryos-dev postgres-0 -- pg_isready

   # Test connection
   kubectl exec -n memoryos-dev deployment/memoryos -- python -c "import psycopg2; print('DB OK')"
   ```

3. **Hot-Reload Not Working**:
   ```powershell
   # Restart Skaffold
   skaffold delete && skaffold dev

   # Check file permissions
   ls -la deployments/local/
   ```

### Cleanup

```powershell
# Stop Skaffold development
# Press Ctrl+C in Skaffold terminal

# Clean up resources
skaffold delete

# Or run cleanup script
.\cleanup-local-k8s.ps1

# Reset Docker Desktop Kubernetes
# Docker Desktop → Settings → Kubernetes → Reset Cluster
```

## Advanced Development

### Custom Profiles

Create custom Skaffold profiles for different scenarios:

```yaml
# In skaffold.yaml
profiles:
- name: debug
  build:
    artifacts:
    - image: memoryos/api
      docker:
        buildArgs:
          ENABLE_DEBUG: "true"

- name: performance
  deploy:
    kubectl:
      manifests:
      - k8s/performance-config.yaml
```

Use profiles:
```powershell
# Debug mode
skaffold dev -p debug

# Performance testing
skaffold dev -p performance
```

### Multiple Environment Support

```powershell
# Development environment
skaffold dev --kube-context=docker-desktop

# Staging environment
skaffold dev --kube-context=staging-cluster

# Different namespaces
skaffold dev --namespace=memoryos-feature-branch
```

---

This development environment provides a complete, production-like local setup with hot-reload capabilities, comprehensive monitoring, and isolated mock services for efficient MemoryOS development.

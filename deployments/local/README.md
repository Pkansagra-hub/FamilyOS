# Quick Observability Setup

Start the local development observability stack:

```bash
cd deployments
python bootstrap.py local
```

Or use Docker Compose directly:

```bash
cd deployments/local
docker-compose up -d
```

## Access Points

After starting:
- **MemoryOS**: http://localhost:8080
- **Metrics**: http://localhost:8081/v1/metrics
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686

## Stop

```bash
cd deployments/local
docker-compose down
```

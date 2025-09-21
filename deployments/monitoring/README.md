# Grafana Provisioning + Prometheus Operator ServiceMonitor (FamilyOS)

This bundle gives you a one-shot setup:
- Grafana provisioning (datasource + dashboards provider)
- FamilyOS dashboard JSON
- Service + ServiceMonitor to scrape `/v1/metrics` from the FamilyOS API
- Optional Grafana Deployment that mounts everything

## Apply (quick demo)

```bash
# namespaces (adjust as needed)
kubectl create ns familyos || true
kubectl create ns monitoring || true

# your FamilyOS API should expose /v1/metrics on port 8081
kubectl apply -f k8s/service.yaml

# Prometheus Operator must be installed and selecting 'release=prometheus'
kubectl apply -f k8s/servicemonitor.yaml

# Grafana (optional one-shot)
kubectl create secret generic grafana-admin -n monitoring       --from-literal=username=admin --from-literal=password=admin

kubectl apply -f grafana/grafana-deployment.yaml
```

Grafana will read:
- `/etc/grafana/provisioning/datasources/datasources.yaml` -> Prometheus DS (env PROMETHEUS_URL override)
- `/etc/grafana/provisioning/dashboards/dashboards.yaml` -> provider pointing at `/var/lib/grafana/dashboards/familyos`
- `/var/lib/grafana/dashboards/familyos/familyos-observability.json` -> the dashboard

## Notes
- If you already run Grafana, copy the two provisioning YAMLs under `/etc/grafana/provisioning/...` and place
  `familyos-observability.json` under a dashboards directory configured by your instance.
- Adjust labels in `ServiceMonitor.spec.selector.matchLabels` to match your Service.
- If your API only exposes a single port for both HTTP and metrics, drop the `http-metrics` port and set `targetPort: 8080`.

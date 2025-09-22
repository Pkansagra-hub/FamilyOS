# observability/ — Contract Bundle v1.0.0

Scope: On-device logs, metrics, traces with correlation across API and Event Bus.

Key decisions
- **PII-safe by default**: redaction rules applied before sink; band-aware (GREEN/AMBER show limited fields; RED masks message; BLACK denies write).
- **Bounded cardinality**: strict label budgets; no user text in labels.
- **Correlation**: every record carries `request_id`, `trace_id`, `span_id`, `event_id?`, `space_id`, `band`.
- **Health surfaces**: `/health`, `/ready`, `/metrics` (Prometheus text) exposed locally.

Compatibility
- Additive module bundle. No changes to `contracts/api` nor `contracts/events`.
- Future additions: extra metrics/histogram buckets → minor.

Evidence: `observability/README.md`, `observability/{middleware.py,trace.py,metrics.py,logging.py,sinks.py}`.
Assumptions: No remote OTEL collector is required; if present, export honors MLS/E2EE policy.

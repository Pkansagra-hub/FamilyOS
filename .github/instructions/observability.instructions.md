---
description: Metrics, traces/spans, and structured logging.
applyTo: "observability/**/*.py,api/**/*.py,events/**/*.py,storage/**/*.py"
---
# 👀 Observability — Metrics · Traces · Logs

## 1) Metrics
- Prefix: **`familyos_`**; low-cardinality labels; document units.
- Emit counters/gauges/histograms for critical paths and errors.

## 2) Traces/Spans
- Name: `area.component.method`; propagate correlation/request ids.
- Annotate spans with policy context where safe (band/space/policy_version).

## 3) Logs
- JSON structured; include context ids. **Never log PII/secrets**.
- Redact sensitive fields; prefer event ids over raw payloads.

## 4) Tests
- Assert that key metrics/spans/logs are emitted for new features.
# retrieval/ — Contract Bundle v1.0.0

Scope: P01 broker fusing FTS+vector, ranking & QoS; emits `recall_request` & `recall_result`.

Decisions:
- API supports `mode: sync|async`; events are always emitted.
- Idempotency-Key required in async; dedupe by `request_id`.
- RED band masks `snippet_text`, `source_uri`; BLACK denies queries.
- Store bounded `trace` (max 64 steps).

Evidence: retrieval/{README.md,broker.py,fusion.py,ranker.py,qos_gate.py,trace_builder.py,stores/*}; contracts/events/examples/{recall_request_*.json,recall_result_*.json}

# Contract Tests - Retrieval Module

## Schema Validation Tests

### JSON Schema Compliance
- ✅ Validate `query_log.schema.json` with sample data
- ✅ Validate `cache_entry.schema.json` with sample data
- ✅ Validate event schemas in `catalog.json`
- ✅ Check schema $id consistency and versioning

### Data Integrity Tests
- ✅ Query hash format validation (64-char hex)
- ✅ Correlation ID uniqueness constraints
- ✅ Required field presence validation
- ✅ Enum value boundary testing

## Event Flow Tests

### Idempotency Validation
- ✅ RECALL_REQUESTED dedupe by (actor.user_id, query_hash, correlation_id)
- ✅ Duplicate correlation_id handling
- ✅ Envelope.id uniqueness enforcement
- ✅ Retry behavior with exponential backoff

### Causality Testing
- ✅ REQUEST→RESULT correlation_id linking
- ✅ Query hash consistency across events
- ✅ Timestamp ordering validation
- ✅ Space_id isolation enforcement

## Policy Compliance Tests

### Band-Based Access Control
- ✅ GREEN: Full query text and snippets allowed
- ✅ AMBER: Query hash only, truncated snippets (200 chars)
- ✅ RED: Query hash only, no snippets returned
- ✅ BLACK: Complete request blocking with audit

### PII Redaction Validation
- ✅ Query text hashing for AMBER+ bands
- ✅ Snippet masking per band policy
- ✅ Log field exclusion (query_text, snippet)
- ✅ Metrics label validation (no PII in labels)

### ABAC/RBAC Enforcement
- ✅ Space-scoped query authorization
- ✅ Actor capability validation (RECALL permission)
- ✅ Device trust level impact on band assignment
- ✅ Rate limiting per actor (100/min) and space (1000/hour)

## Performance & SLO Tests

### Latency Requirements
- ✅ P95 latency ≤ 120ms for all query types
- ✅ P99 latency ≤ 250ms target validation
- ✅ Cache hit response time optimization
- ✅ Query budget enforcement testing

### Cache Behavior Tests
- ✅ Cache hit ratio ≥ 70% validation
- ✅ LRU eviction policy compliance
- ✅ TTL-based expiration (24h/6h/1h/0 by band)
- ✅ Size limit enforcement (100MB max)
- ✅ Space isolation in cache partitioning

## Security Tests

### Threat Model Validation
- ✅ Cross-space query isolation
- ✅ Cache timing attack mitigation (±5% jitter)
- ✅ Query injection attempt blocking
- ✅ Unauthorized correlation_id access prevention

### Audit Trail Tests
- ✅ All AMBER+ queries generate audit events
- ✅ Correlation ID tracking through full lifecycle
- ✅ Envelope signature validation
- ✅ Policy version tracking

## Operational Tests

### Job Execution Validation
- ✅ Cache maintenance job (5min schedule)
- ✅ Query log rotation (daily 2 AM)
- ✅ Cache warmup effectiveness
- ✅ Health monitoring accuracy
- ✅ Security audit anomaly detection

### Error Handling Tests
- ✅ DLQ routing for failed events
- ✅ Circuit breaker activation under load
- ✅ Graceful degradation scenarios
- ✅ 429 rate limit response with Retry-After

### Observability Validation
- ✅ Metrics emission completeness
- ✅ Trace correlation (envelope.id → trace_id)
- ✅ Log format consistency
- ✅ Dashboard query accuracy

## Integration Tests

### Cross-Module Interaction
- ✅ Integration with global API `/v1/recall` endpoint
- ✅ Envelope schema compatibility
- ✅ Event bus message flow
- ✅ Storage backend interaction

### Migration Tests
- ✅ v0→v1 schema migration safety
- ✅ Rollback procedure validation
- ✅ Data preservation during upgrades
- ✅ Index rebuilding performance

## Test Automation

### Continuous Validation
```bash
# Run all contract tests
./tests/validate.sh

# Performance regression tests
./tests/perf-regression.sh

# Security compliance scan
./tests/security-scan.sh

# Schema drift detection
./tests/schema-drift.sh
```

### Test Data Generation
- Synthetic query patterns for different bands
- Realistic cache behavior simulation
- Security test vectors and edge cases
- Performance load testing scenarios

## Success Criteria

All tests must pass with:
- 🎯 Schema validation: 100% compliance
- 🎯 Policy enforcement: 100% accuracy
- 🎯 Performance SLOs: 95%+ achievement
- 🎯 Security controls: 100% effectiveness
- 🎯 Operational reliability: 99.9%+ uptime

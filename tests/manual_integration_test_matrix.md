# Manual Integration Test Matrix

## API Endpoints to Cover
- [ ] /v1/memories/{id} (GET)
- [ ] /v1/tools/memory/submit (POST)
- [ ] /v1/tools/memory/recall (POST)
- [ ] /v1/admin/{action} (GET/POST)
- [ ] /v1/events/ack (POST)
- [ ] /v1/events/stream (GET)
- [ ] /v1/privacy/{action} (GET/POST)
- [ ] /health (GET)
- [ ] /metrics (GET)

## Event Topics
- [ ] HIPPO_ENCODE
- [ ] Cognitive event topics
- [ ] Admin event topics

## Policy Enforcement Scenarios
- [ ] ALLOW (GREEN trust, valid capabilities)
- [ ] DENY (BLACK trust, no capabilities)
- [ ] DENY (missing capability)
- [ ] ALLOW_REDACTED (obligation: REDACT_PII)
- [ ] Caching: repeated requests
- [ ] Audit logging: success/failure

## Middleware Edge/Error Cases
- [ ] Auth failure (missing/invalid headers)
- [ ] Policy denial (forbidden operation/resource)
- [ ] Safety block (dangerous content, forbidden file type)
- [ ] QoS throttling (high load, low priority)
- [ ] Security block (blocked IP, threat detected)
- [ ] Observability: metrics, trace, error logging

## Event Bus/Handler Pipeline
- [ ] Publish event (valid/invalid)
- [ ] Subscribe handler (success/failure)
- [ ] Ack/Nack event
- [ ] Retry logic (simulate failure)
- [ ] DLQ (dead letter queue)
- [ ] Handler pipeline error

## Headers to Test
- [ ] X-Test-User
- [ ] X-Test-Role
- [ ] Authorization (valid/invalid)
- [ ] X-Priority (critical/high/low)
- [ ] X-Forwarded-For
- [ ] X-Real-IP

## Payloads
- [ ] Valid payload
- [ ] Invalid payload (missing fields)
- [ ] Large payload (exceeds limits)
- [ ] Dangerous content (script, SQL injection)
- [ ] Forbidden file type (.exe, .bat)

## System States
- [ ] High load (simulate max concurrent requests)
- [ ] Blocked IP (simulate repeated violations)
- [ ] Rate limits (exceed per-minute/5-minute limits)
- [ ] Critical safety/security (simulate threat)

---

> Use this matrix to implement and validate all manual integration tests in tests/manual_integration_test.py. Log all middleware state and metrics for each scenario.

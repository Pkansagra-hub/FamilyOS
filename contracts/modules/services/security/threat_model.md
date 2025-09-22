## STRIDE
- Spoofing: require bearer + device binding; actor.caps checked.
- Tampering: append-only receipts; hash payloads; envelope.signature if available.
- Repudiation: audit events (SERVICE_HEALTH_CHANGED, MEMORY_RECEIPT_CREATED).
- Information disclosure: AMBER requires `mls_group`.
- DoS: rate limits on API planes; queue back-pressure.
- Elevation of privilege: RBAC+ABAC gates, policy bands.

Residual risk: misconfiguration of caps. Mitigations: contract tests.

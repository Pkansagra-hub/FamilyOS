STRIDE Summary:
- Spoofing: internal_service_token required; mTLS recommended on-device IPC.
- Tampering: immutable fields (ts, request_id) set by middleware; audit trail in `observability/audit`.
- Repudiation: audit receipts for writes.
- Information Disclosure: band-based masking; MLS required for exports.
- DoS: rate limits on /metrics; cardinality budget.
- Elevation: no user-supplied labels become span attributes without whitelist.
Residual: Local attacker with root can read stores; mitigated by device encryption.

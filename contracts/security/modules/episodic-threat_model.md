STRIDE summary:
- Spoofing: mTLS/bearer + envelope actor; ABAC scope.
- Tampering: WAL + checksums; immutable envelope IDs; audit trail.
- Repudiation: audit events on append/export; DSAR receipts.
- Information Disclosure: band/redaction; E2EE/MLS at rest; on-device only.
- DoS: rate clamp via P17 budgets; bounded WAL segment sizes.
- Elevation: RBAC/ABAC; per-space keys; no cross-space joins.
Residual risk: local device root compromise (mitigate by OS hardening).

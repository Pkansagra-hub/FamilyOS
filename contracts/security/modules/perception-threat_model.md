# STRIDE Summary (Perception)
- Spoofing: mtls/bearer required; sensor_id bound to device cert.
- Tampering: envelope signature; reject if signature missing/invalid.
- Repudiation: audit logs with envelope.id and device_id.
- Info Disclosure: PII redaction, TTL, local-only obligations for AMBER.
- DoS: rate limits (per device_id); 429 with Retry-After.
- Elevation: ABAC checks on device_trust.

Residual Risk: transient exposure in frame buffers (bounded by TTL).

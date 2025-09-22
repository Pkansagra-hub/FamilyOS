# STRIDE Threat Model Summary (Retrieval)

## Spoofing
- **Risk**: Unauthorized actors submitting queries
- **Mitigations**:
  - Envelope signature validation
  - Actor identity verification via MLS
  - Device trust levels enforced
- **Residual**: Device compromise could spoof legitimate actor

## Tampering
- **Risk**: Query manipulation, result poisoning, cache corruption
- **Mitigations**:
  - Envelope integrity protection
  - Query hash verification
  - Cache entry checksums
  - Space ID ownership verification
- **Residual**: Race conditions in cache updates

## Repudiation
- **Risk**: Denial of query activities, especially for sensitive content
- **Mitigations**:
  - Comprehensive audit logging with envelope.id
  - Query log retention (7 days)
  - Correlation ID tracking
- **Residual**: Log tampering if local storage compromised

## Information Disclosure
- **Risk**: PII exposure in query text, results, logs, metrics
- **Mitigations**:
  - Query text hashing (SHA256) for storage/caching
  - Band-dependent snippet masking (AMBER=partial, RED=none)
  - PII redaction in logs and metrics
  - Cache encryption for sensitive bands
- **Residual**: Timing attacks might reveal query patterns

## Denial of Service
- **Risk**: Resource exhaustion, cache flooding, query storms
- **Mitigations**:
  - Per-actor rate limiting (429 + Retry-After)
  - Query latency budgets
  - Cache size limits (100MB)
  - Circuit breakers for backend stores
  - Background cleanup jobs
- **Residual**: Distributed query flooding across actors

## Elevation of Privilege
- **Risk**: Cross-space data access, unauthorized cache access
- **Mitigations**:
  - Space-scoped query isolation
  - ABAC checks on space membership
  - Cache partitioning by space_id
  - Band-based access controls
- **Residual**: Admin role compromise

## Additional Security Considerations
- **Cache Timing**: Random jitter (±5%) added to cache responses
- **Query Privacy**: Raw queries only stored for GREEN band with explicit policy
- **Cross-Space**: Queries strictly scoped to actor's accessible spaces
- **Encryption**: AMBER+ results encrypted at rest with space keys
- **Retention**: Automatic cleanup after TTL expiration

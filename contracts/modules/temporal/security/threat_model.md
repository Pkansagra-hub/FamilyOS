STRIDE summary:
- Spoofing: MLS + mTLS on producers; envelope.actor/device verified.
- Tampering: immutable envelope; hash field; audit trail.
- Repudiation: audit events + correlation IDs.
- Information Disclosure: space scoping + redaction; no content in index.
- Denial of Service: quotas per space; backoff; GC.
- Elevation of Privilege: RBAC+ABAC checks at producer/consumer.
Residual risk: Low.

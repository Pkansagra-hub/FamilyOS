# affect/ — Module Contract (v1.0.0)

Scope: On-device affect computation from sensor/text frames; writes affect state snapshots; no public HTTP.

Assumptions: Raw frames are handled by perception; affect consumes frame refs/events. All processing is on-device.

Reuse:
- Global envelope: `contracts/globals/events/envelope.schema.json` (required fields, bands, MLS).
- Global policy/versioning: `contracts/policy/POLICY_VERSIONING.md`.

Surfaces:
- Events: `SENSORY_FRAME.v1` (ingest), `AFFECT_ANALYZE.v1` (internal), `AFFECT_UPDATE.v1` (result).
- Storage: `affect.state` snapshots (append).
- Policy: RBAC/ABAC with bands; AMBER default; RED escalations restricted.
- Observability: metrics/logs/traces suitable for SLOs.

Compatibility:
- v1.0.0 initial. Future additions (dimensions, tags) are additive.

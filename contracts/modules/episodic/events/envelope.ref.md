This module **must** bind every event to the global envelope (`contracts/events/envelope.schema.json`):
- Required: `band` (GREEN/AMBER/RED/BLACK), `actor`, `user_id`, `device_id`, `space_id`, `policy_version`, `mls_group`, `qos`.
- Invariants: `band` & `obligations` cannot change semantics (see `contracts/POLICY_VERSIONING.md`).
- Obligations:
  - AMBER: undo window respected by tombstones.
  - RED/BLACK: redact content fields; BLACK never projects to retrieval.

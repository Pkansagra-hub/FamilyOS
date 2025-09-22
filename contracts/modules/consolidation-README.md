# consolidation/ — Module Contract (v1.0.0)

Scope: On-device dedup, rollups, reconciliation across events within a space. No cross-space merges.

Surfaces:
- Events: HIPPO_ENCODED, ROLLUP_CREATED, CANON_APPLIED, TOMBSTONE_APPLIED.
- Storage: rollup_record, canonical_record (append).
- Policy: AMBER default; exports apply pii masks.
- Jobs: nightly compaction and reconcile-drift.

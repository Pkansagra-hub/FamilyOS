# temporal v0 → v1 Migration

- Create table `time_index` with indices in `indices.yaml`.
- Backfill: rolling window last 30d per space/granularity.
- Dual-write window: N/A (new table).
- Rollback: drop table (no user content).

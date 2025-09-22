# Migration v0 → v1 (retrieval)

- Create collections `retrieval_trace`, `retrieval_cache_entry` with indices in indices.yaml.
- No backfill required.
- Rollback: drop new collections; no existing data affected.

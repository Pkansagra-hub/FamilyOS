Initial contract release. No migration. Future changes:
- Add nullable fields → minor; create index concurrently where supported.
- Segment model changes → dual-write and backfill; require major if incompatible.

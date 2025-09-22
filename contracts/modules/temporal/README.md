# temporal/ — Contract Bundle (v1.0.0)

**Purpose.** Provide a canonical, space‑scoped **time index** and event interfaces for relative time queries and reindex operations. Purely on‑device; stores *time metadata only*.

**Surfaces**
- Events: `TEMPORAL_RANGE_REQUEST`, `TEMPORAL_RANGE_RESPONSE`, `TEMPORAL_INDEX_BUILT` (envelope v1.1+).
- Storage: `time_index.schema.json` (append‑only index rows).
- No HTTP API; accessed via events and internal services.

**Compatibility**
- Envelope: ≥1.1.0; Policy bands unchanged.
- Additive; no global breaking changes.

**Assumptions**
- `workspace/` may emit `WORKSPACE_BROADCAST@1.0` that seeds range context.
- All times in UTC with explicit `tz` in payload when derived from user phrases.

**Privacy & Policy**
- Bands: Read GREEN/AMBER; Writes AMBER+. Space‑scoped; MLS group required.
- No PII beyond `space_id` / device/actor IDs in envelope.

**Audit**
- All index writes emit `TEMPORAL_INDEX_BUILT` with hashes and counts.

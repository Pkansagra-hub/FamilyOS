This module binds to the **global Event Envelope** (`contracts/events/envelope.schema.json`).

**Required fields**: `schema_version`, `id`, `ts`, `topic`, `band`, `actor`, `device`, `space_id`, `mls_group` (AMBER+), `trace`, `obligations[]`, `payload`.

**Policy bands**
- HEALTH emits at `band=GREEN`.
- Any state transition (start/stop, degraded) MUST be AMBER+ if it leaks operational topology; otherwise GREEN with redaction.

This module **must** populate envelope fields:
- `topic`: one of `TEMPORAL_RANGE_REQUEST@1.0`, `TEMPORAL_RANGE_RESPONSE@1.0`, `TEMPORAL_INDEX_BUILT@1.0`.
- `band`: Read flows emit GREEN; writes to index emit AMBER.
- `space_id`, `actor`, `device`, `mls_group`: required; `policy_version` pinned to active POLICY_VERSIONING.
- `idempotency_key`: `sha256(space_id + g + window.start + window.end)` for index writes.
- `trace`: provide `correlation_id` to pair request/response.

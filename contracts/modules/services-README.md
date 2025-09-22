# Services Contract (v1)

**Scope.** Orchestration layer across Write/Recall/Index. No direct HTTP in this module; exposed via `api/*` routes. Emits receipts & health. On‑device, E2EE, auditable.

**Dependencies.** Policy, Event Bus, Hippocampus, Storage, Observability.

**Compatibility.** New bundle; additive to `contracts/events/*` and `contracts/api/*`. No changes to global schemas. See `versions.yaml`.

**Assumptions.** Code is currently stubbed; contract reflects `services/README.md` diagrams and intended flows.

**PII.** Titles/notes never stored here; receipts carry hashes only.

**Envelope.** All events MUST use `contracts/events/envelope.schema.json` and set `band` per policy (AMBER+ for state changes), `trace`, `mls_group` for AMBER/RED/BLACK.

# episodic — Contract Bundle (v1.0.0)

**Scope:** Append-only, space-scoped event log with segments and links. WAL-first then DB insert; temporal indexing.
**Why:** Human‑readable diary of lived events; basis for recall, replay, consolidation.

## Key Design Decisions
- **Append-only** with **tombstones** (policy-driven), per `episodic/README.md` (~55, ~299, ~355).
- **WAL → DB** ordering with replay safety (ibid. ~122, ~331).
- **Temporal indices** and segment boundaries (ibid. ~246–255, ~368–409).
- Idempotency: `envelope.event_id` or `(space_id,event_id)`; dedupe hash optional.
- **No HTTP API** here; ingest via P02 Writer; recall via Retrieval module.
- **Events:** consumes `SENSORY_FRAME@1.0` (optional), emits/consumes `WORKSPACE_BROADCAST@1.0`, `MEMORY_RECEIPT_CREATED@1.0`, uses `HIPPO_ENCODE@1.0`.

## Compatibility
- Contracts v1.0.0; compatible with `contracts/events@1.0` and `contracts/api@1.0`.
- Future: adding nullable fields or indices = **minor**; changing types/semantics = **major** with migration.

## Assumptions
- Attachments metadata only (no raw media). Redaction manifests honored.
- Space-scoped E2EE/MLS as per security module posture.

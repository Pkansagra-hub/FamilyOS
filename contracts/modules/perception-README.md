# perception — Contract Bundle (v1.0.0)

**Scope.** Sensor → preattentive → fusion → `SENSORY_FRAME` events. Optional edge HTTP ingest. Frames are **ephemeral**; durable "memories" live elsewhere.

**Design anchors:** `contracts/events/envelope.schema.json` (envelope), `events/README.md` (bus), `perception/README.md` (module intent), examples `contracts/events/examples/sensory_frame_*.json`.

**Assumptions (conservative):**
- Frame payloads may contain PII; default **AMBER** for mic/camera unless device_trust=high.
- Ephemeral storage with TTL ≤ 24h for debugging; default off in PROD.

**Compatibility.** Initial **1.0.0**. Additive minors only for new optional fields. Majors require migration notes.

**Cross-module:** Emits events to bus; no direct dependency on retrieval/prospective.

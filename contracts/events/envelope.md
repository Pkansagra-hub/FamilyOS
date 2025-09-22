# Event Envelope (contracts/events/envelope.schema.json)

**Purpose.** Canonical wrapper for every internal event. Enforced at **bus ingress**; any producer that violates the contract is rejected. Contract gates live in CI and block merges on breaking changes. :contentReference[oaicite:27]{index=27}

**Design roots.**
- **Hybrid routing** (`qos.routing`: `fast-path` vs `gate-path`) and minimal event set from the FamilyOS Project Index. :contentReference[oaicite:28]{index=28}
- **Policy bands** (GREEN/AMBER/RED/BLACK) with **MLS/E2EE** requirement and **redaction** for AMBER+; **DSAR/Tombstones** invariants; **Safety** events restricted to RED/BLACK. :contentReference[oaicite:29]{index=29}:contentReference[oaicite:30]{index=30}
- **SLO budgets**: write p95≤80 ms, recall p95≤120 ms, encryption p95≤15 ms, index build p95≤250 ms, sync window≤5 s — reflected in QoS and comments. :contentReference[oaicite:31]{index=31}

---

## Fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `schema_version` | string (semver) | ✓ | Version of envelope schema emitted; adapters handle non-breaking evolution. :contentReference[oaicite:32]{index=32} |
| `id` | UUID or ULID | ✓ | Event id; supports replay/receipts. |
| `ts` / `ingest_ts` | RFC3339 | ts ✓ | Creation vs ingress time. |
| `topic` | enum \| `NAME@X.Y` | ✓ | Enum from minimal set (e.g., `RECALL_REQUEST`, `DSAR_EXPORT`, …) or versioned name. :contentReference[oaicite:33]{index=33} |
| `band` | enum | ✓ | `GREEN`, `AMBER`, `RED`, `BLACK`. AMBER+ enforces MLS + redaction rules. |
| `actor` | object | ✓ | `user_id` (uuid), `agent_id`, `caps` ⟶ `WRITE/RECALL/PROJECT/SCHEDULE`. :contentReference[oaicite:34]{index=34} |
| `device` | object | ✓ | `device_id`, `platform` (ios/android/macos/windows/linux/web/edge), `app_version` (semver), `locale`. |
| `space_id` | string | ✓ | `personal:<uuid>`, `shared:household`, `selective:<pair>`, `extended:*`, `interfamily:*`. :contentReference[oaicite:35]{index=35} |
| `policy_version` | string (semver) | ✓ | Policy bundle used to evaluate event. :contentReference[oaicite:36]{index=36} |
| `abac` | object | — | `role`, `trust`, `geo_precision` (city/region only). |
| `mls_group` | string | AMBER+ | MLS group name; required for AMBER/RED/BLACK events. :contentReference[oaicite:37]{index=37} |
| `qos` | object | ✓ | `routing`, `priority` (1–10), `latency_budget_ms` (1–1000), `retries` (0–3), `deadline_ms`. Budgets reflect SLOs. :contentReference[oaicite:38]{index=38} |
| `trace` | object | — | `trace_id`, `span_id`, `parent_span_id`, `sampled`. Coverage ≥95% of modules. :contentReference[oaicite:39]{index=39} |
| `obligations` | array | — | Any of `REDACT_PII`, `AUDIT_ACCESS`, `TOMBSTONE_ON_DELETE`, `SYNC_REQUIRED`. |
| `redaction_applied` | boolean | — | True iff redactor already masked payload PII. |
| `hashes` | object | ✓ | `payload_sha256` (req), `envelope_sha256`, `prev_event_id`, `merkle_root`. |
| `idempotency_key` | string | — | 8–64 chars for de-duplication. |
| `payload` | object | ✓ | Event body; validated by each topic’s own schema. |
| `signature` | object | ✓ | `alg` (ed25519/ecdsa_p256), `key_id`, `public_key`, `signature`. :contentReference[oaicite:40]{index=40} |
| `x_extensions` | object | — | Namespaced keys `x_*` only; used for controlled experimentation. |

---

## Enums & Conditionals

- **Topics** (excerpt): `HIPPO_ENCODE`, `RECALL_REQUEST`, `RECALL_RESULT`, `DSAR_EXPORT`, `REINDEX_REQUEST`, `TOMBSTONE_APPLIED`, `SAFETY_ALERT`, etc. Full list lives in `$defs.EventTopicEnum`. :contentReference[oaicite:41]{index=41}
- **Bands:** `GREEN`, `AMBER`, `RED`, `BLACK`.

**Policy conditionals (enforced in schema):**
1. AMBER/RED/BLACK ⇒ require `mls_group` **and** either `redaction_applied=true` **or** `obligations` contains `REDACT_PII`. :contentReference[oaicite:42]{index=42}
2. `TOMBSTONE_APPLIED` ⇒ `obligations` contains `TOMBSTONE_ON_DELETE`. :contentReference[oaicite:43]{index=43}
3. `DSAR_EXPORT` ⇒ `obligations` contains `AUDIT_ACCESS`. :contentReference[oaicite:44]{index=44}
4. `SAFETY_ALERT` ⇒ `band ∈ {RED, BLACK}`. :contentReference[oaicite:45]{index=45}

---

## QoS & SLOs

- `qos.latency_budget_ms` is capped at **1000ms** and should match pipeline SLOs: write≤80, recall≤120, encryption≤15, index≤250. CI perf gates enforce these budgets in practice even though schema provides a general upper bound. :contentReference[oaicite:46]{index=46}

---

## Versioning & Change Control

- **SemVer** for `schema_version` and `policy_version`.
- **Non‑breaking** additions only (new optional fields/enums).
- **Breaking** changes require adapters + deprecation windows; merges block via **contract‑checks** workflow. :contentReference[oaicite:47]{index=47}

---

## Extensibility

- Only `x_*` keys allowed (e.g., `x_experimentId`). Additions must be documented and tested; remove or graduate into canonical fields within two release trains.

---

## Validation

Run:

```bash
pytest -q tests/contracts/test_envelope_validation.py

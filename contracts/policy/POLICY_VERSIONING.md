# Contract & Policy Versioning

**Applies to:** `contracts/**` (API, Events, Storage, Pipelines), plus any generated code or validators that derive from these contracts.

## 0) TL;DR (non-negotiables)

* **SemVer** for all contracts: **MAJOR.MINOR.PATCH** (e.g., `1.4.2`).
* **Breaking change** → **MAJOR** bump + written migration plan + deprecation window (≥ **2 releases**) + CI contract tests must pass against **previous MINOR**.
* **Envelope invariants:** `band` and `obligations` **cannot be removed** in MINOR; see “Frozen Invariants” below for the full never-break list.
* **Team D owns contracts** and has veto on merges that alter `contracts/**`.

---

## 1) Scope & Artifacts

Contracts include (non-exhaustive):

* **Events:** `contracts/events/envelope.schema.json`, `contracts/events/topics.yaml`, `contracts/events/schemas/*.json`
* **API:** `contracts/api/openapi.vX.yaml` (e.g., `openapi.v1.yaml`)
* **Storage:** `contracts/storage/interfaces.md` (+ repo invariants)
* **Pipelines:** `contracts/pipelines/*.md` (registry, health, retry/DLQ semantics)

Generated validators/stubs must reflect the versioned artifacts above.

---

## 2) Semantic Versioning (what changes bump what)

### PATCH (x.y.Z)

* Non-functional clarifications (docs/comments)
* Tightening schema **descriptions** only
* Adding **optional** examples or non-normative fields in examples
* Fixing typos in descriptions; **no schema structure changes**

### MINOR (x.Y.z)

* **Additive, backward-compatible** changes only:

  * Add **new optional fields** with sensible defaults
  * Add **new topics** (events) or **new API routes** that do not affect existing ones
  * Add **new optional headers** (e.g., `X-Experiment-Id`)
  * Broaden enums **only if** existing values remain valid

> MINOR **must not**: make an optional field required, remove fields, narrow enums, change types, or alter required order/semantics.

### MAJOR (X.y.z)

* Any **incompatibility**:

  * Remove or rename a field/route/topic
  * Make optional → **required**
  * Change field type (string→object, number→string, etc.)
  * Narrow an enum
  * Remove or alter **frozen invariants** (see below)

---

## 3) Frozen Invariants (never break within same MAJOR)

These hold across all MINOR/PATCH within a given MAJOR:

* **Event Envelope:** required keys: `id`, `ts`, `topic`, `actor`, `device`, `space_id`, `band`, `policy_version`, `qos`, `hashes.payload_sha256`, `payload`, `signature`.

  * `band` values: `GREEN|AMBER|RED|BLACK` (no removal).
  * If `band ∈ {AMBER, RED, BLACK}` → `mls_group` **required**.
  * `additionalProperties: false` must remain in envelope and topic payload schemas.
  * `idempotency_key` semantics (dedupe) must not change.
* **API:** Stable **path prefix** (`/v1` for MAJOR=1). `POST /v1/tools/memory/submit` returns **202 Accepted** (async) in v1; must stay that way in 1.x.
* **Storage:** UnitOfWork invariants (atomicity, idempotent receipts, WAL/sync PRAGMAs) remain stable in 1.x.
* **Pipelines:** Bus idempotency, retry/backoff, DLQ naming pattern remain stable in 1.x.

> If you must change any invariant → **MAJOR**.

---

## 4) Version Advertising & Negotiation

* **Events:** producers MUST include `topic` with `@major.minor` (e.g., `ACTION_DECISION@1.0`). Consumers MAY accept `@1.x` but MUST log payload mismatches.
* **API:** clients MUST send `X-Contract-Version: <major.minor>`; server responds with `X-Contract-Active: <major.minor>`; if mismatch, return `406 Not Acceptable` with supported versions.
* **Storage:** repository adapters MUST declare `supports_contract_major = 1` and fail fast if mismatched.

---

## 5) Deprecation & Freeze Windows

* **Deprecation window:** at least **2 release trains** (≥ 4 weeks) where **dual-read/dual-write** shims run behind P16 feature flags.
* **Freeze week:** the last week before `rel/YYYY.Qn` is **contract freeze**; no changes to `contracts/**` allowed except CVE/emergency (see §9).

---

## 6) Approval Matrix (who signs what)

| Change Type                             | TL of Owning Team | Team D (Platform) | All TLs (A/B/C) |
| --------------------------------------- | ----------------- | ----------------- | --------------- |
| PATCH docs/clarifications               | ✅                 |                   |                 |
| MINOR additive (optional fields/routes) | ✅                 | ✅ (CI gate)       |                 |
| MAJOR (breaking)                        | ✅                 | ✅ (veto power)    | ✅ (ack)         |
| Frozen invariant change (within major)  |                   | ❌ (reject)        | ❌               |
| Emergency CVE/abuse fix                 | ✅                 | ✅                 | (FYI)           |

---

## 7) Mandatory CI Gates

* **Contract validation:** `.github/workflows/contract-checks.yml` must validate JSON/YAML, run schema tests, and **diff contracts vs main** to detect breaking changes.
* **Backward-compat tests:** when MINOR bumps, CI runs implementation against **previous MINOR** (n−1) examples.
* **Golden examples:** `contracts/events/examples/*.json` and `tests/contracts/*` must be updated in the same PR.

> PRs changing `contracts/**` without updated tests **fail**.

---

## 8) Migration Playbooks

### 8.1 Add optional field (MINOR)

1. Update schema (`minVersion: 1.<n+1>`), add example.
2. Implement dual handling: consumers ignore if absent.
3. Ship behind P16 flag if behavior affected.
4. Monitor canary; remove flag next release.

### 8.2 Make field required (MAJOR)

1. Add in `1.x` as **optional**; release for ≥2 trains.
2. Introduce writers that always populate it; readers tolerant.
3. Cut **2.0**: mark **required**; maintain adapter for old producers for one release.
4. Run backfill if needed; publish migration report.

### 8.3 Remove field/route/topic (MAJOR)

1. Add deprecation notice in **n**; publish removal plan and timeline.
2. Add runtime warning metric `memoryos.contracts.deprecated_usage_total`.
3. Cut **n+1 major**; ship adapter that ignores field for one train; delete afterward.

---

## 9) Emergency Procedure (Security/Abuse)

* Team D may **hot-patch** `contracts/**` to block abusive payloads.
* Publish `ADR/ADR-SEC-XXXX.md` within 48h and open backport PRs.
* Emergency changes still follow **MAJOR** semantics but may ship with a shortened window; consumers must be tolerant (fail closed at the edge).

---

## 10) Changelog & Documentation

* Maintain `contracts/CHANGELOG.md` with entries per artifact:

  ```
  ## [1.3.0] - 2025-09-08
  - events/topics.yaml: add PROSPECTIVE_SCHEDULE@1.1 (optional field `origin`)
  - api/openapi.v1.yaml: add header `Idempotency-Key`
  ```
* Every MAJOR bump must include an ADR (e.g., `ADR/ADR-00NN.md`) explaining rationale, migration, and rollback.

---

## 11) Examples & Validation (normative)

* Each topic MUST have a **schema\_ref** (JSON Schema) and at least **3 examples** in `contracts/events/examples/<topic>/`.
* Envelope examples MUST include **AMBER/RED/BLACK** cases to exercise MLS requirements.
* OpenAPI examples MUST include happy-path and policy denial responses.

---

## 12) Contract Drift Alarms

* Team D owns black-box probes that publish synthetic events/API calls daily; any validation failure pages **Platform on-call** and blocks release train promotion.

---

## 13) Never-Break List (v1.x summary)

1. Envelope required fields as listed in §3.
2. `band` enum values.
3. `/v1` path prefix; `submit` → `202 Accepted`.
4. UoW atomic + idempotent receipts + WAL; DLQ naming & retry semantics.
5. Metrics namespaces: `memoryos.api.*`, `memoryos.pipelines.pXX.*`, `memoryos.storage.*`.

---

## 14) Version File & Headers (implementation notes)

* Server must expose active contract version at:

  * Header: `X-Contract-Active: 1.<minor>`
  * Route: `GET /v1/contracts/version` → `{ "api":"1.3", "events":"1.2", "storage":"1.1" }`
* Code should centralize version constants (e.g., `memory/version.py`) to avoid drift.

---

### Appendix A — Breaking-change detector (CI hint)

* Scripts referenced by CI should compare JSON Schema ASTs and OpenAPI diffs; mark **required field additions**, **enum narrowing**, **type changes** as breaking.

### Appendix B — Feature flags & canaries

* All behavior that could alter external shape must be behind **P16 flags**; topics with `canary: true` route to shadow consumers until stability is proven.

---

**Ownership:** Team D (Platform & Release).
**Effective date:** upon merge to `main`.
**Violation handling:** PRs violating this policy will be rejected by CI; manual overrides require D-TL approval and a follow-up ADR.

---
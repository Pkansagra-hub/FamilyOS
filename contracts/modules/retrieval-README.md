# retrieval — Contract Bundle (v1.0.0)

**Scope:** P01 Recall + P17 QoS. Defines API subset (reusing global OpenAPI), event consumption, and trace log storage.
**Evidence:** `contracts/api/openapi.v1.yaml` `/v1/tools/memory/recall`; `retrieval/README.md` trace builder (~107–160).

**API:** Reuses `contracts/api/openapi.v1.yaml` with module-scoped subset below (no breaking changes).

**Assumptions:** Cache stores only derived results and anonymized keys; raw query text not logged unless GREEN and policy allows.

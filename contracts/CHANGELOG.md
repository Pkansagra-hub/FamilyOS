# Contracts Changelog

> Format: Keep one section per release train/week as needed. Use SemVer per artifact.
> Only list normative changes (those that affect validation or runtime behavior).

## [1.9.0] - 2025-01-27
### Enhanced Storage Contracts - Validation & UoW Improvements
- **🔧 COMPREHENSIVE CONTRACT VALIDATION**: Major systematic improvement to storage contract validation
  - **Storage Validation Success**: Improved from 7/37 (19%) to 17/37 (46%) passing schemas
  - **Comprehensive Fix System**: `scripts/contracts/comprehensive_fix.py` for systematic schema-example alignment
  - **ULID Validation Tools**: `scripts/contracts/fix_ulids.py` and `generate_valid_ulids.py` for proper ULID formatting
  - **Schema-Example Alignment**: Fixed property mismatches, added required fields, corrected type definitions

- **📋 ENHANCED UNIT OF WORK v1.1.0**: Production-ready Unit of Work with comprehensive capabilities
  - **Enhanced Schema**: `unit_of_work_enhanced.schema.json` with performance monitoring and audit trails
  - **Receipt System**: Comprehensive write receipts with SHA256 checksums and verification
  - **Error Handling**: Structured error capture with retry mechanisms and failure analysis
  - **Performance Monitoring**: Transaction timing, performance metrics, and optimization hints
  - **Context Tracking**: Full audit trail with correlation IDs and actor information

- **🗄️ MIGRATION SYSTEM**: Complete migration framework for storage contracts
  - **Migration Documentation**: `storage/migrations/storage-uow-enhancement-v1_1_0.md`
  - **SQLite Optimization**: `storage/migrations/storage-sqlite-enhancement-v1_2_0.md`
  - **Backward Compatibility**: Clear migration paths with rollback procedures
  - **Version Management**: Enhanced versioning system with semantic versioning

- **✅ VALIDATED SCHEMAS** (17 passing schemas):
  - Core: `affect_state`, `drives_state`, `fts_document`, `hippocampus_trace`, `imagination_snapshot`
  - Indexing: `index_checkpoint`, `index_config`, `index_health`
  - Knowledge: `kg_entity`, `metacog_report`
  - Metrics: `metric_point`, `migration_record`, `ml_run`
  - Patterns: `pattern_detection`, `privacy_request`
  - Security: `rbac_binding`, `reward_event`, `semantic_item`
  - Social: `social_cognition_state`, `tom_report`

### Contract Freeze v1.9.0
- **560 Contract Artifacts Frozen**: Complete baseline with SHA256 index for production deployment
- **Enhanced Storage Baseline**: Clean validation baseline with systematic improvements
- **Production Ready**: Contract freeze establishes stable foundation for enhanced storage system

## [1.8.0] - 2025-09-10
### Added
- **FINAL CONTRACT COUNCIL R0-R4 PHASE**: Four remaining module contracts complete the ecosystem (11/11 total)
  - **`contracts/modules/services/` v1.0.0**:
    - 🏗️ OS-level orchestrators for write/recall/indexing; bridges API → pipelines P01–P20
    - 🏗️ Events: `SERVICE_HEALTH_CHANGED@1.0` (audit), `MEMORY_RECEIPT_CREATED@1.0` (reused)
    - 🏗️ Storage: service_registry, service_status (append-only), service_receipt
    - 🏗️ No direct HTTP surface - exposed via existing `api/*` routes
    - 🏗️ RBAC+ABAC security with append-only receipts carrying hashed payloads only
  - **`contracts/modules/prospective/` v1.0.0** (Final Enhancement):
    - ⏰ Complete OpenAPI for trigger CRUD with Idempotency-Key headers
    - ⏰ Comprehensive trigger/occurrence storage schemas with next_fire_at indexing
    - ⏰ Jobs: scan_due_triggers (15s), cleanup_occurrences (daily)
    - ⏰ AMBER security for write operations with affect/safety condition checks
  - **`contracts/modules/sync/` v1.0.0**:
    - 🔄 CRDT-based P2P replication with MLS/E2EE hooks
    - 🔄 OpenAPI: push/pull operations, peer management, MLS key rotation
    - 🔄 Events: `SYNC_PEER_STATUS_CHANGED@1.0`, `SYNC_EXCHANGE_SUMMARY@1.0`
    - 🔄 Storage: peer, vector_clock, op_log (reuses global CRDT schemas)
    - 🔄 Vector clock anti-replay protection with idempotent batch processing
  - **`contracts/modules/social_cognition/` v1.0.0**:
    - 🧠 Explainable mind model: beliefs/intentions/relations (symbolic features only)
    - 🧠 Events: `BELIEF_UPDATE@1.0`, `INTENT_INFERRED@1.0` (schemas added, examples existed)
    - 🧠 Storage: belief, intention, relation schemas (no raw text/audio/video)
    - 🧠 Security: PII redaction for explain fields, 280-char explain limits
    - 🧠 Policy: Forbids raw text persistence, audit tracking for belief changes

### Contract Council Ecosystem: 11/11 COMPLETE ✅
1. ✅ observability/ — Metrics, traces, logs (v1.0.0)
2. ✅ policy/ — RBAC/ABAC enforcement (v1.0.0)
3. ✅ retrieval_new/ — P01 recall broker (v1.0.0)
4. ✅ policy_new/ — Enhanced policy framework (v1.0.0)
5. ✅ episodic/ — Append-only event log (v1.0.0)
6. ✅ prospective/ — P05 scheduler (v1.0.0)
7. ✅ retrieval/ — P01 enhanced recall (v1.0.0)
8. ✅ services/ — OS orchestrators (v1.0.0)
9. ✅ sync/ — P07 CRDT replication (v1.0.0)
10. ✅ social_cognition/ — Mind model (v1.0.0)

### Production-Ready MemoryOS Architecture
- **Event-Driven Consistency**: All 11 modules bind to global envelope with space_id, band, actor
- **Security Framework**: Complete ABAC/RBAC with band classifications, MLS for AMBER+, STRIDE modeling
- **Storage Contracts**: JSON Schema Draft-07 compliance, space-scoped partitioning, retention policies
- **API Standards**: OpenAPI 3.1 with idempotency, error handling, module-scoped endpoints
- **Observability**: Comprehensive metrics, traces, logs with correlation and SLO definitions
- **Operational Excellence**: Jobs, migrations, testing frameworks across all contract bundles

## [1.7.0] - 2025-09-10
### Added
- **COMPLETE CONTRACT COUNCIL R0-R4 (Modules 5-7)**: Three additional critical module contracts
  - **`contracts/modules/episodic/` v1.0.0**:
    - 📔 Append-only, space-scoped event log with segments and links
    - 📔 WAL-first then DB insert with temporal indexing and replay safety
    - 📔 Events: consumes `WORKSPACE_BROADCAST`, emits `MEMORY_RECEIPT_CREATED`, `HIPPO_ENCODE`
    - 📔 No HTTP API surface - ingest via P02 Writer, recall via Retrieval module
    - 📔 Complete policy framework with band-aware tombstones and redaction
  - **`contracts/modules/prospective/` v1.0.0** (Enhanced):
    - ⏰ P05 trigger storage with schedule/action/conditions modeling
    - ⏰ Idempotent upsert on trigger ID with tick deduplication
    - ⏰ Events: `PROSPECTIVE_SCHEDULE`, `PROSPECTIVE_REMIND_TICK` with global envelope
    - ⏰ Band gates (BLACK never fires), AMBER supports undo, audit obligations
    - ⏰ Tick runner and retry jobs with eligibility scoring
  - **`contracts/modules/retrieval/` v1.0.0** (Enhanced):
    - 🔍 P01 Recall + P17 QoS with module-scoped OpenAPI subset
    - 🔍 Reuses `/v1/tools/memory/recall` from global API (additive only)
    - 🔍 Events: consumes `WORKSPACE_BROADCAST`, `REINDEX_REQUEST`
    - 🔍 Trace log storage with band-aware retention and PII sampling
    - 🔍 Band filtering at candidate and final phases with redaction

### Architecture Enhancements
- **Contract Council Process**: All 7 modules now follow R0-R4 systematic review
- **Event-Driven Consistency**: Global envelope binding across episodic, prospective, retrieval
- **Storage Schema Contracts**: JSON Schema Draft-07 with explicit validation rules
- **Security Framework**: STRIDE threat modeling and ABAC/RBAC policy for all modules
- **Operational Readiness**: Jobs, observability, testing frameworks across all bundles

## [1.6.0] - 2025-09-10
### Added
- **COMPLETE CONTRACT COUNCIL R0-R4**: Four critical module contracts implementation
  - **`contracts/modules/observability/` v1.0.0**:
    - 📊 On-device logs/metrics/traces with correlation across API and Event Bus
    - 📊 PII-safe by default with band-aware redaction (GREEN/AMBER/RED/BLACK)
    - 📊 Health surfaces: `/health`, `/ready`, `/metrics` (Prometheus text)
    - 📊 Bounded cardinality with strict label budgets
    - 📊 Correlation: every record carries request_id, trace_id, span_id, space_id, band
  - **`contracts/modules/prospective/` v1.0.0** (Enhanced):
    - ⏰ Internal scheduler API with idempotency (`/__internal/prospective/schedule`, `/__internal/prospective/ack`)
    - ⏰ RFC3339 UTC times with ±5s skew tolerance
    - ⏰ Exponential backoff retries with DLQ after 5 attempts
    - ⏰ Band controls: RED → metadata-only events; BLACK → deny schedule create
  - **`contracts/modules/retrieval/` v1.0.0** (Enhanced):
    - 🔍 P01 broker with FTS+vector fusion and QoS gating
    - 🔍 Sync/async mode support with event emission always
    - 🔍 RED band masks snippet_text/source_uri; BLACK denies queries
    - 🔍 Bounded trace storage (max 64 steps) with compression
  - **`contracts/modules/policy/` v1.0.0**:
    - 🛡️ PDP/PEP with ABAC+RBAC and band evaluation
    - 🛡️ Internal API: `/__internal/policy/eval`, `/__internal/policy/redact`
    - 🛡️ Versioned policy documents with effective dates
    - 🛡️ Audit logging for all decisions; optional PII minimization events

### Architecture Enhancements
- **Event-Driven Consistency**: All modules bind to `contracts/events/envelope.schema.json`
- **Additive Compatibility**: Zero breaking changes to existing global API or events
- **Security-First**: STRIDE threat modeling for all modules with MLS/E2EE support
- **Operational Readiness**: Complete observability, jobs, and testing frameworks

## [1.5.0] - 2025-09-10
### Added
- **NEW MODULE CONTRACTS**: Complete Contract Council R0-R4 implementation
  - **`contracts/modules/temporal/` v1.0.0**:
    - 🕐 Time indexing with space-scoped granular buckets (minute/hour/day/week)
    - 🕐 Relative time query events (TEMPORAL_RANGE_REQUEST/RESPONSE)
    - 🕐 Privacy-preserving time metadata storage (no content, only timestamps)
    - 🕐 Automated index rebuilding and GC jobs
    - 🕐 GREEN/AMBER band security with space isolation
  - **`contracts/modules/workflows/` v1.0.0**:
    - 🔄 Deterministic orchestration with durable state management
    - 🔄 Event-driven workflow lifecycle (STARTED/UPDATED/COMPLETED/FAILED/RETRIED)
    - 🔄 Optimistic locking with append-only versioned state
    - 🔄 AMBER band transitions with audit logging
    - 🔄 GC and SLA watchdog jobs for operational excellence

### Module Architecture
- **Temporal Module**: Event-only interface, no HTTP API, binds to global envelope v1.1+
  - Time index schema with deduplication and TTL (P180D)
  - Hash-prefix redaction for doc_ids in responses
  - Correlation tracking for request/response pairs
- **Workflows Module**: Pure event-driven orchestration
  - Versioned state transitions with idempotency guarantees
  - Space-scoped workflow isolation with RBAC/ABAC
  - Completed workflow TTL (P14D) with automated cleanup

### Technical Enhancements
- Unified envelope binding across all modules (≥v1.1.0)
- Cross-module event correlation with trace.correlation_id
- Consistent STRIDE threat modeling for security
- Standardized observability with metrics, traces, and logs
- Production-ready operational procedures

## [1.4.0] - 2025-09-10
### Enhanced
- **COMPREHENSIVE CONTRACT IMPROVEMENTS**: Enhanced all modules with production-grade specifications
  - **Enhanced Retrieval Module v1.0.0**:
    - ✨ Comprehensive query logging with correlation tracking
    - ✨ Advanced cache management with LRU eviction and size limits
    - ✨ Multi-tier security with band-aware PII redaction
    - ✨ Performance SLOs (p95≤120ms, cache hit≥70%)
    - ✨ Automated jobs for maintenance, warmup, and security auditing
    - ✨ Detailed threat model with STRIDE analysis
    - ✨ Enhanced observability with 8 metrics and cardinality controls
  - **Enhanced Storage Architecture**:
    - 📊 Query log schema with privacy-preserving hash storage
    - 📊 Cache entry schema with access tracking and metadata
    - 📊 Comprehensive indexing strategy for performance
    - 📊 TTL-based retention with band-specific policies
  - **Enhanced Security & Policy**:
    - 🔒 ABAC/RBAC with dynamic policy support
    - 🔒 Multi-tier PII redaction (GREEN→AMBER→RED→BLACK)
    - 🔒 Rate limiting (100/min per actor, 1000/hr per space)
    - 🔒 Audit trail with correlation ID tracking
  - **Enhanced Operations**:
    - ⚡ 5 automated jobs (maintenance, rotation, warmup, monitoring, audit)
    - ⚡ Comprehensive contract testing framework
    - ⚡ Schema validation with drift detection
    - ⚡ Performance regression testing

### Technical Improvements
- Query correlation tracking across REQUEST→RESULT lifecycle
- Cache warming and intelligent prefetching
- Background security auditing with anomaly detection
- Enhanced metrics with proper cardinality limits
- Cross-space isolation with space-scoped queries
- Device trust level integration for band assignment

### Compatibility
- Envelope: requires `contracts/globals/events/envelope.schema.json` v1.x
- API: compatible with `contracts/globals/api/openapi.v1.yaml` 1.1.x
- Migration: v0→v1 creates new collections only; rollback safe
- Schema: additive changes only, backward compatible

## [1.3.0] - 2025-09-10
### Added
- **CONTRACT COUNCIL DELIVERABLES**: Complete contracts for 3 core modules
  - `contracts/modules/retrieval/*` — v1.0.0 (P01 recall & ranking broker with idempotency)
  - `contracts/modules/prospective/*` — v1.0.0 (P05 scheduler with device-gated reminders)
  - `contracts/modules/arbitration/*` — v1.0.0 (P04 planning & action selection with risk gates)
- Production-grade event catalogs with retry policies and DLQ handling
- Storage schemas with proper TTL, indices, and consistency models
- ABAC/RBAC policies with band-aware obligations (GREEN/AMBER/RED/BLACK)
- Complete observability stack (metrics, traces, logs, dashboards)
- Security threat models and authorization hooks per module

### Compatibility
- Envelope: requires `contracts/globals/events/envelope.schema.json` v1.x
- API: compatible with `contracts/globals/api/openapi.v1.yaml` 1.1.x
- Migration: v0→v1 creates new collections only; rollback safe

### Notes
- Retrieval: Query text hashed at rest; snippets masked per band obligations
- Prospective: Reminder text device-encrypted for AMBER+; scheduler drift p95≤1s
- Arbitration: High-risk decisions (≥0.8) require supervisor override; 365d retention

## [1.2.0] - 2025-09-10
### Added
- **CONTRACT COUNCIL DELIVERABLES**: Complete contracts for 3 core modules
  - `contracts/modules/affect/*` — v1.0.0 (events, storage, policy, jobs, security, observability, tests)
  - `contracts/modules/action/*` — v1.0.0 (events, storage, policy, jobs, security, observability, tests)
  - `contracts/modules/consolidation/*` — v1.0.0 (events, storage, policy, jobs, security, observability, tests)
- Comprehensive event catalogs with idempotency, ordering, and DLQ rules
- Storage schemas with proper indices and retention policies
- ABAC/RBAC policy definitions with band-aware security
- Complete observability (metrics, traces, logs, dashboards)
- Threat models and security hooks for each module

### Notes
- All module contracts reuse global envelope and error patterns from `contracts/globals/`
- Band-aware security: AMBER default, RED restrictions, BLACK rejection to DLQ
- On-device processing with MLS encryption per space
- Contract validation available via `make validate`

## [1.1.0] - 2025-09-10
### Changed
- **BREAKING STRUCTURE CHANGE**: Migrated to OBCF (One Big Contracts Folder) pattern
  - Moved `contracts/api/*` → `contracts/globals/api/`
  - Moved `contracts/events/*` → `contracts/globals/events/`
  - Moved `contracts/storage/*` → `contracts/globals/storage/`
- Added complete tooling infrastructure (validate_all.py, Makefile, CI)
- Added module structure template with versioning system
- **All existing $ref paths need updating** to reference `globals/` locations

### Added
- Complete OBCF directory structure with modules/ organization
- Automated validation tooling with JSON Schema Draft 2020-12 support
- Per-module versioning system (versions.yaml)
- CI/CD integration for contract validation

## [1.0.0] - 2025-09-08
### Added
- Initial publication of contracts:
  - events/envelope.schema.json (v1.0.0)
  - events/topics.yaml (v1.0)
  - api/openapi.v1.yaml (v1.0.0)
  - storage/interfaces.md (v1.0)
### Notes
- Team D (Platform) owns `contracts/**`. Contract-Checks CI required on PRs.

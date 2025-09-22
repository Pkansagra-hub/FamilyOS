# MemoryOS Contract Modules

**Complete Contract Council R0-R4 Implementation**

This directory contains production-ready contract bundles for the core MemoryOS modules, implementing the Contract Council's comprehensive specification with privacy-first, on-device posture and enterprise-grade security.

## Module Overview

| Module | Version | Purpose | API Surface | Event Topics |
|--------|---------|---------|-------------|--------------|
| **retrieval/** | v1.0.0 | P01 recall & ranking broker | Optional `/v1/recall/query` | RECALL_REQUEST, RECALL_RESULT, RECALL_TRACE_WRITTEN |
| **prospective/** | v1.0.0 | P05 triggers and scheduling | `/v1/prospective/triggers` CRUD | PROS_TRIGGER_FIRED/SKIPPED/DELETED + reuses existing |
| **temporal/** | v1.0.0 | Time indexing & range queries | Event-only (no HTTP) | TEMPORAL_RANGE_REQUEST/RESPONSE, TEMPORAL_INDEX_BUILT |
| **workflows/** | v1.0.0 | Deterministic orchestration | Event-only (no HTTP) | WORKFLOW_STARTED/UPDATED/COMPLETED/FAILED/RETRIED |
| **arbitration/** | v1.0.0 | Decision engines & policies | Event-driven rules | DECISION_REQUEST/RESULT, POLICY_UPDATED |
| **learning/** | v1.0.0 | P06 learning & neuromodulation | Event-only (no HTTP) | LEARNING_TICK, NEUROMOD_ADJUSTMENT, PATTERN_DETECTED |
| **cortex/** | v1.0.0 | Prediction & bandit algorithms | Event-only (no HTTP) | PREDICTION_COMPUTED, BANDIT_UPDATE, FEATURE_EXTRACTED |
| **metacognition/** | v1.0.0 | Self-monitoring & reflection | Event-only (no HTTP) | METACOG_REPORT, CONFIDENCE_UPDATE, ERROR_DETECTED |
| **imagination/** | v1.0.0 | Simulation & creative ideation | Event-only (no HTTP) | SIMULATION_RESULT, DREAM_SEQUENCE, CREATIVE_INSIGHT |
| **drives/** | v1.0.0 | Motivation & reward modeling | Event-only (no HTTP) | DRIVE_TICK, REWARD_COMPUTED, HOMEOSTASIS_ALERT |

## Architecture Principles

### 🔐 **Security-First Design**
- **Band-based Access Control**: GREEN (read), AMBER (write), RED (admin), BLACK (emergency)
- **RBAC/ABAC Integration**: Role and attribute-based permissions with device trust
- **STRIDE Threat Modeling**: Comprehensive security analysis for each module
- **MLS/E2EE Support**: End-to-end encryption with group membership
- **Audit Logging**: Immutable audit trails with correlation tracking

### 📊 **Data Privacy & Compliance**
- **Space-Scoped Isolation**: All operations confined to space boundaries
- **PII Redaction**: Multi-tier redaction policies with allowlists/blocklists
- **Retention Policies**: TTL-based cleanup with configurable windows
- **Content Separation**: Metadata vs content storage with privacy preservation

### ⚡ **Production Readiness**
- **SLO Compliance**: Performance targets (p95 ≤ 120ms, cache hit ≥ 70%)
- **Observability**: Comprehensive metrics, traces, and logs
- **Operational Jobs**: Automated maintenance, monitoring, and alerting
- **Schema Validation**: Contract testing with drift detection
- **Graceful Degradation**: Circuit breakers and backoff strategies

### 🔄 **Event-Driven Architecture**
- **Global Envelope**: Unified event schema with correlation IDs
- **Idempotency**: Deterministic replay protection via deduplication keys
- **Topic Consistency**: Reuse existing topics, additive-only changes
- **Cross-Module Communication**: Event-first with optional HTTP facades

## Contract Structure

Each module follows the standardized contract bundle structure:

```
contracts/modules/{module}/
├── README.md                    # Module purpose and interfaces
├── versions.yaml               # SemVer tracking and compatibility
├── api/                        # HTTP API specifications (if any)
│   ├── openapi.yaml           # Module-specific API paths
│   └── errors.md              # Error codes and handling
├── events/                     # Event-driven interfaces
│   ├── catalog.json           # Event topics and schemas
│   └── envelope.ref.md        # Envelope population rules
├── storage/                    # Persistent data contracts
│   ├── schemas/*.schema.json  # JSON Schema validation
│   ├── indices.yaml          # Database indexing strategy
│   └── migrations/           # Version upgrade procedures
├── policy/                     # Security and access control
│   ├── abac_rbac.yaml        # Authorization matrix
│   └── pii_redaction.yaml    # Data privacy rules
├── jobs/                       # Operational automation
│   └── jobs.yaml             # Scheduled tasks and maintenance
├── security/                   # Threat modeling and controls
│   ├── threat_model.md       # STRIDE analysis
│   └── authz_hooks.md        # Authorization enforcement
├── observability/              # Monitoring and diagnostics
│   ├── metrics.yaml          # Performance metrics
│   ├── traces.md             # Distributed tracing
│   ├── logs.md               # Structured logging
│   └── dashboards/           # Visualization configs
├── tests/                      # Contract validation
│   ├── contract-tests.md     # Test scenarios
│   ├── schema-index.json     # Schema validation index
│   └── validate.sh           # Automated testing script
```

## Global Dependencies

All modules bind to shared contracts:

- **`contracts/globals/events/envelope.schema.json`** v1.1+ — Universal event wrapper
- **`contracts/globals/api/openapi.v1.yaml`** — Central API specification
- **`contracts/globals/policy/POLICY_VERSIONING.md`** — Frozen invariants
- **`contracts/globals/storage/crdt.schema.json`** — Conflict-free data types

## Integration Guidelines

### 🚀 **Adding New Modules**
1. Follow the standardized contract bundle structure
2. Bind to global envelope schema v1.1+
3. Implement STRIDE threat modeling
4. Define observability contracts
5. Create comprehensive test coverage

### 📈 **Upgrading Modules**
1. Follow SemVer: patch (fixes), minor (additive), major (breaking)
2. Maintain backward compatibility in events and storage
3. Update migration procedures in `storage/migrations/`
4. Version policy changes in `policy/` directory
5. Update compatibility matrix in `versions.yaml`

### 🔍 **Testing & Validation**
```bash
# Validate all module contracts
for module in retrieval prospective temporal workflows arbitration; do
  cd contracts/modules/$module/tests
  ./validate.sh
done

# Run comprehensive contract tests
npm run test:contracts

# Schema validation
npm run validate:schemas
```

## Deployment Considerations

### **Environment Requirements**
- **Envelope Compatibility**: All modules require envelope schema ≥v1.1.0
- **API Integration**: Prospective and retrieval modules require global API minor bump
- **Storage Migration**: New modules are additive; existing data unaffected
- **Security Policies**: Band assignments and RBAC/ABAC rules must be configured

### **Rollback Safety**
- All schema changes are additive and backward compatible
- New storage collections can be dropped without data loss
- Event topics are versioned and don't impact existing consumers
- Policy changes maintain default-deny security posture

## Support & Documentation

- **Architecture Handbook**: `docs/architecture-handbook.md`
- **Contract Policy**: `contracts/POLICY_VERSIONING.md`
- **Global Events**: `contracts/globals/events/`
- **Changelog**: `contracts/CHANGELOG.md`

---

**Contract Council Approval**: All modules approved R0-R4 with unanimous consent
**Effective Date**: 2025-09-10
**Compatibility**: Envelope ≥v1.1.0, API additive minor bumps

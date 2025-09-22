---
version: "1.0.0"
date_created: "2025-09-10"
created_by: "Contract Council R0-R4"

module_info:
  name: "policy"
  version: "1.0.0"
  description: "PDP/PEP with ABAC+RBAC and band evaluation"
  category: "security"
  stability: "stable"

# ============================================================================
# OVERVIEW
# ============================================================================

overview: |
  The Policy module implements a Policy Decision Point (PDP) and Policy
  Enforcement Point (PEP) architecture with Attribute-Based Access Control
  (ABAC) combined with Role-Based Access Control (RBAC). It provides
  centralized policy evaluation, real-time redaction, and comprehensive
  audit logging.

  Key capabilities:
  - Policy evaluation engine with ABAC+RBAC
  - Real-time content redaction based on band classification
  - Versioned policy documents with effective dates
  - Comprehensive audit logging for all decisions
  - PII minimization and data protection compliance

# ============================================================================
# ARCHITECTURE
# ============================================================================

architecture:
  components:
    policy_decision_point:
      description: "Centralized policy evaluation engine"
      responsibilities:
        - Evaluate access requests against policies
        - Apply ABAC+RBAC rules
        - Generate policy decisions with reasons
        - Cache decisions for performance

    policy_enforcement_point:
      description: "Real-time content redaction and enforcement"
      responsibilities:
        - Apply redaction rules based on band/context
        - Enforce access controls
        - Filter content based on policy decisions
        - Log enforcement actions

    policy_store:
      description: "Versioned policy document storage"
      responsibilities:
        - Store policy documents with versions
        - Manage effective dates
        - Provide policy retrieval APIs
        - Support policy rollback

    audit_logger:
      description: "Comprehensive audit trail"
      responsibilities:
        - Log all policy decisions
        - Track access attempts
        - Record redaction actions
        - Generate compliance reports

  data_flow:
    policy_evaluation:
      - Request attributes collected
      - Applicable policies identified
      - ABAC rules evaluated
      - RBAC permissions checked
      - Decision rendered with audit trail

    content_redaction:
      - Content analyzed for sensitivity
      - Band classification applied
      - Redaction rules executed
      - Redacted content returned
      - Actions logged for audit

# ============================================================================
# INTERFACES
# ============================================================================

interfaces:
  internal_api:
    base_path: "/__internal/policy"
    endpoints:
      - path: "/eval"
        description: "Policy evaluation endpoint"
        security: "ABAC with context validation"

      - path: "/redact"
        description: "Content redaction endpoint"
        security: "ABAC with content classification"

      - path: "/policies"
        description: "Policy management endpoint"
        security: "RBAC admin only"

  events:
    emitted:
      - POLICY_DECISION_MADE
      - POLICY_VIOLATION_DETECTED
      - REDACTION_APPLIED
      - POLICY_UPDATED

    consumed:
      - CONTENT_CLASSIFICATION_REQUEST
      - ACCESS_REQUEST
      - AUDIT_LOG_REQUEST

# ============================================================================
# SECURITY MODEL
# ============================================================================

security:
  band_controls:
    GREEN:
      policy_access: "full"
      redaction_level: "none"
      audit_detail: "standard"

    AMBER:
      policy_access: "full"
      redaction_level: "minimal"
      audit_detail: "enhanced"

    RED:
      policy_access: "restricted"
      redaction_level: "aggressive"
      audit_detail: "comprehensive"

    BLACK:
      policy_access: "deny"
      redaction_level: "total"
      audit_detail: "security_only"

  threat_mitigation:
    - Policy tampering → Versioned policies with integrity checks
    - Unauthorized access → ABAC+RBAC with space isolation
    - Data leakage → Band-aware redaction and PII detection
    - Audit manipulation → Immutable audit logs with signatures
    - Privilege escalation → Principle of least privilege enforcement

# ============================================================================
# OPERATIONAL REQUIREMENTS
# ============================================================================

operations:
  performance_targets:
    policy_evaluation_latency: "< 50ms p95"
    redaction_throughput: "> 1000 ops/sec"
    policy_cache_hit_rate: "> 90%"
    audit_log_durability: "99.9%"

  reliability:
    availability: "99.9%"
    policy_consistency: "strong"
    audit_integrity: "cryptographic"

  monitoring:
    key_metrics:
      - Policy evaluation latency
      - Redaction operation count
      - Access denial rate
      - Audit log volume
      - Policy cache performance

  compliance:
    standards:
      - GDPR (data protection)
      - SOX (audit requirements)
      - HIPAA (healthcare data)
      - PCI DSS (payment data)

# ============================================================================
# DATA CONTRACTS
# ============================================================================

storage:
  policy_documents:
    schema: "storage/policy_document.schema.json"
    versioning: "semantic"
    retention: "indefinite"

  policy_decisions:
    schema: "storage/policy_decision.schema.json"
    retention: "90_days"
    compression: "after_30_days"

  audit_logs:
    schema: "storage/audit_log.schema.json"
    retention: "7_years"
    immutable: true

events:
  catalog: "events/catalog.json"
  envelope: "../globals/envelope.schema.json"
  validation: "strict"

# ============================================================================
# COMPATIBILITY
# ============================================================================

compatibility:
  api_version: "1.0.0"
  breaking_changes: "none"
  deprecations: "none"
  migration_path: "n/a"

dependencies:
  internal:
    - globals/envelope.schema.json (event envelope)
    - globals/band.schema.json (security bands)

  external:
    - Policy evaluation engine
    - Cryptographic libraries
    - Audit log storage

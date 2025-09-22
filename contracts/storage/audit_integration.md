# Storage Audit Integration Contract v1.0

**Module:** `storage/`
**Dependencies:** `policy/audit.py`
**Compliance:** GDPR, CCPA, SOX, HIPAA
**Effective:** 2025-09-12

---

## Overview

This contract defines the integration between the storage layer and the policy audit system, ensuring comprehensive audit trails, compliance reporting, and data retention management.

## 1. Policy Audit Integration

### 1.1 Audit Event Interface

All storage operations MUST emit audit events to the policy audit system:

```typescript
interface StorageAuditEvent {
  type: "STORAGE_OPERATION" | "COMPLIANCE_REPORT" | "RETENTION_ACTION"
  operation: "CREATE" | "READ" | "UPDATE" | "DELETE" | "PURGE"
  store_name: string
  envelope_id: string
  space_id: string
  actor_id: string
  timestamp: string          // ISO 8601 UTC
  receipt_hash: string       // Cryptographic receipt hash
  metadata: {
    record_count?: number
    data_size_bytes?: number
    retention_applied?: boolean
    compliance_flags?: string[]
    band?: "GREEN" | "AMBER" | "RED" | "BLACK"
  }
  result: "SUCCESS" | "FAILED" | "PARTIAL"
  error?: string
}
```

### 1.2 Audit Logger Integration

Storage modules MUST integrate with `policy.audit.AuditLogger`:

```python
from policy.audit import AuditLogger

class AuditableStore:
    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger

    def _log_operation(self, event: StorageAuditEvent):
        self.audit_logger.log(event)
```

## 2. Compliance Reporting

### 2.1 Data Subject Rights (GDPR Art. 15-22)

Storage layer MUST support compliance queries:

```python
@dataclass
class ComplianceQuery:
    subject_id: str              # Data subject identifier
    query_type: "ACCESS" | "PORTABILITY" | "ERASURE" | "RECTIFICATION"
    space_id: Optional[str]      # Scope to specific space
    date_range: Optional[tuple[datetime, datetime]]

@dataclass
class ComplianceReport:
    query: ComplianceQuery
    total_records: int
    accessible_records: int      # After policy filtering
    stores_searched: List[str]
    data_locations: List[str]    # Physical storage paths
    retention_status: Dict[str, str]  # store -> retention_policy
    actions_taken: List[str]     # e.g., ["REDACTED_PII", "ENCRYPTED_AT_REST"]
    generated_at: datetime
    report_hash: str             # Integrity verification
```

### 2.2 Retention Management

```python
@dataclass
class RetentionPolicy:
    store_name: str
    data_category: str           # "PERSONAL" | "BUSINESS" | "SYSTEM"
    retention_period_days: int
    deletion_method: "SOFT" | "HARD" | "CRYPTO_ERASE"
    compliance_basis: str        # Legal basis for retention

@dataclass
class RetentionAction:
    policy: RetentionPolicy
    records_affected: int
    action_taken: str
    verification_hash: str
    executed_at: datetime
```

## 3. Historical Receipt Queries

### 3.1 Audit Trail Queries

ReceiptsStore MUST support comprehensive audit queries:

```python
class ReceiptsStore:
    async def query_compliance_trail(
        self,
        query: ComplianceQuery
    ) -> ComplianceReport:
        """Generate compliance report with full audit trail."""

    async def query_receipts_by_subject(
        self,
        subject_id: str,
        include_deleted: bool = False
    ) -> List[WriteReceipt]:
        """Find all receipts affecting a data subject."""

    async def query_retention_candidates(
        self,
        policy: RetentionPolicy
    ) -> List[WriteReceipt]:
        """Find receipts eligible for retention actions."""

    async def verify_audit_integrity(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> AuditIntegrityReport:
        """Verify cryptographic integrity of audit trail."""
```

### 3.2 Audit Integrity Verification

```python
@dataclass
class AuditIntegrityReport:
    verified_receipts: int
    corrupted_receipts: int
    missing_receipts: int
    hash_chain_status: str       # "VALID" | "BROKEN" | "UNKNOWN"
    last_verified_receipt: str
    integrity_score: float       # 0.0 to 1.0
    anomalies: List[str]
```

## 4. Data Retention Management

### 4.1 Automatic Retention Processing

```python
class RetentionManager:
    async def apply_retention_policies(self) -> List[RetentionAction]:
        """Apply all active retention policies."""

    async def schedule_retention_review(
        self,
        policy: RetentionPolicy
    ) -> None:
        """Schedule retention policy review."""

    async def generate_retention_report(
        self,
        compliance_period: tuple[datetime, datetime]
    ) -> RetentionComplianceReport:
        """Generate compliance report for retention actions."""
```

### 4.2 Right to Erasure (GDPR Art. 17)

```python
@dataclass
class ErasureRequest:
    subject_id: str
    erasure_scope: "ALL" | "PARTIAL"
    space_filter: Optional[str]
    legal_basis: str
    requested_at: datetime

@dataclass
class ErasureResult:
    request: ErasureRequest
    records_found: int
    records_erased: int
    stores_affected: List[str]
    verification_hashes: List[str]
    completed_at: datetime
    attestation: str             # Cryptographic attestation
```

## 5. Performance Requirements

### 5.1 Audit Event Throughput
- **Minimum:** 10,000 audit events/second
- **Target:** 50,000 audit events/second
- **Latency:** <5ms p95 for audit logging

### 5.2 Compliance Query Performance
- **Subject data access:** <1 second for up to 1M records
- **Retention candidate queries:** <10 seconds for full scan
- **Integrity verification:** <30 seconds for 1 year of receipts

## 6. Security Requirements

### 6.1 Audit Log Security
- **Immutability:** Audit logs MUST be append-only
- **Integrity:** SHA-256 chaining for tamper detection
- **Confidentiality:** PII redaction before audit logging
- **Access Control:** Audit logs require ADMIN capability

### 6.2 Compliance Data Protection
- **In-Transit:** TLS 1.3 for compliance report transmission
- **At-Rest:** AES-256 for stored compliance reports
- **Retention:** Compliance reports follow data retention policies

## 7. Testing Requirements

### 7.1 Compliance Test Suite
```python
# Test compliance query coverage
def test_gdpr_data_subject_access():
    """Test GDPR Article 15 - Right of access."""

def test_gdpr_data_portability():
    """Test GDPR Article 20 - Right to data portability."""

def test_gdpr_right_to_erasure():
    """Test GDPR Article 17 - Right to erasure."""

def test_retention_policy_enforcement():
    """Test automatic retention policy application."""

def test_audit_integrity_verification():
    """Test cryptographic audit trail integrity."""
```

### 7.2 Performance Benchmarks
```python
def benchmark_audit_event_throughput():
    """Verify 10k+ audit events/second."""

def benchmark_compliance_query_latency():
    """Verify sub-second compliance queries."""

def benchmark_retention_processing():
    """Verify retention policy processing performance."""
```

## 8. Migration and Versioning

### 8.1 Schema Evolution
- Audit event schema follows SemVer
- Breaking changes require migration plan
- Backward compatibility for 2 major versions

### 8.2 Compliance History
- All compliance queries include schema version
- Historical reports remain valid across upgrades
- Audit integrity preserved during migrations

---

**Contract Version:** 1.0
**Next Review:** 2025-12-12
**Stakeholders:** Storage Team, Policy Team, Compliance Team

# Storage Authorization Hooks v1.0

**Module:** `storage/`
**Dependencies:** `security/mls_group.py`, `policy/`
**Threat Level:** HIGH
**Effective:** 2025-09-12

---

## Overview

This document defines authorization hooks, space-scoped security controls, and MLS group integration for the storage layer to ensure comprehensive access control and data protection.

## 1. Space-Scoped Security Model

### 1.1 Space Isolation

All storage operations MUST be scoped to a specific space with appropriate authorization:

```python
@dataclass
class SpaceContext:
    space_id: str                    # e.g., "personal/alice", "shared:household"
    actor_id: str                    # Requesting actor
    device_id: str                   # Device making request
    mls_group_id: Optional[str]      # MLS group for encryption
    band: Literal["GREEN", "AMBER", "RED", "BLACK"]  # Security band
    capabilities: Set[str]           # Authorized capabilities

class SpaceSecurityHooks:
    async def authorize_read(
        self,
        context: SpaceContext,
        resource: str
    ) -> AuthzResult:
        """Authorize read access to storage resource."""

    async def authorize_write(
        self,
        context: SpaceContext,
        resource: str,
        data_band: str
    ) -> AuthzResult:
        """Authorize write access with band elevation checks."""

    async def authorize_delete(
        self,
        context: SpaceContext,
        resource: str
    ) -> AuthzResult:
        """Authorize delete/tombstone operations."""
```

### 1.2 Band-Based Access Control

Security band enforcement MUST prevent unauthorized access:

```python
@dataclass
class BandPolicy:
    band: str
    read_capabilities: Set[str]      # Required caps for read
    write_capabilities: Set[str]     # Required caps for write
    encryption_required: bool        # Force encryption at rest
    audit_level: str                 # "BASIC" | "DETAILED" | "COMPREHENSIVE"
    cross_space_restrictions: List[str]  # Prohibited operations

BAND_POLICIES = {
    "GREEN": BandPolicy(
        band="GREEN",
        read_capabilities={"memory.read"},
        write_capabilities={"memory.write"},
        encryption_required=False,
        audit_level="BASIC",
        cross_space_restrictions=[]
    ),
    "AMBER": BandPolicy(
        band="AMBER",
        read_capabilities={"memory.read"},
        write_capabilities={"memory.write"},
        encryption_required=True,
        audit_level="DETAILED",
        cross_space_restrictions=["PROJECT_UNENCRYPTED"]
    ),
    "RED": BandPolicy(
        band="RED",
        read_capabilities={"memory.read", "privacy.redact"},
        write_capabilities={"memory.write", "privacy.redact"},
        encryption_required=True,
        audit_level="COMPREHENSIVE",
        cross_space_restrictions=["PROJECT", "DETACH"]
    ),
    "BLACK": BandPolicy(
        band="BLACK",
        read_capabilities={"memory.read", "privacy.redact", "security.admin"},
        write_capabilities={"memory.write", "privacy.redact", "security.admin"},
        encryption_required=True,
        audit_level="COMPREHENSIVE",
        cross_space_restrictions=["PROJECT", "DETACH", "BACKUP", "EXPORT"]
    )
}
```

## 2. MLS Group Integration

### 2.1 MLS Group Lifecycle

Storage layer MUST integrate with MLS groups for encryption:

```python
class MLSSecurityProvider:
    async def get_group_for_space(self, space_id: str) -> Optional[MLSGroup]:
        """Get active MLS group for space."""

    async def encrypt_for_space(
        self,
        space_id: str,
        plaintext: bytes
    ) -> EncryptedData:
        """Encrypt data using space's MLS group."""

    async def decrypt_for_space(
        self,
        space_id: str,
        encrypted_data: EncryptedData,
        actor_context: SpaceContext
    ) -> bytes:
        """Decrypt data if actor has group access."""

    async def rotate_space_keys(self, space_id: str) -> MLSGroup:
        """Rotate MLS group keys for space."""
```

### 2.2 Encryption at Rest Hooks

```python
@dataclass
class EncryptionConfig:
    algorithm: str = "AES-256-GCM"
    key_derivation: str = "HKDF-SHA256"
    envelope_encryption: bool = True    # Use MLS group keys
    field_level_encryption: List[str] = field(default_factory=list)

class EncryptionHooks:
    async def should_encrypt(
        self,
        context: SpaceContext,
        data_type: str
    ) -> bool:
        """Determine if data should be encrypted at rest."""

    async def encrypt_data(
        self,
        context: SpaceContext,
        data: Any,
        config: EncryptionConfig
    ) -> EncryptedData:
        """Encrypt data for storage."""

    async def decrypt_data(
        self,
        context: SpaceContext,
        encrypted_data: EncryptedData
    ) -> Any:
        """Decrypt data for authorized access."""
```

## 3. Storage Authorization Interface

### 3.1 Authorization Result

```python
@dataclass
class AuthzResult:
    decision: Literal["ALLOW", "DENY", "ALLOW_REDACTED"]
    reasons: List[str]               # Human-readable reasons
    obligations: List[str]           # Required post-authz actions
    redaction_rules: List[str]       # PII redaction requirements
    audit_required: bool = True      # Force audit logging
    ttl_seconds: Optional[int] = None  # Result cache TTL

    @property
    def is_allowed(self) -> bool:
        return self.decision in ["ALLOW", "ALLOW_REDACTED"]
```

### 3.2 Store Authorization Hooks

All storage implementations MUST implement authorization hooks:

```python
class SecureBaseStore(BaseStore):
    def __init__(
        self,
        config: StoreConfig,
        security_hooks: SpaceSecurityHooks,
        mls_provider: MLSSecurityProvider
    ):
        super().__init__(config)
        self.security_hooks = security_hooks
        self.mls_provider = mls_provider

    async def _authorize_operation(
        self,
        context: SpaceContext,
        operation: str,
        resource: str,
        data_band: Optional[str] = None
    ) -> AuthzResult:
        """Authorize storage operation."""

    async def _apply_encryption(
        self,
        context: SpaceContext,
        data: Any
    ) -> Any:
        """Apply encryption if required by policy."""

    async def _audit_operation(
        self,
        context: SpaceContext,
        operation: str,
        result: AuthzResult,
        metadata: Dict[str, Any]
    ) -> None:
        """Audit storage operation."""
```

## 4. Cross-Space Operations

### 4.1 Projection Security

Cross-space projections require enhanced authorization:

```python
@dataclass
class ProjectionRequest:
    from_space: str
    to_space: str
    operation: Literal["PROJECT", "REFER", "DETACH"]
    data_band: str
    consent_purpose: Optional[str]

class CrossSpaceSecurityHooks:
    async def authorize_projection(
        self,
        context: SpaceContext,
        request: ProjectionRequest
    ) -> AuthzResult:
        """Authorize cross-space data projection."""

    async def apply_projection_policy(
        self,
        request: ProjectionRequest,
        data: Any
    ) -> Any:
        """Apply redaction/encryption for projection."""
```

### 4.2 Consent Verification

```python
class ConsentVerificationHooks:
    async def verify_consent(
        self,
        from_space: str,
        to_space: str,
        purpose: str,
        actor_id: str
    ) -> bool:
        """Verify consent exists for cross-space operation."""

    async def record_consent_usage(
        self,
        consent_record: str,
        operation_details: Dict[str, Any]
    ) -> None:
        """Record consent usage for audit trail."""
```

## 5. Threat Mitigation

### 5.1 Data Exfiltration Prevention

```python
class ExfiltrationPrevention:
    async def detect_bulk_access(
        self,
        context: SpaceContext,
        access_pattern: AccessPattern
    ) -> ThreatAssessment:
        """Detect potential bulk data access."""

    async def rate_limit_operations(
        self,
        context: SpaceContext,
        operation: str
    ) -> bool:
        """Apply rate limiting to prevent abuse."""
```

### 5.2 Privilege Escalation Detection

```python
class PrivilegeEscalationDetection:
    async def validate_capability_claims(
        self,
        context: SpaceContext,
        claimed_capabilities: Set[str]
    ) -> ValidationResult:
        """Validate capability claims against policy."""

    async def detect_anomalous_access(
        self,
        context: SpaceContext,
        historical_patterns: List[AccessPattern]
    ) -> AnomalyReport:
        """Detect anomalous access patterns."""
```

## 6. Performance and Caching

### 6.1 Authorization Caching

```python
class AuthzCache:
    async def cache_authz_result(
        self,
        cache_key: str,
        result: AuthzResult,
        ttl_seconds: int
    ) -> None:
        """Cache authorization result."""

    async def get_cached_authz(
        self,
        cache_key: str
    ) -> Optional[AuthzResult]:
        """Retrieve cached authorization result."""

    def invalidate_cache_for_space(self, space_id: str) -> None:
        """Invalidate all cached results for space."""
```

### 6.2 Performance Requirements

- **Authorization latency:** <5ms p95 for cached results
- **MLS encryption:** <10ms p95 for 1KB payload
- **Cross-space consent check:** <50ms p95
- **Bulk operation rate limiting:** 1000 ops/second per actor

## 7. Integration Points

### 7.1 Policy Integration

```python
from policy import RbacEngine, AbacEngine, ConsentStore

class StoragePolicyIntegration:
    def __init__(
        self,
        rbac: RbacEngine,
        abac: AbacEngine,
        consent: ConsentStore
    ):
        self.rbac = rbac
        self.abac = abac
        self.consent = consent

    async def evaluate_storage_policy(
        self,
        context: SpaceContext,
        operation: str,
        resource: str
    ) -> AuthzResult:
        """Integrate with policy engines for authorization."""
```

### 7.2 Security Module Integration

```python
from security import MLSGroup, Encryptor, KeyManager

class StorageSecurityIntegration:
    def __init__(
        self,
        mls_groups: Dict[str, MLSGroup],
        encryptor: Encryptor,
        key_manager: KeyManager
    ):
        self.mls_groups = mls_groups
        self.encryptor = encryptor
        self.key_manager = key_manager
```

## 8. Testing Requirements

### 8.1 Security Test Suite

```python
def test_space_isolation():
    """Test that spaces are properly isolated."""

def test_band_access_control():
    """Test band-based access restrictions."""

def test_mls_encryption_integration():
    """Test MLS group encryption/decryption."""

def test_cross_space_authorization():
    """Test cross-space projection authorization."""

def test_consent_verification():
    """Test consent verification for projections."""

def test_privilege_escalation_prevention():
    """Test privilege escalation detection."""

def test_bulk_access_detection():
    """Test bulk access pattern detection."""
```

### 8.2 Performance Benchmarks

```python
def benchmark_authorization_latency():
    """Verify <5ms p95 authorization latency."""

def benchmark_encryption_throughput():
    """Verify MLS encryption performance."""

def benchmark_cross_space_operations():
    """Verify cross-space operation performance."""
```

---

**Contract Version:** 1.0
**Next Review:** 2025-12-12
**Security Clearance:** TOP SECRET
**Stakeholders:** Storage Team, Security Team, Policy Team

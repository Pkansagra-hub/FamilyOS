"""
API schemas converted from OpenAPI contract.

All Pydantic models for request/response schemas defined in contracts/api/openapi.v1.yaml
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.networks import HttpUrl

# =============================================================================
# ENUMS
# =============================================================================


class AuthMethod(str, Enum):
    MTLS = "mtls"
    JWT = "jwt"
    API_KEY = "api_key"


class Capability(str, Enum):
    WRITE = "WRITE"
    RECALL = "RECALL"
    PROJECT = "PROJECT"
    SCHEDULE = "SCHEDULE"


class TrustLevel(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"
    BLACK = "black"


class SecurityBand(str, Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    BLACK = "BLACK"


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ALLOW_REDACTED = "ALLOW_REDACTED"


class Obligation(str, Enum):
    REDACT_PII = "REDACT_PII"
    AUDIT_ACCESS = "AUDIT_ACCESS"
    TOMBSTONE_ON_DELETE = "TOMBSTONE_ON_DELETE"
    SYNC_REQUIRED = "SYNC_REQUIRED"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class DsarType(str, Enum):
    EXPORT = "export"
    ERASURE = "erasure"


class SubjectType(str, Enum):
    USER = "user"
    DEVICE = "device"
    AGENT = "agent"


class ProjectMode(str, Enum):
    PROJECT = "project"
    COPY = "copy"


class KeyScope(str, Enum):
    SIGNING = "signing"
    ENCRYPTION = "encryption"
    ALL = "all"


class IndexScope(str, Enum):
    FTS = "fts"
    VECTOR = "vector"
    EMBEDDINGS = "embeddings"
    SEMANTIC = "semantic"
    ALL = "all"


class QoSRouting(str, Enum):
    FAST_PATH = "fast-path"
    GATE_PATH = "gate-path"


# =============================================================================
# CORE MODELS
# =============================================================================


class Problem(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs"""

    model_config = ConfigDict(extra="forbid")

    type: HttpUrl
    title: str
    status: int = Field(..., ge=100, le=599)
    detail: Optional[str] = None
    instance: Optional[HttpUrl] = None
    trace_id: Optional[str] = Field(None, alias="traceId", pattern=r"^[a-f0-9]{32}$")


class SecurityContext(BaseModel):
    """Security context for authenticated requests"""

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(..., description="User identifier - UUID or username")
    device_id: str = Field(..., pattern=r"^[A-Za-z0-9._:-]{3,64}$")
    authenticated: bool
    auth_method: Optional[AuthMethod] = None
    capabilities: Optional[List[Capability]] = None
    mls_group: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9._:-]{3,64}$")
    trust_level: Optional[TrustLevel] = None

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user ID format - accepts UUID or alphanumeric username"""
        if not v:
            raise ValueError("user_id cannot be empty")

        # Allow UUID format
        try:
            UUID(v)
            return v
        except ValueError:
            pass

        # Allow alphanumeric usernames (for dev mode and policy lookups)
        if re.match(r"^[A-Za-z0-9._-]{2,64}$", v):
            return v

        raise ValueError(
            "user_id must be a valid UUID or alphanumeric username (2-64 chars, a-z, A-Z, 0-9, ., _, - allowed)"
        )

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v: str) -> str:
        """Validate device ID format and content"""
        if not re.match(r"^[A-Za-z0-9._:-]{3,64}$", v):
            raise ValueError(
                "device_id must be 3-64 characters, alphanumeric with ._:- allowed"
            )

        # Additional business logic validation
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("device_id cannot start or end with hyphen")

        return v

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(
        cls, v: Optional[List[Capability]]
    ) -> Optional[List[Capability]]:
        """Validate capabilities list for duplicates and consistency"""
        if v is None:
            return v

        # Remove duplicates while preserving order
        seen: set[Capability] = set()
        unique_caps: List[Capability] = []
        for cap in v:
            if cap not in seen:
                seen.add(cap)
                unique_caps.append(cap)

        return unique_caps

    @model_validator(mode="after")
    def validate_security_context_consistency(self) -> "SecurityContext":
        """Cross-field validation for security context consistency"""
        if self.authenticated:
            if self.auth_method is None:
                raise ValueError("auth_method is required when authenticated=True")

            # For mTLS authentication, device_id and mls_group should be consistent
            if self.auth_method == AuthMethod.MTLS and self.mls_group is not None:
                # Basic consistency check - device_id should be related to mls_group
                if not any(char.isalnum() for char in self.device_id):
                    raise ValueError("Invalid device_id format for mTLS authentication")

        # Trust level and capabilities consistency
        if self.trust_level == TrustLevel.BLACK and self.capabilities:
            raise ValueError("BLACK trust level should not have capabilities")

        return self


class QoSHeaders(BaseModel):
    """Quality of Service headers contract"""

    model_config = ConfigDict(extra="forbid")

    priority: Optional[int] = Field(None, ge=1, le=10)
    latency_budget_ms: Optional[int] = Field(None, ge=1, le=1000)
    deadline_ms: Optional[int] = Field(None, ge=1)
    retries: Optional[int] = Field(None, ge=0, le=3)
    routing: Optional[QoSRouting] = None


class QoSConfig(BaseModel):
    """QoS configuration for requests"""

    model_config = ConfigDict(extra="forbid")

    priority: Optional[int] = Field(None, ge=1, le=10)
    latency_budget_ms: Optional[int] = Field(None, ge=1, le=1000)
    retries: Optional[int] = Field(None, ge=0, le=3)


class PolicyDecisionResponse(BaseModel):
    """Policy middleware decision response"""

    model_config = ConfigDict(extra="forbid")

    decision: PolicyDecision
    reasons: List[str]
    obligations: Optional[List[Obligation]] = None
    band: Optional[SecurityBand] = None

    @field_validator("reasons")
    @classmethod
    def validate_reasons(cls, v: List[str]) -> List[str]:
        """Validate policy decision reasons"""
        if not v:
            raise ValueError(
                "At least one reason must be provided for policy decisions"
            )

        # Remove empty reasons and duplicates while preserving order
        seen: set[str] = set()
        valid_reasons: List[str] = []

        for reason in v:
            reason = reason.strip()
            if reason and reason not in seen:
                seen.add(reason)
                valid_reasons.append(reason)

        if not valid_reasons:
            raise ValueError("All reasons are empty after validation")

        # Limit reason length
        for reason in valid_reasons:
            if len(reason) > 500:
                raise ValueError("Individual reason cannot exceed 500 characters")

        return valid_reasons

    @field_validator("obligations")
    @classmethod
    def validate_obligations(
        cls, v: Optional[List[Obligation]]
    ) -> Optional[List[Obligation]]:
        """Validate policy obligations"""
        if v is None:
            return v

        # Remove duplicates while preserving order
        seen: set[Obligation] = set()
        unique_obligations: List[Obligation] = []

        for obligation in v:
            if obligation not in seen:
                seen.add(obligation)
                unique_obligations.append(obligation)

        return unique_obligations

    @model_validator(mode="after")
    def validate_policy_decision_consistency(self) -> "PolicyDecisionResponse":
        """Cross-field validation for policy decision consistency"""
        # DENY decisions should have clear reasons
        if self.decision == PolicyDecision.DENY and len(self.reasons) < 1:
            raise ValueError("DENY decisions must have detailed reasons")

        # ALLOW_REDACTED must have redaction obligations
        if self.decision == PolicyDecision.ALLOW_REDACTED:
            if not self.obligations or Obligation.REDACT_PII not in self.obligations:
                raise ValueError(
                    "ALLOW_REDACTED decisions must include REDACT_PII obligation"
                )

        # Band consistency with decision
        if self.band:
            if self.decision == PolicyDecision.DENY and self.band in [
                SecurityBand.GREEN,
                SecurityBand.AMBER,
            ]:
                raise ValueError(
                    "DENY decisions with GREEN/AMBER bands are inconsistent"
                )

            if (
                self.decision == PolicyDecision.ALLOW
                and self.band == SecurityBand.BLACK
            ):
                raise ValueError("ALLOW decisions with BLACK band are inconsistent")

        # Obligations consistency
        if self.obligations:
            # SYNC_REQUIRED should only be with shared/extended spaces
            if Obligation.SYNC_REQUIRED in self.obligations:
                # This validation would need context about the space_id from the request
                # For now, just ensure it's with appropriate decisions
                if self.decision == PolicyDecision.DENY:
                    raise ValueError(
                        "SYNC_REQUIRED obligation incompatible with DENY decision"
                    )

        return self


# =============================================================================
# MEMORY MANAGEMENT SCHEMAS
# =============================================================================


class SubmitRequest(BaseModel):
    """Request to submit new memory content"""

    model_config = ConfigDict(extra="forbid")

    space_id: str = Field(
        ..., pattern=r"^(personal|selective|shared|extended|interfamily):"
    )
    text: Optional[str] = None
    attachments: Optional[List[HttpUrl]] = None
    payload: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9._:-]{8,64}$")
    qos: Optional[QoSConfig] = None

    @field_validator("space_id")
    @classmethod
    def validate_space_id(cls, v: str) -> str:
        """Validate space_id format and business rules"""
        # Basic pattern validation is already done by Field pattern

        # Extract space type and suffix
        if ":" not in v:
            raise ValueError("space_id must contain a colon separator")

        space_type, suffix = v.split(":", 1)

        # Validate space type
        valid_types = {"personal", "selective", "shared", "extended", "interfamily"}
        if space_type not in valid_types:
            raise ValueError(
                f"Invalid space type: {space_type}. Must be one of {valid_types}"
            )

        # Validate suffix is not empty
        if not suffix:
            raise ValueError("space_id suffix cannot be empty")

        # Additional validation for specific space types
        if space_type == "personal" and not suffix.isalnum():
            raise ValueError("personal space suffix must be alphanumeric")

        return v

    @field_validator("text")
    @classmethod
    def validate_text_content(cls, v: Optional[str]) -> Optional[str]:
        """Validate text content for length and safety"""
        if v is None:
            return v

        # Trim whitespace
        v = v.strip()

        # Minimum length check
        if len(v) < 1:
            return None  # Convert empty string to None

        # Maximum length check
        if len(v) > 1_000_000:  # 1MB text limit
            raise ValueError("text content exceeds maximum length of 1MB")

        # Basic content safety check
        if "\x00" in v:
            raise ValueError("text content cannot contain null bytes")

        return v

    @field_validator("attachments")
    @classmethod
    def validate_attachments(
        cls, v: Optional[List[HttpUrl]]
    ) -> Optional[List[HttpUrl]]:
        """Validate attachment URLs and limits"""
        if v is None:
            return v

        # Maximum number of attachments
        if len(v) > 100:
            raise ValueError("Maximum 100 attachments allowed per submission")

        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique_attachments: List[HttpUrl] = []
        for url in v:
            url_str = str(url)
            if url_str not in seen:
                seen.add(url_str)
                unique_attachments.append(url)

        return unique_attachments

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate payload structure and size"""
        if v is None:
            return v

        # Basic size limit (rough estimation)
        import json

        try:
            payload_str = json.dumps(v)
            if len(payload_str) > 10_000_000:  # 10MB limit
                raise ValueError("payload exceeds maximum size of 10MB")
        except (TypeError, ValueError) as e:
            raise ValueError(f"payload is not JSON serializable: {e}")

        # Prevent certain problematic keys
        forbidden_keys = {"__proto__", "constructor", "prototype"}
        if any(key in forbidden_keys for key in v.keys()):
            raise ValueError("payload contains forbidden keys")

        return v

    @model_validator(mode="after")
    def validate_submit_request_consistency(self) -> "SubmitRequest":
        """Cross-field validation for submit request"""
        # Must have either text or attachments or payload
        if not any([self.text, self.attachments, self.payload]):
            raise ValueError(
                "Must provide at least one of: text, attachments, or payload"
            )

        # QoS validation based on content size
        if self.qos and self.qos.latency_budget_ms:
            content_size = 0
            if self.text:
                content_size += len(self.text)
            if self.attachments:
                content_size += len(self.attachments) * 100  # Rough estimate

            # Large content should have higher latency budget
            if content_size > 100_000 and self.qos.latency_budget_ms < 200:
                raise ValueError("Large content requires latency_budget_ms >= 200ms")

        return self


class SubmitAccepted(BaseModel):
    """Response when memory submission is accepted"""

    status: str = Field(..., pattern="^accepted$")
    envelope_id: str
    receipt_url: Optional[HttpUrl] = None


class WriteReceipt(BaseModel):
    """Receipt confirming write completion"""

    envelope_id: str
    committed: bool
    stores: List[Dict[str, Any]]


class RecallFilters(BaseModel):
    """Filters for memory recall queries"""

    model_config = ConfigDict(extra="forbid")

    after: Optional[datetime] = None
    before: Optional[datetime] = None
    topics: Optional[List[str]] = None
    bands: Optional[List[SecurityBand]] = None


class RecallRequest(BaseModel):
    """Request to recall memories"""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)
    space_id: Optional[str] = Field(
        None, pattern=r"^(personal|selective|shared|extended|interfamily):"
    )
    k: Optional[int] = Field(10, ge=1, le=200)
    filters: Optional[RecallFilters] = None
    return_trace: Optional[bool] = False
    qos: Optional[QoSConfig] = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate search query content and format"""
        # Trim whitespace
        v = v.strip()

        # Length checks
        if len(v) < 1:
            raise ValueError("query cannot be empty after trimming")

        if len(v) > 10_000:
            raise ValueError("query exceeds maximum length of 10,000 characters")

        # Basic safety checks
        if "\x00" in v:
            raise ValueError("query cannot contain null bytes")

        # Prevent potential injection attacks
        dangerous_patterns = ["<script", "javascript:", "data:text/html"]
        query_lower = v.lower()
        if any(pattern in query_lower for pattern in dangerous_patterns):
            raise ValueError("query contains potentially dangerous content")

        return v

    @field_validator("space_id")
    @classmethod
    def validate_space_id_recall(cls, v: Optional[str]) -> Optional[str]:
        """Validate space_id for recall requests"""
        if v is None:
            return v

        # Reuse the validation logic from SubmitRequest
        if ":" not in v:
            raise ValueError("space_id must contain a colon separator")

        space_type, suffix = v.split(":", 1)
        valid_types = {"personal", "selective", "shared", "extended", "interfamily"}
        if space_type not in valid_types:
            raise ValueError(f"Invalid space type: {space_type}")

        if not suffix:
            raise ValueError("space_id suffix cannot be empty")

        return v

    @field_validator("k")
    @classmethod
    def validate_k_value(cls, v: Optional[int]) -> Optional[int]:
        """Validate the number of results to return"""
        if v is None:
            return 10  # Default value

        # Additional business logic validation
        if v > 100:
            # Warning for large result sets - consider performance implications
            pass  # Allow but could log a warning in real implementation

        return v

    @model_validator(mode="after")
    def validate_recall_request_consistency(self) -> "RecallRequest":
        """Cross-field validation for recall request"""
        # Adjust k based on QoS settings
        if self.qos and self.qos.latency_budget_ms:
            if self.qos.latency_budget_ms < 100 and self.k and self.k > 50:
                raise ValueError(
                    "Low latency budget requires k <= 50 for optimal performance"
                )

        # Validate filters consistency
        if self.filters and self.filters.after and self.filters.before:
            if self.filters.after >= self.filters.before:
                raise ValueError("filters.after must be before filters.before")

        # Large result sets with complex filters may need higher latency budget
        if (
            self.k
            and self.k > 100
            and self.filters
            and (self.filters.topics or self.filters.bands)
            and self.qos
            and self.qos.latency_budget_ms
            and self.qos.latency_budget_ms < 200
        ):
            raise ValueError(
                "Large result sets with filters require latency_budget_ms >= 200ms"
            )

        return self


class RecallItem(BaseModel):
    """Individual recalled memory item"""

    id: str
    score: float = Field(..., ge=0)
    topic: Optional[str] = None
    band: Optional[SecurityBand] = None
    snippet: Optional[str] = None
    space_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class RecallTrace(BaseModel):
    """Trace information for recall debugging"""

    features: Optional[List[str]] = None
    fusion: Optional[Dict[str, Any]] = None
    ranker: Optional[Dict[str, Any]] = None


class RecallResponse(BaseModel):
    """Response containing recalled memories"""

    items: List[RecallItem]
    trace: Optional[RecallTrace] = None


# =============================================================================
# SHARING SCHEMAS
# =============================================================================


class ProjectRequest(BaseModel):
    """Request to project memory to shared space"""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    target_space_id: str = Field(
        ..., pattern=r"^(personal|selective|shared|extended|interfamily):"
    )
    mode: Optional[ProjectMode] = None
    comment: Optional[str] = Field(None, max_length=512)


class ProjectAccepted(BaseModel):
    """Response when projection is accepted"""

    link_group_id: str
    status: str = Field(..., pattern="^accepted$")


class ReferFilters(BaseModel):
    """Filters for reference requests"""

    model_config = ConfigDict(extra="forbid")

    bands: Optional[List[SecurityBand]] = None


class ReferRequest(BaseModel):
    """Request to reference existing memory"""

    source_id: str
    filters: Optional[ReferFilters] = None


class ReferResponse(BaseModel):
    """Response with referenced memory content"""

    resolved: Optional[bool] = None
    payload: Optional[Dict[str, Any]] = None


class DetachRequest(BaseModel):
    """Request to detach memory from space"""

    source_id: str
    target_space_id: Optional[str] = Field(
        None, pattern=r"^(personal|selective|shared|extended|interfamily):"
    )


class UndoShareRequest(BaseModel):
    """Request to undo sharing operation"""

    link_group_id: str


# =============================================================================
# PRIVACY & DSAR SCHEMAS
# =============================================================================


class DsarSubject(BaseModel):
    """Subject of DSAR request"""

    model_config = ConfigDict(extra="forbid")

    user_id: Optional[UUID] = None
    space_id: Optional[str] = Field(
        None, pattern=r"^(personal|selective|shared|extended|interfamily):"
    )


class DsarFilters(BaseModel):
    """Filters for DSAR requests"""

    model_config = ConfigDict(extra="forbid")

    after: Optional[datetime] = None
    before: Optional[datetime] = None


class DsarRequest(BaseModel):
    """Data Subject Access Request"""

    model_config = ConfigDict(extra="forbid")

    type: DsarType
    subject: DsarSubject
    filters: Optional[DsarFilters] = None


# =============================================================================
# JOB MANAGEMENT SCHEMAS
# =============================================================================


class JobAccepted(BaseModel):
    """Response when job is accepted"""

    job_id: str
    status: JobStatus
    status_url: Optional[HttpUrl] = None


class JobStatusResponse(BaseModel):
    """Job status response"""

    job_id: str
    status: JobStatus
    result_url: Optional[HttpUrl] = None
    error: Optional[Problem] = None


# =============================================================================
# SECURITY & ENCRYPTION SCHEMAS
# =============================================================================


class MlsJoinRequest(BaseModel):
    """Request to join MLS group"""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(..., min_length=3, max_length=64)
    public_key: str = Field(..., description="Base64 encoded public key")

    @field_validator("device_id")
    @classmethod
    def validate_device_id_mls(cls, v: str) -> str:
        """Validate device ID for MLS group joining"""
        # Basic pattern check
        if not re.match(r"^[A-Za-z0-9._:-]+$", v):
            raise ValueError(
                "device_id can only contain alphanumeric characters and ._:-"
            )

        # Cannot start/end with special characters
        if v.startswith((".", "_", ":", "-")) or v.endswith((".", "_", ":", "-")):
            raise ValueError("device_id cannot start or end with special characters")

        return v

    @field_validator("public_key")
    @classmethod
    def validate_public_key(cls, v: str) -> str:
        """Validate base64 encoded public key format"""
        import base64

        try:
            # Try to decode to validate base64 format
            decoded = base64.b64decode(v, validate=True)

            # Basic length checks for common key types
            key_len = len(decoded)

            if key_len < 32:
                raise ValueError("public key too short (minimum 32 bytes)")

            if key_len > 1024:
                raise ValueError("public key too long (maximum 1024 bytes)")

        except Exception as e:
            raise ValueError(f"Invalid base64 encoded public key: {e}")

        return v


class MlsJoinResponse(BaseModel):
    """Response to MLS join request"""

    group_id: str
    device_id: str
    epoch: int = Field(..., ge=0)
    welcome: Optional[str] = Field(None, description="Base64 encoded welcome message")


class KeyRotateRequest(BaseModel):
    """Request to rotate cryptographic keys"""

    scope: KeyScope


class RatchetAdvanceRequest(BaseModel):
    """Request to advance MLS ratchet"""

    group_id: str
    device_id: str


# =============================================================================
# INDEX REBUILD SCHEMAS
# =============================================================================


class IndexRebuildRequest(BaseModel):
    """Request to rebuild search indices"""

    model_config = ConfigDict(extra="forbid")

    scope: IndexScope
    shard_ids: Optional[List[str]] = None
    resume_from_checkpoint: Optional[bool] = True


# =============================================================================
# REGISTRY SCHEMAS
# =============================================================================


class ToolInfo(BaseModel):
    """Information about a registered tool"""

    id: str
    name: str
    caps: Optional[List[str]] = None


class ToolsList(BaseModel):
    """List of registered tools"""

    items: Optional[List[ToolInfo]] = None


class PromptInfo(BaseModel):
    """Information about a registered prompt"""

    id: str
    name: str
    content: Optional[str] = None


class PromptsList(BaseModel):
    """List of registered prompts"""

    items: Optional[List[PromptInfo]] = None


# =============================================================================
# RBAC SCHEMAS
# =============================================================================


class RoleInfo(BaseModel):
    """Information about a role"""

    name: str
    caps: Optional[List[str]] = None


class RolesList(BaseModel):
    """List of roles"""

    items: Optional[List[RoleInfo]] = None


class RoleBindingSubject(BaseModel):
    """Subject for role binding"""

    type: SubjectType
    id: str


class RoleBinding(BaseModel):
    """Role binding assignment"""

    role: str
    subject: RoleBindingSubject


# =============================================================================
# SYNC SCHEMAS
# =============================================================================


class PeerRegister(BaseModel):
    """Request to register sync peer"""

    peer_id: str
    url: HttpUrl


class SyncPeerInfo(BaseModel):
    """Information about sync peer"""

    peer_id: str
    lag_seconds: float = Field(..., ge=0)


class SyncStatus(BaseModel):
    """Synchronization status"""

    window_seconds: float = Field(..., ge=0)
    peers: List[SyncPeerInfo]


# =============================================================================
# FEATURE FLAGS SCHEMAS
# =============================================================================


class FlagInfo(BaseModel):
    """Information about a feature flag"""

    key: str
    enabled: bool


class FlagsList(BaseModel):
    """List of feature flags"""

    items: Optional[List[FlagInfo]] = None


# =============================================================================
# EVENT ENVELOPE SCHEMAS
# =============================================================================


class EventTopic(str, Enum):
    """Event topic enumeration from envelope schema"""

    HIPPO_ENCODE = "HIPPO_ENCODE"
    HIPPO_ENCODED = "HIPPO_ENCODED"
    WORKSPACE_BROADCAST = "WORKSPACE_BROADCAST"
    SENSORY_FRAME = "SENSORY_FRAME"
    RECALL_REQUEST = "RECALL_REQUEST"
    RECALL_RESULT = "RECALL_RESULT"
    PROSPECTIVE_SCHEDULE = "PROSPECTIVE_SCHEDULE"
    REMIND_TICK = "REMIND_TICK"
    ACTION_DECISION = "ACTION_DECISION"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    LEARNING_TICK = "LEARNING_TICK"
    AFFECT_ANALYZE = "AFFECT_ANALYZE"
    AFFECT_UPDATE = "AFFECT_UPDATE"
    DRIVE_TICK = "DRIVE_TICK"
    METACOG_REPORT = "METACOG_REPORT"
    BELIEF_UPDATE = "BELIEF_UPDATE"
    DSAR_EXPORT = "DSAR_EXPORT"
    REINDEX_REQUEST = "REINDEX_REQUEST"
    ML_RUN_EVENT = "ML_RUN_EVENT"
    WORKFLOW_UPDATE = "WORKFLOW_UPDATE"
    PII_MINIMIZED = "PII_MINIMIZED"
    TOMBSTONE_APPLIED = "TOMBSTONE_APPLIED"
    SAFETY_ALERT = "SAFETY_ALERT"
    JOB_STATUS_CHANGED = "JOB_STATUS_CHANGED"
    MEMORY_RECEIPT_CREATED = "MEMORY_RECEIPT_CREATED"
    INTEGRATION_THING_CHANGED = "INTEGRATION_THING_CHANGED"
    PRESENCE_DEVICE_CHANGED = "PRESENCE_DEVICE_CHANGED"
    SAFETY_BAND_CHANGED = "SAFETY_BAND_CHANGED"
    PROSPECTIVE_REMIND_TICK = "PROSPECTIVE_REMIND_TICK"
    TOMBSTONE_PROPAGATE = "TOMBSTONE_PROPAGATE"


class Platform(str, Enum):
    """Device platform enumeration"""

    IOS = "ios"
    ANDROID = "android"
    MACOS = "macos"
    WINDOWS = "windows"
    LINUX = "linux"
    WEB = "web"
    EDGE = "edge"


class Role(str, Enum):
    """ABAC role enumeration"""

    PARENT = "parent"
    CHILD = "child"
    GUEST = "guest"
    SYSTEM = "system"
    SERVICE = "service"


class GeoPrecision(str, Enum):
    """Geographic precision levels"""

    CITY = "city"
    REGION = "region"


class SignatureAlgorithm(str, Enum):
    """Signature algorithm enumeration"""

    ED25519 = "ed25519"
    ECDSA_P256 = "ecdsa_p256"


class EnvelopeActor(BaseModel):
    """Actor information in event envelope"""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    agent_id: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9._:-]{3,64}$")
    caps: List[Capability] = Field(..., min_length=1)

    @field_validator("caps")
    @classmethod
    def validate_caps_unique(cls, v: List[Capability]) -> List[Capability]:
        """Ensure capabilities are unique"""
        return list(dict.fromkeys(v))  # Remove duplicates while preserving order


class EnvelopeDevice(BaseModel):
    """Device information in event envelope"""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(..., pattern=r"^[A-Za-z0-9._:-]{3,64}$")
    platform: Optional[Platform] = None
    app_version: Optional[str] = Field(
        None, pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-.]+)?$"
    )
    locale: Optional[str] = Field(None, pattern=r"^[A-Za-z]{2}(-[A-Za-z]{2})?$")


class EnvelopeABAC(BaseModel):
    """ABAC attributes in event envelope"""

    model_config = ConfigDict(extra="forbid")

    role: Optional[Role] = None
    trust: Optional[TrustLevel] = None
    geo_precision: Optional[GeoPrecision] = None


class EnvelopeQoS(BaseModel):
    """QoS configuration in event envelope"""

    model_config = ConfigDict(extra="forbid")

    routing: Optional[QoSRouting] = QoSRouting.GATE_PATH
    priority: int = Field(..., ge=1, le=10)
    latency_budget_ms: int = Field(..., ge=1, le=1000)
    retries: Optional[int] = Field(None, ge=0, le=3)
    deadline_ms: Optional[int] = Field(None, ge=1)


class EnvelopeTrace(BaseModel):
    """Tracing information in event envelope"""

    model_config = ConfigDict(extra="forbid")

    trace_id: Optional[str] = Field(None, pattern=r"^[a-f0-9]{32}$")
    span_id: Optional[str] = Field(None, pattern=r"^[a-f0-9]{16}$")
    parent_span_id: Optional[str] = Field(None, pattern=r"^[a-f0-9]{16}$")
    sampled: Optional[bool] = True


class EnvelopeHashes(BaseModel):
    """Hash values in event envelope"""

    model_config = ConfigDict(extra="forbid")

    payload_sha256: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    envelope_sha256: Optional[str] = Field(None, pattern=r"^[a-f0-9]{64}$")
    prev_event_id: Optional[str] = None  # UUID or ULID
    merkle_root: Optional[str] = Field(None, pattern=r"^[a-f0-9]{64}$")

    @field_validator("prev_event_id")
    @classmethod
    def validate_prev_event_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate prev_event_id as UUID or ULID"""
        if v is None:
            return v

        # Try UUID format first
        try:
            UUID(v)
            return v
        except ValueError:
            pass

        # Try ULID format (Crockford base32)
        if re.match(r"^[0-7][0-9A-HJKMNP-TV-Z]{25}$", v):
            return v

        raise ValueError("prev_event_id must be a valid UUID or ULID")


class EnvelopeSignature(BaseModel):
    """Signature information in event envelope"""

    model_config = ConfigDict(extra="forbid")

    alg: SignatureAlgorithm
    key_id: str = Field(..., pattern=r"^[A-Za-z0-9._:-]{8,128}$")
    public_key: Optional[str] = Field(None, description="Base64 encoded public key")
    signature: str = Field(..., description="Base64 encoded signature")

    @field_validator("public_key", "signature")
    @classmethod
    def validate_base64_fields(cls, v: Optional[str]) -> Optional[str]:
        """Validate base64 encoded fields"""
        if v is None:
            return v

        import base64

        try:
            base64.b64decode(v, validate=True)
            return v
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {e}")


class Envelope(BaseModel):
    """
    Canonical Event Envelope schema

    This represents the validated envelope format used by all modules
    and pipelines (P01-P20) with strict validation at bus ingress.
    """

    model_config = ConfigDict(extra="forbid")

    # Required fields
    schema_version: str = Field(
        ...,
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$",
    )
    id: str  # UUID or ULID
    ts: datetime
    topic: str  # EventTopic or name@semver format
    actor: EnvelopeActor
    device: EnvelopeDevice
    space_id: str = Field(
        ...,
        pattern=r"^(personal|selective|shared|extended|interfamily):[A-Za-z0-9_\-.]+$",
    )
    band: SecurityBand
    policy_version: str = Field(
        ..., pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?$"
    )
    qos: EnvelopeQoS
    hashes: EnvelopeHashes
    payload: Dict[str, Any]
    signature: EnvelopeSignature

    # Optional fields
    ingest_ts: Optional[datetime] = None
    abac: Optional[EnvelopeABAC] = None
    mls_group: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9._:-]{3,64}$")
    trace: Optional[EnvelopeTrace] = None
    obligations: List[Obligation] = Field(default_factory=list)
    redaction_applied: bool = False
    idempotency_key: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9._:-]{8,64}$")
    x_extensions: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_envelope_id(cls, v: str) -> str:
        """Validate envelope ID as UUID or ULID"""
        # Try UUID format first
        try:
            UUID(v)
            return v
        except ValueError:
            pass

        # Try ULID format (Crockford base32)
        if re.match(r"^[0-7][0-9A-HJKMNP-TV-Z]{25}$", v):
            return v

        raise ValueError("id must be a valid UUID or ULID")

    @field_validator("topic")
    @classmethod
    def validate_envelope_topic(cls, v: str) -> str:
        """Validate topic as enum value or name@semver format"""
        # Check if it's a standard topic
        try:
            EventTopic(v)
            return v
        except ValueError:
            pass

        # Check if it's name@semver format
        if re.match(r"^[A-Z][A-Z0-9_]+@[0-9]+\.[0-9]+$", v):
            return v

        raise ValueError("topic must be a valid EventTopic or name@semver format")

    @field_validator("x_extensions")
    @classmethod
    def validate_extensions(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extension keys are properly namespaced"""
        for key in v.keys():
            if not re.match(r"^x_[A-Za-z0-9][A-Za-z0-9_]*$", key):
                raise ValueError(
                    f"Extension key '{key}' must start with 'x_' and be properly formatted"
                )
        return v

    @model_validator(mode="after")
    def validate_envelope_consistency(self) -> "Envelope":
        """Cross-field validation for envelope consistency"""

        # AMBER/RED/BLACK bands require mls_group
        if self.band in [SecurityBand.AMBER, SecurityBand.RED, SecurityBand.BLACK]:
            if not self.mls_group:
                raise ValueError(f"{self.band} band requires mls_group")

            # Must have redaction applied OR redaction obligation
            if (
                not self.redaction_applied
                and Obligation.REDACT_PII not in self.obligations
            ):
                raise ValueError(
                    f"{self.band} band requires redaction_applied=True or REDACT_PII obligation"
                )

        # Topic-specific obligation requirements
        if self.topic == EventTopic.TOMBSTONE_APPLIED:
            if Obligation.TOMBSTONE_ON_DELETE not in self.obligations:
                raise ValueError(
                    "TOMBSTONE_APPLIED topic requires TOMBSTONE_ON_DELETE obligation"
                )

        if self.topic == EventTopic.DSAR_EXPORT:
            if Obligation.AUDIT_ACCESS not in self.obligations:
                raise ValueError("DSAR_EXPORT topic requires AUDIT_ACCESS obligation")

        if self.topic == EventTopic.JOB_STATUS_CHANGED:
            if self.band not in [SecurityBand.GREEN, SecurityBand.AMBER]:
                raise ValueError(
                    "JOB_STATUS_CHANGED topic requires GREEN or AMBER band"
                )

        if self.topic == EventTopic.MEMORY_RECEIPT_CREATED:
            if Obligation.AUDIT_ACCESS not in self.obligations:
                raise ValueError(
                    "MEMORY_RECEIPT_CREATED topic requires AUDIT_ACCESS obligation"
                )

        return self


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def validate_space_id_prefix(space_id: str) -> str:
    """Validate space_id format"""
    if not space_id.startswith(
        ("personal:", "selective:", "shared:", "extended:", "interfamily:")
    ):
        raise ValueError("space_id must start with valid space type prefix")
    return space_id


def validate_trace_id_format(trace_id: str) -> str:
    """Validate X-Trace-Id header format"""
    if not re.match(r"^[a-f0-9]{32}$", trace_id):
        raise ValueError("trace_id must be a 32-character lowercase hex string")
    return trace_id


def validate_policy_version_format(version: str) -> str:
    """Validate X-Policy-Version header format (semver)"""
    semver_pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?$"
    if not re.match(semver_pattern, version):
        raise ValueError("policy version must follow semantic versioning format")
    return version


def validate_device_capabilities_compatibility(
    device_id: str, capabilities: List[Capability], trust_level: TrustLevel
) -> bool:
    """Validate that device capabilities are compatible with trust level"""

    # BLACK trust level devices should have no capabilities
    if trust_level == TrustLevel.BLACK and capabilities:
        return False

    # RED trust level devices should have limited capabilities
    if trust_level == TrustLevel.RED:
        allowed_red_caps = {Capability.RECALL}
        if not set(capabilities).issubset(allowed_red_caps):
            return False

    # AMBER trust level can have most capabilities except PROJECT
    if trust_level == TrustLevel.AMBER:
        restricted_amber_caps = {Capability.PROJECT}
        if set(capabilities).intersection(restricted_amber_caps):
            return False

    # GREEN trust level can have all capabilities
    return True


def validate_qos_budget_realistic(
    operation: str, latency_budget_ms: int, content_size_estimate: int = 0
) -> bool:
    """Validate that QoS latency budget is realistic for operation"""

    # Minimum budgets by operation type
    min_budgets = {
        "submit": 50,  # Write operations
        "recall": 80,  # Read operations
        "project": 100,  # Sharing operations
        "encrypt": 10,  # Encryption operations
        "index": 200,  # Index rebuild operations
    }

    min_budget = min_budgets.get(operation, 50)

    # Adjust for content size
    if content_size_estimate > 100_000:  # 100KB+
        min_budget += 50
    if content_size_estimate > 1_000_000:  # 1MB+
        min_budget += 100

    return latency_budget_ms >= min_budget


def validate_space_transition_allowed(
    source_space: str, target_space: str, user_capabilities: List[Capability]
) -> bool:
    """Validate that space transition is allowed based on user capabilities"""

    # Extract space types
    source_type = source_space.split(":")[0] if ":" in source_space else source_space
    target_type = target_space.split(":")[0] if ":" in target_space else target_space

    # Personal to any space requires PROJECT capability
    if source_type == "personal" and target_type != "personal":
        return Capability.PROJECT in user_capabilities

    # Any space to interfamily requires special permissions
    if target_type == "interfamily":
        return Capability.PROJECT in user_capabilities

    # Most other transitions are allowed
    return True


def validate_memory_content_safety(
    text: Optional[str] = None, payload: Optional[Dict[str, Any]] = None
) -> List[str]:
    """
    Validate memory content for safety and policy compliance.
    Returns list of warnings/issues found.
    """
    issues: List[str] = []

    if text:
        # Check for potentially sensitive patterns
        sensitive_patterns = [
            (
                r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
                "potential credit card number",
            ),
            (r"\b\d{3}-\d{2}-\d{4}\b", "potential SSN"),
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email address"),
            (
                r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
                "phone number",
            ),
        ]

        for pattern, description in sensitive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(f"Detected {description} in text content")

    if payload:
        # Check for sensitive keys in payload
        sensitive_keys = {"password", "secret", "token", "key", "credential", "auth"}
        payload_keys = set(str(k).lower() for k in payload.keys())

        for sensitive_key in sensitive_keys:
            if any(sensitive_key in key for key in payload_keys):
                issues.append(
                    f"Potentially sensitive key detected in payload: {sensitive_key}"
                )

    return issues


def validate_mls_group_consistency(
    device_id: str, mls_group: str, public_key: str
) -> bool:
    """Validate MLS group membership consistency"""

    # Basic format checks
    if not device_id or not mls_group or not public_key:
        return False

    # Device ID should be compatible with MLS group naming
    # This is a simplified check - real implementation would verify cryptographic consistency
    if len(device_id) < 3 or len(mls_group) < 3:
        return False

    # Public key should be valid base64
    import base64

    try:
        decoded_key = base64.b64decode(public_key, validate=True)
        if len(decoded_key) < 32:  # Minimum key size
            return False
    except Exception:
        return False

    return True


# =============================================================================
# SCHEMA REGISTRY AND FACTORY FUNCTIONS
# =============================================================================


def get_request_schema(operation_id: str) -> Optional[type[BaseModel]]:
    """Get the appropriate request schema for an operation"""
    schema_mapping: Dict[str, type[BaseModel]] = {
        "submitMemory": SubmitRequest,
        "recallMemory": RecallRequest,
        "projectMemory": ProjectRequest,
        "referMemory": ReferRequest,
        "detachCopy": DetachRequest,
        "undoShare": UndoShareRequest,
        "createDsar": DsarRequest,
        "joinMlsGroup": MlsJoinRequest,
        "rotateKeys": KeyRotateRequest,
        "advanceRatchet": RatchetAdvanceRequest,
        "rebuildIndex": IndexRebuildRequest,
        "registerPeer": PeerRegister,
        "upsertBinding": RoleBinding,
    }
    return schema_mapping.get(operation_id)


def get_response_schema(operation_id: str) -> Optional[type[BaseModel]]:
    """Get the appropriate response schema for an operation"""
    schema_mapping: Dict[str, type[BaseModel]] = {
        "submitMemory": SubmitAccepted,
        "recallMemory": RecallResponse,
        "projectMemory": ProjectAccepted,
        "referMemory": ReferResponse,
        "detachCopy": ProjectAccepted,
        "createDsar": JobAccepted,
        "getDsarStatus": JobStatusResponse,
        "joinMlsGroup": MlsJoinResponse,
        "getReceipt": WriteReceipt,
        "listTools": ToolsList,
        "listPrompts": PromptsList,
        "listRoles": RolesList,
        "syncStatus": SyncStatus,
        "listFlags": FlagsList,
    }
    return schema_mapping.get(operation_id)


def create_problem_response(
    status: int,
    title: str,
    detail: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> Problem:
    """Factory function to create standardized Problem responses"""

    # Map status codes to standard URIs
    type_mapping = {
        400: "https://memoryos.local/problems/bad-request",
        401: "https://memoryos.local/problems/unauthorized",
        403: "https://memoryos.local/problems/forbidden",
        404: "https://memoryos.local/problems/not-found",
        409: "https://memoryos.local/problems/conflict",
        422: "https://memoryos.local/problems/validation-error",
        429: "https://memoryos.local/problems/rate-limited",
        500: "https://memoryos.local/problems/internal-error",
        503: "https://memoryos.local/problems/service-unavailable",
    }

    problem_type = type_mapping.get(status, "https://memoryos.local/problems/unknown")

    return Problem(
        type=HttpUrl(problem_type),
        title=title,
        status=status,
        detail=detail,
        traceId=trace_id,
    )

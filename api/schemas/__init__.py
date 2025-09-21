# Schema package exports
"""
Pydantic schemas for MemoryOS API organized by domain.
"""

# Core schemas
from .core import (
    ActionCapability,
    ActivityLog,
    AuthMethod,
    Capability,
    MemoryItem,
    MemorySpace,
    SecurityBand,
    SecurityContext,
    SpacePolicy,
    TrustLevel,
    UserProfile,
)

# Event schemas
from .events import (
    Envelope,
    MemoryEvent,
    MemoryRecalledEvent,
    MemorySubmittedEvent,
    PolicyEvent,
    SecurityEvent,
    SyncEvent,
)

# Memory schemas (API-level schemas per MMD diagram)
from .memory import (
    MemoryBatch,
    MemoryEnvelope,
    MemoryProjection,
    MemoryReference,
    MemoryResult,
    RecallQuery,
)

# Request/Response schemas
from .requests import (
    ProjectRequest,
    RecallRequest,
    RegisterRequest,
    SubmitRequest,
    SyncRequest,
    UnregisterRequest,
)
from .responses import (
    BatchResponse,
    ErrorResponse,
    HealthResponse,
    ProjectResponse,
    RecallResponse,
    RegisterResponse,
    SubmitResponse,
    SyncResponse,
    UnregisterResponse,
)

# Security schemas
from .security import (
    AccessToken,
    AuthenticationChallenge,
    PermissionScope,
    PolicyDecisionResponse,
    Problem,
    RoleDefinition,
    SecurityAuditLog,
)

# Validation utilities
from .validation import (
    validate_memory_content,
    validate_memory_item,
    validate_query_parameters,
    validate_security_context,
    validate_space_identifier,
    validate_space_policy,
    validate_temporal_bounds,
)

__all__ = [
    # Core
    "SecurityContext",
    "MemoryItem",
    "SpacePolicy",
    "UserProfile",
    "MemorySpace",
    "ActivityLog",
    "ActionCapability",
    "SecurityBand",
    "TrustLevel",
    "Capability",
    # Requests
    "SubmitRequest",
    "RecallRequest",
    "ProjectRequest",
    "RegisterRequest",
    "UnregisterRequest",
    "SyncRequest",
    # Responses
    "SubmitResponse",
    "RecallResponse",
    "ProjectResponse",
    "RegisterResponse",
    "UnregisterResponse",
    "SyncResponse",
    "HealthResponse",
    "ErrorResponse",
    "BatchResponse",
    # Memory API schemas (per MMD diagram)
    "MemoryBatch",
    "MemoryEnvelope",
    "MemoryProjection",
    "MemoryReference",
    "MemoryResult",
    "RecallQuery",
    # Security
    "PolicyDecisionResponse",
    "Problem",
    "AuthenticationChallenge",
    "AccessToken",
    "SecurityAuditLog",
    "PermissionScope",
    "RoleDefinition",
    # Events
    "Envelope",
    "MemoryEvent",
    "MemorySubmittedEvent",
    "MemoryRecalledEvent",
    "PolicyEvent",
    "SecurityEvent",
    "SyncEvent",
    # Validation
    "validate_memory_content",
    "validate_security_context",
    "validate_space_policy",
    "validate_temporal_bounds",
    "validate_space_identifier",
    "validate_query_parameters",
    "validate_memory_item",
]

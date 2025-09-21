"""
Type definitions for enhanced ABAC implementation.
Issue #27: Complete ABAC implementation types

Provides contract-compliant type definitions for the enhanced ABAC system.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Protocol
from dataclasses import dataclass, field

# Core ABAC types
Band = Literal["GREEN", "AMBER", "RED", "BLACK"]
TrustLevel = Literal["untrusted", "trusted", "hardened", "verified"]
NetworkType = Literal["trusted", "untrusted", "cellular", "vpn"]
AuthMethod = Literal["mtls", "jwt", "api_key", "device_cert"]
TemporalContext = Literal["work_hours", "family_time", "sleep_time", "emergency"]
Decision = Literal["ALLOW", "ALLOW_REDACTED", "DENY"]
GeofenceZone = Literal["home", "school", "work", "public", "unknown"]
RelationType = Literal["family", "guardian", "friend", "colleague", "unknown"]
ActorTrustLevel = Literal["low", "normal", "high", "verified"]

# Context types
RequestUrgency = Literal["low", "normal", "high", "emergency"]
RequestPurpose = Literal["learning", "safety", "maintenance", "social", "work", "personal"]
SensitivityLevel = Literal["public", "internal", "confidential", "secret"]
RequestSource = Literal["user_initiated", "system_initiated", "scheduled", "emergency"]
BehaviorPattern = Literal["normal", "unusual", "suspicious", "malicious"]
AccessFrequency = Literal["rarely", "occasionally", "regularly", "frequently"]
SecurityAlertLevel = Literal["normal", "elevated", "high", "critical"]
EmotionalState = Literal["calm", "excited", "stressed", "anxious", "happy"]

# Resource types
ResourceType = Literal["memory", "space", "episodic", "temporal", "capability", "tool", "data"]
ActionType = Literal["read", "write", "delete", "execute", "share", "modify", "create"]

# Obligations dictionary type
ObligationsDict = Dict[str, Any]

# Performance metrics
@dataclass
class PerformanceMetrics:
    """Performance metrics for ABAC operations."""
    total_evaluations: int = 0
    cache_hit_rate: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    average_evaluation_time_ms: float = 0.0
    p95_evaluation_time_ms: float = 0.0
    evaluation_count: int = 0

# Conflict resolution types
@dataclass
class ConflictRecord:
    """Record of a policy conflict and its resolution."""
    timestamp: str
    request_id: str
    conflict_type: str
    conflicting_policies: List[str]
    resolution_strategy: str
    final_decision: Decision
    final_band: Band
    final_obligations: List[str]
    reasoning: str
    confidence_score: float

# Decision context types
@dataclass
class RequestContext:
    """Context information about an access request."""
    resource_type: ResourceType
    action: ActionType
    urgency: RequestUrgency = "normal"
    purpose: Optional[RequestPurpose] = None
    batch_size: int = 1
    sensitive_level: SensitivityLevel = "internal"
    redaction_allowed: bool = True
    request_source: RequestSource = "user_initiated"

@dataclass
class HistoricalContext:
    """Historical access patterns and behavior."""
    recent_access_count: int = 0
    recent_failures: int = 0
    average_session_duration: float = 0.0
    behavior_pattern: BehaviorPattern = "normal"
    last_access_time: Optional[str] = None
    access_frequency: AccessFrequency = "occasionally"
    violation_history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class RealtimeContext:
    """Real-time environmental and system context."""
    system_load: float = 0.0
    network_latency: float = 0.0
    concurrent_users: int = 0
    security_alert_level: SecurityAlertLevel = "normal"
    resource_availability: float = 1.0
    maintenance_mode: bool = False
    peak_usage_hours: bool = False
    affect_state: Optional[Dict[str, Any]] = None

@dataclass
class AffectState:
    """Emotional and affective state information."""
    arousal: float = 0.0
    safety_pressure: float = 0.0
    emotional_state: EmotionalState = "calm"

# Protocol definitions
class SafetyPipeline(Protocol):
    """Protocol for P18 Safety Pipeline integration."""
    
    def assess_context(self, ctx: Any) -> Dict[str, Any]:
        """Assess safety context and return risk assessment."""
        ...
    
    def validate_content(self, content: str, context: Any) -> Dict[str, Any]:
        """Validate content for safety violations."""
        ...
    
    def get_mitigation_actions(self, risk_assessment: Dict[str, Any]) -> List[str]:
        """Get recommended mitigation actions."""
        ...

class CacheBackend(Protocol):
    """Protocol for caching backend."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        ...
    
    def setex(self, key: str, ttl: int, value: Any) -> None:
        """Set cached value with TTL."""
        ...
    
    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set cached value with TTL (alternative signature)."""
        ...

# Enhanced attribute types (contract-compliant)
@dataclass
class ActorAttrs:
    """Actor (user) attributes for ABAC evaluation."""
    actor_id: str
    is_minor: bool = False
    relation: Optional[RelationType] = None
    trust_level: ActorTrustLevel = "normal"
    role: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    space_access: List[str] = field(default_factory=list)
    auth_method: Optional[AuthMethod] = None
    session_id: Optional[str] = None
    user_agent: Optional[str] = None

@dataclass 
class DeviceAttrs:
    """Device attributes for ABAC evaluation."""
    device_id: str
    trust: TrustLevel = "trusted"
    battery_low: bool = False
    cpu_throttled: bool = False
    screen_locked: bool = False
    location_verified: bool = True
    network_type: NetworkType = "trusted"
    mls_group: Optional[str] = None
    device_fingerprint: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    rooted_jailbroken: bool = False

@dataclass
class EnvAttrs:
    """Environmental attributes for ABAC evaluation."""
    time_of_day_hours: float = 12.0
    location: Optional[str] = None
    space_band_min: Optional[Band] = None
    arousal: Optional[float] = None
    safety_pressure: Optional[float] = None
    curfew_hours: Optional[List[int]] = None
    risk_assessment: Optional[Dict[str, float]] = None
    temporal_context: Optional[TemporalContext] = None
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    geofence_zone: Optional[GeofenceZone] = None
    ambient_noise_level: Optional[float] = None
    family_present: bool = True

@dataclass
class AbacContext:
    """Complete ABAC context including all attribute categories."""
    actor: ActorAttrs
    device: DeviceAttrs
    env: EnvAttrs
    request_metadata: Optional[Dict[str, Any]] = None

# Decision outcome types
@dataclass
class ObligationSpec:
    """Specification for a policy obligation."""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    mandatory: bool = False

@dataclass
class DecisionOutcome:
    """Complete decision outcome with obligations and reasoning."""
    decision: Decision
    band: Band
    obligations: List[ObligationSpec] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    confidence_score: float = 1.0
    audit_id: str = ""
    evaluation_time_ms: float = 0.0
    cache_hit: bool = False

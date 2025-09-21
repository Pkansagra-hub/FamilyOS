"""
Attention Gate Types - Future-Ready Type Definitions

Designed for extensibility and learning integration while maintaining
production safety and explainability.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class GateAction(Enum):
    """Gate decision actions with clear semantics"""

    ADMIT = "ADMIT"  # Process immediately
    BOOST = "BOOST"  # Process with elevated priority
    DEFER = "DEFER"  # Queue for later processing
    DROP = "DROP"  # Reject with reason


class IntentType(Enum):
    """Derived intent types for smart routing"""

    PROSPECTIVE_SCHEDULE = "PROSPECTIVE_SCHEDULE"
    RECALL = "RECALL"
    WRITE = "WRITE"
    PROJECT = "PROJECT"
    HIPPO_ENCODE = "HIPPO_ENCODE"
    UNKNOWN = "UNKNOWN"


@dataclass
class Actor:
    """Request actor information"""

    person_id: str
    role: str
    device_trust: Optional[str] = None


@dataclass
class PolicyContext:
    """Policy and security context"""

    band: str  # GREEN/AMBER/RED/BLACK
    abac: Dict[str, Any] = field(default_factory=dict)
    obligations: List[str] = field(default_factory=list)


@dataclass
class AffectSignals:
    """Affect analysis results"""

    valence: float  # -1.0 to 1.0
    arousal: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    tags: List[str] = field(default_factory=list)


@dataclass
class MetacogSignals:
    """Metacognition signals for learning"""

    uncertainty: float  # 0.0 to 1.0
    confidence: float = 0.0
    surprise: float = 0.0


@dataclass
class QoSSignals:
    """Quality of Service constraints"""

    budget_ms: int = 15
    device_thermal: str = "Nominal"
    battery_level: Optional[float] = None


@dataclass
class ContextSignals:
    """Environmental and social context"""

    recent_similar_requests: int = 0
    child_present: bool = False
    time_of_day: Optional[str] = None
    social_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestContent:
    """Content structure for requests requiring analysis"""

    text: str
    content_type: str = "text/plain"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Conversation context for intent derivation"""

    previous_intent: Optional[IntentType] = None
    turn_count: int = 0
    topic_continuity: float = 0.0


@dataclass
class GateRequest:
    """
    Complete gate decision request with extensible signal structure.

    Designed to support future learning while maintaining compatibility.
    """

    request_id: str
    actor: Actor
    space_id: str
    policy: PolicyContext
    payload: Dict[str, Any]

    # Content for analysis
    content: Optional[RequestContent] = None
    conversation_context: Optional[ConversationContext] = None

    # Optional fields for graceful degradation
    declared_intent: Optional[str] = None
    declared_confidence: float = 0.0

    # Signal bundles - extensible for future features
    affect: Optional[AffectSignals] = None
    metacog: Optional[MetacogSignals] = None
    qos: Optional[QoSSignals] = None
    context: Optional[ContextSignals] = None

    # Tracing and versioning
    trace_id: str = ""
    version: str = "gate:2025-09-14"
    timestamp: Optional[datetime] = None


@dataclass
class IntentConfidence:
    """Confidence metadata for derived intents"""

    score: float  # 0.0 to 1.0
    source: str  # "pattern_matching", "temporal_analysis", etc.
    evidence: str  # Human-readable evidence description


@dataclass
class DerivedIntent:
    """Intent derived by the gate"""

    intent: IntentType
    confidence: IntentConfidence
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingInfo:
    """Routing instructions for downstream processing"""

    topic: str
    priority: int = 0
    deadline: Optional[datetime] = None
    retry_policy: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SalienceFeatures:
    """
    Salience calculation features - designed for learning integration.

    All features normalized to [0,1] or [-1,1] for stability.
    """

    # Core features (always present)
    urgency: float = 0.0
    novelty: float = 0.0
    value: float = 0.0

    # Risk and cost factors
    risk: float = 0.0
    cost: float = 0.0
    social_risk: float = 0.0

    # Affect integration
    affect_arousal: float = 0.0
    affect_valence: float = 0.0

    # Context factors
    context_bump: float = 0.0
    temporal_fit: float = 0.0

    # Learning features (for future adaptation)
    personal_relevance: float = 0.0
    goal_alignment: float = 0.0

    # Raw feature dictionary for extensibility
    raw_features: Dict[str, float] = field(default_factory=dict)


@dataclass
class SalienceWeights:
    """
    Salience calculation weights - designed for learning adaptation.

    Structure supports both hardcoded and learned weights.
    """

    # Core weights
    urgency: float = 1.0
    novelty: float = 0.8
    value: float = 0.9

    # Penalty weights (negative in calculation)
    risk: float = 0.7
    cost: float = 0.6
    social_risk: float = 0.5

    # Affect weights
    affect_arousal: float = 0.4
    affect_valence: float = 0.2

    # Context weights
    context_bump: float = 0.3
    temporal_fit: float = 0.3

    # Learning weights (for future features)
    personal_relevance: float = 0.0
    goal_alignment: float = 0.0

    # Bias term
    bias: float = 0.0

    # Calibration parameters for learning
    temperature: float = 1.0
    platt_a: float = 1.0
    platt_b: float = 0.0

    # Metadata for learning
    adaptation_count: int = 0
    last_updated: Optional[datetime] = None
    learning_rate: float = 0.01

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization"""
        return {
            "urgency": self.urgency,
            "novelty": self.novelty,
            "value": self.value,
            "risk": self.risk,
            "cost": self.cost,
            "social_risk": self.social_risk,
            "affect_arousal": self.affect_arousal,
            "affect_valence": self.affect_valence,
            "context_bump": self.context_bump,
            "temporal_fit": self.temporal_fit,
            "personal_relevance": self.personal_relevance,
            "goal_alignment": self.goal_alignment,
            "bias": self.bias,
            "temperature": self.temperature,
            "platt_a": self.platt_a,
            "platt_b": self.platt_b,
        }


@dataclass
class GateDecisionTrace:
    """
    Decision tracing for explainability and learning.

    Captures all information needed for audit and weight learning.
    """

    trace_id: str
    features: Optional[SalienceFeatures]  # Optional for error cases
    weights: Optional[SalienceWeights]  # Optional for error cases
    raw_score: float
    calibrated_priority: float
    thresholds: Dict[str, float]
    decision_path: List[str]
    execution_time_ms: float

    # Learning metadata
    adaptation_context: Dict[str, Any] = field(default_factory=dict)
    ab_variant: Optional[str] = None


@dataclass
class GateDecision:
    """Core gate decision with full tracing"""

    action: GateAction
    priority: float  # 0.0 to 1.0 after calibration
    reasons: List[str]
    obligations: List[str] = field(default_factory=list)
    ttl_ms: int = 30000

    # Learning integration
    confidence: float = 1.0
    uncertainty: float = 0.0


@dataclass
class GateResponse:
    """
    Complete gate response with extensible structure.

    Supports future learning features while maintaining compatibility.
    """

    gate_decision: GateDecision
    derived_intents: List[DerivedIntent]
    routing: RoutingInfo
    trace: GateDecisionTrace

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    version: str = "gate:2025-09-14"

    # Future extensibility
    learning_feedback: Dict[str, Any] = field(default_factory=dict)
    adaptation_hints: Dict[str, Any] = field(default_factory=dict)


# Learning Integration Types


@dataclass
class LearningOutcome:
    """Outcome data for learning weight adaptation"""

    request_id: str
    gate_decision: GateAction
    actual_outcome: str  # success/failure/timeout/cancel
    user_feedback: Optional[str] = None
    downstream_metrics: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AdaptationUpdate:
    """Weight update from learning system"""

    component: str  # "attention_gate/salience"
    space_id: str
    weight_deltas: Dict[str, float]
    calibration_updates: Dict[str, float] = field(default_factory=dict)
    learning_metadata: Dict[str, Any] = field(default_factory=dict)


# Configuration Types


@dataclass
class ThresholdConfig:
    """Decision thresholds with learning support"""

    admit: float = 0.6
    boost: float = 0.8
    drop: float = 0.2

    # Adaptive thresholds (for future learning)
    adaptive_enabled: bool = False
    adaptation_rate: float = 0.01
    min_threshold: float = 0.1
    max_threshold: float = 0.9


@dataclass
class BackpressureConfig:
    """Backpressure and circuit breaker configuration"""

    enabled: bool = True
    token_bucket_rate: int = 10  # tokens per second
    token_bucket_burst: int = 20
    circuit_breaker_threshold: int = 5  # failures before opening
    circuit_breaker_timeout_ms: int = 30000


@dataclass
class LearningConfig:
    """Learning integration configuration"""

    enabled: bool = False
    learning_rate: float = 0.01
    adaptation_frequency: str = "hourly"  # hourly/daily/weekly
    min_samples: int = 100  # minimum samples before adaptation
    safety_checks: bool = True
    rollback_threshold: float = 0.1  # performance degradation threshold


# Error Types


class AttentionGateError(Exception):
    """Base exception for attention gate errors"""

    pass


class PolicyViolationError(AttentionGateError):
    """Raised when policy constraints are violated"""

    pass


class BackpressureError(AttentionGateError):
    """Raised when backpressure limits are exceeded"""

    pass


class ConfigurationError(AttentionGateError):
    """Raised when configuration is invalid"""

    pass

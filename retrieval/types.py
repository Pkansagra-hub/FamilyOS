"""
Retrieval Service Type Definitions
Comprehensive type system for P01 Recall and P17 QoS pipelines
Aligned with OpenAPI contracts and event system
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# =============================================================================
# Enums and Constants
# =============================================================================


class SecurityBand(str, Enum):
    """Security classification bands for memory items"""

    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    BLACK = "BLACK"


class SpaceType(str, Enum):
    """Space type classifications"""

    PERSONAL = "personal"
    SELECTIVE = "selective"
    SHARED = "shared"
    EXTENDED = "extended"
    INTERFAMILY = "interfamily"


class RetrievalOperation(str, Enum):
    """Retrieval operation types for policy evaluation"""

    READ = "recall:read"
    TRACE = "recall:trace"
    DEBUG = "recall:debug"


class SensitivityLevel(str, Enum):
    """Data sensitivity classification levels"""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


# =============================================================================
# Filter and Request Types
# =============================================================================


@dataclass
class TemporalFilter:
    """Time-based filtering for memory items"""

    after: Optional[datetime] = None
    before: Optional[datetime] = None
    within_days: Optional[int] = None

    def __post_init__(self):
        # Validation: cannot mix within_days with after/before
        if self.within_days is not None and (
            self.after is not None or self.before is not None
        ):
            raise ValueError("Cannot specify within_days with after/before filters")

        # Validation: after must be before 'before'
        if self.after is not None and self.before is not None:
            if self.after >= self.before:
                raise ValueError("'after' timestamp must be before 'before' timestamp")


@dataclass
class RetrievalFilters:
    """Comprehensive filter specification for retrieval requests"""

    # Temporal filters
    after: Optional[datetime] = None
    before: Optional[datetime] = None
    within_days: Optional[int] = None

    # Topic filters
    topics: Optional[List[str]] = None
    exclude_topics: Optional[List[str]] = None
    topic_logic: str = "OR"  # "AND" | "OR"

    # Security filters
    bands: Optional[List[SecurityBand]] = None
    max_band: Optional[SecurityBand] = None
    min_band: Optional[SecurityBand] = None
    max_sensitivity: Optional[SensitivityLevel] = None

    # Space filters
    space_types: Optional[List[SpaceType]] = None
    space_ids: Optional[List[str]] = None
    owner_filter: str = (
        "all_accessible"  # "owner_only" | "include_shared" | "all_accessible"
    )
    include_owners: Optional[List[str]] = None
    exclude_owners: Optional[List[str]] = None

    # Content filters
    content_types: Optional[List[str]] = (
        None  # ["text", "image", "audio", "video", "document", "structured"]
    )
    languages: Optional[List[str]] = None  # ISO 639-1 codes
    min_content_length: Optional[int] = None
    max_content_length: Optional[int] = None
    has_attachments: Optional[bool] = None

    # Quality filters (performance intensive)
    min_quality_score: Optional[float] = None
    min_relevance_score: Optional[float] = None
    exclude_duplicates: bool = True
    min_engagement: Optional[int] = None

    def __post_init__(self):
        # Validate temporal constraints
        if self.within_days is not None and (
            self.after is not None or self.before is not None
        ):
            raise ValueError("Cannot specify within_days with after/before filters")
        if self.after is not None and self.before is not None:
            if self.after >= self.before:
                raise ValueError("'after' timestamp must be before 'before' timestamp")

        # Validate topic filter overlap
        if (
            self.topics is not None
            and self.exclude_topics is not None
            and set(self.topics) & set(self.exclude_topics)
        ):
            raise ValueError("topics and exclude_topics cannot overlap")

        # Validate topic logic
        if self.topic_logic not in ["AND", "OR"]:
            raise ValueError("topic_logic must be 'AND' or 'OR'")

        # Validate owner filters overlap
        if (
            self.include_owners is not None
            and self.exclude_owners is not None
            and set(self.include_owners) & set(self.exclude_owners)
        ):
            raise ValueError("include_owners and exclude_owners cannot overlap")

        # Validate owner filter enum
        if self.owner_filter not in ["owner_only", "include_shared", "all_accessible"]:
            raise ValueError(
                "owner_filter must be 'owner_only', 'include_shared', or 'all_accessible'"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API serialization"""
        result = {}
        if self.after:
            result["after"] = self.after.isoformat()
        if self.before:
            result["before"] = self.before.isoformat()
        if self.within_days:
            result["within_days"] = self.within_days
        if self.topics:
            result["topics"] = self.topics
        if self.exclude_topics:
            result["exclude_topics"] = self.exclude_topics
        if self.topic_logic != "OR":
            result["topic_logic"] = self.topic_logic
        if self.bands:
            result["bands"] = [band.value for band in self.bands]
        if self.max_band:
            result["max_band"] = self.max_band.value
        if self.min_band:
            result["min_band"] = self.min_band.value
        if self.space_types:
            result["space_types"] = [st.value for st in self.space_types]
        if self.space_ids:
            result["space_ids"] = self.space_ids
        if self.owner_filter != "all_accessible":
            result["owner_filter"] = self.owner_filter
        if self.include_owners:
            result["include_owners"] = self.include_owners
        if self.exclude_owners:
            result["exclude_owners"] = self.exclude_owners
        if self.content_types:
            result["content_types"] = self.content_types
        if self.languages:
            result["languages"] = self.languages
        if self.min_content_length:
            result["min_content_length"] = self.min_content_length
        if self.max_content_length:
            result["max_content_length"] = self.max_content_length
        if self.has_attachments is not None:
            result["has_attachments"] = self.has_attachments
        if self.min_quality_score:
            result["min_quality_score"] = self.min_quality_score
        if self.min_relevance_score:
            result["min_relevance_score"] = self.min_relevance_score
        if not self.exclude_duplicates:
            result["exclude_duplicates"] = self.exclude_duplicates
        if self.min_engagement:
            result["min_engagement"] = self.min_engagement
        return result


@dataclass
class QoSBudget:
    """Quality of Service budget constraints"""

    latency_budget_ms: int = 100
    priority: int = 5
    max_results: int = 50
    allow_partial: bool = True
    timeout_behavior: str = "graceful"  # "graceful" | "strict"
    mode: str = "sync"  # "sync" | "async"
    ranking_profile: Optional[str] = None

    def __post_init__(self):
        if not 1 <= self.latency_budget_ms <= 5000:
            raise ValueError("latency_budget_ms must be between 1-5000")
        if not 1 <= self.priority <= 10:
            raise ValueError("priority must be between 1-10")
        if not 1 <= self.max_results <= 200:
            raise ValueError("max_results must be between 1-200")
        if self.mode not in ["sync", "async"]:
            raise ValueError("mode must be 'sync' or 'async'")
        if self.timeout_behavior not in ["graceful", "strict"]:
            raise ValueError("timeout_behavior must be 'graceful' or 'strict'")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API serialization"""
        result = {
            "latency_budget_ms": self.latency_budget_ms,
            "priority": self.priority,
            "max_results": self.max_results,
            "allow_partial": self.allow_partial,
            "timeout_behavior": self.timeout_behavior,
            "mode": self.mode,
        }
        if self.ranking_profile:
            result["ranking_profile"] = self.ranking_profile
        return result


@dataclass
class RetrievalRequest:
    """Complete retrieval request specification"""

    query: str
    space_id: Optional[str] = None
    k: int = 10
    filters: Optional[RetrievalFilters] = None
    return_trace: bool = False
    qos: Optional[QoSBudget] = None

    # Internal fields for processing
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    operation: RetrievalOperation = RetrievalOperation.READ

    def __post_init__(self):
        if not self.query or not self.query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= self.k <= 200:
            raise ValueError("k must be between 1-200")
        if self.space_id and not any(
            self.space_id.startswith(f"{space.value}:") for space in SpaceType
        ):
            raise ValueError("space_id must have valid space type prefix")

        # Set defaults
        if self.filters is None:
            self.filters = RetrievalFilters()
        if self.qos is None:
            self.qos = QoSBudget()

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API request format"""
        result = {"query": self.query, "k": self.k, "return_trace": self.return_trace}
        if self.space_id:
            result["space_id"] = self.space_id
        if self.filters:
            result["filters"] = self.filters.to_dict()
        if self.qos:
            result["qos"] = {
                "latency_budget_ms": self.qos.latency_budget_ms,
                "priority": self.qos.priority,
            }
        return result


# =============================================================================
# Response and Result Types
# =============================================================================


@dataclass
class FeatureVector:
    """Feature vector for ranking algorithms"""

    bm25: float = 0.0
    tfidf_cosine: float = 0.0
    recency: float = 0.0
    personalization: float = 0.0
    affect_compat: float = 0.0
    tom_alignment: float = 0.0
    length_penalty: float = 0.0
    source_prior: float = 0.0
    rrf_boost: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization"""
        return {
            "bm25": self.bm25,
            "tfidf_cosine": self.tfidf_cosine,
            "recency": self.recency,
            "personalization": self.personalization,
            "affect_compat": self.affect_compat,
            "tom_alignment": self.tom_alignment,
            "length_penalty": self.length_penalty,
            "source_prior": self.source_prior,
            "rrf_boost": self.rrf_boost,
        }


@dataclass
class RetrievalCandidate:
    """Internal candidate during retrieval processing"""

    doc_id: str
    content: str
    source: str  # "fts" | "vector" | "kg"
    raw_score: float
    features: Optional[FeatureVector] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.features is None:
            self.features = FeatureVector()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RetrievalItem:
    """Final retrieval result item for API response"""

    id: str
    score: float
    topic: Optional[str] = None
    band: Optional[SecurityBand] = None
    snippet: Optional[str] = None
    space_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

    # Internal processing metadata
    features: Optional[FeatureVector] = None
    reasons: Optional[List[str]] = None
    confidence: Optional[float] = None

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API response format"""
        result = {"id": self.id, "score": self.score}
        if self.topic:
            result["topic"] = self.topic
        if self.band:
            result["band"] = self.band.value
        if self.snippet:
            result["snippet"] = self.snippet
        if self.space_id:
            result["space_id"] = self.space_id
        if self.payload:
            result["payload"] = self.payload
        return result


@dataclass
class RetrievalTrace:
    """Tracing information for retrieval operations"""

    stage: str
    top_candidates: List[str] = field(default_factory=list)
    features_used: List[str] = field(default_factory=list)
    fusion_weights: Optional[Dict[str, float]] = None
    ranker_weights: Optional[Dict[str, float]] = None
    mmr_lambda: Optional[float] = None
    calibration_params: Optional[Dict[str, float]] = None
    processing_steps: List[str] = field(default_factory=list)

    def add_step(self, step: str) -> None:
        """Add processing step to trace"""
        self.processing_steps.append(step)

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API response format"""
        result = {}
        if self.features_used:
            result["features"] = self.features_used
        if self.fusion_weights:
            result["fusion"] = self.fusion_weights
        if self.ranker_weights:
            result["ranker"] = self.ranker_weights
        return result


@dataclass
class RetrievalResponse:
    """Complete retrieval response"""

    items: List[RetrievalItem]
    used_time_ms: float = 0.0
    trace: Optional[RetrievalTrace] = None

    # Metadata
    total_candidates: int = 0
    query_id: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to API response format"""
        result: Dict[str, Any] = {"items": [item.to_api_dict() for item in self.items]}
        if self.used_time_ms > 0:
            result["used_time_ms"] = self.used_time_ms
        if self.trace:
            result["trace"] = self.trace.to_api_dict()
        if self.total_candidates > 0:
            result["total_candidates"] = self.total_candidates
        if self.query_id:
            result["query_id"] = self.query_id
        if self.warnings:
            result["warnings"] = self.warnings
        return result

    def add_warning(self, warning: str) -> None:
        """Add warning message"""
        self.warnings.append(warning)


# =============================================================================
# Event Types
# =============================================================================


@dataclass
class RetrievalRequestEvent:
    """Event emitted when retrieval request received"""

    request_id: str
    user_id: str
    query: str
    space_id: Optional[str]
    timestamp: datetime
    qos_budget: int

    def to_event_payload(self) -> Dict[str, Any]:
        """Convert to event payload"""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "query": self.query,
            "space_id": self.space_id,
            "timestamp": self.timestamp.isoformat(),
            "qos_budget": self.qos_budget,
        }


@dataclass
class RetrievalResponseEvent:
    """Event emitted when retrieval response ready"""

    request_id: str
    user_id: str
    result_count: int
    processing_time_ms: float
    timestamp: datetime
    success: bool
    error_code: Optional[str] = None

    def to_event_payload(self) -> Dict[str, Any]:
        """Convert to event payload"""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "result_count": self.result_count,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error_code": self.error_code,
        }


@dataclass
class QoSExceededEvent:
    """Event emitted when QoS budget exceeded"""

    request_id: str
    user_id: str
    budget_ms: int
    actual_ms: float
    stage: str
    timestamp: datetime

    def to_event_payload(self) -> Dict[str, Any]:
        """Convert to event payload"""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "budget_ms": self.budget_ms,
            "actual_ms": self.actual_ms,
            "stage": self.stage,
            "timestamp": self.timestamp.isoformat(),
        }


# =============================================================================
# Policy and Access Control Types
# =============================================================================


@dataclass
class PolicyContext:
    """Context for policy evaluation"""

    user_id: str
    role: str
    operation: RetrievalOperation
    space_id: Optional[str]
    clearance_level: int
    department: str
    requested_bands: List[SecurityBand]
    timestamp: datetime
    qos_budget: int

    # Enhanced context for comprehensive policy evaluation
    content_types: Optional[List[str]] = None
    space_types: Optional[List[SpaceType]] = None
    temporal_range_days: Optional[int] = None
    quality_requirements: Optional[Dict[str, float]] = None
    business_hours_only: bool = False

    def to_policy_input(self) -> Dict[str, Any]:
        """Convert to policy engine input format"""
        policy_input = {
            "action": "recall",
            "operation": self.operation.value,
            "user": {
                "id": self.user_id,
                "role": self.role,
                "clearance_level": self.clearance_level,
                "department": self.department,
            },
            "context": {
                "space_id": self.space_id,
                "qos": {"latency_budget_ms": self.qos_budget},
                "timestamp": self.timestamp.isoformat(),
                "business_hours_only": self.business_hours_only,
            },
            "filters": {
                "bands": [band.value for band in self.requested_bands],
            },
        }

        # Add optional enhanced context
        if self.content_types:
            policy_input["filters"]["content_types"] = self.content_types
        if self.space_types:
            policy_input["filters"]["space_types"] = [
                st.value for st in self.space_types
            ]
        if self.temporal_range_days:
            policy_input["context"]["temporal_range_days"] = self.temporal_range_days
        if self.quality_requirements:
            policy_input["context"]["quality_requirements"] = self.quality_requirements

        return policy_input


@dataclass
class PolicyDecision:
    """Result of policy evaluation"""

    decision: str  # "PERMIT" | "DENY" | "INDETERMINATE"
    reasons: List[str]
    constraints: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, str]]] = None

    # Enhanced policy decision details
    policy_version: Optional[str] = None
    evaluation_time_ms: Optional[float] = None
    applied_rules: Optional[List[str]] = None

    @property
    def is_permitted(self) -> bool:
        """Check if access is permitted"""
        return self.decision == "PERMIT"

    @property
    def max_results(self) -> int:
        """Get maximum results constraint"""
        if self.constraints and "max_results" in self.constraints:
            return self.constraints["max_results"]
        return 50  # default

    @property
    def allowed_bands(self) -> List[SecurityBand]:
        """Get allowed security bands"""
        if self.constraints and "allowed_bands" in self.constraints:
            return [SecurityBand(band) for band in self.constraints["allowed_bands"]]
        return [SecurityBand.GREEN]  # default

    @property
    def time_constraints(self) -> Dict[str, Any]:
        """Get temporal constraints"""
        if self.constraints and "temporal" in self.constraints:
            return self.constraints["temporal"]
        return {}

    @property
    def space_constraints(self) -> Dict[str, Any]:
        """Get space access constraints"""
        if self.constraints and "space" in self.constraints:
            return self.constraints["space"]
        return {}

    def get_constraint(self, key: str, default: Any = None) -> Any:
        """Get specific constraint value"""
        if self.constraints and key in self.constraints:
            return self.constraints[key]
        return default


# =============================================================================
# Error Types
# =============================================================================


class RetrievalError(Exception):
    """Base exception for retrieval operations"""

    def __init__(
        self, message: str, code: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class QueryValidationError(RetrievalError):
    """Query validation failed"""

    def __init__(self, message: str, field: str):
        super().__init__(message, "QUERY_VALIDATION_ERROR", {"field": field})


class PolicyDeniedError(RetrievalError):
    """Access denied by policy"""

    def __init__(self, message: str, policy_decision: PolicyDecision):
        super().__init__(message, "POLICY_DENIED", {"decision": policy_decision})


class QoSBudgetExceededError(RetrievalError):
    """QoS budget exceeded"""

    def __init__(self, budget_ms: int, actual_ms: float, stage: str):
        message = f"QoS budget {budget_ms}ms exceeded: {actual_ms:.1f}ms in {stage}"
        super().__init__(
            message,
            "QOS_BUDGET_EXCEEDED",
            {"budget_ms": budget_ms, "actual_ms": actual_ms, "stage": stage},
        )


class IndexUnavailableError(RetrievalError):
    """Index temporarily unavailable"""

    def __init__(self, index_type: str):
        super().__init__(
            f"Index {index_type} unavailable",
            "INDEX_UNAVAILABLE",
            {"index_type": index_type},
        )


# =============================================================================
# Utility Functions
# =============================================================================


def validate_space_id(space_id: str) -> bool:
    """Validate space ID format"""
    if not space_id:
        return False
    try:
        space_type, _ = space_id.split(":", 1)
        return space_type in [s.value for s in SpaceType]
    except ValueError:
        return False


def create_trace_id() -> str:
    """Generate a trace ID for request tracking"""
    import uuid

    return uuid.uuid4().hex


def parse_filters_from_dict(data: Dict[str, Any]) -> RetrievalFilters:
    """Parse filters from API request dictionary"""
    filters = RetrievalFilters()

    # Temporal filters
    if "after" in data:
        filters.after = datetime.fromisoformat(data["after"].replace("Z", "+00:00"))
    if "before" in data:
        filters.before = datetime.fromisoformat(data["before"].replace("Z", "+00:00"))
    if "within_days" in data:
        filters.within_days = data["within_days"]

    # Topic filters
    if "topics" in data:
        filters.topics = data["topics"]
    if "exclude_topics" in data:
        filters.exclude_topics = data["exclude_topics"]
    if "topic_logic" in data:
        filters.topic_logic = data["topic_logic"]

    # Security filters
    if "bands" in data:
        filters.bands = [SecurityBand(band) for band in data["bands"]]
    if "max_band" in data:
        filters.max_band = SecurityBand(data["max_band"])
    if "min_band" in data:
        filters.min_band = SecurityBand(data["min_band"])
    if "max_sensitivity" in data:
        filters.max_sensitivity = SensitivityLevel(data["max_sensitivity"])

    # Space filters
    if "space_types" in data:
        filters.space_types = [SpaceType(st) for st in data["space_types"]]
    if "space_ids" in data:
        filters.space_ids = data["space_ids"]
    if "owner_filter" in data:
        filters.owner_filter = data["owner_filter"]
    if "include_owners" in data:
        filters.include_owners = data["include_owners"]
    if "exclude_owners" in data:
        filters.exclude_owners = data["exclude_owners"]

    # Content filters
    if "content_types" in data:
        filters.content_types = data["content_types"]
    if "languages" in data:
        filters.languages = data["languages"]
    if "min_content_length" in data:
        filters.min_content_length = data["min_content_length"]
    if "max_content_length" in data:
        filters.max_content_length = data["max_content_length"]
    if "has_attachments" in data:
        filters.has_attachments = data["has_attachments"]

    # Quality filters
    if "min_quality_score" in data:
        filters.min_quality_score = data["min_quality_score"]
    if "min_relevance_score" in data:
        filters.min_relevance_score = data["min_relevance_score"]
    if "exclude_duplicates" in data:
        filters.exclude_duplicates = data["exclude_duplicates"]
    if "min_engagement" in data:
        filters.min_engagement = data["min_engagement"]

    return filters


# Type aliases for convenience
RequestType = RetrievalRequest
ResponseType = RetrievalResponse
FilterType = RetrievalFilters
ItemType = RetrievalItem
CandidateType = RetrievalCandidate

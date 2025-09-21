"""
Cognitive Event Types - Brain-Inspired Event Classifications
===========================================================

Defines the complete taxonomy of cognitive events that flow through the
MemoryOS cognitive architecture, following neuroscience-inspired patterns
for memory formation, attention, decision-making, and learning.

**Event Categories:**
- Memory Events: Hippocampal memory formation and consolidation
- Recall Events: Context assembly and retrieval coordination
- Attention Events: Thalamic attention and working memory control
- Arbitration Events: Basal ganglia action selection and decision-making
- Learning Events: Dopaminergic learning signals and adaptation

All events include cognitive_trace_id for cross-namespace correlation and
support comprehensive observability for cognitive workflow tracking.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from events.types import Event, EventMeta


class CognitiveEventType(Enum):
    """Brain-inspired cognitive event types with neuroscience backing."""

    # Memory Formation Events (Hippocampal System)
    MEMORY_WRITE_INITIATED = "cognitive.memory.write.initiated"
    MEMORY_SPACE_RESOLVED = "cognitive.memory.write.space_resolved"
    MEMORY_REDACTED = "cognitive.memory.write.redacted"
    MEMORY_COMMITTED = "cognitive.memory.write.committed"
    MEMORY_FAILED = "cognitive.memory.write.failed"

    # Context Assembly Events (Retrieval System)
    RECALL_CONTEXT_REQUESTED = "cognitive.recall.context.requested"
    RECALL_STORES_QUERIED = "cognitive.recall.stores.queried"
    RECALL_RESULTS_FUSED = "cognitive.recall.results.fused"
    RECALL_BUNDLE_ASSEMBLED = "cognitive.recall.bundle.assembled"
    RECALL_BUNDLE_FAILED = "cognitive.recall.bundle.failed"

    # Attention & Working Memory Events (Thalamic/Prefrontal System)
    ATTENTION_GATE_ADMIT = "cognitive.attention.gate.admit"
    ATTENTION_GATE_DEFER = "cognitive.attention.gate.defer"
    ATTENTION_GATE_BOOST = "cognitive.attention.gate.boost"
    ATTENTION_GATE_DROP = "cognitive.attention.gate.drop"
    WORKING_MEMORY_UPDATED = "cognitive.working_memory.updated"
    WORKING_MEMORY_EVICTED = "cognitive.working_memory.evicted"

    # Decision Making Events (Basal Ganglia System)
    ARBITRATION_DECISION_REQUESTED = "cognitive.arbitration.decision.requested"
    ARBITRATION_HABIT_EVALUATED = "cognitive.arbitration.habit.evaluated"
    ARBITRATION_PLANNER_EVALUATED = "cognitive.arbitration.planner.evaluated"
    ARBITRATION_DECISION_MADE = "cognitive.arbitration.decision.made"
    ARBITRATION_DECISION_FAILED = "cognitive.arbitration.decision.failed"

    # Learning & Adaptation Events (Dopaminergic System)
    LEARNING_OUTCOME_RECEIVED = "cognitive.learning.outcome.received"
    LEARNING_HABIT_UPDATED = "cognitive.learning.habit.updated"
    LEARNING_PLANNER_UPDATED = "cognitive.learning.planner.updated"
    LEARNING_SELF_MODEL_UPDATED = "cognitive.learning.self_model.updated"


class CognitiveProcessingStage(Enum):
    """Stages of cognitive processing pipeline."""

    INITIATED = "initiated"
    VALIDATION = "validation"
    ROUTING = "routing"
    PROCESSING = "processing"
    COORDINATION = "coordination"
    COMPLETION = "completion"
    ERROR_HANDLING = "error_handling"


class CognitiveErrorType(Enum):
    """Types of cognitive processing errors."""

    VALIDATION_ERROR = "validation_error"
    ROUTING_ERROR = "routing_error"
    PROCESSING_ERROR = "processing_error"
    TIMEOUT_ERROR = "timeout_error"
    COORDINATION_ERROR = "coordination_error"
    RESOURCE_ERROR = "resource_error"
    INTEGRITY_ERROR = "integrity_error"


class RoutingStrategy(Enum):
    """Routing strategies for cognitive events."""

    BROADCAST = "broadcast"  # Send to all consumers
    ROUND_ROBIN = "round_robin"  # Load balance across consumers
    PRIORITY = "priority"  # Route by priority/salience
    STICKY_SESSION = "sticky_session"  # Route by session affinity
    COGNITIVE_LOAD = "cognitive_load"  # Route by least loaded consumer


@dataclass
class CognitiveTrace:
    """Cognitive processing trace for cross-namespace correlation."""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_trace_id: Optional[str] = None
    session_id: Optional[str] = None
    actor_id: Optional[str] = None
    space_id: Optional[str] = None

    # Processing context
    processing_stage: CognitiveProcessingStage = CognitiveProcessingStage.INITIATED
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stage_started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Performance tracking
    latency_budget_ms: Optional[int] = None
    priority: int = 5
    salience_score: Optional[float] = None

    # Routing information
    routing_strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN
    target_consumers: Optional[List[str]] = None
    retry_count: int = 0
    max_retries: int = 3

    # Cognitive context
    cognitive_load: Optional[float] = None
    attention_level: Optional[float] = None
    working_memory_pressure: Optional[float] = None

    def advance_stage(self, new_stage: CognitiveProcessingStage) -> None:
        """Advance to next processing stage."""
        self.processing_stage = new_stage
        self.stage_started_at = datetime.now(timezone.utc)

    def get_processing_duration_ms(self) -> float:
        """Get total processing duration in milliseconds."""
        now = datetime.now(timezone.utc)
        return (now - self.started_at).total_seconds() * 1000

    def get_stage_duration_ms(self) -> float:
        """Get current stage duration in milliseconds."""
        now = datetime.now(timezone.utc)
        return (now - self.stage_started_at).total_seconds() * 1000

    def is_over_budget(self) -> bool:
        """Check if processing is over latency budget."""
        if not self.latency_budget_ms:
            return False
        return self.get_processing_duration_ms() > self.latency_budget_ms

    def should_retry(self) -> bool:
        """Check if operation should be retried."""
        return self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment retry counter."""
        self.retry_count += 1


@dataclass
class CognitiveEvent:
    """Cognitive event with brain-inspired processing context."""

    event_type: CognitiveEventType
    trace: CognitiveTrace
    payload: Dict[str, Any]

    # Event metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_component: Optional[str] = None
    target_components: Optional[List[str]] = None

    # Processing requirements
    requires_coordination: bool = False
    coordination_timeout_ms: Optional[int] = None
    validation_schema: Optional[str] = None

    # Brain-inspired attributes
    neural_pathway: Optional[str] = None  # e.g., "hippocampal", "thalamic", "cortical"
    plasticity_required: bool = False  # Whether this event should trigger learning
    neuromodulation: Optional[Dict[str, float]] = None  # Dopamine, serotonin, etc.

    def to_base_event(self, meta: EventMeta) -> Event:
        """Convert to base Event type for the events bus."""
        # Add cognitive trace to the payload
        enhanced_payload = {
            **self.payload,
            "cognitive_trace_id": self.trace.trace_id,
            "cognitive_trace": {
                "parent_trace_id": self.trace.parent_trace_id,
                "session_id": self.trace.session_id,
                "processing_stage": self.trace.processing_stage.value,
                "started_at": self.trace.started_at.isoformat(),
                "priority": self.trace.priority,
                "salience_score": self.trace.salience_score,
                "routing_strategy": self.trace.routing_strategy.value,
                "retry_count": self.trace.retry_count,
                "cognitive_load": self.trace.cognitive_load,
                "attention_level": self.trace.attention_level,
                "working_memory_pressure": self.trace.working_memory_pressure,
            },
            "cognitive_event": {
                "source_component": self.source_component,
                "target_components": self.target_components,
                "requires_coordination": self.requires_coordination,
                "neural_pathway": self.neural_pathway,
                "plasticity_required": self.plasticity_required,
                "neuromodulation": self.neuromodulation,
            },
        }

        return Event(meta=meta, payload=enhanced_payload)

    @classmethod
    def from_base_event(cls, event: Event) -> Optional["CognitiveEvent"]:
        """Extract cognitive event from base Event if it has cognitive context."""
        payload = event.payload

        # Check if this is a cognitive event
        if "cognitive_trace_id" not in payload:
            return None

        # Extract cognitive trace
        trace_data = payload.get("cognitive_trace", {})
        trace = CognitiveTrace(
            trace_id=payload["cognitive_trace_id"],
            parent_trace_id=trace_data.get("parent_trace_id"),
            session_id=trace_data.get("session_id"),
            processing_stage=CognitiveProcessingStage(
                trace_data.get(
                    "processing_stage", CognitiveProcessingStage.INITIATED.value
                )
            ),
            priority=trace_data.get("priority", 5),
            salience_score=trace_data.get("salience_score"),
            routing_strategy=RoutingStrategy(
                trace_data.get("routing_strategy", RoutingStrategy.ROUND_ROBIN.value)
            ),
            retry_count=trace_data.get("retry_count", 0),
            cognitive_load=trace_data.get("cognitive_load"),
            attention_level=trace_data.get("attention_level"),
            working_memory_pressure=trace_data.get("working_memory_pressure"),
        )

        # Parse started_at if available
        if "started_at" in trace_data:
            trace.started_at = datetime.fromisoformat(trace_data["started_at"])

        # Extract cognitive event data
        cognitive_data = payload.get("cognitive_event", {})

        # Determine event type from topic
        try:
            event_type = CognitiveEventType(event.meta.topic.value)
        except ValueError:
            # Not a recognized cognitive event type
            return None

        # Create clean payload without cognitive metadata
        clean_payload = {
            k: v
            for k, v in payload.items()
            if k not in ["cognitive_trace_id", "cognitive_trace", "cognitive_event"]
        }

        return cls(
            event_type=event_type,
            trace=trace,
            payload=clean_payload,
            source_component=cognitive_data.get("source_component"),
            target_components=cognitive_data.get("target_components"),
            requires_coordination=cognitive_data.get("requires_coordination", False),
            neural_pathway=cognitive_data.get("neural_pathway"),
            plasticity_required=cognitive_data.get("plasticity_required", False),
            neuromodulation=cognitive_data.get("neuromodulation"),
        )


@dataclass
class CognitiveError:
    """Cognitive processing error with context."""

    error_type: CognitiveErrorType
    message: str
    trace_id: str
    component: str

    # Error context
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stage: Optional[CognitiveProcessingStage] = None
    retry_count: int = 0

    # Technical details
    exception_type: Optional[str] = None
    stack_trace: Optional[str] = None
    error_code: Optional[str] = None

    # Recovery information
    recoverable: bool = True
    recovery_strategy: Optional[str] = None
    estimated_recovery_time_ms: Optional[int] = None


@dataclass
class CognitiveProcessingResult:
    """Result of cognitive event processing."""

    trace_id: str
    success: bool
    stage: CognitiveProcessingStage

    # Timing information
    started_at: datetime
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Processing details
    processed_by: Optional[str] = None
    output_events: Optional[List[CognitiveEvent]] = None
    coordination_results: Optional[Dict[str, Any]] = None

    # Performance metrics
    latency_ms: Optional[float] = None
    cognitive_load_impact: Optional[float] = None
    memory_usage_mb: Optional[float] = None

    # Error information (if success=False)
    error: Optional[CognitiveError] = None

    def __post_init__(self):
        """Calculate latency if not provided."""
        if self.latency_ms is None:
            self.latency_ms = (
                self.completed_at - self.started_at
            ).total_seconds() * 1000


@dataclass
class RoutingDecision:
    """Decision about how to route a cognitive event."""

    target_consumers: List[str]
    routing_strategy: RoutingStrategy
    priority: int

    # Routing rationale
    reasoning: str
    confidence: float
    alternatives_considered: Optional[List[str]] = None

    # Load balancing information
    consumer_loads: Optional[Dict[str, float]] = None
    estimated_processing_time_ms: Optional[float] = None

    # Coordination requirements
    requires_coordination: bool = False
    coordination_timeout_ms: Optional[int] = None
    coordination_participants: Optional[List[str]] = None


def create_cognitive_event(
    event_type: CognitiveEventType,
    payload: Dict[str, Any],
    source_component: str,
    session_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    space_id: Optional[str] = None,
    priority: int = 5,
    salience_score: Optional[float] = None,
    latency_budget_ms: Optional[int] = None,
    neural_pathway: Optional[str] = None,
    requires_coordination: bool = False,
) -> CognitiveEvent:
    """Factory function to create a cognitive event with proper trace context."""

    trace = CognitiveTrace(
        session_id=session_id,
        actor_id=actor_id,
        space_id=space_id,
        priority=priority,
        salience_score=salience_score,
        latency_budget_ms=latency_budget_ms,
    )

    return CognitiveEvent(
        event_type=event_type,
        trace=trace,
        payload=payload,
        source_component=source_component,
        requires_coordination=requires_coordination,
        neural_pathway=neural_pathway,
    )


def create_memory_write_event(
    write_intent: Dict[str, Any],
    session_id: str,
    actor_id: str,
    space_id: str,
    salience_score: float = 0.5,
) -> CognitiveEvent:
    """Create a memory write initiated event."""
    return create_cognitive_event(
        event_type=CognitiveEventType.MEMORY_WRITE_INITIATED,
        payload={"write_intent": write_intent},
        source_component="memory_steward",
        session_id=session_id,
        actor_id=actor_id,
        space_id=space_id,
        salience_score=salience_score,
        neural_pathway="hippocampal",
        requires_coordination=True,
    )


def create_recall_request_event(
    query: Dict[str, Any],
    session_id: str,
    actor_id: str,
    space_id: str,
    priority: int = 5,
) -> CognitiveEvent:
    """Create a recall context requested event."""
    return create_cognitive_event(
        event_type=CognitiveEventType.RECALL_CONTEXT_REQUESTED,
        payload={"query": query},
        source_component="context_bundle",
        session_id=session_id,
        actor_id=actor_id,
        space_id=space_id,
        priority=priority,
        neural_pathway="cortical",
        requires_coordination=True,
    )


def create_attention_event(
    attention_decision: str,
    item_info: Dict[str, Any],
    session_id: str,
    salience_score: float,
) -> CognitiveEvent:
    """Create an attention gate decision event."""
    event_type_map = {
        "admit": CognitiveEventType.ATTENTION_GATE_ADMIT,
        "defer": CognitiveEventType.ATTENTION_GATE_DEFER,
        "boost": CognitiveEventType.ATTENTION_GATE_BOOST,
        "drop": CognitiveEventType.ATTENTION_GATE_DROP,
    }

    return create_cognitive_event(
        event_type=event_type_map[attention_decision],
        payload={"item_info": item_info, "decision": attention_decision},
        source_component="attention_gate",
        session_id=session_id,
        salience_score=salience_score,
        neural_pathway="thalamic",
    )


def create_working_memory_event(
    action: str,
    item_data: Dict[str, Any],
    session_id: str,
) -> CognitiveEvent:
    """Create a working memory update event."""
    event_type = (
        CognitiveEventType.WORKING_MEMORY_UPDATED
        if action == "updated"
        else CognitiveEventType.WORKING_MEMORY_EVICTED
    )

    return create_cognitive_event(
        event_type=event_type,
        payload={"action": action, "item_data": item_data},
        source_component="working_memory",
        session_id=session_id,
        neural_pathway="prefrontal",
    )

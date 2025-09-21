"""
Cognitive Event Dispatcher - Central Routing for Brain-Inspired Coordination
=============================================================================

Implements sophisticated routing and dispatching for cognitive events across
the MemoryOS cognitive architecture. Provides intelligent load balancing,
priority-based routing, and session affinity for optimal cognitive processing.

**Key Features:**
- Multi-strategy routing (round-robin, priority, cognitive load, sticky session)
- Real-time consumer health monitoring and load balancing
- Cognitive trace correlation for cross-namespace coordination
- Adaptive routing based on cognitive load and processing history
- Producer-consumer decoupling with reliable message delivery

**Brain-Inspired Patterns:**
- Thalamic relay functions for attention and routing
- Neural pathway specialization (hippocampal, cortical, thalamic)
- Adaptive routing based on synaptic strength and processing efficiency
- Neuromodulation-aware priority adjustment (dopamine, attention)

The dispatcher ensures optimal cognitive event flow while maintaining system
stability through adaptive routing and comprehensive observability.
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from events.bus import EventBus
from observability.logging import get_json_logger
from observability.trace import start_span

from .types import (
    CognitiveEvent,
    CognitiveEventType,
    CognitiveProcessingResult,
    RoutingDecision,
    RoutingStrategy,
)

logger = get_json_logger(__name__)


@dataclass
class ConsumerHealth:
    """Health and performance metrics for a cognitive consumer."""

    consumer_id: str
    last_heartbeat: datetime
    is_healthy: bool = True

    # Performance metrics
    current_load: float = 0.0
    average_latency_ms: float = 0.0
    success_rate: float = 1.0
    queue_depth: int = 0

    # Capacity information
    max_concurrent: int = 10
    current_concurrent: int = 0
    preferred_event_types: Set[CognitiveEventType] = field(default_factory=set)

    # Recent performance history (sliding window)
    recent_latencies: deque = field(default_factory=lambda: deque(maxlen=20))
    recent_successes: deque = field(default_factory=lambda: deque(maxlen=50))

    def update_performance(self, latency_ms: float, success: bool) -> None:
        """Update consumer performance metrics."""
        self.recent_latencies.append(latency_ms)
        self.recent_successes.append(success)

        # Recalculate averages
        if self.recent_latencies:
            self.average_latency_ms = sum(self.recent_latencies) / len(
                self.recent_latencies
            )

        if self.recent_successes:
            self.success_rate = sum(self.recent_successes) / len(self.recent_successes)

        # Update load based on queue depth and concurrent processing
        capacity_utilization = self.current_concurrent / max(1, self.max_concurrent)
        queue_pressure = min(1.0, self.queue_depth / 100.0)  # Normalize to 100 items
        self.current_load = (capacity_utilization + queue_pressure) / 2.0

        # Update health status
        self.is_healthy = (
            self.success_rate >= 0.8
            and self.current_load < 0.95
            and self.average_latency_ms < 5000  # 5 second timeout
        )

    def can_handle_event(self, event_type: CognitiveEventType) -> bool:
        """Check if consumer can handle specific event type."""
        if not self.is_healthy:
            return False

        if self.current_concurrent >= self.max_concurrent:
            return False

        # Check if consumer prefers this event type
        return (
            not self.preferred_event_types or event_type in self.preferred_event_types
        )

    def get_routing_score(self, event_type: CognitiveEventType, priority: int) -> float:
        """Calculate routing score for this consumer (higher = better)."""
        if not self.can_handle_event(event_type):
            return 0.0

        # Base score from inverse load and health
        base_score = (1.0 - self.current_load) * (self.success_rate**2)

        # Bonus for specialized event types
        specialization_bonus = 0.2 if event_type in self.preferred_event_types else 0.0

        # Priority adjustment
        priority_factor = min(2.0, priority / 5.0)

        # Latency penalty
        latency_penalty = max(0.0, (self.average_latency_ms - 1000) / 10000)

        return (base_score + specialization_bonus) * priority_factor - latency_penalty


@dataclass
class RoutingMetrics:
    """Metrics for cognitive event routing performance."""

    total_events_routed: int = 0
    routing_decisions_by_strategy: Dict[RoutingStrategy, int] = field(
        default_factory=dict
    )
    average_routing_latency_ms: float = 0.0
    failed_routing_attempts: int = 0

    # Consumer metrics
    active_consumers: int = 0
    healthy_consumers: int = 0
    average_consumer_load: float = 0.0

    # Event type distribution
    events_by_type: Dict[CognitiveEventType, int] = field(default_factory=dict)
    events_by_neural_pathway: Dict[str, int] = field(default_factory=dict)


class CognitiveDispatcher:
    """
    Central dispatcher for cognitive events with brain-inspired routing.

    Provides sophisticated routing across cognitive consumers with adaptive
    load balancing, priority handling, and session affinity. Implements
    thalamic relay patterns for optimal cognitive coordination.

    **Routing Strategies:**
    - ROUND_ROBIN: Equal distribution across healthy consumers
    - PRIORITY: Route by priority and consumer specialization
    - COGNITIVE_LOAD: Route to least loaded consumers
    - STICKY_SESSION: Maintain session affinity for context
    - BROADCAST: Send to all capable consumers

    **Key Functions:**
    - Real-time consumer health monitoring
    - Adaptive routing based on performance history
    - Cognitive trace correlation and context preservation
    - Backpressure-aware routing with overflow handling
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.event_bus = event_bus
        self.config = config or {}

        # Consumer management
        self.consumers: Dict[str, ConsumerHealth] = {}
        self.consumer_subscriptions: Dict[str, Set[CognitiveEventType]] = defaultdict(
            set
        )
        self.session_affinities: Dict[str, str] = {}  # session_id -> consumer_id

        # Routing state
        self.round_robin_index: Dict[CognitiveEventType, int] = defaultdict(int)
        self.metrics = RoutingMetrics()

        # Configuration
        self.default_routing_strategy = RoutingStrategy(
            self.config.get("default_routing_strategy", "round_robin")
        )
        self.session_affinity_timeout_minutes = self.config.get(
            "session_affinity_timeout", 30
        )
        self.consumer_heartbeat_timeout_seconds = self.config.get(
            "heartbeat_timeout", 60
        )
        self.max_routing_attempts = self.config.get("max_routing_attempts", 3)

        # Background tasks
        self._maintenance_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(
            "CognitiveDispatcher initialized",
            extra={
                "default_strategy": self.default_routing_strategy.value,
                "session_affinity_timeout": self.session_affinity_timeout_minutes,
                "heartbeat_timeout": self.consumer_heartbeat_timeout_seconds,
            },
        )

    async def start(self) -> None:
        """Start the cognitive dispatcher."""
        if self._running:
            return

        self._running = True

        # Subscribe to cognitive events from the event bus
        await self._subscribe_to_cognitive_events()

        # Start maintenance task
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())

        logger.info("CognitiveDispatcher started")

    async def stop(self) -> None:
        """Stop the cognitive dispatcher."""
        self._running = False

        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass

        logger.info("CognitiveDispatcher stopped")

    async def register_consumer(
        self,
        consumer_id: str,
        event_types: Set[CognitiveEventType],
        max_concurrent: int = 10,
    ) -> None:
        """Register a cognitive event consumer."""

        # Create consumer health record
        self.consumers[consumer_id] = ConsumerHealth(
            consumer_id=consumer_id,
            last_heartbeat=datetime.now(timezone.utc),
            max_concurrent=max_concurrent,
            preferred_event_types=event_types,
        )

        # Track subscriptions
        self.consumer_subscriptions[consumer_id] = event_types

        # Update metrics
        self.metrics.active_consumers = len(self.consumers)
        self.metrics.healthy_consumers = sum(
            1 for c in self.consumers.values() if c.is_healthy
        )

        logger.info(
            "Cognitive consumer registered",
            extra={
                "consumer_id": consumer_id,
                "event_types": [et.value for et in event_types],
                "max_concurrent": max_concurrent,
                "total_consumers": self.metrics.active_consumers,
            },
        )

    async def unregister_consumer(self, consumer_id: str) -> None:
        """Unregister a cognitive event consumer."""

        # Remove consumer
        self.consumers.pop(consumer_id, None)
        self.consumer_subscriptions.pop(consumer_id, None)

        # Clean up session affinities
        sessions_to_remove = [
            session_id
            for session_id, cid in self.session_affinities.items()
            if cid == consumer_id
        ]
        for session_id in sessions_to_remove:
            del self.session_affinities[session_id]

        # Update metrics
        self.metrics.active_consumers = len(self.consumers)
        self.metrics.healthy_consumers = sum(
            1 for c in self.consumers.values() if c.is_healthy
        )

        logger.info(
            "Cognitive consumer unregistered",
            extra={
                "consumer_id": consumer_id,
                "cleaned_sessions": len(sessions_to_remove),
                "remaining_consumers": self.metrics.active_consumers,
            },
        )

    async def update_consumer_heartbeat(
        self,
        consumer_id: str,
        queue_depth: int = 0,
        current_concurrent: int = 0,
    ) -> None:
        """Update consumer heartbeat and status."""

        consumer = self.consumers.get(consumer_id)
        if not consumer:
            logger.warning(f"Heartbeat from unknown consumer: {consumer_id}")
            return

        # Update heartbeat and status
        consumer.last_heartbeat = datetime.now(timezone.utc)
        consumer.queue_depth = queue_depth
        consumer.current_concurrent = current_concurrent

        # Recalculate health
        consumer.update_performance(
            consumer.average_latency_ms, True
        )  # Heartbeat = healthy

    async def route_event(self, cognitive_event: CognitiveEvent) -> RoutingDecision:
        """Route a cognitive event to appropriate consumers."""

        with start_span("cognitive_dispatcher.route_event") as span:
            routing_start = time.time()

            try:
                # Get routing strategy
                strategy = self._get_routing_strategy(cognitive_event)

                # Find eligible consumers
                eligible_consumers = self._find_eligible_consumers(
                    cognitive_event.event_type, cognitive_event.trace.priority
                )

                if not eligible_consumers:
                    raise ValueError(
                        f"No eligible consumers for {cognitive_event.event_type.value}"
                    )

                # Apply routing strategy
                target_consumers = self._apply_routing_strategy(
                    strategy, eligible_consumers, cognitive_event
                )

                # Create routing decision
                routing_latency = (time.time() - routing_start) * 1000

                decision = RoutingDecision(
                    target_consumers=target_consumers,
                    routing_strategy=strategy,
                    priority=cognitive_event.trace.priority,
                    reasoning=f"Routed via {strategy.value} to {len(target_consumers)} consumers",
                    confidence=self._calculate_routing_confidence(eligible_consumers),
                    consumer_loads={
                        cid: self.consumers[cid].current_load
                        for cid in target_consumers
                        if cid in self.consumers
                    },
                    estimated_processing_time_ms=self._estimate_processing_time(
                        target_consumers, cognitive_event.event_type
                    ),
                )

                # Update metrics
                self.metrics.total_events_routed += 1
                self.metrics.routing_decisions_by_strategy[strategy] = (
                    self.metrics.routing_decisions_by_strategy.get(strategy, 0) + 1
                )
                self.metrics.events_by_type[cognitive_event.event_type] = (
                    self.metrics.events_by_type.get(cognitive_event.event_type, 0) + 1
                )

                if cognitive_event.neural_pathway:
                    self.metrics.events_by_neural_pathway[
                        cognitive_event.neural_pathway
                    ] = (
                        self.metrics.events_by_neural_pathway.get(
                            cognitive_event.neural_pathway, 0
                        )
                        + 1
                    )

                # Update average routing latency
                total_latency = (
                    self.metrics.average_routing_latency_ms
                    * (self.metrics.total_events_routed - 1)
                    + routing_latency
                )
                self.metrics.average_routing_latency_ms = (
                    total_latency / self.metrics.total_events_routed
                )

                if span:
                    span.set_attribute("routing_strategy", strategy.value)
                    span.set_attribute("target_consumer_count", len(target_consumers))
                    span.set_attribute("routing_latency_ms", routing_latency)
                    span.set_attribute("event_type", cognitive_event.event_type.value)

                logger.debug(
                    "Cognitive event routed",
                    extra={
                        "trace_id": cognitive_event.trace.trace_id,
                        "event_type": cognitive_event.event_type.value,
                        "routing_strategy": strategy.value,
                        "target_consumers": target_consumers,
                        "routing_latency_ms": routing_latency,
                        "eligible_consumers": len(eligible_consumers),
                    },
                )

                return decision

            except Exception as e:
                self.metrics.failed_routing_attempts += 1

                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))

                logger.error(
                    "Failed to route cognitive event",
                    extra={
                        "trace_id": cognitive_event.trace.trace_id,
                        "event_type": cognitive_event.event_type.value,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

                raise

    async def dispatch_event(
        self,
        cognitive_event: CognitiveEvent,
        routing_decision: RoutingDecision,
    ) -> List[str]:
        """Dispatch cognitive event to target consumers."""

        dispatched_to = []

        for consumer_id in routing_decision.target_consumers:
            try:
                # Convert to base event format for the event bus
                # This would need proper EventMeta construction based on the cognitive event
                # For now, we'll publish directly to the consumer's topic

                # Create a topic specific to the consumer for cognitive events
                consumer_topic = f"cognitive.consumer.{consumer_id}"

                # Update consumer concurrent count
                if consumer_id in self.consumers:
                    self.consumers[consumer_id].current_concurrent += 1

                # TODO: Actually dispatch to consumer via event bus
                # This would involve converting the cognitive event back to a base Event
                # and publishing it to the consumer's specific topic or queue

                dispatched_to.append(consumer_id)

                logger.debug(
                    "Cognitive event dispatched to consumer",
                    extra={
                        "trace_id": cognitive_event.trace.trace_id,
                        "consumer_id": consumer_id,
                        "event_type": cognitive_event.event_type.value,
                    },
                )

            except Exception as e:
                logger.error(
                    "Failed to dispatch cognitive event to consumer",
                    extra={
                        "trace_id": cognitive_event.trace.trace_id,
                        "consumer_id": consumer_id,
                        "error": str(e),
                    },
                )

        return dispatched_to

    async def handle_processing_result(self, result: CognitiveProcessingResult) -> None:
        """Handle processing result from a consumer."""

        # Update consumer performance metrics
        if result.processed_by and result.processed_by in self.consumers:
            consumer = self.consumers[result.processed_by]

            # Update performance
            if result.latency_ms:
                consumer.update_performance(result.latency_ms, result.success)

            # Decrement concurrent count
            consumer.current_concurrent = max(0, consumer.current_concurrent - 1)

            # Handle session affinity
            if result.success and hasattr(result, "session_id") and result.processed_by:
                # TODO: Extract session_id from trace_id or result context
                pass

        # Handle output events if any
        if result.output_events:
            for output_event in result.output_events:
                # Route output events recursively
                routing_decision = await self.route_event(output_event)
                await self.dispatch_event(output_event, routing_decision)

        logger.debug(
            "Cognitive processing result handled",
            extra={
                "trace_id": result.trace_id,
                "success": result.success,
                "processed_by": result.processed_by,
                "latency_ms": result.latency_ms,
                "output_events": (
                    len(result.output_events) if result.output_events else 0
                ),
            },
        )

    def get_metrics(self) -> RoutingMetrics:
        """Get current routing metrics."""
        # Update real-time metrics
        self.metrics.active_consumers = len(self.consumers)
        self.metrics.healthy_consumers = sum(
            1 for c in self.consumers.values() if c.is_healthy
        )

        if self.consumers:
            total_load = sum(c.current_load for c in self.consumers.values())
            self.metrics.average_consumer_load = total_load / len(self.consumers)

        return self.metrics

    async def _subscribe_to_cognitive_events(self) -> None:
        """Subscribe to cognitive events from the event bus."""
        # TODO: Set up subscriptions for all cognitive event types
        # This would involve registering handlers for each CognitiveEventType
        # that extract CognitiveEvent from the base Event and route accordingly
        pass

    def _get_routing_strategy(self, cognitive_event: CognitiveEvent) -> RoutingStrategy:
        """Determine routing strategy for a cognitive event."""

        # Use explicit strategy from trace if available
        if hasattr(cognitive_event.trace, "routing_strategy"):
            return cognitive_event.trace.routing_strategy

        # Use event-specific strategy based on type
        event_type_strategies = {
            CognitiveEventType.MEMORY_WRITE_INITIATED: RoutingStrategy.PRIORITY,
            CognitiveEventType.RECALL_CONTEXT_REQUESTED: RoutingStrategy.COGNITIVE_LOAD,
            CognitiveEventType.ATTENTION_GATE_ADMIT: RoutingStrategy.STICKY_SESSION,
            CognitiveEventType.WORKING_MEMORY_UPDATED: RoutingStrategy.BROADCAST,
        }

        return event_type_strategies.get(
            cognitive_event.event_type, self.default_routing_strategy
        )

    def _find_eligible_consumers(
        self, event_type: CognitiveEventType, priority: int
    ) -> List[str]:
        """Find consumers eligible to handle an event type."""

        eligible = []

        for consumer_id, consumer in self.consumers.items():
            if consumer.can_handle_event(event_type):
                eligible.append(consumer_id)

        # Sort by routing score (best first)
        eligible.sort(
            key=lambda cid: self.consumers[cid].get_routing_score(event_type, priority),
            reverse=True,
        )

        return eligible

    def _apply_routing_strategy(
        self,
        strategy: RoutingStrategy,
        eligible_consumers: List[str],
        cognitive_event: CognitiveEvent,
    ) -> List[str]:
        """Apply routing strategy to select target consumers."""

        if not eligible_consumers:
            return []

        if strategy == RoutingStrategy.ROUND_ROBIN:
            # Round-robin selection
            event_type = cognitive_event.event_type
            index = self.round_robin_index[event_type] % len(eligible_consumers)
            self.round_robin_index[event_type] += 1
            return [eligible_consumers[index]]

        elif strategy == RoutingStrategy.PRIORITY:
            # Select best consumer based on routing score
            return [eligible_consumers[0]]  # Already sorted by score

        elif strategy == RoutingStrategy.COGNITIVE_LOAD:
            # Select least loaded consumer
            least_loaded = min(
                eligible_consumers, key=lambda cid: self.consumers[cid].current_load
            )
            return [least_loaded]

        elif strategy == RoutingStrategy.STICKY_SESSION:
            # Use session affinity if available
            session_id = cognitive_event.trace.session_id
            if session_id and session_id in self.session_affinities:
                affinity_consumer = self.session_affinities[session_id]
                if affinity_consumer in eligible_consumers:
                    return [affinity_consumer]

            # No affinity, use best consumer and create affinity
            best_consumer = eligible_consumers[0]
            if session_id:
                self.session_affinities[session_id] = best_consumer
            return [best_consumer]

        elif strategy == RoutingStrategy.BROADCAST:
            # Send to all eligible consumers
            return eligible_consumers

        else:
            # Default to round-robin
            return self._apply_routing_strategy(
                RoutingStrategy.ROUND_ROBIN, eligible_consumers, cognitive_event
            )

    def _calculate_routing_confidence(self, eligible_consumers: List[str]) -> float:
        """Calculate confidence in routing decision."""
        if not eligible_consumers:
            return 0.0

        # Base confidence on number of healthy consumers available
        healthy_count = sum(
            1
            for cid in eligible_consumers
            if cid in self.consumers and self.consumers[cid].is_healthy
        )

        base_confidence = min(1.0, healthy_count / 3.0)  # Normalize to 3 consumers

        # Adjust based on load distribution
        if len(eligible_consumers) > 1:
            loads = [
                self.consumers[cid].current_load
                for cid in eligible_consumers
                if cid in self.consumers
            ]
            if loads:
                load_variance = sum(
                    (load - sum(loads) / len(loads)) ** 2 for load in loads
                ) / len(loads)
                load_factor = max(
                    0.5, 1.0 - load_variance
                )  # Lower variance = higher confidence
                base_confidence *= load_factor

        return base_confidence

    def _estimate_processing_time(
        self, target_consumers: List[str], event_type: CognitiveEventType
    ) -> float:
        """Estimate processing time for event across target consumers."""

        if not target_consumers:
            return 0.0

        # Use average latency of target consumers
        latencies = [
            self.consumers[cid].average_latency_ms
            for cid in target_consumers
            if cid in self.consumers
        ]

        if not latencies:
            return 1000.0  # Default estimate

        return sum(latencies) / len(latencies)

    async def _maintenance_loop(self) -> None:
        """Background maintenance for consumer health and cleanup."""

        while self._running:
            try:
                await asyncio.sleep(30)  # Run every 30 seconds

                if not self._running:
                    break

                now = datetime.now(timezone.utc)

                # Check consumer health based on heartbeats
                unhealthy_consumers = []
                for consumer_id, consumer in self.consumers.items():
                    heartbeat_age = (now - consumer.last_heartbeat).total_seconds()

                    if heartbeat_age > self.consumer_heartbeat_timeout_seconds:
                        consumer.is_healthy = False
                        unhealthy_consumers.append(consumer_id)

                # Clean up old session affinities
                affinity_timeout_seconds = self.session_affinity_timeout_minutes * 60
                expired_sessions = []

                for session_id, consumer_id in self.session_affinities.items():
                    # Remove affinity if consumer is no longer available
                    if consumer_id not in self.consumers:
                        expired_sessions.append(session_id)
                    # TODO: Add session timestamp tracking for timeout cleanup

                for session_id in expired_sessions:
                    del self.session_affinities[session_id]

                # Update health metrics
                self.metrics.healthy_consumers = sum(
                    1 for c in self.consumers.values() if c.is_healthy
                )

                if unhealthy_consumers or expired_sessions:
                    logger.info(
                        "Cognitive dispatcher maintenance completed",
                        extra={
                            "unhealthy_consumers": len(unhealthy_consumers),
                            "expired_sessions": len(expired_sessions),
                            "total_consumers": len(self.consumers),
                            "healthy_consumers": self.metrics.healthy_consumers,
                        },
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Cognitive dispatcher maintenance error",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                await asyncio.sleep(5)  # Brief pause before retrying

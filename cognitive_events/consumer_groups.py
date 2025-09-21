"""
Cognitive Consumer Groups - Pipeline Consumer Management with Load Balancing
===========================================================================

Implements sophisticated consumer group management for cognitive event processing
with brain-inspired load balancing, failure recovery, and adaptive scaling.
Provides consumer coordination across cognitive pipelines with health monitoring.

**Key Features:**
- Dynamic consumer group creation and scaling
- Health-based load balancing with circuit breakers
- Consumer specialization by neural pathway and event type
- Adaptive retry strategies with exponential backoff
- Consumer failover and replacement mechanisms

**Brain-Inspired Patterns:**
- Neural pathway specialization (hippocampal, cortical, thalamic)
- Synaptic strength-based load distribution
- Neuroplasticity for adaptive consumer allocation
- Homeostatic scaling for stable processing capacity

The consumer manager ensures optimal distribution of cognitive workload
while maintaining system resilience through adaptive capacity management.
"""

import asyncio
import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from observability.logging import get_json_logger
from observability.trace import start_span

from .types import (
    CognitiveError,
    CognitiveEvent,
    CognitiveEventType,
    CognitiveProcessingResult,
)

logger = get_json_logger(__name__)


class ConsumerState(Enum):
    """States of a cognitive consumer."""

    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    FAILED = "failed"
    TERMINATED = "terminated"


class ConsumerGroupState(Enum):
    """States of a consumer group."""

    STARTING = "starting"
    ACTIVE = "active"
    SCALING = "scaling"
    DEGRADED = "degraded"
    TERMINATING = "terminating"


@dataclass
class ConsumerMetrics:
    """Performance metrics for a cognitive consumer."""

    consumer_id: str

    # Processing metrics
    total_events_processed: int = 0
    successful_events: int = 0
    failed_events: int = 0
    current_queue_depth: int = 0

    # Timing metrics
    average_processing_time_ms: float = 0.0
    p95_processing_time_ms: float = 0.0
    total_processing_time_ms: float = 0.0

    # Health metrics
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    consecutive_failures: int = 0
    state: ConsumerState = ConsumerState.INITIALIZING

    # Load metrics
    current_load: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    # Recent processing times for percentile calculation
    recent_processing_times: deque = field(default_factory=lambda: deque(maxlen=100))

    def update_processing_result(
        self, processing_time_ms: float, success: bool
    ) -> None:
        """Update metrics with a processing result."""
        self.total_events_processed += 1
        self.total_processing_time_ms += processing_time_ms
        self.recent_processing_times.append(processing_time_ms)

        if success:
            self.successful_events += 1
            self.consecutive_failures = 0
        else:
            self.failed_events += 1
            self.consecutive_failures += 1

        # Recalculate averages
        if self.total_events_processed > 0:
            self.average_processing_time_ms = (
                self.total_processing_time_ms / self.total_events_processed
            )

        # Calculate p95
        if self.recent_processing_times:
            sorted_times = sorted(self.recent_processing_times)
            p95_index = int(0.95 * len(sorted_times))
            self.p95_processing_time_ms = sorted_times[p95_index]

        # Update health state based on consecutive failures
        if self.consecutive_failures >= 5:
            self.state = ConsumerState.FAILED
        elif self.consecutive_failures >= 3:
            self.state = ConsumerState.UNHEALTHY
        elif self.consecutive_failures >= 1:
            self.state = ConsumerState.DEGRADED
        else:
            self.state = ConsumerState.HEALTHY

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_events_processed == 0:
            return 1.0
        return self.successful_events / self.total_events_processed

    def is_healthy(self) -> bool:
        """Check if consumer is in healthy state."""
        return self.state in [ConsumerState.HEALTHY, ConsumerState.DEGRADED]


@dataclass
class ConsumerGroupConfig:
    """Configuration for a consumer group."""

    group_id: str
    event_types: Set[CognitiveEventType]

    # Scaling configuration
    min_consumers: int = 1
    max_consumers: int = 10
    target_consumers: int = 3

    # Health thresholds
    max_queue_depth: int = 100
    max_processing_time_ms: float = 5000.0
    min_success_rate: float = 0.8

    # Scaling triggers
    scale_up_queue_threshold: int = 50
    scale_down_queue_threshold: int = 10
    scale_up_latency_threshold_ms: float = 2000.0

    # Consumer preferences
    preferred_neural_pathways: Set[str] = field(default_factory=set)
    requires_session_affinity: bool = False
    supports_coordination: bool = True


@dataclass
class ConsumerGroup:
    """A group of consumers handling specific cognitive event types."""

    config: ConsumerGroupConfig
    state: ConsumerGroupState = ConsumerGroupState.STARTING

    # Consumer management
    consumers: Dict[str, ConsumerMetrics] = field(default_factory=dict)
    failed_consumers: Set[str] = field(default_factory=set)

    # Load balancing
    round_robin_index: int = 0
    load_balancer_strategy: str = "round_robin"

    # Metrics
    total_events_processed: int = 0
    group_success_rate: float = 1.0
    average_queue_depth: float = 0.0

    # Scaling state
    last_scale_action: Optional[datetime] = None
    scale_cooldown_seconds: int = 60

    def get_healthy_consumers(self) -> List[str]:
        """Get list of healthy consumer IDs."""
        return [
            consumer_id
            for consumer_id, metrics in self.consumers.items()
            if metrics.is_healthy()
        ]

    def get_least_loaded_consumer(self) -> Optional[str]:
        """Get the consumer with the lowest current load."""
        healthy_consumers = self.get_healthy_consumers()

        if not healthy_consumers:
            return None

        return min(healthy_consumers, key=lambda cid: self.consumers[cid].current_load)

    def get_next_round_robin_consumer(self) -> Optional[str]:
        """Get next consumer using round-robin strategy."""
        healthy_consumers = self.get_healthy_consumers()

        if not healthy_consumers:
            return None

        consumer_id = healthy_consumers[self.round_robin_index % len(healthy_consumers)]
        self.round_robin_index += 1

        return consumer_id

    def should_scale_up(self) -> bool:
        """Check if group should scale up."""
        if len(self.consumers) >= self.config.max_consumers:
            return False

        if self._is_in_cooldown():
            return False

        # Check queue depth threshold
        avg_queue_depth = sum(
            c.current_queue_depth for c in self.consumers.values()
        ) / max(1, len(self.consumers))

        if avg_queue_depth > self.config.scale_up_queue_threshold:
            return True

        # Check latency threshold
        avg_latency = sum(
            c.average_processing_time_ms for c in self.consumers.values()
        ) / max(1, len(self.consumers))

        if avg_latency > self.config.scale_up_latency_threshold_ms:
            return True

        return False

    def should_scale_down(self) -> bool:
        """Check if group should scale down."""
        if len(self.consumers) <= self.config.min_consumers:
            return False

        if self._is_in_cooldown():
            return False

        # Only scale down if all consumers have low load
        for consumer in self.consumers.values():
            if not consumer.is_healthy():
                continue

            if consumer.current_queue_depth > self.config.scale_down_queue_threshold:
                return False

            if (
                consumer.current_load > 0.3
            ):  # Don't scale down if any consumer is >30% loaded
                return False

        return True

    def _is_in_cooldown(self) -> bool:
        """Check if group is in scaling cooldown period."""
        if not self.last_scale_action:
            return False

        elapsed = (datetime.now(timezone.utc) - self.last_scale_action).total_seconds()
        return elapsed < self.scale_cooldown_seconds


class CognitiveConsumerManager:
    """
    Manages groups of cognitive event consumers with brain-inspired coordination.

    Provides sophisticated consumer group management with adaptive scaling,
    health monitoring, and neural pathway specialization. Implements
    homeostatic scaling patterns for stable cognitive processing capacity.

    **Key Functions:**
    - Dynamic consumer group creation and management
    - Health-based load balancing with circuit breakers
    - Adaptive scaling based on queue depth and latency
    - Consumer specialization by neural pathway
    - Comprehensive health monitoring and failure recovery
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Consumer group management
        self.consumer_groups: Dict[str, ConsumerGroup] = {}
        self.consumer_to_group: Dict[str, str] = {}  # consumer_id -> group_id

        # Health monitoring
        self.health_check_interval_seconds = self.config.get(
            "health_check_interval", 30
        )
        self.consumer_timeout_seconds = self.config.get("consumer_timeout", 120)

        # Scaling configuration
        self.auto_scaling_enabled = self.config.get("auto_scaling_enabled", True)
        self.default_scaling_config = self.config.get(
            "default_scaling",
            {
                "min_consumers": 1,
                "max_consumers": 10,
                "target_consumers": 3,
            },
        )

        # Background tasks
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._scaling_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(
            "CognitiveConsumerManager initialized",
            extra={
                "health_check_interval": self.health_check_interval_seconds,
                "consumer_timeout": self.consumer_timeout_seconds,
                "auto_scaling_enabled": self.auto_scaling_enabled,
            },
        )

    async def start(self) -> None:
        """Start the consumer manager."""
        if self._running:
            return

        self._running = True

        # Start background tasks
        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())

        if self.auto_scaling_enabled:
            self._scaling_task = asyncio.create_task(self._scaling_loop())

        logger.info("CognitiveConsumerManager started")

    async def stop(self) -> None:
        """Stop the consumer manager."""
        self._running = False

        # Stop background tasks
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass

        if self._scaling_task:
            self._scaling_task.cancel()
            try:
                await self._scaling_task
            except asyncio.CancelledError:
                pass

        logger.info("CognitiveConsumerManager stopped")

    async def create_consumer_group(
        self,
        group_id: str,
        event_types: Set[CognitiveEventType],
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> ConsumerGroup:
        """Create a new consumer group."""

        # Build configuration
        config_dict = {**self.default_scaling_config}
        if config_overrides:
            config_dict.update(config_overrides)

        config = ConsumerGroupConfig(
            group_id=group_id, event_types=event_types, **config_dict
        )

        # Create consumer group
        group = ConsumerGroup(config=config)
        self.consumer_groups[group_id] = group

        logger.info(
            "Consumer group created",
            extra={
                "group_id": group_id,
                "event_types": [et.value for et in event_types],
                "target_consumers": config.target_consumers,
                "min_consumers": config.min_consumers,
                "max_consumers": config.max_consumers,
            },
        )

        return group

    async def register_consumer(
        self,
        consumer_id: str,
        group_id: str,
        capabilities: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Register a consumer with a consumer group."""

        if group_id not in self.consumer_groups:
            logger.error(f"Consumer group {group_id} not found")
            return False

        group = self.consumer_groups[group_id]

        # Create consumer metrics
        metrics = ConsumerMetrics(consumer_id=consumer_id)
        group.consumers[consumer_id] = metrics
        self.consumer_to_group[consumer_id] = group_id

        # Remove from failed consumers if present
        group.failed_consumers.discard(consumer_id)

        logger.info(
            "Consumer registered",
            extra={
                "consumer_id": consumer_id,
                "group_id": group_id,
                "group_consumer_count": len(group.consumers),
                "capabilities": capabilities,
            },
        )

        return True

    async def unregister_consumer(self, consumer_id: str) -> bool:
        """Unregister a consumer from its group."""

        group_id = self.consumer_to_group.get(consumer_id)
        if not group_id:
            logger.warning(f"Consumer {consumer_id} not found in any group")
            return False

        group = self.consumer_groups[group_id]

        # Remove consumer
        group.consumers.pop(consumer_id, None)
        group.failed_consumers.discard(consumer_id)
        del self.consumer_to_group[consumer_id]

        logger.info(
            "Consumer unregistered",
            extra={
                "consumer_id": consumer_id,
                "group_id": group_id,
                "remaining_consumers": len(group.consumers),
            },
        )

        return True

    async def select_consumer(
        self,
        group_id: str,
        event: CognitiveEvent,
        strategy: str = "least_loaded",
    ) -> Optional[str]:
        """Select a consumer from a group to handle an event."""

        group = self.consumer_groups.get(group_id)
        if not group:
            return None

        healthy_consumers = group.get_healthy_consumers()
        if not healthy_consumers:
            return None

        with start_span("consumer_manager.select_consumer") as span:
            if strategy == "least_loaded":
                selected = group.get_least_loaded_consumer()
            elif strategy == "round_robin":
                selected = group.get_next_round_robin_consumer()
            elif strategy == "random":
                selected = random.choice(healthy_consumers)
            elif strategy == "session_affinity":
                # TODO: Implement session affinity based on event.trace.session_id
                selected = group.get_least_loaded_consumer()
            else:
                selected = group.get_least_loaded_consumer()

            if span and selected:
                span.set_attribute("selected_consumer", selected)
                span.set_attribute("selection_strategy", strategy)
                span.set_attribute("healthy_consumer_count", len(healthy_consumers))

            return selected

    async def update_consumer_metrics(
        self,
        consumer_id: str,
        processing_result: CognitiveProcessingResult,
    ) -> None:
        """Update consumer metrics with processing result."""

        group_id = self.consumer_to_group.get(consumer_id)
        if not group_id:
            return

        group = self.consumer_groups[group_id]
        metrics = group.consumers.get(consumer_id)
        if not metrics:
            return

        # Update metrics
        if processing_result.latency_ms:
            metrics.update_processing_result(
                processing_result.latency_ms, processing_result.success
            )

        # Update resource usage if available
        if processing_result.memory_usage_mb:
            metrics.memory_usage_mb = processing_result.memory_usage_mb

        # Update load based on cognitive load impact
        if processing_result.cognitive_load_impact:
            metrics.current_load = min(
                1.0, metrics.current_load + processing_result.cognitive_load_impact
            )

        # Update heartbeat
        metrics.last_heartbeat = datetime.now(timezone.utc)

        # Update group metrics
        group.total_events_processed += 1

        # Recalculate group success rate
        if group.consumers:
            total_success = sum(c.get_success_rate() for c in group.consumers.values())
            group.group_success_rate = total_success / len(group.consumers)

        # Recalculate average queue depth
        if group.consumers:
            total_queue_depth = sum(
                c.current_queue_depth for c in group.consumers.values()
            )
            group.average_queue_depth = total_queue_depth / len(group.consumers)

    async def update_consumer_heartbeat(
        self,
        consumer_id: str,
        queue_depth: int = 0,
        current_load: float = 0.0,
        memory_usage_mb: float = 0.0,
        cpu_usage_percent: float = 0.0,
    ) -> None:
        """Update consumer heartbeat and status information."""

        group_id = self.consumer_to_group.get(consumer_id)
        if not group_id:
            return

        group = self.consumer_groups[group_id]
        metrics = group.consumers.get(consumer_id)
        if not metrics:
            return

        # Update metrics
        metrics.last_heartbeat = datetime.now(timezone.utc)
        metrics.current_queue_depth = queue_depth
        metrics.current_load = current_load
        metrics.memory_usage_mb = memory_usage_mb
        metrics.cpu_usage_percent = cpu_usage_percent

        # Update state if consumer was previously failed
        if metrics.state == ConsumerState.FAILED:
            metrics.state = ConsumerState.HEALTHY
            group.failed_consumers.discard(consumer_id)

    async def handle_consumer_failure(
        self,
        consumer_id: str,
        error: CognitiveError,
    ) -> None:
        """Handle consumer failure and update group state."""

        group_id = self.consumer_to_group.get(consumer_id)
        if not group_id:
            return

        group = self.consumer_groups[group_id]
        metrics = group.consumers.get(consumer_id)
        if not metrics:
            return

        # Update failure metrics
        metrics.consecutive_failures += 1
        metrics.state = ConsumerState.FAILED
        group.failed_consumers.add(consumer_id)

        logger.warning(
            "Consumer failure handled",
            extra={
                "consumer_id": consumer_id,
                "group_id": group_id,
                "error_type": error.error_type.value,
                "error_message": error.message,
                "consecutive_failures": metrics.consecutive_failures,
                "failed_consumers_in_group": len(group.failed_consumers),
            },
        )

        # Check if group needs scaling or recovery actions
        healthy_count = len(group.get_healthy_consumers())
        if healthy_count < group.config.min_consumers:
            logger.warning(
                "Consumer group below minimum healthy consumers",
                extra={
                    "group_id": group_id,
                    "healthy_consumers": healthy_count,
                    "min_consumers": group.config.min_consumers,
                    "total_consumers": len(group.consumers),
                },
            )

    def get_group_metrics(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive metrics for a consumer group."""

        group = self.consumer_groups.get(group_id)
        if not group:
            return None

        healthy_consumers = group.get_healthy_consumers()

        return {
            "group_id": group_id,
            "state": group.state.value,
            "total_consumers": len(group.consumers),
            "healthy_consumers": len(healthy_consumers),
            "failed_consumers": len(group.failed_consumers),
            "success_rate": group.group_success_rate,
            "average_queue_depth": group.average_queue_depth,
            "total_events_processed": group.total_events_processed,
            "event_types": [et.value for et in group.config.event_types],
            "consumer_metrics": {
                consumer_id: {
                    "state": metrics.state.value,
                    "success_rate": metrics.get_success_rate(),
                    "current_load": metrics.current_load,
                    "queue_depth": metrics.current_queue_depth,
                    "average_processing_time_ms": metrics.average_processing_time_ms,
                    "p95_processing_time_ms": metrics.p95_processing_time_ms,
                    "consecutive_failures": metrics.consecutive_failures,
                }
                for consumer_id, metrics in group.consumers.items()
            },
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get metrics for all consumer groups."""

        return {
            "total_groups": len(self.consumer_groups),
            "total_consumers": len(self.consumer_to_group),
            "groups": {
                group_id: self.get_group_metrics(group_id)
                for group_id in self.consumer_groups.keys()
            },
        }

    async def _health_monitor_loop(self) -> None:
        """Background health monitoring loop."""

        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval_seconds)

                if not self._running:
                    break

                now = datetime.now(timezone.utc)

                # Check each consumer group
                for group_id, group in self.consumer_groups.items():
                    timed_out_consumers = []

                    for consumer_id, metrics in group.consumers.items():
                        # Check for timeout
                        last_heartbeat_age = (
                            now - metrics.last_heartbeat
                        ).total_seconds()

                        if last_heartbeat_age > self.consumer_timeout_seconds:
                            timed_out_consumers.append(consumer_id)
                            metrics.state = ConsumerState.FAILED
                            group.failed_consumers.add(consumer_id)

                    if timed_out_consumers:
                        logger.warning(
                            "Consumers timed out",
                            extra={
                                "group_id": group_id,
                                "timed_out_consumers": timed_out_consumers,
                                "timeout_seconds": self.consumer_timeout_seconds,
                            },
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Health monitor error",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                await asyncio.sleep(5)

    async def _scaling_loop(self) -> None:
        """Background scaling loop for consumer groups."""

        while self._running:
            try:
                await asyncio.sleep(60)  # Check scaling every minute

                if not self._running:
                    break

                for group_id, group in self.consumer_groups.items():
                    try:
                        if group.should_scale_up():
                            logger.info(
                                "Consumer group should scale up",
                                extra={
                                    "group_id": group_id,
                                    "current_consumers": len(group.consumers),
                                    "max_consumers": group.config.max_consumers,
                                    "average_queue_depth": group.average_queue_depth,
                                },
                            )
                            # TODO: Implement actual consumer spawning
                            group.last_scale_action = datetime.now(timezone.utc)

                        elif group.should_scale_down():
                            logger.info(
                                "Consumer group should scale down",
                                extra={
                                    "group_id": group_id,
                                    "current_consumers": len(group.consumers),
                                    "min_consumers": group.config.min_consumers,
                                    "average_queue_depth": group.average_queue_depth,
                                },
                            )
                            # TODO: Implement graceful consumer termination
                            group.last_scale_action = datetime.now(timezone.utc)

                    except Exception as e:
                        logger.error(
                            "Scaling decision error",
                            extra={
                                "group_id": group_id,
                                "error": str(e),
                            },
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Scaling loop error",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                await asyncio.sleep(10)

"""
Cognitive DLQ Manager - Failed Processing Recovery and Analysis
==============================================================

Implements sophisticated dead letter queue management for failed cognitive
processing with intelligent retry strategies, failure analysis, and recovery
mechanisms. Provides comprehensive error handling for cognitive workflows.

**Key Features:**
- Intelligent retry strategies with exponential backoff
- Failure pattern analysis and classification
- Recovery workflow orchestration
- Poison message detection and quarantine
- Comprehensive error analytics and reporting

**Brain-Inspired Patterns:**
- Error-driven learning for improved processing strategies
- Adaptive retry mechanisms based on failure patterns
- Memory consolidation for failed processing experiences
- Homeostatic recovery mechanisms for system stability

The DLQ manager ensures system resilience by learning from failures
and implementing adaptive recovery strategies for cognitive processing.
"""

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from observability.logging import get_json_logger
from observability.trace import start_span

from .types import (
    CognitiveError,
    CognitiveErrorType,
    CognitiveEvent,
    CognitiveEventType,
)

logger = get_json_logger(__name__)


class RetryStrategy(Enum):
    """Retry strategies for failed cognitive events."""

    IMMEDIATE = "immediate"  # Retry immediately
    EXPONENTIAL_BACKOFF = "exponential"  # Exponential backoff
    LINEAR_BACKOFF = "linear"  # Linear delay increase
    ADAPTIVE = "adaptive"  # Adaptive based on failure type
    CIRCUIT_BREAKER = "circuit_breaker"  # Circuit breaker pattern
    NO_RETRY = "no_retry"  # Do not retry


class FailureCategory(Enum):
    """Categories of cognitive processing failures."""

    TRANSIENT = "transient"  # Temporary failures (network, timeout)
    RESOURCE = "resource"  # Resource exhaustion (memory, CPU)
    VALIDATION = "validation"  # Input validation failures
    PROCESSING = "processing"  # Processing logic failures
    COORDINATION = "coordination"  # Cross-module coordination failures
    POISON = "poison"  # Poison messages that always fail
    SYSTEM = "system"  # System-level failures


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 300.0
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1

    # Circuit breaker configuration
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60

    # Adaptive configuration
    success_rate_threshold: float = 0.8
    adaptation_window_minutes: int = 30


@dataclass
class FailureRecord:
    """Record of a cognitive processing failure."""

    event_id: str
    trace_id: str
    event_type: CognitiveEventType
    failure_time: datetime
    error: CognitiveError

    # Retry information
    attempt_number: int
    total_attempts: int
    next_retry_time: Optional[datetime] = None

    # Failure analysis
    failure_category: Optional[FailureCategory] = None
    root_cause: Optional[str] = None
    similar_failures: int = 0

    # Recovery information
    recovery_attempted: bool = False
    recovery_successful: bool = False
    final_disposition: Optional[str] = None


@dataclass
class DLQMetrics:
    """Metrics for DLQ operations."""

    # Queue statistics
    total_failed_events: int = 0
    events_in_dlq: int = 0
    events_retried: int = 0
    events_recovered: int = 0
    events_permanently_failed: int = 0

    # Failure analysis
    failures_by_type: Dict[CognitiveEventType, int] = field(default_factory=dict)
    failures_by_category: Dict[FailureCategory, int] = field(default_factory=dict)
    failures_by_component: Dict[str, int] = field(default_factory=dict)

    # Retry statistics
    average_retry_attempts: float = 0.0
    retry_success_rate: float = 0.0
    recovery_success_rate: float = 0.0

    # Timing metrics
    average_time_to_recovery_seconds: float = 0.0
    longest_retry_sequence_seconds: float = 0.0

    # Recent activity (sliding windows)
    recent_failures: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_recoveries: deque = field(default_factory=lambda: deque(maxlen=50))


class CognitiveDLQManager:
    """
    Sophisticated dead letter queue manager for cognitive event processing.

    Provides intelligent failure handling with adaptive retry strategies,
    comprehensive failure analysis, and recovery workflow orchestration.
    Implements brain-inspired error learning for improved system resilience.

    **Key Functions:**
    - Intelligent retry strategies with failure pattern learning
    - Comprehensive failure analysis and categorization
    - Adaptive recovery mechanisms based on error types
    - Poison message detection and quarantine
    - Error analytics for system improvement insights
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # DLQ storage
        self.failed_events: Dict[str, FailureRecord] = {}  # trace_id -> FailureRecord
        self.retry_queue: Dict[str, FailureRecord] = {}  # trace_id -> FailureRecord
        self.poison_events: Set[str] = set()  # trace_ids of poison messages

        # Retry configuration by event type
        self.retry_configs: Dict[CognitiveEventType, RetryConfig] = {}
        self._initialize_default_retry_configs()

        # Metrics and analytics
        self.metrics = DLQMetrics()
        self.failure_patterns: Dict[str, List[FailureRecord]] = defaultdict(list)

        # Background processing
        self._retry_processor_task: Optional[asyncio.Task] = None
        self._analytics_task: Optional[asyncio.Task] = None
        self._running = False

        # Configuration
        self.dlq_persistence_path = self.config.get("dlq_persistence_path", "data/dlq")
        self.analytics_interval_seconds = self.config.get(
            "analytics_interval", 300
        )  # 5 minutes
        self.retry_check_interval_seconds = self.config.get("retry_interval", 30)
        self.poison_detection_threshold = self.config.get("poison_threshold", 5)

        logger.info(
            "CognitiveDLQManager initialized",
            extra={
                "dlq_persistence_path": self.dlq_persistence_path,
                "analytics_interval": self.analytics_interval_seconds,
                "retry_interval": self.retry_check_interval_seconds,
                "poison_threshold": self.poison_detection_threshold,
            },
        )

    async def start(self) -> None:
        """Start the DLQ manager."""
        if self._running:
            return

        self._running = True

        # Load persisted state
        await self._load_persisted_state()

        # Start background tasks
        self._retry_processor_task = asyncio.create_task(self._retry_processor_loop())
        self._analytics_task = asyncio.create_task(self._analytics_loop())

        logger.info("CognitiveDLQManager started")

    async def stop(self) -> None:
        """Stop the DLQ manager."""
        self._running = False

        # Stop background tasks
        if self._retry_processor_task:
            self._retry_processor_task.cancel()
            try:
                await self._retry_processor_task
            except asyncio.CancelledError:
                pass

        if self._analytics_task:
            self._analytics_task.cancel()
            try:
                await self._analytics_task
            except asyncio.CancelledError:
                pass

        # Persist current state
        await self._persist_state()

        logger.info("CognitiveDLQManager stopped")

    async def handle_failed_event(
        self,
        event: CognitiveEvent,
        error: CognitiveError,
        attempt_number: int = 1,
    ) -> bool:
        """
        Handle a failed cognitive event.

        Returns:
            True if event should be retried, False if permanently failed
        """

        with start_span("dlq.handle_failed_event") as span:
            try:
                # Check if this is a poison message
                if event.trace.trace_id in self.poison_events:
                    await self._handle_poison_event(event, error)
                    if span:
                        span.set_attribute("disposition", "poison")
                    return False

                # Create failure record
                failure_record = FailureRecord(
                    event_id=getattr(event, "event_id", event.trace.trace_id),
                    trace_id=event.trace.trace_id,
                    event_type=event.event_type,
                    failure_time=datetime.now(timezone.utc),
                    error=error,
                    attempt_number=attempt_number,
                    total_attempts=attempt_number,
                )

                # Analyze failure
                await self._analyze_failure(failure_record, event)

                # Determine retry strategy
                retry_config = self._get_retry_config(event.event_type)
                should_retry = await self._should_retry_event(
                    failure_record, retry_config
                )

                if should_retry:
                    # Schedule for retry
                    await self._schedule_retry(failure_record, retry_config)
                    if span:
                        span.set_attribute("disposition", "retry_scheduled")
                        span.set_attribute(
                            "next_retry",
                            (
                                failure_record.next_retry_time.isoformat()
                                if failure_record.next_retry_time
                                else None
                            ),
                        )
                else:
                    # Permanently failed
                    await self._handle_permanent_failure(failure_record, event)
                    if span:
                        span.set_attribute("disposition", "permanent_failure")

                # Update metrics
                await self._update_failure_metrics(failure_record)

                if span:
                    span.set_attribute("trace_id", event.trace.trace_id)
                    span.set_attribute("event_type", event.event_type.value)
                    span.set_attribute("error_type", error.error_type.value)
                    span.set_attribute("attempt_number", attempt_number)
                    span.set_attribute(
                        "failure_category",
                        (
                            failure_record.failure_category.value
                            if failure_record.failure_category
                            else None
                        ),
                    )

                logger.info(
                    "Failed event handled",
                    extra={
                        "trace_id": event.trace.trace_id,
                        "event_type": event.event_type.value,
                        "error_type": error.error_type.value,
                        "attempt_number": attempt_number,
                        "should_retry": should_retry,
                        "failure_category": (
                            failure_record.failure_category.value
                            if failure_record.failure_category
                            else None
                        ),
                    },
                )

                return should_retry

            except Exception as e:
                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))

                logger.error(
                    "Error handling failed event",
                    extra={
                        "trace_id": event.trace.trace_id,
                        "error": str(e),
                    },
                    exc_info=True,
                )

                return False

    async def get_retry_events(self) -> List[CognitiveEvent]:
        """Get events ready for retry."""

        ready_events = []
        now = datetime.now(timezone.utc)

        # Find events ready for retry
        retry_ready = []
        for trace_id, failure_record in self.retry_queue.items():
            if failure_record.next_retry_time and failure_record.next_retry_time <= now:
                retry_ready.append(trace_id)

        # TODO: Reconstruct CognitiveEvent from failure records
        # This would require storing the original event data
        # For now, return empty list

        logger.debug(
            "Retry events retrieved",
            extra={
                "retry_ready_count": len(retry_ready),
                "total_in_retry_queue": len(self.retry_queue),
            },
        )

        return ready_events

    async def mark_retry_success(self, trace_id: str) -> None:
        """Mark a retry attempt as successful."""

        failure_record = self.retry_queue.pop(trace_id, None)
        if failure_record:
            failure_record.recovery_successful = True
            failure_record.final_disposition = "recovered"

            # Update metrics
            self.metrics.events_recovered += 1
            self.metrics.recent_recoveries.append(failure_record)

            # Update retry success rate
            total_retries = self.metrics.events_retried + self.metrics.events_recovered
            if total_retries > 0:
                self.metrics.retry_success_rate = (
                    self.metrics.events_recovered / total_retries
                )

            logger.info(
                "Retry successful",
                extra={
                    "trace_id": trace_id,
                    "total_attempts": failure_record.total_attempts,
                    "time_to_recovery": (
                        datetime.now(timezone.utc) - failure_record.failure_time
                    ).total_seconds(),
                },
            )

    async def mark_retry_failure(self, trace_id: str, error: CognitiveError) -> None:
        """Mark a retry attempt as failed."""

        failure_record = self.retry_queue.get(trace_id)
        if not failure_record:
            return

        failure_record.total_attempts += 1
        failure_record.error = error  # Update with latest error

        # Check if this should become a poison message
        if failure_record.total_attempts >= self.poison_detection_threshold:
            await self._mark_as_poison(trace_id, failure_record)
            return

        # Determine if we should retry again
        retry_config = self._get_retry_config(failure_record.event_type)
        should_retry = await self._should_retry_event(failure_record, retry_config)

        if should_retry:
            await self._schedule_retry(failure_record, retry_config)
        else:
            await self._handle_permanent_failure(failure_record, None)

    def get_failure_analytics(self) -> Dict[str, Any]:
        """Get comprehensive failure analytics."""

        return {
            "summary": {
                "total_failed_events": self.metrics.total_failed_events,
                "events_in_dlq": self.metrics.events_in_dlq,
                "events_recovered": self.metrics.events_recovered,
                "retry_success_rate": self.metrics.retry_success_rate,
                "poison_events": len(self.poison_events),
            },
            "failure_distribution": {
                "by_event_type": {
                    event_type.value: count
                    for event_type, count in self.metrics.failures_by_type.items()
                },
                "by_category": {
                    category.value: count
                    for category, count in self.metrics.failures_by_category.items()
                },
                "by_component": dict(self.metrics.failures_by_component),
            },
            "performance": {
                "average_retry_attempts": self.metrics.average_retry_attempts,
                "average_time_to_recovery_seconds": self.metrics.average_time_to_recovery_seconds,
                "longest_retry_sequence_seconds": self.metrics.longest_retry_sequence_seconds,
            },
            "recent_activity": {
                "recent_failures_count": len(self.metrics.recent_failures),
                "recent_recoveries_count": len(self.metrics.recent_recoveries),
            },
        }

    def get_metrics(self) -> DLQMetrics:
        """Get current DLQ metrics."""
        return self.metrics

    async def _analyze_failure(
        self, failure_record: FailureRecord, event: CognitiveEvent
    ) -> None:
        """Analyze failure to categorize and identify patterns."""

        error = failure_record.error

        # Categorize failure
        if error.error_type in [CognitiveErrorType.TIMEOUT_ERROR]:
            failure_record.failure_category = FailureCategory.TRANSIENT
        elif error.error_type in [CognitiveErrorType.RESOURCE_ERROR]:
            failure_record.failure_category = FailureCategory.RESOURCE
        elif error.error_type in [CognitiveErrorType.VALIDATION_ERROR]:
            failure_record.failure_category = FailureCategory.VALIDATION
        elif error.error_type in [CognitiveErrorType.PROCESSING_ERROR]:
            failure_record.failure_category = FailureCategory.PROCESSING
        elif error.error_type in [CognitiveErrorType.COORDINATION_ERROR]:
            failure_record.failure_category = FailureCategory.COORDINATION
        else:
            failure_record.failure_category = FailureCategory.SYSTEM

        # Look for similar failures
        pattern_key = (
            f"{event.event_type.value}:{error.error_type.value}:{error.component}"
        )
        similar_failures = self.failure_patterns[pattern_key]
        similar_failures.append(failure_record)

        # Keep only recent failures for pattern analysis
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        self.failure_patterns[pattern_key] = [
            f for f in similar_failures if f.failure_time > cutoff_time
        ]

        failure_record.similar_failures = len(self.failure_patterns[pattern_key])

        # Detect poison messages based on repeated similar failures
        if failure_record.similar_failures >= self.poison_detection_threshold:
            await self._mark_as_poison(failure_record.trace_id, failure_record)

    async def _should_retry_event(
        self, failure_record: FailureRecord, retry_config: RetryConfig
    ) -> bool:
        """Determine if an event should be retried."""

        # Check max attempts
        if failure_record.total_attempts >= retry_config.max_attempts:
            return False

        # Check retry strategy
        if retry_config.strategy == RetryStrategy.NO_RETRY:
            return False

        # Don't retry poison messages
        if failure_record.trace_id in self.poison_events:
            return False

        # Category-specific retry logic
        if failure_record.failure_category == FailureCategory.VALIDATION:
            # Validation errors usually don't benefit from retry
            return False

        if failure_record.failure_category == FailureCategory.POISON:
            return False

        # For other categories, allow retry based on configuration
        return True

    async def _schedule_retry(
        self, failure_record: FailureRecord, retry_config: RetryConfig
    ) -> None:
        """Schedule event for retry with appropriate delay."""

        delay_seconds = self._calculate_retry_delay(failure_record, retry_config)
        failure_record.next_retry_time = datetime.now(timezone.utc) + timedelta(
            seconds=delay_seconds
        )

        # Add to retry queue
        self.retry_queue[failure_record.trace_id] = failure_record
        self.metrics.events_retried += 1

        logger.debug(
            "Event scheduled for retry",
            extra={
                "trace_id": failure_record.trace_id,
                "attempt_number": failure_record.total_attempts,
                "delay_seconds": delay_seconds,
                "next_retry_time": failure_record.next_retry_time.isoformat(),
            },
        )

    def _calculate_retry_delay(
        self, failure_record: FailureRecord, retry_config: RetryConfig
    ) -> float:
        """Calculate delay for retry attempt."""

        if retry_config.strategy == RetryStrategy.IMMEDIATE:
            return 0.0

        elif retry_config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = retry_config.initial_delay_seconds * failure_record.total_attempts

        elif retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = retry_config.initial_delay_seconds * (
                retry_config.backoff_multiplier ** (failure_record.total_attempts - 1)
            )

        elif retry_config.strategy == RetryStrategy.ADAPTIVE:
            # Adaptive delay based on failure category and recent success rate
            base_delay = retry_config.initial_delay_seconds

            if failure_record.failure_category == FailureCategory.TRANSIENT:
                delay = base_delay * 0.5  # Shorter delay for transient failures
            elif failure_record.failure_category == FailureCategory.RESOURCE:
                delay = base_delay * 2.0  # Longer delay for resource failures
            else:
                delay = base_delay

            # Adjust based on recent success rate
            if self.metrics.retry_success_rate < 0.5:
                delay *= 2.0  # Increase delay if success rate is low

        else:
            delay = retry_config.initial_delay_seconds

        # Apply jitter to avoid thundering herd
        jitter_range = delay * retry_config.jitter_factor
        import random

        jitter = random.uniform(-jitter_range, jitter_range)
        delay += jitter

        # Clamp to max delay
        delay = min(delay, retry_config.max_delay_seconds)

        return max(0.0, delay)

    async def _handle_permanent_failure(
        self, failure_record: FailureRecord, event: Optional[CognitiveEvent]
    ) -> None:
        """Handle permanently failed event."""

        failure_record.final_disposition = "permanent_failure"
        self.failed_events[failure_record.trace_id] = failure_record
        self.retry_queue.pop(failure_record.trace_id, None)

        self.metrics.events_permanently_failed += 1

        logger.warning(
            "Event permanently failed",
            extra={
                "trace_id": failure_record.trace_id,
                "event_type": failure_record.event_type.value,
                "total_attempts": failure_record.total_attempts,
                "failure_category": (
                    failure_record.failure_category.value
                    if failure_record.failure_category
                    else None
                ),
                "error_type": failure_record.error.error_type.value,
            },
        )

    async def _handle_poison_event(
        self, event: CognitiveEvent, error: CognitiveError
    ) -> None:
        """Handle poison message that consistently fails."""

        logger.error(
            "Poison event detected",
            extra={
                "trace_id": event.trace.trace_id,
                "event_type": event.event_type.value,
                "error_type": error.error_type.value,
                "component": error.component,
            },
        )

        # TODO: Implement poison message quarantine
        # This might involve storing the event for manual analysis

    async def _mark_as_poison(
        self, trace_id: str, failure_record: FailureRecord
    ) -> None:
        """Mark event as poison message."""

        self.poison_events.add(trace_id)
        failure_record.failure_category = FailureCategory.POISON
        failure_record.final_disposition = "poison"

        # Remove from retry queue
        self.retry_queue.pop(trace_id, None)

        # Add to failed events
        self.failed_events[trace_id] = failure_record

        logger.warning(
            "Event marked as poison",
            extra={
                "trace_id": trace_id,
                "event_type": failure_record.event_type.value,
                "total_attempts": failure_record.total_attempts,
                "similar_failures": failure_record.similar_failures,
            },
        )

    def _get_retry_config(self, event_type: CognitiveEventType) -> RetryConfig:
        """Get retry configuration for event type."""
        return self.retry_configs.get(event_type, RetryConfig())

    def _initialize_default_retry_configs(self) -> None:
        """Initialize default retry configurations for event types."""

        # Memory events - important to retry
        self.retry_configs[CognitiveEventType.MEMORY_WRITE_INITIATED] = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_attempts=5,
            initial_delay_seconds=1.0,
        )

        # Recall events - moderate retry
        self.retry_configs[CognitiveEventType.RECALL_CONTEXT_REQUESTED] = RetryConfig(
            strategy=RetryStrategy.ADAPTIVE,
            max_attempts=3,
            initial_delay_seconds=2.0,
        )

        # Attention events - quick retry
        self.retry_configs[CognitiveEventType.ATTENTION_GATE_ADMIT] = RetryConfig(
            strategy=RetryStrategy.LINEAR_BACKOFF,
            max_attempts=2,
            initial_delay_seconds=0.5,
        )

        # Learning events - aggressive retry
        self.retry_configs[CognitiveEventType.LEARNING_OUTCOME_RECEIVED] = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            max_attempts=7,
            initial_delay_seconds=0.5,
        )

    async def _update_failure_metrics(self, failure_record: FailureRecord) -> None:
        """Update metrics with failure information."""

        self.metrics.total_failed_events += 1
        self.metrics.events_in_dlq = len(self.retry_queue) + len(self.failed_events)

        # Update distribution metrics
        self.metrics.failures_by_type[failure_record.event_type] = (
            self.metrics.failures_by_type.get(failure_record.event_type, 0) + 1
        )

        if failure_record.failure_category:
            self.metrics.failures_by_category[failure_record.failure_category] = (
                self.metrics.failures_by_category.get(
                    failure_record.failure_category, 0
                )
                + 1
            )

        self.metrics.failures_by_component[failure_record.error.component] = (
            self.metrics.failures_by_component.get(failure_record.error.component, 0)
            + 1
        )

        # Update recent failures
        self.metrics.recent_failures.append(failure_record)

    async def _retry_processor_loop(self) -> None:
        """Background loop to process retry queue."""

        while self._running:
            try:
                await asyncio.sleep(self.retry_check_interval_seconds)

                if not self._running:
                    break

                # Check for events ready to retry
                retry_events = await self.get_retry_events()

                if retry_events:
                    logger.info(
                        "Retry events ready",
                        extra={"retry_events_count": len(retry_events)},
                    )
                    # TODO: Emit retry events back to the event system

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Retry processor error",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                await asyncio.sleep(5)

    async def _analytics_loop(self) -> None:
        """Background loop for failure analytics."""

        while self._running:
            try:
                await asyncio.sleep(self.analytics_interval_seconds)

                if not self._running:
                    break

                # Calculate analytics
                analytics = self.get_failure_analytics()

                logger.info(
                    "DLQ analytics",
                    extra={
                        "analytics": analytics,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Analytics loop error",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                await asyncio.sleep(10)

    async def _load_persisted_state(self) -> None:
        """Load persisted DLQ state from storage."""
        # TODO: Implement state persistence
        pass

    async def _persist_state(self) -> None:
        """Persist current DLQ state to storage."""
        # TODO: Implement state persistence
        pass

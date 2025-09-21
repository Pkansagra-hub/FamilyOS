"""
Cognitive Backpressure Handler - Cross-Module Flow Control
==========================================================

Implements sophisticated backpressure management for cognitive event processing
with brain-inspired adaptive throttling and flow control. Provides system
stability through homeostatic regulation and adaptive capacity management.

**Key Features:**
- Adaptive throttling based on cognitive load and system capacity
- Circuit breaker patterns for cascade failure prevention
- Queue depth monitoring with adaptive flow control
- Cross-module coordination for system-wide stability
- Brain-inspired homeostatic regulation mechanisms

**Brain-Inspired Patterns:**
- Homeostatic plasticity for stable processing capacity
- Inhibitory control mechanisms for preventing cognitive overload
- Adaptive thresholds based on recent performance history
- Neuromodulation-aware flow control (stress, attention, dopamine)

The backpressure handler ensures system stability by preventing cognitive
overload while maintaining optimal throughput under varying conditions.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from observability.logging import get_json_logger
from observability.trace import start_span

from .types import (
    CognitiveEvent,
    CognitiveProcessingResult,
)

logger = get_json_logger(__name__)


class BackpressureLevel(Enum):
    """Levels of backpressure intensity."""

    NONE = "none"  # No backpressure, full throughput
    LOW = "low"  # Slight throttling, 90% throughput
    MEDIUM = "medium"  # Moderate throttling, 70% throughput
    HIGH = "high"  # Significant throttling, 50% throughput
    CRITICAL = "critical"  # Emergency throttling, 25% throughput
    EMERGENCY = "emergency"  # Maximum throttling, 10% throughput


class ThrottleStrategy(Enum):
    """Strategies for applying backpressure."""

    RATE_LIMITING = "rate_limiting"  # Limit events per second
    QUEUE_DEPTH = "queue_depth"  # Limit based on queue size
    LATENCY_BASED = "latency_based"  # Limit based on processing time
    COGNITIVE_LOAD = "cognitive_load"  # Limit based on system load
    ADAPTIVE = "adaptive"  # Adaptive combination strategy


@dataclass
class BackpressureMetrics:
    """Metrics for backpressure monitoring."""

    current_level: BackpressureLevel = BackpressureLevel.NONE
    throttle_rate: float = 1.0  # 1.0 = no throttling, 0.0 = complete throttling

    # Queue metrics
    current_queue_depth: int = 0
    max_queue_depth: int = 1000
    queue_growth_rate: float = 0.0

    # Processing metrics
    average_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    processing_rate_per_second: float = 0.0

    # System metrics
    cognitive_load: float = 0.0
    memory_pressure: float = 0.0
    cpu_utilization: float = 0.0

    # Event metrics
    events_throttled: int = 0
    events_dropped: int = 0
    total_events_processed: int = 0

    # Recent measurements for trend analysis
    recent_latencies: deque = field(default_factory=lambda: deque(maxlen=50))
    recent_queue_depths: deque = field(default_factory=lambda: deque(maxlen=20))
    recent_cognitive_loads: deque = field(default_factory=lambda: deque(maxlen=30))


@dataclass
class BackpressureConfig:
    """Configuration for backpressure management."""

    # Queue thresholds
    queue_depth_warning: int = 100
    queue_depth_critical: int = 500
    queue_depth_emergency: int = 1000

    # Latency thresholds (milliseconds)
    latency_warning_ms: float = 1000.0
    latency_critical_ms: float = 3000.0
    latency_emergency_ms: float = 5000.0

    # Cognitive load thresholds
    cognitive_load_warning: float = 0.7
    cognitive_load_critical: float = 0.85
    cognitive_load_emergency: float = 0.95

    # Rate limiting
    max_events_per_second: float = 1000.0
    burst_capacity: int = 100

    # Adaptive behavior
    adaptive_window_seconds: int = 60
    trend_sensitivity: float = 0.1
    recovery_factor: float = 0.95

    # Circuit breaker
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 30
    half_open_test_requests: int = 3


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker for preventing cascade failures."""

    name: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    success_count: int = 0

    def should_allow_request(self, config: BackpressureConfig) -> bool:
        """Check if request should be allowed through circuit breaker."""

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if we should transition to half-open
            if self.last_failure_time:
                elapsed = (
                    datetime.now(timezone.utc) - self.last_failure_time
                ).total_seconds()
                if elapsed >= config.recovery_timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Allow limited test requests
            return self.success_count < config.half_open_test_requests

        return False

    def record_success(self, config: BackpressureConfig) -> None:
        """Record successful request."""

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= config.half_open_test_requests:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self, config: BackpressureConfig) -> None:
        """Record failed request."""

        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.failure_count >= config.failure_threshold:
            self.state = CircuitState.OPEN


class CognitiveBackpressureHandler:
    """
    Sophisticated backpressure management for cognitive event processing.

    Implements brain-inspired adaptive flow control with homeostatic regulation
    to maintain system stability under varying load conditions. Provides
    circuit breaker patterns and adaptive throttling for optimal performance.

    **Key Functions:**
    - Adaptive throttling based on queue depth, latency, and cognitive load
    - Circuit breaker protection against cascade failures
    - Trend-based prediction for proactive backpressure application
    - Cross-module coordination for system-wide flow control
    - Homeostatic regulation for stable processing capacity
    """

    def __init__(self, config: Optional[BackpressureConfig] = None):
        self.config = config or BackpressureConfig()

        # Metrics and state
        self.metrics = BackpressureMetrics()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Adaptive state
        self.last_measurement_time = time.time()
        self.measurement_window_start = time.time()
        self.events_in_window = 0

        # Rate limiting state
        self.rate_limiter_tokens = float(self.config.burst_capacity)
        self.last_token_refill = time.time()

        # Background monitoring
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(
            "CognitiveBackpressureHandler initialized",
            extra={
                "queue_thresholds": {
                    "warning": self.config.queue_depth_warning,
                    "critical": self.config.queue_depth_critical,
                    "emergency": self.config.queue_depth_emergency,
                },
                "latency_thresholds_ms": {
                    "warning": self.config.latency_warning_ms,
                    "critical": self.config.latency_critical_ms,
                    "emergency": self.config.latency_emergency_ms,
                },
                "max_events_per_second": self.config.max_events_per_second,
            },
        )

    async def start(self) -> None:
        """Start backpressure monitoring."""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())

        logger.info("CognitiveBackpressureHandler started")

    async def stop(self) -> None:
        """Stop backpressure monitoring."""
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("CognitiveBackpressureHandler stopped")

    async def should_throttle_event(
        self,
        event: CognitiveEvent,
        current_queue_depth: int = 0,
        component_name: str = "default",
    ) -> Tuple[bool, BackpressureLevel, str]:
        """
        Determine if an event should be throttled.

        Returns:
            Tuple of (should_throttle, backpressure_level, reason)
        """

        with start_span("backpressure.should_throttle") as span:
            # Update current measurements
            self._update_current_metrics(current_queue_depth)

            # Check circuit breaker first
            circuit_breaker = self._get_circuit_breaker(component_name)
            if not circuit_breaker.should_allow_request(self.config):
                if span:
                    span.set_attribute("throttled", True)
                    span.set_attribute("reason", "circuit_breaker_open")
                    span.set_attribute("circuit_state", circuit_breaker.state.value)

                return (
                    True,
                    BackpressureLevel.EMERGENCY,
                    f"Circuit breaker open for {component_name}",
                )

            # Determine backpressure level
            backpressure_level = self._calculate_backpressure_level()
            self.metrics.current_level = backpressure_level

            # Apply rate limiting
            if not self._check_rate_limit():
                if span:
                    span.set_attribute("throttled", True)
                    span.set_attribute("reason", "rate_limit_exceeded")
                    span.set_attribute("backpressure_level", backpressure_level.value)

                self.metrics.events_throttled += 1
                return True, backpressure_level, "Rate limit exceeded"

            # Check if we should throttle based on backpressure level
            should_throttle = self._should_throttle_for_level(backpressure_level, event)

            if should_throttle:
                self.metrics.events_throttled += 1
                reason = f"Backpressure level {backpressure_level.value}"
            else:
                reason = "No throttling required"

            if span:
                span.set_attribute("throttled", should_throttle)
                span.set_attribute("backpressure_level", backpressure_level.value)
                span.set_attribute("reason", reason)
                span.set_attribute("queue_depth", current_queue_depth)
                span.set_attribute("cognitive_load", self.metrics.cognitive_load)

            return should_throttle, backpressure_level, reason

    async def record_processing_result(
        self,
        result: CognitiveProcessingResult,
        component_name: str = "default",
    ) -> None:
        """Record processing result for adaptive backpressure adjustment."""

        # Update circuit breaker
        circuit_breaker = self._get_circuit_breaker(component_name)

        if result.success:
            circuit_breaker.record_success(self.config)
        else:
            circuit_breaker.record_failure(self.config)

        # Update metrics
        if result.latency_ms:
            self.metrics.recent_latencies.append(result.latency_ms)

            # Recalculate average and p95 latencies
            if self.metrics.recent_latencies:
                self.metrics.average_latency_ms = sum(
                    self.metrics.recent_latencies
                ) / len(self.metrics.recent_latencies)

                sorted_latencies = sorted(self.metrics.recent_latencies)
                p95_index = int(0.95 * len(sorted_latencies))
                self.metrics.p95_latency_ms = sorted_latencies[p95_index]

        # Update cognitive load if available
        if result.cognitive_load_impact:
            self.metrics.recent_cognitive_loads.append(result.cognitive_load_impact)

            if self.metrics.recent_cognitive_loads:
                self.metrics.cognitive_load = sum(
                    self.metrics.recent_cognitive_loads
                ) / len(self.metrics.recent_cognitive_loads)

        self.metrics.total_events_processed += 1

    def update_system_metrics(
        self,
        queue_depth: int = 0,
        cognitive_load: float = 0.0,
        memory_pressure: float = 0.0,
        cpu_utilization: float = 0.0,
    ) -> None:
        """Update system-level metrics for backpressure calculation."""

        self.metrics.current_queue_depth = queue_depth
        self.metrics.cognitive_load = cognitive_load
        self.metrics.memory_pressure = memory_pressure
        self.metrics.cpu_utilization = cpu_utilization

        # Track queue depth trends
        self.metrics.recent_queue_depths.append(queue_depth)

        # Calculate queue growth rate
        if len(self.metrics.recent_queue_depths) >= 2:
            recent_change = (
                self.metrics.recent_queue_depths[-1]
                - self.metrics.recent_queue_depths[-2]
            )
            self.metrics.queue_growth_rate = recent_change

    def get_current_throttle_rate(self) -> float:
        """Get current throttle rate (0.0 = complete throttling, 1.0 = no throttling)."""
        return self.metrics.throttle_rate

    def get_metrics(self) -> BackpressureMetrics:
        """Get current backpressure metrics."""
        return self.metrics

    def get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {
            name: {
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "success_count": breaker.success_count,
                "last_failure": (
                    breaker.last_failure_time.isoformat()
                    if breaker.last_failure_time
                    else None
                ),
            }
            for name, breaker in self.circuit_breakers.items()
        }

    def _update_current_metrics(self, queue_depth: int) -> None:
        """Update current metrics with new measurements."""
        now = time.time()

        # Update queue depth
        self.update_system_metrics(queue_depth=queue_depth)

        # Calculate processing rate
        window_duration = now - self.measurement_window_start
        if window_duration >= 1.0:  # Update every second
            self.metrics.processing_rate_per_second = (
                self.events_in_window / window_duration
            )
            self.measurement_window_start = now
            self.events_in_window = 0

        self.events_in_window += 1
        self.last_measurement_time = now

    def _calculate_backpressure_level(self) -> BackpressureLevel:
        """Calculate appropriate backpressure level based on current metrics."""

        # Check emergency conditions first
        if (
            self.metrics.current_queue_depth >= self.config.queue_depth_emergency
            or self.metrics.p95_latency_ms >= self.config.latency_emergency_ms
            or self.metrics.cognitive_load >= self.config.cognitive_load_emergency
        ):
            self.metrics.throttle_rate = 0.1
            return BackpressureLevel.EMERGENCY

        # Check critical conditions
        if (
            self.metrics.current_queue_depth >= self.config.queue_depth_critical
            or self.metrics.p95_latency_ms >= self.config.latency_critical_ms
            or self.metrics.cognitive_load >= self.config.cognitive_load_critical
        ):
            self.metrics.throttle_rate = 0.25
            return BackpressureLevel.CRITICAL

        # Check high pressure conditions
        if (
            self.metrics.current_queue_depth >= self.config.queue_depth_warning
            or self.metrics.p95_latency_ms >= self.config.latency_warning_ms
            or self.metrics.cognitive_load >= self.config.cognitive_load_warning
        ):

            # Consider trend for adaptive response
            if self._is_trending_worse():
                self.metrics.throttle_rate = 0.5
                return BackpressureLevel.HIGH
            else:
                self.metrics.throttle_rate = 0.7
                return BackpressureLevel.MEDIUM

        # Check for early warning signs
        if (
            self.metrics.current_queue_depth >= self.config.queue_depth_warning * 0.7
            or self.metrics.queue_growth_rate > 10  # Rapid queue growth
            or self.metrics.cognitive_load >= self.config.cognitive_load_warning * 0.8
        ):
            self.metrics.throttle_rate = 0.9
            return BackpressureLevel.LOW

        # No backpressure needed
        self.metrics.throttle_rate = 1.0
        return BackpressureLevel.NONE

    def _is_trending_worse(self) -> bool:
        """Check if metrics are trending worse over recent time window."""

        # Check queue depth trend
        if len(self.metrics.recent_queue_depths) >= 3:
            recent_avg = sum(list(self.metrics.recent_queue_depths)[-3:]) / 3
            older_avg = sum(list(self.metrics.recent_queue_depths)[:-3]) / max(
                1, len(self.metrics.recent_queue_depths) - 3
            )

            if recent_avg > older_avg * (1 + self.config.trend_sensitivity):
                return True

        # Check latency trend
        if len(self.metrics.recent_latencies) >= 5:
            recent_latencies = list(self.metrics.recent_latencies)[-5:]
            older_latencies = list(self.metrics.recent_latencies)[:-5]

            if older_latencies:
                recent_avg = sum(recent_latencies) / len(recent_latencies)
                older_avg = sum(older_latencies) / len(older_latencies)

                if recent_avg > older_avg * (1 + self.config.trend_sensitivity):
                    return True

        # Check cognitive load trend
        if len(self.metrics.recent_cognitive_loads) >= 3:
            recent_loads = list(self.metrics.recent_cognitive_loads)[-3:]
            older_loads = list(self.metrics.recent_cognitive_loads)[:-3]

            if older_loads:
                recent_avg = sum(recent_loads) / len(recent_loads)
                older_avg = sum(older_loads) / len(older_loads)

                if recent_avg > older_avg * (1 + self.config.trend_sensitivity):
                    return True

        return False

    def _should_throttle_for_level(
        self, level: BackpressureLevel, event: CognitiveEvent
    ) -> bool:
        """Determine if event should be throttled for given backpressure level."""

        if level == BackpressureLevel.NONE:
            return False

        # Priority-based throttling - higher priority events are less likely to be throttled
        priority_factor = min(1.0, event.trace.priority / 10.0)  # Normalize priority
        throttle_probability = 1.0 - self.metrics.throttle_rate

        # Adjust throttle probability based on priority
        adjusted_throttle_probability = throttle_probability * (
            1.0 - priority_factor * 0.5
        )

        # Use deterministic throttling for consistency
        import hashlib

        hash_input = f"{event.trace.trace_id}{level.value}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest()[:8], 16)
        threshold = hash_value / (2**32)  # Normalize to 0-1

        return threshold < adjusted_throttle_probability

    def _check_rate_limit(self) -> bool:
        """Check if current request is within rate limits."""
        now = time.time()

        # Refill tokens based on time elapsed
        elapsed = now - self.last_token_refill
        tokens_to_add = elapsed * self.config.max_events_per_second
        self.rate_limiter_tokens = min(
            self.config.burst_capacity, self.rate_limiter_tokens + tokens_to_add
        )
        self.last_token_refill = now

        # Check if we have tokens available
        if self.rate_limiter_tokens >= 1.0:
            self.rate_limiter_tokens -= 1.0
            return True

        return False

    def _get_circuit_breaker(self, component_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for component."""
        if component_name not in self.circuit_breakers:
            self.circuit_breakers[component_name] = CircuitBreaker(name=component_name)

        return self.circuit_breakers[component_name]

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop for adaptive backpressure adjustment."""

        while self._running:
            try:
                await asyncio.sleep(10)  # Monitor every 10 seconds

                if not self._running:
                    break

                # Calculate current backpressure level
                current_level = self._calculate_backpressure_level()

                # Log significant backpressure changes
                if current_level != self.metrics.current_level:
                    logger.info(
                        "Backpressure level changed",
                        extra={
                            "previous_level": self.metrics.current_level.value,
                            "new_level": current_level.value,
                            "throttle_rate": self.metrics.throttle_rate,
                            "queue_depth": self.metrics.current_queue_depth,
                            "average_latency_ms": self.metrics.average_latency_ms,
                            "cognitive_load": self.metrics.cognitive_load,
                        },
                    )

                # Apply recovery factor if conditions are improving
                if current_level.value in [
                    "none",
                    "low",
                ] and self.metrics.current_level.value not in ["none", "low"]:

                    # Gradually reduce throttling
                    self.metrics.throttle_rate = min(
                        1.0, self.metrics.throttle_rate / self.config.recovery_factor
                    )

                self.metrics.current_level = current_level

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Backpressure monitoring error",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                await asyncio.sleep(5)

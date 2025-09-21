"""
Cognitive Load Monitor - Executive Control Resource Management
============================================================

This module implements cognitive load monitoring for working memory, inspired
by the brain's executive control mechanisms that track and regulate cognitive
resource allocation to maintain optimal performance and prevent overload.

**Neuroscience Inspiration:**
The anterior cingulate cortex (ACC) and dorsolateral prefrontal cortex (dlPFC)
monitor cognitive demand and resource availability, implementing metacognitive
control over working memory operations. This system prevents cognitive overload
and optimizes resource allocation across competing tasks.

**Research Backing:**
- Botvinick et al. (2001): Conflict monitoring and cognitive control
- Kool et al. (2010): Decision making and the avoidance of cognitive demand
- Shenhav et al. (2013): The expected value of control
- Kurzban et al. (2013): An opportunity cost model of subjective effort

The implementation provides real-time load monitoring, adaptive thresholding,
and performance optimization recommendations for working memory efficiency.
"""

import asyncio
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from observability.logging import get_json_logger
from observability.trace import start_span

from .manager import Priority, WorkingMemoryItem, WorkingMemoryType

logger = get_json_logger(__name__)


class LoadLevel(Enum):
    """Cognitive load level classifications."""

    MINIMAL = 1  # Very low load, can handle more
    LOW = 2  # Low load, comfortable operation
    MODERATE = 3  # Moderate load, optimal performance
    HIGH = 4  # High load, approaching limits
    CRITICAL = 5  # Critical load, performance degradation


@dataclass
class LoadMetrics:
    """Cognitive load measurement metrics."""

    capacity_utilization: float = 0.0  # Working memory capacity used
    processing_complexity: float = 0.0  # Complexity of current operations
    attention_fragmentation: float = 0.0  # Attention divided across tasks
    temporal_pressure: float = 0.0  # Time pressure indicators
    interference_level: float = 0.0  # Task interference/conflict
    resource_competition: float = 0.0  # Competition for cognitive resources
    overall_load: float = 0.0  # Combined load score
    load_level: LoadLevel = LoadLevel.MINIMAL


@dataclass
class LoadThresholds:
    """Adaptive thresholds for load management."""

    minimal_threshold: float = 0.2
    low_threshold: float = 0.4
    moderate_threshold: float = 0.6
    high_threshold: float = 0.8
    critical_threshold: float = 0.95

    # Adaptive adjustment parameters
    adaptation_rate: float = 0.05
    performance_window: int = 10
    stress_amplification: float = 1.2


@dataclass
class PerformanceIndicators:
    """Performance indicators for load optimization."""

    response_time_ms: float = 0.0
    accuracy_rate: float = 1.0
    throughput_items_per_second: float = 0.0
    error_rate: float = 0.0
    cognitive_efficiency: float = 1.0
    user_satisfaction: float = 1.0


@dataclass
class LoadAlert:
    """Alert for cognitive load threshold violations."""

    timestamp: datetime
    load_level: LoadLevel
    load_value: float
    threshold_violated: str
    contributing_factors: List[str]
    recommended_actions: List[str]
    severity: str


class CognitiveLoadMonitor:
    """
    Implements cognitive load monitoring for working memory optimization.

    Provides real-time monitoring of cognitive load across multiple dimensions,
    adaptive threshold management, and performance optimization recommendations
    to maintain optimal working memory efficiency.

    **Key Functions:**
    - Multi-dimensional load measurement
    - Adaptive threshold management
    - Performance correlation analysis
    - Load prediction and early warning
    - Optimization recommendations
    """

    def __init__(
        self,
        thresholds: Optional[LoadThresholds] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.thresholds = thresholds or LoadThresholds()
        self.config = config or {}

        # Load tracking
        self.current_metrics = LoadMetrics()
        self.metrics_history: List[LoadMetrics] = []
        self.performance_history: List[PerformanceIndicators] = []

        # Alert system
        self.active_alerts: List[LoadAlert] = []
        self.alert_callbacks: List[Callable[[LoadAlert], None]] = []

        # Performance tracking
        self.load_events: List[Dict[str, Any]] = []
        self.optimization_suggestions: List[Dict[str, Any]] = []

        # Background monitoring
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task[None]] = None
        self._monitoring_interval = self.config.get("monitoring_interval_seconds", 5)

        logger.info(
            "CognitiveLoadMonitor initialized",
            extra={
                "monitoring_interval": self._monitoring_interval,
                "thresholds": {
                    "minimal": self.thresholds.minimal_threshold,
                    "low": self.thresholds.low_threshold,
                    "moderate": self.thresholds.moderate_threshold,
                    "high": self.thresholds.high_threshold,
                    "critical": self.thresholds.critical_threshold,
                },
            },
        )

    async def start_monitoring(self) -> None:
        """Start background cognitive load monitoring."""

        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info("Cognitive load monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop background cognitive load monitoring."""

        self._monitoring_active = False

        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Cognitive load monitoring stopped")

    async def measure_cognitive_load(
        self,
        working_memory_items: List[WorkingMemoryItem],
        session_count: int,
        processing_operations: Optional[List[Dict[str, Any]]] = None,
        performance_data: Optional[PerformanceIndicators] = None,
    ) -> LoadMetrics:
        """
        Measure current cognitive load across multiple dimensions.

        Evaluates cognitive load by analyzing working memory utilization,
        processing complexity, attention fragmentation, and other factors
        that contribute to overall cognitive demand.

        Args:
            working_memory_items: Current working memory contents
            session_count: Number of active sessions
            processing_operations: Current processing operations
            performance_data: Current performance indicators

        Returns:
            LoadMetrics with comprehensive load assessment
        """
        with start_span("working_memory.cognitive_load.measure") as span:
            try:
                # Calculate capacity utilization
                capacity_util = await self._calculate_capacity_utilization(
                    working_memory_items
                )

                # Calculate processing complexity
                complexity = await self._calculate_processing_complexity(
                    working_memory_items, processing_operations
                )

                # Calculate attention fragmentation
                fragmentation = await self._calculate_attention_fragmentation(
                    working_memory_items, session_count
                )

                # Calculate temporal pressure
                temporal_pressure = await self._calculate_temporal_pressure(
                    working_memory_items, performance_data
                )

                # Calculate interference level
                interference = await self._calculate_interference_level(
                    working_memory_items
                )

                # Calculate resource competition
                competition = await self._calculate_resource_competition(
                    working_memory_items, session_count
                )

                # Calculate overall load
                overall_load = await self._calculate_overall_load(
                    capacity_util,
                    complexity,
                    fragmentation,
                    temporal_pressure,
                    interference,
                    competition,
                )

                # Determine load level
                load_level = self._determine_load_level(overall_load)

                # Create metrics object
                metrics = LoadMetrics(
                    capacity_utilization=capacity_util,
                    processing_complexity=complexity,
                    attention_fragmentation=fragmentation,
                    temporal_pressure=temporal_pressure,
                    interference_level=interference,
                    resource_competition=competition,
                    overall_load=overall_load,
                    load_level=load_level,
                )

                # Update current metrics
                self.current_metrics = metrics

                # Add to history
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > 200:
                    self.metrics_history = self.metrics_history[-100:]

                # Check for alerts
                await self._check_load_alerts(metrics)

                # Update performance tracking
                if performance_data:
                    self.performance_history.append(performance_data)
                    if len(self.performance_history) > 100:
                        self.performance_history = self.performance_history[-50:]

                if span:
                    span.set_attribute("overall_load", overall_load)
                    span.set_attribute("load_level", load_level.value)
                    span.set_attribute("capacity_utilization", capacity_util)

                logger.debug(
                    "Cognitive load measured",
                    extra={
                        "overall_load": overall_load,
                        "load_level": load_level.name,
                        "capacity_utilization": capacity_util,
                        "processing_complexity": complexity,
                        "attention_fragmentation": fragmentation,
                        "items_count": len(working_memory_items),
                        "session_count": session_count,
                    },
                )

                return metrics

            except Exception as e:
                logger.error(
                    "Failed to measure cognitive load",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "items_count": len(working_memory_items),
                        "session_count": session_count,
                    },
                )

                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))

                # Return safe default
                return LoadMetrics()

    async def _calculate_capacity_utilization(
        self, items: List[WorkingMemoryItem]
    ) -> float:
        """Calculate working memory capacity utilization."""

        if not items:
            return 0.0

        # Base utilization (7±2 items capacity)
        base_capacity = 7
        base_utilization = len(items) / base_capacity

        # Adjust for priority distribution (high priority items "cost" more)
        priority_weights = {
            Priority.CRITICAL: 1.5,
            Priority.HIGH: 1.2,
            Priority.MEDIUM: 1.0,
            Priority.LOW: 0.8,
            Priority.MINIMAL: 0.6,
        }

        weighted_count = sum(priority_weights.get(item.priority, 1.0) for item in items)
        weighted_utilization = weighted_count / (
            base_capacity * 1.2
        )  # Adjust capacity for weights

        # Combine base and weighted utilization
        utilization = (base_utilization * 0.6) + (weighted_utilization * 0.4)

        return min(1.0, utilization)

    async def _calculate_processing_complexity(
        self, items: List[WorkingMemoryItem], operations: Optional[List[Dict[str, Any]]]
    ) -> float:
        """Calculate processing complexity based on content and operations."""

        if not items:
            return 0.0

        # Content type complexity weights
        type_complexity = {
            WorkingMemoryType.GOAL: 0.9,  # Goals are complex to maintain
            WorkingMemoryType.COMPUTATION: 0.8,  # Computations are complex
            WorkingMemoryType.CONTEXT: 0.6,  # Context moderately complex
            WorkingMemoryType.RETRIEVAL: 0.5,  # Retrieved content moderate
            WorkingMemoryType.ATTENTION: 0.4,  # Attention items simpler
            WorkingMemoryType.BUFFER: 0.3,  # Buffer items simplest
        }

        # Calculate content complexity
        content_complexity = 0.0
        for item in items:
            item_complexity = type_complexity.get(item.content_type, 0.5)
            # Adjust for activation (higher activation = more processing)
            activation_factor = item.calculate_activation()
            weighted_complexity = item_complexity * (0.5 + 0.5 * activation_factor)
            content_complexity += weighted_complexity

        content_complexity /= len(items)

        # Factor in active operations
        operation_complexity = 0.0
        if operations:
            operation_weights = {
                "search": 0.7,
                "compare": 0.6,
                "transform": 0.8,
                "analyze": 0.9,
                "synthesize": 1.0,
            }

            total_ops = len(operations)
            weighted_ops = sum(
                operation_weights.get(op.get("type", ""), 0.5) for op in operations
            )
            operation_complexity = min(1.0, weighted_ops / max(1, total_ops))

        # Combine complexity factors
        overall_complexity = (content_complexity * 0.7) + (operation_complexity * 0.3)

        return min(1.0, overall_complexity)

    async def _calculate_attention_fragmentation(
        self, items: List[WorkingMemoryItem], session_count: int
    ) -> float:
        """Calculate attention fragmentation across sessions and tasks."""

        if not items:
            return 0.0

        # Session fragmentation (more sessions = more fragmentation)
        session_fragmentation = min(
            1.0, session_count / 3.0
        )  # Normalize to 3 sessions max

        # Priority distribution fragmentation
        priority_counts = {}
        for item in items:
            priority_counts[item.priority] = priority_counts.get(item.priority, 0) + 1

        # Calculate entropy of priority distribution
        total_items = len(items)
        priority_entropy = 0.0
        for count in priority_counts.values():
            if count > 0:
                p = count / total_items
                priority_entropy -= p * (p.bit_length() - 1) if p > 0 else 0

        # Normalize entropy (max entropy for 5 priorities ≈ 2.32)
        normalized_entropy = min(1.0, priority_entropy / 2.32)

        # Content type fragmentation
        type_counts = {}
        for item in items:
            type_counts[item.content_type] = type_counts.get(item.content_type, 0) + 1

        type_fragmentation = len(type_counts) / 6.0  # 6 possible types

        # Combine fragmentation factors
        overall_fragmentation = (
            session_fragmentation * 0.4
            + normalized_entropy * 0.3
            + type_fragmentation * 0.3
        )

        return min(1.0, overall_fragmentation)

    async def _calculate_temporal_pressure(
        self,
        items: List[WorkingMemoryItem],
        performance_data: Optional[PerformanceIndicators],
    ) -> float:
        """Calculate temporal pressure from urgency and timing constraints."""

        if not items:
            return 0.0

        now = datetime.now(timezone.utc)

        # Age-based pressure (older items create pressure)
        age_pressures = []
        for item in items:
            age_hours = (now - item.created_at).total_seconds() / 3600
            # Pressure increases exponentially with age for high priority items
            if item.priority.value >= Priority.HIGH.value:
                age_pressure = min(1.0, (age_hours / 24.0) ** 2)  # 24 hours max
            else:
                age_pressure = min(1.0, age_hours / 48.0)  # 48 hours for lower priority
            age_pressures.append(age_pressure)

        avg_age_pressure = (
            sum(age_pressures) / len(age_pressures) if age_pressures else 0.0
        )

        # Performance-based pressure
        performance_pressure = 0.0
        if performance_data:
            # High response time = pressure
            if performance_data.response_time_ms > 100:
                response_pressure = min(1.0, performance_data.response_time_ms / 1000.0)
            else:
                response_pressure = 0.0

            # Low accuracy = pressure
            accuracy_pressure = max(0.0, 1.0 - performance_data.accuracy_rate)

            # High error rate = pressure
            error_pressure = min(1.0, performance_data.error_rate * 2.0)

            performance_pressure = (
                response_pressure + accuracy_pressure + error_pressure
            ) / 3.0

        # Combine temporal pressure factors
        overall_pressure = (avg_age_pressure * 0.6) + (performance_pressure * 0.4)

        return min(1.0, overall_pressure)

    async def _calculate_interference_level(
        self, items: List[WorkingMemoryItem]
    ) -> float:
        """Calculate interference between working memory items."""

        if len(items) < 2:
            return 0.0

        # Simple interference calculation based on content similarity
        # (In production, this could use semantic similarity)

        interference_score = 0.0
        comparisons = 0

        for i, item1 in enumerate(items):
            for item2 in items[i + 1 :]:
                comparisons += 1

                # Content type interference
                type_interference = 0.0
                if item1.content_type == item2.content_type:
                    type_interference = 0.3

                # Priority interference (similar priorities compete)
                priority_diff = abs(item1.priority.value - item2.priority.value)
                priority_interference = max(0.0, 0.5 - (priority_diff * 0.1))

                # Session interference (different sessions = less interference)
                session_interference = (
                    0.4 if item1.session_id == item2.session_id else 0.1
                )

                # Activation interference (high activation items interfere more)
                activation_product = (
                    item1.calculate_activation() * item2.calculate_activation()
                )
                activation_interference = activation_product * 0.3

                item_interference = (
                    type_interference
                    + priority_interference
                    + session_interference
                    + activation_interference
                )

                interference_score += min(1.0, item_interference)

        # Normalize by number of comparisons
        if comparisons > 0:
            normalized_interference = interference_score / comparisons
        else:
            normalized_interference = 0.0

        return min(1.0, normalized_interference)

    async def _calculate_resource_competition(
        self, items: List[WorkingMemoryItem], session_count: int
    ) -> float:
        """Calculate competition for cognitive resources."""

        if not items:
            return 0.0

        # Session competition (more sessions = more competition)
        session_competition = min(1.0, session_count / 2.0)  # Normalize to 2 sessions

        # Priority competition (many high priority items compete)
        high_priority_count = sum(
            1 for item in items if item.priority.value >= Priority.HIGH.value
        )
        priority_competition = min(
            1.0, high_priority_count / 3.0
        )  # Normalize to 3 items

        # Activation competition (many active items compete)
        high_activation_count = sum(
            1 for item in items if item.calculate_activation() > 0.7
        )
        activation_competition = min(
            1.0, high_activation_count / 4.0
        )  # Normalize to 4 items

        # Content type diversity (different types compete for different resources)
        unique_types = len(set(item.content_type for item in items))
        type_competition = min(1.0, unique_types / 4.0)  # Normalize to 4 types

        # Combine competition factors
        overall_competition = (
            session_competition * 0.3
            + priority_competition * 0.3
            + activation_competition * 0.25
            + type_competition * 0.15
        )

        return min(1.0, overall_competition)

    async def _calculate_overall_load(
        self,
        capacity_util: float,
        complexity: float,
        fragmentation: float,
        temporal_pressure: float,
        interference: float,
        competition: float,
    ) -> float:
        """Calculate overall cognitive load from component factors."""

        # Weighted combination of load factors
        overall_load = (
            capacity_util * 0.25  # Capacity is fundamental
            + complexity * 0.20  # Processing complexity important
            + fragmentation * 0.15  # Attention fragmentation significant
            + temporal_pressure * 0.15  # Time pressure important
            + interference * 0.15  # Interference affects performance
            + competition * 0.10  # Resource competition moderate impact
        )

        # Apply nonlinear scaling (load compounds)
        # High loads become disproportionately worse
        if overall_load > 0.7:
            scaling_factor = 1.0 + ((overall_load - 0.7) * 0.5)
            overall_load = min(1.0, overall_load * scaling_factor)

        return overall_load

    def _determine_load_level(self, overall_load: float) -> LoadLevel:
        """Determine load level from overall load score."""

        if overall_load <= self.thresholds.minimal_threshold:
            return LoadLevel.MINIMAL
        elif overall_load <= self.thresholds.low_threshold:
            return LoadLevel.LOW
        elif overall_load <= self.thresholds.moderate_threshold:
            return LoadLevel.MODERATE
        elif overall_load <= self.thresholds.high_threshold:
            return LoadLevel.HIGH
        else:
            return LoadLevel.CRITICAL

    async def _check_load_alerts(self, metrics: LoadMetrics) -> None:
        """Check for load threshold violations and generate alerts."""

        alerts_to_add = []
        now = datetime.now(timezone.utc)

        # Check for threshold violations
        if metrics.load_level == LoadLevel.CRITICAL:
            alert = LoadAlert(
                timestamp=now,
                load_level=metrics.load_level,
                load_value=metrics.overall_load,
                threshold_violated="critical",
                contributing_factors=self._identify_load_factors(metrics),
                recommended_actions=self._generate_load_recommendations(metrics),
                severity="high",
            )
            alerts_to_add.append(alert)

        elif metrics.load_level == LoadLevel.HIGH:
            # Check if sustained high load
            recent_metrics = (
                self.metrics_history[-5:] if len(self.metrics_history) >= 5 else []
            )
            sustained_high = all(
                m.load_level.value >= LoadLevel.HIGH.value for m in recent_metrics
            )

            if sustained_high:
                alert = LoadAlert(
                    timestamp=now,
                    load_level=metrics.load_level,
                    load_value=metrics.overall_load,
                    threshold_violated="sustained_high",
                    contributing_factors=self._identify_load_factors(metrics),
                    recommended_actions=self._generate_load_recommendations(metrics),
                    severity="medium",
                )
                alerts_to_add.append(alert)

        # Add new alerts and notify callbacks
        for alert in alerts_to_add:
            self.active_alerts.append(alert)

            # Trigger alert callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(
                        "Alert callback failed",
                        extra={"error": str(e), "callback": str(callback)},
                    )

            logger.warning(
                "Cognitive load alert triggered",
                extra={
                    "load_level": alert.load_level.name,
                    "load_value": alert.load_value,
                    "threshold_violated": alert.threshold_violated,
                    "severity": alert.severity,
                    "contributing_factors": alert.contributing_factors,
                },
            )

        # Clean up old alerts (keep last 20)
        if len(self.active_alerts) > 20:
            self.active_alerts = self.active_alerts[-10:]

    def _identify_load_factors(self, metrics: LoadMetrics) -> List[str]:
        """Identify primary contributing factors to cognitive load."""

        factors = []

        if metrics.capacity_utilization > 0.8:
            factors.append("high_capacity_utilization")

        if metrics.processing_complexity > 0.7:
            factors.append("complex_processing")

        if metrics.attention_fragmentation > 0.6:
            factors.append("attention_fragmentation")

        if metrics.temporal_pressure > 0.7:
            factors.append("temporal_pressure")

        if metrics.interference_level > 0.5:
            factors.append("task_interference")

        if metrics.resource_competition > 0.6:
            factors.append("resource_competition")

        return factors

    def _generate_load_recommendations(self, metrics: LoadMetrics) -> List[str]:
        """Generate recommendations for reducing cognitive load."""

        recommendations = []

        if metrics.capacity_utilization > 0.8:
            recommendations.append("reduce_working_memory_items")
            recommendations.append("prioritize_critical_items_only")

        if metrics.attention_fragmentation > 0.6:
            recommendations.append("focus_on_single_session")
            recommendations.append("consolidate_similar_tasks")

        if metrics.processing_complexity > 0.7:
            recommendations.append("simplify_operations")
            recommendations.append("defer_complex_computations")

        if metrics.temporal_pressure > 0.7:
            recommendations.append("extend_processing_time")
            recommendations.append("reduce_urgency_requirements")

        if metrics.interference_level > 0.5:
            recommendations.append("separate_conflicting_tasks")
            recommendations.append("sequence_similar_operations")

        if metrics.resource_competition > 0.6:
            recommendations.append("reduce_concurrent_sessions")
            recommendations.append("schedule_resource_intensive_tasks")

        return recommendations

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop for continuous load assessment."""

        while self._monitoring_active:
            try:
                await asyncio.sleep(self._monitoring_interval)

                if not self._monitoring_active:
                    break

                # This would be called with actual working memory state
                # For now, just log that monitoring is running
                logger.debug(
                    "Cognitive load monitoring cycle",
                    extra={
                        "current_load": self.current_metrics.overall_load,
                        "load_level": self.current_metrics.load_level.name,
                        "active_alerts": len(self.active_alerts),
                    },
                )

                # Adaptive threshold adjustment
                await self._adjust_adaptive_thresholds()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Cognitive load monitoring error",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                await asyncio.sleep(1)

    async def _adjust_adaptive_thresholds(self) -> None:
        """Adjust thresholds based on performance history."""

        if len(self.performance_history) < 10:
            return

        recent_performance = self.performance_history[-10:]
        avg_accuracy = statistics.mean(p.accuracy_rate for p in recent_performance)
        avg_efficiency = statistics.mean(
            p.cognitive_efficiency for p in recent_performance
        )

        # If performance is consistently poor, lower thresholds
        if avg_accuracy < 0.8 or avg_efficiency < 0.7:
            adjustment = -self.thresholds.adaptation_rate
        # If performance is excellent, raise thresholds slightly
        elif avg_accuracy > 0.95 and avg_efficiency > 0.9:
            adjustment = self.thresholds.adaptation_rate * 0.5
        else:
            adjustment = 0.0

        if adjustment != 0.0:
            self.thresholds.high_threshold = max(
                0.5, min(0.9, self.thresholds.high_threshold + adjustment)
            )
            self.thresholds.critical_threshold = max(
                0.7, min(0.99, self.thresholds.critical_threshold + adjustment)
            )

            logger.debug(
                "Adaptive thresholds adjusted",
                extra={
                    "adjustment": adjustment,
                    "new_high_threshold": self.thresholds.high_threshold,
                    "new_critical_threshold": self.thresholds.critical_threshold,
                    "avg_accuracy": avg_accuracy,
                    "avg_efficiency": avg_efficiency,
                },
            )

    def add_alert_callback(self, callback: Callable[[LoadAlert], None]) -> None:
        """Add callback for load alerts."""
        self.alert_callbacks.append(callback)

    def remove_alert_callback(self, callback: Callable[[LoadAlert], None]) -> None:
        """Remove alert callback."""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)

    async def measure_cognitive_load_with_cache_metrics(
        self,
        working_memory_items: List[WorkingMemoryItem],
        session_count: int,
        processing_operations: Optional[List[Dict[str, Any]]] = None,
        performance_data: Optional[PerformanceIndicators] = None,
        cache_stats: Optional[Dict[str, Any]] = None,
    ) -> LoadMetrics:
        """
        Enhanced cognitive load measurement with hierarchical cache metrics.

        Incorporates cache performance into load calculations to provide
        more accurate assessment of cognitive resource utilization and
        system efficiency.

        Args:
            working_memory_items: Current working memory contents
            session_count: Number of active sessions
            processing_operations: Current processing operations
            performance_data: Current performance indicators
            cache_stats: Hierarchical cache performance statistics

        Returns:
            LoadMetrics with cache-aware load assessment
        """
        with start_span("working_memory.cognitive_load.measure_cache_aware") as span:
            try:
                # Start with base load measurement
                base_metrics = await self.measure_cognitive_load(
                    working_memory_items,
                    session_count,
                    processing_operations,
                    performance_data,
                )

                # Apply cache-aware adjustments if cache stats available
                if cache_stats:
                    cache_adjusted_metrics = await self._apply_cache_load_adjustments(
                        base_metrics, cache_stats
                    )

                    if span:
                        span.set_attribute("cache_aware", True)
                        span.set_attribute(
                            "cache_efficiency",
                            cache_stats.get("overall", {}).get("cache_efficiency", 0.0),
                        )
                        span.set_attribute(
                            "l1_hit_rate",
                            cache_stats.get("l1", {})
                            .get("metrics", {})
                            .get("hit_rate", 0.0),
                        )

                    return cache_adjusted_metrics
                else:
                    if span:
                        span.set_attribute("cache_aware", False)

                    return base_metrics

            except Exception as e:
                logger.error(
                    "Cache-aware cognitive load measurement failed",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "items_count": len(working_memory_items),
                        "session_count": session_count,
                    },
                )

                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))

                # Fallback to base measurement
                return await self.measure_cognitive_load(
                    working_memory_items,
                    session_count,
                    processing_operations,
                    performance_data,
                )

    async def _apply_cache_load_adjustments(
        self,
        base_metrics: LoadMetrics,
        cache_stats: Dict[str, Any],
    ) -> LoadMetrics:
        """Apply cache performance adjustments to cognitive load metrics."""

        # Calculate cache-specific load factors
        cache_load_factors = self._calculate_cache_load_factors(cache_stats)

        # Adjust capacity utilization based on cache efficiency
        cache_efficiency = cache_stats.get("overall", {}).get("cache_efficiency", 50.0)
        efficiency_factor = cache_efficiency / 100.0  # Normalize to 0-1

        # High cache efficiency reduces effective capacity pressure
        capacity_adjustment = base_metrics.capacity_utilization * (
            1.0 - (efficiency_factor * 0.2)
        )

        # Adjust processing complexity based on cache hit rates
        l1_hit_rate = (
            cache_stats.get("l1", {}).get("metrics", {}).get("hit_rate", 0.0) / 100.0
        )
        l2_hit_rate = (
            cache_stats.get("l2", {}).get("metrics", {}).get("hit_rate", 0.0) / 100.0
        )

        # High hit rates reduce processing complexity (faster access)
        avg_hit_rate = (l1_hit_rate + l2_hit_rate) / 2.0
        complexity_adjustment = base_metrics.processing_complexity * (
            1.0 - (avg_hit_rate * 0.15)
        )

        # Add cache pressure as a load factor
        cache_pressure = cache_load_factors.get("cache_pressure", 0.0)

        # Recalculate overall load with cache adjustments
        adjusted_overall_load = await self._calculate_overall_load_with_cache(
            capacity_adjustment,
            complexity_adjustment,
            base_metrics.attention_fragmentation,
            base_metrics.temporal_pressure,
            base_metrics.interference_level,
            base_metrics.resource_competition,
            cache_pressure,
        )

        # Create adjusted metrics
        adjusted_metrics = LoadMetrics(
            capacity_utilization=capacity_adjustment,
            processing_complexity=complexity_adjustment,
            attention_fragmentation=base_metrics.attention_fragmentation,
            temporal_pressure=base_metrics.temporal_pressure,
            interference_level=base_metrics.interference_level,
            resource_competition=base_metrics.resource_competition,
            overall_load=adjusted_overall_load,
            load_level=self._determine_load_level(adjusted_overall_load),
        )

        return adjusted_metrics

    def _calculate_cache_load_factors(
        self, cache_stats: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate cache-specific load factors."""

        # Cache utilization pressures
        l1_utilization = cache_stats.get("l1", {}).get("utilization", 0.0)
        l2_utilization = cache_stats.get("l2", {}).get("utilization", 0.0)

        # Cache performance metrics
        l1_hit_rate = cache_stats.get("l1", {}).get("metrics", {}).get("hit_rate", 0.0)
        l2_hit_rate = cache_stats.get("l2", {}).get("metrics", {}).get("hit_rate", 0.0)
        l3_hit_rate = cache_stats.get("l3", {}).get("metrics", {}).get("hit_rate", 0.0)

        # Cache eviction and promotion activity
        l1_evictions = cache_stats.get("l1", {}).get("metrics", {}).get("evictions", 0)
        l2_evictions = cache_stats.get("l2", {}).get("metrics", {}).get("evictions", 0)
        l1_promotions = (
            cache_stats.get("l1", {}).get("metrics", {}).get("promotions", 0)
        )
        l2_promotions = (
            cache_stats.get("l2", {}).get("metrics", {}).get("promotions", 0)
        )

        # Calculate cache pressure
        cache_pressure = (
            l1_utilization * 0.5  # L1 pressure most critical
            + l2_utilization * 0.3  # L2 pressure moderate
            + min(1.0, (l1_evictions + l2_evictions) / 50.0) * 0.2  # Eviction pressure
        )

        # Calculate cache efficiency score
        avg_hit_rate = (l1_hit_rate + l2_hit_rate + l3_hit_rate) / 3.0
        cache_efficiency = avg_hit_rate / 100.0  # Normalize to 0-1

        # Calculate cache activity (high activity can indicate load)
        cache_activity = min(
            1.0, (l1_promotions + l2_promotions + l1_evictions + l2_evictions) / 20.0
        )

        # Calculate cache memory overhead
        # L1 is most expensive (in terms of cognitive resources)
        l1_size = cache_stats.get("l1", {}).get("size", 0)
        l2_size = cache_stats.get("l2", {}).get("size", 0)

        memory_overhead = (l1_size * 0.1 + l2_size * 0.05) / 100.0  # Normalize

        return {
            "cache_pressure": min(1.0, cache_pressure),
            "cache_efficiency": cache_efficiency,
            "cache_activity": cache_activity,
            "memory_overhead": min(1.0, memory_overhead),
        }

    async def _calculate_overall_load_with_cache(
        self,
        capacity_util: float,
        complexity: float,
        fragmentation: float,
        temporal_pressure: float,
        interference: float,
        competition: float,
        cache_pressure: float,
    ) -> float:
        """Calculate overall cognitive load including cache factors."""

        # Base load calculation with adjusted weights to account for cache
        base_load = (
            capacity_util * 0.20  # Reduced weight due to cache efficiency
            + complexity * 0.18  # Reduced due to cache hit benefits
            + fragmentation * 0.15  # Attention fragmentation unchanged
            + temporal_pressure * 0.15  # Time pressure unchanged
            + interference * 0.15  # Interference unchanged
            + competition * 0.10  # Resource competition unchanged
            + cache_pressure * 0.07  # New cache pressure factor
        )

        # Apply nonlinear scaling for high loads
        if base_load > 0.7:
            scaling_factor = 1.0 + ((base_load - 0.7) * 0.5)
            base_load = min(1.0, base_load * scaling_factor)

        return base_load

    async def get_cache_aware_load_report(
        self, cache_stats: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get comprehensive load report with cache metrics integration."""

        base_report = await self.get_load_report()

        if not cache_stats:
            return {**base_report, "cache_integration": False}

        # Add cache-specific metrics
        cache_load_factors = self._calculate_cache_load_factors(cache_stats)

        cache_section = {
            "cache_integration": True,
            "cache_metrics": {
                "l1_utilization": cache_stats.get("l1", {}).get("utilization", 0.0),
                "l2_utilization": cache_stats.get("l2", {}).get("utilization", 0.0),
                "l1_hit_rate": cache_stats.get("l1", {})
                .get("metrics", {})
                .get("hit_rate", 0.0),
                "l2_hit_rate": cache_stats.get("l2", {})
                .get("metrics", {})
                .get("hit_rate", 0.0),
                "l3_hit_rate": cache_stats.get("l3", {})
                .get("metrics", {})
                .get("hit_rate", 0.0),
                "overall_cache_efficiency": cache_stats.get("overall", {}).get(
                    "cache_efficiency", 0.0
                ),
                "total_promotions": (
                    cache_stats.get("l1", {}).get("metrics", {}).get("promotions", 0)
                    + cache_stats.get("l2", {}).get("metrics", {}).get("promotions", 0)
                ),
                "total_evictions": (
                    cache_stats.get("l1", {}).get("metrics", {}).get("evictions", 0)
                    + cache_stats.get("l2", {}).get("metrics", {}).get("evictions", 0)
                ),
            },
            "cache_load_factors": cache_load_factors,
            "cache_recommendations": self._generate_cache_load_recommendations(
                cache_load_factors, cache_stats
            ),
        }

        return {**base_report, **cache_section}

    def _generate_cache_load_recommendations(
        self, cache_load_factors: Dict[str, float], cache_stats: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for cache-related load optimization."""

        recommendations = []

        cache_pressure = cache_load_factors.get("cache_pressure", 0.0)
        cache_efficiency = cache_load_factors.get("cache_efficiency", 0.0)
        cache_activity = cache_load_factors.get("cache_activity", 0.0)

        # Cache pressure recommendations
        if cache_pressure > 0.8:
            recommendations.append(
                "reduce_working_memory_items_to_relieve_cache_pressure"
            )
            recommendations.append("prioritize_l1_cache_for_critical_items_only")

            l1_utilization = cache_stats.get("l1", {}).get("utilization", 0.0)
            if l1_utilization > 0.9:
                recommendations.append("aggressive_l1_eviction_to_l2_needed")

        elif cache_pressure > 0.6:
            recommendations.append("monitor_cache_pressure_closely")
            recommendations.append("consider_proactive_l2_cleanup")

        # Cache efficiency recommendations
        if cache_efficiency < 0.4:  # Low efficiency
            recommendations.append("improve_cache_hit_rates_through_better_locality")
            recommendations.append("review_working_memory_access_patterns")

            l1_hit_rate = (
                cache_stats.get("l1", {}).get("metrics", {}).get("hit_rate", 0.0)
            )
            l2_hit_rate = (
                cache_stats.get("l2", {}).get("metrics", {}).get("hit_rate", 0.0)
            )

            if l1_hit_rate < 50.0:
                recommendations.append("optimize_l1_cache_admission_policy")
            if l2_hit_rate < 60.0:
                recommendations.append("increase_l2_cache_capacity_or_ttl")

        # Cache activity recommendations
        if cache_activity > 0.7:  # High activity indicates thrashing
            recommendations.append("reduce_cache_thrashing_through_better_policies")
            recommendations.append("consider_longer_cache_retention_times")

            promotions = cache_stats.get("l1", {}).get("metrics", {}).get(
                "promotions", 0
            ) + cache_stats.get("l2", {}).get("metrics", {}).get("promotions", 0)
            evictions = cache_stats.get("l1", {}).get("metrics", {}).get(
                "evictions", 0
            ) + cache_stats.get("l2", {}).get("metrics", {}).get("evictions", 0)

            if evictions > promotions * 2:
                recommendations.append("review_eviction_policies_too_aggressive")

        # Memory overhead recommendations
        memory_overhead = cache_load_factors.get("memory_overhead", 0.0)
        if memory_overhead > 0.3:
            recommendations.append("optimize_cache_memory_footprint")
            recommendations.append("consider_cache_size_reduction")

        return recommendations
        """Get comprehensive cognitive load report."""

        recent_metrics = self.metrics_history[-20:] if self.metrics_history else []
        recent_performance = (
            self.performance_history[-20:] if self.performance_history else []
        )

        if recent_metrics:
            avg_load = statistics.mean(m.overall_load for m in recent_metrics)
            load_trend = (
                recent_metrics[-1].overall_load - recent_metrics[0].overall_load
                if len(recent_metrics) > 1
                else 0.0
            )

            load_distribution = {}
            for metrics in recent_metrics:
                level = metrics.load_level.name
                load_distribution[level] = load_distribution.get(level, 0) + 1
        else:
            avg_load = 0.0
            load_trend = 0.0
            load_distribution = {}

        if recent_performance:
            avg_accuracy = statistics.mean(p.accuracy_rate for p in recent_performance)
            avg_efficiency = statistics.mean(
                p.cognitive_efficiency for p in recent_performance
            )
        else:
            avg_accuracy = 1.0
            avg_efficiency = 1.0

        return {
            "current_metrics": {
                "overall_load": self.current_metrics.overall_load,
                "load_level": self.current_metrics.load_level.name,
                "capacity_utilization": self.current_metrics.capacity_utilization,
                "processing_complexity": self.current_metrics.processing_complexity,
                "attention_fragmentation": self.current_metrics.attention_fragmentation,
                "temporal_pressure": self.current_metrics.temporal_pressure,
                "interference_level": self.current_metrics.interference_level,
                "resource_competition": self.current_metrics.resource_competition,
            },
            "trends": {
                "average_load": avg_load,
                "load_trend": load_trend,
                "load_distribution": load_distribution,
            },
            "performance": {
                "average_accuracy": avg_accuracy,
                "average_efficiency": avg_efficiency,
                "performance_samples": len(recent_performance),
            },
            "alerts": {
                "active_alerts": len(self.active_alerts),
                "recent_alerts": [
                    {
                        "timestamp": alert.timestamp.isoformat(),
                        "load_level": alert.load_level.name,
                        "threshold_violated": alert.threshold_violated,
                        "severity": alert.severity,
                    }
                    for alert in self.active_alerts[-5:]
                ],
            },
            "thresholds": {
                "minimal": self.thresholds.minimal_threshold,
                "low": self.thresholds.low_threshold,
                "moderate": self.thresholds.moderate_threshold,
                "high": self.thresholds.high_threshold,
                "critical": self.thresholds.critical_threshold,
            },
            "monitoring": {
                "active": self._monitoring_active,
                "interval_seconds": self._monitoring_interval,
                "metrics_history_size": len(self.metrics_history),
                "performance_history_size": len(self.performance_history),
            },
        }


# TODO: Production enhancements needed:
# - Implement machine learning-based load prediction
# - Add physiological indicators integration (if available)
# - Implement personalized load threshold learning
# - Add support for load balancing across multiple users
# - Implement proactive load management strategies
# - Add integration with external performance metrics
# - Implement real-time load optimization recommendations

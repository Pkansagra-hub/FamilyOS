"""
LRU Eviction Manager - Priority-Aware Memory Cleanup
===================================================

This module implements priority-aware Least Recently Used (LRU) eviction
strategies for working memory, inspired by the brain's selective forgetting
mechanisms that prioritize important information while clearing less relevant
content to maintain cognitive efficiency.

**Neuroscience Inspiration:**
The brain employs sophisticated forgetting mechanisms where information
decays based on its importance, recency, and frequency of access. The
hippocampus and prefrontal cortex coordinate to maintain goal-relevant
information while allowing task-irrelevant content to fade.

**Research Backing:**
- Anderson & Schooler (1991): Reflections of the environment in memory
- Bjork & Bjork (1992): A new theory of disuse and an old theory of stimulus fluctuation
- Storm & Levy (2012): A progress report on the inhibitory account of retrieval-induced forgetting
- Conway & Pleydell-Pearce (2000): The construction of autobiographical memories

The implementation provides intelligent eviction policies that balance recency,
frequency, priority, and activation levels for optimal memory management.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from observability.logging import get_json_logger
from observability.trace import start_span

from .manager import Priority, WorkingMemoryItem

logger = get_json_logger(__name__)


class EvictionStrategy(Enum):
    """Eviction strategy types."""

    STANDARD_LRU = "standard_lru"  # Classic LRU
    PRIORITY_LRU = "priority_lru"  # Priority-weighted LRU
    ACTIVATION_BASED = "activation_based"  # Activation decay-based
    HYBRID = "hybrid"  # Combined strategy
    ADAPTIVE = "adaptive"  # Dynamic strategy selection


@dataclass
class EvictionCandidate:
    """Candidate item for eviction with scoring."""

    item: WorkingMemoryItem
    eviction_score: float
    age_factor: float
    frequency_factor: float
    priority_factor: float
    activation_factor: float

    def __lt__(self, other: "EvictionCandidate") -> bool:
        """For heap ordering (lower score = better eviction candidate)."""
        return self.eviction_score < other.eviction_score


@dataclass
class EvictionMetrics:
    """Metrics for eviction performance tracking."""

    total_evictions: int = 0
    evictions_by_strategy: Dict[EvictionStrategy, int] = field(default_factory=dict)
    evictions_by_priority: Dict[Priority, int] = field(default_factory=dict)
    average_eviction_score: float = 0.0
    precision_rate: float = 0.0  # How often evicted items stayed evicted
    recall_efficiency: float = 0.0  # How well we evicted the right items


class LRUEvictionManager:
    """
    Implements priority-aware LRU eviction for working memory.

    Provides sophisticated eviction strategies that consider multiple factors
    including recency, frequency, priority, and activation levels to make
    intelligent decisions about which items to remove from working memory.

    **Key Functions:**
    - Multi-factor eviction scoring
    - Priority-preserving LRU policies
    - Activation-based decay modeling
    - Adaptive strategy selection
    - Cognitive load-aware eviction timing
    """

    def __init__(
        self,
        strategy: EvictionStrategy = EvictionStrategy.HYBRID,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.strategy = strategy
        self.config = config or {}

        # Configuration parameters
        self.priority_weight = self.config.get("priority_weight", 0.4)
        self.recency_weight = self.config.get("recency_weight", 0.3)
        self.frequency_weight = self.config.get("frequency_weight", 0.2)
        self.activation_weight = self.config.get("activation_weight", 0.1)

        # Eviction thresholds
        self.min_activation_threshold = self.config.get("min_activation_threshold", 0.1)
        self.age_threshold_hours = self.config.get("age_threshold_hours", 24)
        self.frequency_threshold = self.config.get("frequency_threshold", 1)

        # Performance tracking
        self.metrics = EvictionMetrics()
        self.eviction_history: List[Dict[str, Any]] = []
        self.strategy_performance: Dict[EvictionStrategy, float] = {}

        logger.info(
            "LRUEvictionManager initialized",
            extra={
                "strategy": strategy.value,
                "priority_weight": self.priority_weight,
                "recency_weight": self.recency_weight,
                "frequency_weight": self.frequency_weight,
                "activation_weight": self.activation_weight,
            },
        )

    async def select_eviction_candidates(
        self,
        items: List[WorkingMemoryItem],
        count: int,
        exclude_priorities: Optional[List[Priority]] = None,
        exclude_session: Optional[str] = None,
        cognitive_load: float = 0.0,
    ) -> List[WorkingMemoryItem]:
        """
        Select items for eviction based on configured strategy.

        Evaluates all working memory items using the selected eviction
        strategy and returns the best candidates for removal while
        respecting priority exclusions and session protections.

        Args:
            items: List of working memory items to evaluate
            count: Number of items to select for eviction
            exclude_priorities: Priority levels to exclude from eviction
            exclude_session: Session ID to exclude from eviction
            cognitive_load: Current cognitive load (0.0-1.0)

        Returns:
            List of items selected for eviction
        """
        with start_span("working_memory.lru_eviction.select_candidates") as span:
            try:
                if not items or count <= 0:
                    return []

                exclude_priorities = exclude_priorities or [Priority.CRITICAL]

                # Filter evictable items
                evictable_items = [
                    item
                    for item in items
                    if (
                        item.priority not in exclude_priorities
                        and (
                            exclude_session is None
                            or item.session_id != exclude_session
                        )
                    )
                ]

                if not evictable_items:
                    logger.warning("No evictable items found")
                    return []

                # Select strategy
                active_strategy = await self._select_active_strategy(
                    evictable_items, cognitive_load
                )

                # Generate candidates with scores
                candidates = []
                for item in evictable_items:
                    candidate = await self._create_eviction_candidate(
                        item, active_strategy, cognitive_load
                    )
                    candidates.append(candidate)

                # Sort candidates by eviction score (lower = better candidate)
                candidates.sort(key=lambda c: c.eviction_score)

                # Select top candidates
                selected_count = min(count, len(candidates))
                selected_items = [candidates[i].item for i in range(selected_count)]

                # Record eviction decisions
                await self._record_eviction_decisions(
                    selected_items, active_strategy, cognitive_load
                )

                if span:
                    span.set_attribute("strategy", active_strategy.value)
                    span.set_attribute("evictable_count", len(evictable_items))
                    span.set_attribute("selected_count", selected_count)
                    span.set_attribute("cognitive_load", cognitive_load)

                logger.info(
                    "Eviction candidates selected",
                    extra={
                        "strategy": active_strategy.value,
                        "total_items": len(items),
                        "evictable_items": len(evictable_items),
                        "selected_count": selected_count,
                        "cognitive_load": cognitive_load,
                    },
                )

                return selected_items

            except Exception as e:
                logger.error(
                    "Failed to select eviction candidates",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "item_count": len(items),
                        "requested_count": count,
                    },
                )

                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))

                return []

    async def _select_active_strategy(
        self, items: List[WorkingMemoryItem], cognitive_load: float
    ) -> EvictionStrategy:
        """Select the best eviction strategy for current conditions."""

        if self.strategy != EvictionStrategy.ADAPTIVE:
            return self.strategy

        # Adaptive strategy selection based on conditions

        # High cognitive load: prefer activation-based (clear low-activation items)
        if cognitive_load > 0.8:
            return EvictionStrategy.ACTIVATION_BASED

        # Medium load: use hybrid approach
        if cognitive_load > 0.5:
            return EvictionStrategy.HYBRID

        # Low load with many high-priority items: priority-aware LRU
        high_priority_ratio = (
            sum(1 for item in items if item.priority.value >= Priority.HIGH.value)
            / len(items)
            if items
            else 0
        )

        if high_priority_ratio > 0.6:
            return EvictionStrategy.PRIORITY_LRU

        # Default to standard LRU for balanced conditions
        return EvictionStrategy.STANDARD_LRU

    async def _create_eviction_candidate(
        self, item: WorkingMemoryItem, strategy: EvictionStrategy, cognitive_load: float
    ) -> EvictionCandidate:
        """Create eviction candidate with appropriate scoring."""

        now = datetime.now(timezone.utc)

        # Calculate individual factors
        age_factor = self._calculate_age_factor(item, now)
        frequency_factor = self._calculate_frequency_factor(item)
        priority_factor = self._calculate_priority_factor(item)
        activation_factor = self._calculate_activation_factor(item)

        # Calculate strategy-specific eviction score
        eviction_score = await self._calculate_eviction_score(
            strategy,
            age_factor,
            frequency_factor,
            priority_factor,
            activation_factor,
            cognitive_load,
        )

        return EvictionCandidate(
            item=item,
            eviction_score=eviction_score,
            age_factor=age_factor,
            frequency_factor=frequency_factor,
            priority_factor=priority_factor,
            activation_factor=activation_factor,
        )

    def _calculate_age_factor(self, item: WorkingMemoryItem, now: datetime) -> float:
        """Calculate age-based factor (higher = older = better eviction candidate)."""

        time_since_access = (now - item.accessed_at).total_seconds()
        hours_since_access = time_since_access / 3600

        # Normalize to 0-1 scale (24 hours = 1.0)
        age_factor = min(1.0, hours_since_access / self.age_threshold_hours)

        return age_factor

    def _calculate_frequency_factor(self, item: WorkingMemoryItem) -> float:
        """Calculate frequency-based factor (lower frequency = better eviction candidate)."""

        # Normalize access count (lower = better candidate)
        # Cap at reasonable max to prevent skew
        max_reasonable_access = 20
        normalized_access = (
            min(item.access_count, max_reasonable_access) / max_reasonable_access
        )

        # Invert so lower frequency = higher eviction score
        frequency_factor = 1.0 - normalized_access

        return frequency_factor

    def _calculate_priority_factor(self, item: WorkingMemoryItem) -> float:
        """Calculate priority-based factor (lower priority = better eviction candidate)."""

        # Normalize priority (lower priority = higher eviction score)
        max_priority_value = Priority.CRITICAL.value
        priority_factor = 1.0 - (item.priority.value / max_priority_value)

        return priority_factor

    def _calculate_activation_factor(self, item: WorkingMemoryItem) -> float:
        """Calculate activation-based factor (lower activation = better eviction candidate)."""

        activation = item.calculate_activation()

        # Invert activation (lower activation = higher eviction score)
        activation_factor = 1.0 - activation

        return activation_factor

    async def _calculate_eviction_score(
        self,
        strategy: EvictionStrategy,
        age_factor: float,
        frequency_factor: float,
        priority_factor: float,
        activation_factor: float,
        cognitive_load: float,
    ) -> float:
        """Calculate eviction score based on strategy."""

        if strategy == EvictionStrategy.STANDARD_LRU:
            # Pure LRU: only age matters
            return age_factor

        elif strategy == EvictionStrategy.PRIORITY_LRU:
            # Priority-weighted LRU
            return (
                self.recency_weight * age_factor
                + self.priority_weight * priority_factor
                + self.frequency_weight * frequency_factor
            )

        elif strategy == EvictionStrategy.ACTIVATION_BASED:
            # Activation-focused eviction
            return (
                self.activation_weight * activation_factor
                + 0.3 * priority_factor
                + 0.3 * age_factor
                + 0.2 * frequency_factor
            )

        elif strategy == EvictionStrategy.HYBRID:
            # Balanced combination of all factors
            base_score = (
                self.recency_weight * age_factor
                + self.frequency_weight * frequency_factor
                + self.priority_weight * priority_factor
                + self.activation_weight * activation_factor
            )

            # Adjust for cognitive load
            load_adjustment = (
                cognitive_load * 0.1
            )  # Slight preference for eviction under load

            return base_score + load_adjustment

        else:
            # Default to hybrid
            return (
                self.recency_weight * age_factor
                + self.frequency_weight * frequency_factor
                + self.priority_weight * priority_factor
                + self.activation_weight * activation_factor
            )

    async def _record_eviction_decisions(
        self,
        evicted_items: List[WorkingMemoryItem],
        strategy: EvictionStrategy,
        cognitive_load: float,
    ) -> None:
        """Record eviction decisions for performance tracking."""

        timestamp = datetime.now(timezone.utc)

        for item in evicted_items:
            eviction_record = {
                "timestamp": timestamp.isoformat(),
                "item_id": item.id,
                "session_id": item.session_id,
                "priority": item.priority.value,
                "activation": item.calculate_activation(),
                "access_count": item.access_count,
                "age_hours": (timestamp - item.created_at).total_seconds() / 3600,
                "strategy": strategy.value,
                "cognitive_load": cognitive_load,
            }

            self.eviction_history.append(eviction_record)

        # Update metrics
        self.metrics.total_evictions += len(evicted_items)

        if strategy not in self.metrics.evictions_by_strategy:
            self.metrics.evictions_by_strategy[strategy] = 0
        self.metrics.evictions_by_strategy[strategy] += len(evicted_items)

        for item in evicted_items:
            if item.priority not in self.metrics.evictions_by_priority:
                self.metrics.evictions_by_priority[item.priority] = 0
            self.metrics.evictions_by_priority[item.priority] += 1

        # Update average eviction score
        if self.eviction_history:
            total_activations = sum(
                record.get("activation", 0.0) for record in self.eviction_history[-100:]
            )
            self.metrics.average_eviction_score = total_activations / min(
                100, len(self.eviction_history)
            )

        # Limit history size
        if len(self.eviction_history) > 500:
            self.eviction_history = self.eviction_history[-250:]

    async def analyze_eviction_patterns(self) -> Dict[str, Any]:
        """Analyze eviction patterns for performance insights."""

        if not self.eviction_history:
            return {"message": "No eviction history available"}

        recent_evictions = self.eviction_history[-100:]  # Last 100 evictions

        # Strategy effectiveness
        strategy_counts = {}
        strategy_avg_activation = {}

        for record in recent_evictions:
            strategy = record["strategy"]
            activation = record["activation"]

            if strategy not in strategy_counts:
                strategy_counts[strategy] = 0
                strategy_avg_activation[strategy] = []

            strategy_counts[strategy] += 1
            strategy_avg_activation[strategy].append(activation)

        # Calculate average activations per strategy
        for strategy in strategy_avg_activation:
            activations = strategy_avg_activation[strategy]
            strategy_avg_activation[strategy] = sum(activations) / len(activations)

        # Priority distribution
        priority_distribution = {}
        for record in recent_evictions:
            priority = record["priority"]
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1

        # Timing analysis
        eviction_times = [
            datetime.fromisoformat(record["timestamp"]) for record in recent_evictions
        ]

        if len(eviction_times) > 1:
            time_intervals = [
                (eviction_times[i] - eviction_times[i - 1]).total_seconds()
                for i in range(1, len(eviction_times))
            ]
            avg_interval = sum(time_intervals) / len(time_intervals)
        else:
            avg_interval = 0

        # Cognitive load correlation
        load_activation_pairs = [
            (record["cognitive_load"], record["activation"])
            for record in recent_evictions
            if "cognitive_load" in record
        ]

        load_correlation = 0.0
        if len(load_activation_pairs) > 5:
            # Simple correlation calculation
            loads, activations = zip(*load_activation_pairs)
            load_mean = sum(loads) / len(loads)
            activation_mean = sum(activations) / len(activations)

            numerator = sum(
                (load - load_mean) * (activation - activation_mean)
                for load, activation in load_activation_pairs
            )

            load_var = sum((load - load_mean) ** 2 for load in loads)
            activation_var = sum((a - activation_mean) ** 2 for a in activations)

            if load_var > 0 and activation_var > 0:
                load_correlation = numerator / (load_var * activation_var) ** 0.5

        return {
            "total_evictions": len(self.eviction_history),
            "recent_evictions": len(recent_evictions),
            "strategy_counts": strategy_counts,
            "strategy_effectiveness": strategy_avg_activation,
            "priority_distribution": priority_distribution,
            "average_interval_seconds": avg_interval,
            "load_activation_correlation": load_correlation,
            "metrics": {
                "total_evictions": self.metrics.total_evictions,
                "average_eviction_score": self.metrics.average_eviction_score,
                "evictions_by_strategy": {
                    k.value: v for k, v in self.metrics.evictions_by_strategy.items()
                },
                "evictions_by_priority": {
                    k.value: v for k, v in self.metrics.evictions_by_priority.items()
                },
            },
        }

    async def optimize_strategy_weights(self) -> Dict[str, Any]:
        """Optimize strategy weights based on performance history."""

        if len(self.eviction_history) < 50:
            return {
                "message": "Insufficient data for optimization",
                "current_weights": {
                    "priority_weight": self.priority_weight,
                    "recency_weight": self.recency_weight,
                    "frequency_weight": self.frequency_weight,
                    "activation_weight": self.activation_weight,
                },
            }

        # Analyze which factors correlate with successful evictions
        # (This is a simplified optimization - could be enhanced with ML)

        recent_evictions = self.eviction_history[-100:]

        # Calculate average activation by priority to assess quality
        priority_activations = {}
        for record in recent_evictions:
            priority = record["priority"]
            activation = record["activation"]

            if priority not in priority_activations:
                priority_activations[priority] = []
            priority_activations[priority].append(activation)

        # Calculate quality score (lower priority items with lower activation = good)
        quality_score = 0.0
        total_weight = 0.0

        for priority, activations in priority_activations.items():
            avg_activation = sum(activations) / len(activations)
            priority_penalty = 1.0 / max(1, priority)  # Lower priority = lower penalty
            weighted_score = avg_activation * priority_penalty
            weight = len(activations)

            quality_score += weighted_score * weight
            total_weight += weight

        quality_score /= total_weight if total_weight > 0 else 1

        # Adjust weights based on quality (simplified heuristic)
        new_weights = {
            "priority_weight": self.priority_weight,
            "recency_weight": self.recency_weight,
            "frequency_weight": self.frequency_weight,
            "activation_weight": self.activation_weight,
        }

        # If quality is poor (high activation items being evicted), increase priority weight
        if quality_score > 0.5:
            new_weights["priority_weight"] = min(0.6, self.priority_weight + 0.05)
            new_weights["activation_weight"] = min(0.3, self.activation_weight + 0.05)
            new_weights["recency_weight"] = max(0.1, self.recency_weight - 0.05)

        # Normalize weights
        total_weight = sum(new_weights.values())
        if total_weight > 0:
            for key in new_weights:
                new_weights[key] /= total_weight

        return {
            "current_quality_score": quality_score,
            "optimized_weights": new_weights,
            "improvement_potential": abs(
                quality_score - 0.3
            ),  # Target quality around 0.3
            "data_points": len(recent_evictions),
        }

    async def get_eviction_stats(self) -> Dict[str, Any]:
        """Get comprehensive eviction statistics."""

        return {
            "metrics": {
                "total_evictions": self.metrics.total_evictions,
                "average_eviction_score": self.metrics.average_eviction_score,
                "precision_rate": self.metrics.precision_rate,
                "recall_efficiency": self.metrics.recall_efficiency,
            },
            "configuration": {
                "strategy": self.strategy.value,
                "priority_weight": self.priority_weight,
                "recency_weight": self.recency_weight,
                "frequency_weight": self.frequency_weight,
                "activation_weight": self.activation_weight,
                "min_activation_threshold": self.min_activation_threshold,
                "age_threshold_hours": self.age_threshold_hours,
            },
            "history_size": len(self.eviction_history),
            "strategies_used": list(self.metrics.evictions_by_strategy.keys()),
            "priorities_evicted": list(self.metrics.evictions_by_priority.keys()),
        }


# TODO: Production enhancements needed:
# - Implement machine learning-based eviction prediction
# - Add support for content-aware eviction policies
# - Implement predictive eviction based on usage patterns
# - Add support for hierarchical eviction (evict related items together)
# - Implement eviction impact assessment and rollback
# - Add integration with memory consolidation triggers
# - Implement personalized eviction preferences learning

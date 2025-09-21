"""
Admission Controller - Working Memory Gatekeeper
==============================================

This module implements salience-based admission control for working memory,
inspired by the brain's attentional gating mechanisms that determine what
information gains access to conscious awareness and active maintenance.

**Neuroscience Inspiration:**
The prefrontal cortex and anterior cingulate cortex work together to gate
information entering working memory. This involves evaluating the relevance,
urgency, and cognitive demands of incoming information against current goals
and available cognitive resources.

**Research Backing:**
- Norman & Shallice (1986): Attention and action: Willed and automatic control
- Posner & Petersen (1990): The attention system of the human brain
- Engle (2002): Working memory capacity and attention control
- Kane & Engle (2003): Working memory capacity and the control of attention

The implementation provides sophisticated admission policies based on content
salience, priority levels, cognitive load, and contextual relevance.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from observability.logging import get_json_logger
from observability.trace import start_span

from .manager import Priority, WorkingMemoryItem, WorkingMemoryType

logger = get_json_logger(__name__)


class AdmissionPolicy(Enum):
    """Admission control policies."""

    STRICT = "strict"  # High salience threshold, limited eviction
    BALANCED = "balanced"  # Moderate thresholds, context-aware
    PERMISSIVE = "permissive"  # Lower thresholds, aggressive eviction
    ADAPTIVE = "adaptive"  # Dynamic thresholds based on load


@dataclass
class AdmissionCriteria:
    """Criteria for admission control decisions."""

    min_salience_threshold: float = 0.3
    priority_boost_factor: float = 0.2
    recency_boost_window_minutes: int = 5
    context_relevance_weight: float = 0.15
    cognitive_load_penalty: float = 0.1
    session_continuity_bonus: float = 0.1


@dataclass
class AdmissionDecision:
    """Result of admission control evaluation."""

    admitted: bool
    confidence: float
    salience_score: float
    adjusted_score: float
    decision_factors: Dict[str, float]
    eviction_recommendation: Optional[Dict[str, Any]] = None
    reason: str = ""


class AdmissionController:
    """
    Implements salience-based admission control for working memory.

    Evaluates incoming information requests against multiple criteria
    including salience, priority, cognitive load, and contextual factors
    to determine admission worthiness using brain-inspired policies.

    **Key Functions:**
    - Multi-factor salience evaluation
    - Priority-aware admission scoring
    - Cognitive load consideration
    - Context relevance assessment
    - Adaptive threshold adjustment
    """

    def __init__(
        self,
        policy: AdmissionPolicy = AdmissionPolicy.BALANCED,
        criteria: Optional[AdmissionCriteria] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.policy = policy
        self.criteria = criteria or AdmissionCriteria()
        self.config = config or {}

        # Adaptive threshold tracking
        self.admission_history: List[Dict[str, Any]] = []
        self.current_cognitive_load = 0.0
        self.load_history: List[float] = []

        # Policy-specific adjustments
        self._adjust_criteria_for_policy()

        logger.info(
            "AdmissionController initialized",
            extra={
                "policy": policy.value,
                "min_salience_threshold": self.criteria.min_salience_threshold,
                "priority_boost_factor": self.criteria.priority_boost_factor,
            },
        )

    async def evaluate_admission(
        self,
        content: Any,
        content_type: WorkingMemoryType,
        priority: Priority,
        base_salience: float,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        current_items: Optional[List[WorkingMemoryItem]] = None,
        cognitive_load: float = 0.0,
    ) -> AdmissionDecision:
        """
        Evaluate whether content should be admitted to working memory.

        Performs comprehensive salience evaluation considering multiple
        factors including priority, cognitive load, context relevance,
        and current working memory state.

        Args:
            content: Content to evaluate for admission
            content_type: Type of working memory content
            priority: Priority level
            base_salience: Base salience score (0.0-1.0)
            session_id: Session identifier
            context: Optional context information
            current_items: Current working memory items
            cognitive_load: Current cognitive load (0.0-1.0)

        Returns:
            AdmissionDecision with admission recommendation
        """
        with start_span("working_memory.admission_controller.evaluate") as span:
            try:
                # Update cognitive load tracking
                self.current_cognitive_load = cognitive_load
                self.load_history.append(cognitive_load)
                if len(self.load_history) > 50:
                    self.load_history = self.load_history[-25:]

                # Initialize decision factors
                decision_factors: Dict[str, float] = {
                    "base_salience": base_salience,
                    "priority_boost": 0.0,
                    "recency_boost": 0.0,
                    "context_relevance": 0.0,
                    "cognitive_load_penalty": 0.0,
                    "session_continuity": 0.0,
                    "content_type_factor": 0.0,
                }

                # Factor 1: Priority boost
                priority_boost = self._calculate_priority_boost(priority)
                decision_factors["priority_boost"] = priority_boost

                # Factor 2: Recency boost (if recently relevant)
                recency_boost = self._calculate_recency_boost(context)
                decision_factors["recency_boost"] = recency_boost

                # Factor 3: Context relevance
                context_relevance = await self._calculate_context_relevance(
                    content, content_type, context, current_items
                )
                decision_factors["context_relevance"] = context_relevance

                # Factor 4: Cognitive load penalty
                load_penalty = self._calculate_cognitive_load_penalty(cognitive_load)
                decision_factors["cognitive_load_penalty"] = load_penalty

                # Factor 5: Session continuity bonus
                continuity_bonus = self._calculate_session_continuity(
                    session_id, content_type, current_items
                )
                decision_factors["session_continuity"] = continuity_bonus

                # Factor 6: Content type factor
                type_factor = self._calculate_content_type_factor(content_type)
                decision_factors["content_type_factor"] = type_factor

                # Calculate adjusted salience score
                adjusted_score = (
                    base_salience
                    + priority_boost
                    + recency_boost
                    + context_relevance
                    + continuity_bonus
                    + type_factor
                    - load_penalty
                )

                # Clamp to valid range
                adjusted_score = max(0.0, min(1.0, adjusted_score))

                # Get dynamic threshold
                threshold = await self._get_adaptive_threshold(
                    cognitive_load, priority, current_items
                )

                # Make admission decision
                admitted = adjusted_score >= threshold
                confidence = self._calculate_confidence(
                    adjusted_score, threshold, decision_factors
                )

                # Generate eviction recommendation if needed
                eviction_recommendation = None
                if not admitted and priority.value >= Priority.HIGH.value:
                    eviction_recommendation = (
                        await self._generate_eviction_recommendation(
                            adjusted_score, priority, current_items
                        )
                    )
                    if eviction_recommendation:
                        admitted = True

                # Create decision
                decision = AdmissionDecision(
                    admitted=admitted,
                    confidence=confidence,
                    salience_score=base_salience,
                    adjusted_score=adjusted_score,
                    decision_factors=decision_factors,
                    eviction_recommendation=eviction_recommendation,
                    reason=self._generate_decision_reason(
                        admitted,
                        adjusted_score,
                        threshold,
                        priority,
                        eviction_recommendation,
                    ),
                )

                # Record decision for adaptive learning
                await self._record_decision(decision, context)

                if span:
                    span.set_attribute("admitted", admitted)
                    span.set_attribute("adjusted_score", adjusted_score)
                    span.set_attribute("threshold", threshold)
                    span.set_attribute("confidence", confidence)

                logger.debug(
                    "Admission evaluation completed",
                    extra={
                        "session_id": session_id,
                        "content_type": content_type.value,
                        "priority": priority.value,
                        "base_salience": base_salience,
                        "adjusted_score": adjusted_score,
                        "threshold": threshold,
                        "admitted": admitted,
                        "confidence": confidence,
                        "decision_factors": decision_factors,
                    },
                )

                return decision

            except Exception as e:
                logger.error(
                    "Admission evaluation failed",
                    extra={
                        "session_id": session_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))

                # Return safe default decision
                return AdmissionDecision(
                    admitted=priority == Priority.CRITICAL,
                    confidence=0.1,
                    salience_score=base_salience,
                    adjusted_score=base_salience,
                    decision_factors={"base_salience": base_salience},
                    reason="evaluation_error",
                )

    def _calculate_priority_boost(self, priority: Priority) -> float:
        """Calculate priority-based boost to salience."""

        priority_multipliers = {
            Priority.CRITICAL: 0.5,  # Strong boost
            Priority.HIGH: 0.3,  # Moderate boost
            Priority.MEDIUM: 0.1,  # Small boost
            Priority.LOW: 0.0,  # No boost
            Priority.MINIMAL: -0.1,  # Small penalty
        }

        base_boost = priority_multipliers.get(priority, 0.0)
        return base_boost * self.criteria.priority_boost_factor

    def _calculate_recency_boost(self, context: Optional[Dict[str, Any]]) -> float:
        """Calculate recency-based boost for recently relevant content."""

        if not context or "last_access" not in context:
            return 0.0

        try:
            last_access = context["last_access"]
            if isinstance(last_access, str):
                last_access = datetime.fromisoformat(last_access.replace("Z", "+00:00"))
            elif not isinstance(last_access, datetime):
                return 0.0

            now = datetime.now(timezone.utc)
            minutes_since_access = (now - last_access).total_seconds() / 60

            if minutes_since_access <= self.criteria.recency_boost_window_minutes:
                # Exponential decay within boost window
                decay_factor = 1.0 - (
                    minutes_since_access / self.criteria.recency_boost_window_minutes
                )
                return 0.15 * decay_factor

        except (ValueError, TypeError):
            pass

        return 0.0

    async def _calculate_context_relevance(
        self,
        content: Any,
        content_type: WorkingMemoryType,
        context: Optional[Dict[str, Any]],
        current_items: Optional[List[WorkingMemoryItem]],
    ) -> float:
        """Calculate context relevance based on current working memory contents."""

        if not current_items or not context:
            return 0.0

        relevance_score = 0.0

        # Check for thematic similarity (simplified)
        content_keywords = self._extract_keywords(content, context)

        for item in current_items:
            item_keywords = self._extract_keywords(item.content, item.metadata)
            similarity = self._calculate_keyword_similarity(
                content_keywords, item_keywords
            )

            # Weight by item priority and activation
            weight = (item.priority.value / 5.0) * min(1.0, item.calculate_activation())
            relevance_score += similarity * weight

        # Normalize by number of items
        if current_items:
            relevance_score /= len(current_items)

        return min(self.criteria.context_relevance_weight, relevance_score)

    def _calculate_cognitive_load_penalty(self, cognitive_load: float) -> float:
        """Calculate penalty based on current cognitive load."""

        if cognitive_load <= 0.5:
            return 0.0  # No penalty for low load

        # Progressive penalty for high cognitive load
        excess_load = cognitive_load - 0.5
        penalty = excess_load * self.criteria.cognitive_load_penalty * 2.0

        return min(0.3, penalty)  # Cap penalty at 0.3

    def _calculate_session_continuity(
        self,
        session_id: str,
        content_type: WorkingMemoryType,
        current_items: Optional[List[WorkingMemoryItem]],
    ) -> float:
        """Calculate bonus for session continuity."""

        if not current_items:
            return 0.0

        # Count items from same session and type
        same_session_count = sum(
            1 for item in current_items if item.session_id == session_id
        )

        same_type_count = sum(
            1
            for item in current_items
            if item.content_type == content_type and item.session_id == session_id
        )

        # Bonus for session continuation
        session_bonus = min(0.1, same_session_count * 0.02)
        type_bonus = min(0.05, same_type_count * 0.025)

        return (session_bonus + type_bonus) * self.criteria.session_continuity_bonus

    def _calculate_content_type_factor(self, content_type: WorkingMemoryType) -> float:
        """Calculate factor based on content type importance."""

        type_factors = {
            WorkingMemoryType.GOAL: 0.15,  # Goals are important
            WorkingMemoryType.CONTEXT: 0.1,  # Context is valuable
            WorkingMemoryType.ATTENTION: 0.1,  # Attention items prioritized
            WorkingMemoryType.RETRIEVAL: 0.05,  # Retrieved content moderate
            WorkingMemoryType.COMPUTATION: 0.0,  # Neutral
            WorkingMemoryType.BUFFER: -0.05,  # Buffer items deprioritized
        }

        return type_factors.get(content_type, 0.0)

    async def _get_adaptive_threshold(
        self,
        cognitive_load: float,
        priority: Priority,
        current_items: Optional[List[WorkingMemoryItem]],
    ) -> float:
        """Get adaptive threshold based on current conditions."""

        base_threshold = self.criteria.min_salience_threshold

        if self.policy == AdmissionPolicy.ADAPTIVE:
            # Adjust threshold based on cognitive load
            load_adjustment = cognitive_load * 0.2  # Increase threshold when loaded

            # Adjust based on priority distribution
            priority_adjustment = 0.0
            if current_items:
                high_priority_ratio = sum(
                    1
                    for item in current_items
                    if item.priority.value >= Priority.HIGH.value
                ) / len(current_items)

                # Lower threshold if mostly low priority items
                priority_adjustment = -0.1 * (1.0 - high_priority_ratio)

            adaptive_threshold = base_threshold + load_adjustment + priority_adjustment
            return max(0.1, min(0.8, adaptive_threshold))

        return base_threshold

    async def _generate_eviction_recommendation(
        self,
        item_score: float,
        item_priority: Priority,
        current_items: Optional[List[WorkingMemoryItem]],
    ) -> Optional[Dict[str, Any]]:
        """Generate recommendation for evicting items to make space."""

        if not current_items:
            return None

        # Find eviction candidates (lower priority, lower activation)
        candidates = [
            item
            for item in current_items
            if (
                item.priority.value < item_priority.value
                and item.priority != Priority.CRITICAL
            )
        ]

        if not candidates:
            return None

        # Sort by eviction desirability (priority, then activation)
        candidates.sort(key=lambda x: (x.priority.value, x.calculate_activation()))

        best_candidate = candidates[0]

        # Only recommend if new item significantly better
        if item_score > best_candidate.salience_score + 0.1:
            return {
                "evict_item_id": best_candidate.id,
                "evict_score": best_candidate.calculate_activation(),
                "evict_priority": best_candidate.priority.value,
                "replacement_score": item_score,
                "improvement": item_score - best_candidate.salience_score,
            }

        return None

    def _calculate_confidence(
        self,
        adjusted_score: float,
        threshold: float,
        decision_factors: Dict[str, float],
    ) -> float:
        """Calculate confidence in the admission decision."""

        # Distance from threshold
        distance = abs(adjusted_score - threshold)
        distance_confidence = min(1.0, distance * 2.0)

        # Factor consistency (how many factors agree)
        positive_factors = sum(1 for v in decision_factors.values() if v > 0)
        negative_factors = sum(1 for v in decision_factors.values() if v < 0)

        factor_consistency = abs(positive_factors - negative_factors) / len(
            decision_factors
        )

        # Combine confidence measures
        confidence = (distance_confidence * 0.7) + (factor_consistency * 0.3)

        return max(0.1, min(1.0, confidence))

    def _generate_decision_reason(
        self,
        admitted: bool,
        adjusted_score: float,
        threshold: float,
        priority: Priority,
        eviction_recommendation: Optional[Dict[str, Any]],
    ) -> str:
        """Generate human-readable reason for decision."""

        if priority == Priority.CRITICAL:
            return "critical_priority_override"

        if eviction_recommendation:
            return "admitted_via_eviction"

        if admitted:
            if adjusted_score > threshold + 0.2:
                return "high_salience"
            elif adjusted_score > threshold + 0.1:
                return "above_threshold"
            else:
                return "marginal_admission"
        else:
            if adjusted_score < threshold - 0.2:
                return "low_salience"
            elif adjusted_score < threshold - 0.1:
                return "below_threshold"
            else:
                return "marginal_rejection"

    async def _record_decision(
        self, decision: AdmissionDecision, context: Optional[Dict[str, Any]]
    ) -> None:
        """Record decision for adaptive learning."""

        decision_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "admitted": decision.admitted,
            "adjusted_score": decision.adjusted_score,
            "cognitive_load": self.current_cognitive_load,
            "policy": self.policy.value,
            "factors": decision.decision_factors,
        }

        self.admission_history.append(decision_record)

        # Limit history size
        if len(self.admission_history) > 200:
            self.admission_history = self.admission_history[-100:]

    def _adjust_criteria_for_policy(self) -> None:
        """Adjust criteria based on selected policy."""

        if self.policy == AdmissionPolicy.STRICT:
            self.criteria.min_salience_threshold += 0.2
            self.criteria.cognitive_load_penalty += 0.05
        elif self.policy == AdmissionPolicy.PERMISSIVE:
            self.criteria.min_salience_threshold -= 0.1
            self.criteria.priority_boost_factor += 0.1
        elif self.policy == AdmissionPolicy.ADAPTIVE:
            # Base criteria, will adjust dynamically
            pass

    def _extract_keywords(
        self, content: Any, metadata: Optional[Dict[str, Any]]
    ) -> Set[str]:
        """Extract keywords from content for similarity calculation."""

        keywords = set()

        # Extract from content string representation
        content_str = str(content).lower()
        # Simple keyword extraction (could be enhanced with NLP)
        words = content_str.split()
        keywords.update(word.strip('.,!?;:"()[]{}') for word in words if len(word) > 2)

        # Extract from metadata
        if metadata:
            for value in metadata.values():
                if isinstance(value, str):
                    words = value.lower().split()
                    keywords.update(
                        word.strip('.,!?;:"()[]{}') for word in words if len(word) > 2
                    )

        return keywords

    def _calculate_keyword_similarity(
        self, keywords1: Set[str], keywords2: Set[str]
    ) -> float:
        """Calculate Jaccard similarity between keyword sets."""

        if not keywords1 or not keywords2:
            return 0.0

        intersection = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)

        return intersection / union if union > 0 else 0.0

    async def evaluate_admission_with_cache_awareness(
        self,
        content: Any,
        content_type: WorkingMemoryType,
        priority: Priority,
        base_salience: float,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        current_items: Optional[List[WorkingMemoryItem]] = None,
        cognitive_load: float = 0.0,
        cache_stats: Optional[Dict[str, Any]] = None,
    ) -> AdmissionDecision:
        """
        Enhanced admission evaluation with hierarchical cache awareness.

        Integrates cache-level performance metrics into admission decisions,
        considering L1/L2/L3 hit rates, promotion patterns, and cache pressure
        to optimize working memory efficiency.

        Args:
            content: Content to evaluate for admission
            content_type: Type of working memory content
            priority: Priority level
            base_salience: Base salience score (0.0-1.0)
            session_id: Session identifier
            context: Optional context information
            current_items: Current working memory items
            cognitive_load: Current cognitive load (0.0-1.0)
            cache_stats: Hierarchical cache performance statistics

        Returns:
            AdmissionDecision with cache-aware recommendations
        """
        with start_span(
            "working_memory.admission_controller.evaluate_cache_aware"
        ) as span:
            try:
                # Start with base evaluation
                base_decision = await self.evaluate_admission(
                    content,
                    content_type,
                    priority,
                    base_salience,
                    session_id,
                    context,
                    current_items,
                    cognitive_load,
                )

                # Apply cache-aware adjustments if cache stats available
                if cache_stats:
                    cache_adjusted_decision = await self._apply_cache_adjustments(
                        base_decision, cache_stats, priority, cognitive_load
                    )

                    # Add cache-specific factors to decision
                    cache_adjusted_decision.decision_factors.update(
                        {
                            "l1_hit_rate": cache_stats.get("l1", {})
                            .get("metrics", {})
                            .get("hit_rate", 0.0),
                            "l2_hit_rate": cache_stats.get("l2", {})
                            .get("metrics", {})
                            .get("hit_rate", 0.0),
                            "cache_pressure": self._calculate_cache_pressure(
                                cache_stats
                            ),
                            "cache_efficiency": cache_stats.get("overall", {}).get(
                                "cache_efficiency", 0.0
                            ),
                        }
                    )

                    if span:
                        span.set_attribute("cache_aware", True)
                        span.set_attribute(
                            "cache_pressure",
                            cache_adjusted_decision.decision_factors["cache_pressure"],
                        )
                        span.set_attribute(
                            "l1_utilization",
                            cache_stats.get("l1", {}).get("utilization", 0.0),
                        )

                    return cache_adjusted_decision
                else:
                    if span:
                        span.set_attribute("cache_aware", False)

                    return base_decision

            except Exception as e:
                logger.error(
                    "Cache-aware admission evaluation failed",
                    extra={
                        "session_id": session_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))

                # Fallback to base evaluation
                return await self.evaluate_admission(
                    content,
                    content_type,
                    priority,
                    base_salience,
                    session_id,
                    context,
                    current_items,
                    cognitive_load,
                )

    async def _apply_cache_adjustments(
        self,
        base_decision: AdmissionDecision,
        cache_stats: Dict[str, Any],
        priority: Priority,
        cognitive_load: float,
    ) -> AdmissionDecision:
        """Apply cache-aware adjustments to admission decision."""

        # Calculate cache pressure
        cache_pressure = self._calculate_cache_pressure(cache_stats)

        # Get cache utilization levels
        l1_utilization = cache_stats.get("l1", {}).get("utilization", 0.0)
        l2_utilization = cache_stats.get("l2", {}).get("utilization", 0.0)

        # Get cache performance metrics
        l1_hit_rate = cache_stats.get("l1", {}).get("metrics", {}).get("hit_rate", 0.0)
        l2_hit_rate = cache_stats.get("l2", {}).get("metrics", {}).get("hit_rate", 0.0)
        cache_efficiency = cache_stats.get("overall", {}).get("cache_efficiency", 0.0)

        # Calculate cache-based adjustments
        cache_adjustment = 0.0

        # 1. Cache pressure penalty
        if cache_pressure > 0.8:  # High cache pressure
            cache_adjustment -= 0.15
        elif cache_pressure > 0.6:  # Moderate cache pressure
            cache_adjustment -= 0.08

        # 2. Cache efficiency bonus/penalty
        if cache_efficiency > 80.0:  # High efficiency, can handle more
            cache_adjustment += 0.05
        elif cache_efficiency < 40.0:  # Low efficiency, be more selective
            cache_adjustment -= 0.1

        # 3. L1 utilization consideration
        if l1_utilization > 0.9:  # L1 nearly full
            if priority.value < Priority.HIGH.value:
                cache_adjustment -= 0.1  # Penalty for non-high priority items
        elif l1_utilization < 0.3:  # L1 has space
            cache_adjustment += 0.05

        # 4. Hit rate consideration for cache warmth
        avg_hit_rate = (l1_hit_rate + l2_hit_rate) / 2.0
        if avg_hit_rate > 80.0:  # Hot cache, good performance
            cache_adjustment += 0.03
        elif avg_hit_rate < 30.0:  # Cold cache, needs warming
            cache_adjustment += 0.02

        # 5. Cognitive load and cache interaction
        if cognitive_load > 0.7 and cache_pressure > 0.7:
            # High load + high cache pressure = very selective
            cache_adjustment -= 0.12

        # Apply adjustment to decision
        adjusted_score = base_decision.adjusted_score + cache_adjustment
        adjusted_score = max(0.0, min(1.0, adjusted_score))  # Clamp to valid range

        # Recalculate admission decision with adjusted score
        threshold = await self._get_adaptive_threshold(cognitive_load, priority, None)
        admitted = adjusted_score >= threshold

        # Update eviction recommendation based on cache state
        eviction_recommendation = base_decision.eviction_recommendation
        if (
            not admitted
            and priority.value >= Priority.HIGH.value
            and cache_pressure > 0.8
        ):
            # More aggressive eviction recommendations under cache pressure
            eviction_recommendation = (
                await self._generate_cache_aware_eviction_recommendation(
                    adjusted_score, priority, cache_stats
                )
            )
            if eviction_recommendation:
                admitted = True

        # Create adjusted decision
        adjusted_decision = AdmissionDecision(
            admitted=admitted,
            confidence=self._calculate_confidence(
                adjusted_score, threshold, base_decision.decision_factors
            ),
            salience_score=base_decision.salience_score,
            adjusted_score=adjusted_score,
            decision_factors={
                **base_decision.decision_factors,
                "cache_adjustment": cache_adjustment,
                "cache_pressure": cache_pressure,
                "cache_efficiency": cache_efficiency,
            },
            eviction_recommendation=eviction_recommendation,
            reason=self._generate_cache_aware_decision_reason(
                admitted, adjusted_score, threshold, cache_adjustment, cache_pressure
            ),
        )

        return adjusted_decision

    def _calculate_cache_pressure(self, cache_stats: Dict[str, Any]) -> float:
        """Calculate overall cache system pressure."""

        l1_utilization = cache_stats.get("l1", {}).get("utilization", 0.0)
        l2_utilization = cache_stats.get("l2", {}).get("utilization", 0.0)

        # L1 pressure is more critical
        l1_pressure = l1_utilization
        l2_pressure = l2_utilization * 0.7  # L2 pressure is less critical

        # Consider eviction rates
        l1_evictions = cache_stats.get("l1", {}).get("metrics", {}).get("evictions", 0)
        l2_evictions = cache_stats.get("l2", {}).get("metrics", {}).get("evictions", 0)

        # High eviction rate indicates pressure
        eviction_pressure = min(1.0, (l1_evictions + l2_evictions) / 100.0)

        # Combined pressure calculation
        overall_pressure = (
            l1_pressure * 0.5  # L1 utilization most important
            + l2_pressure * 0.3  # L2 utilization moderate importance
            + eviction_pressure * 0.2  # Eviction rate indicates churn
        )

        return min(1.0, overall_pressure)

    async def _generate_cache_aware_eviction_recommendation(
        self,
        item_score: float,
        item_priority: Priority,
        cache_stats: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Generate cache-aware eviction recommendation."""

        # Focus on L1 eviction candidates under cache pressure
        l1_utilization = cache_stats.get("l1", {}).get("utilization", 0.0)

        if l1_utilization > 0.8:  # L1 is under pressure
            recommendation = {
                "evict_from_level": "L1",
                "reason": "cache_pressure_l1",
                "target_utilization": 0.7,
                "estimated_improvement": item_score * 0.8,  # Account for cache benefit
                "cache_efficiency_gain": 5.0,  # Estimated efficiency improvement
            }

            # Add L2 demotion suggestion
            if l1_utilization > 0.9:
                recommendation["suggested_demotions"] = 2
                recommendation["demote_to_level"] = "L2"

            return recommendation

        return None

    def _generate_cache_aware_decision_reason(
        self,
        admitted: bool,
        adjusted_score: float,
        threshold: float,
        cache_adjustment: float,
        cache_pressure: float,
    ) -> str:
        """Generate cache-aware decision reason."""

        if cache_adjustment > 0.05:
            cache_factor = "cache_efficiency_bonus"
        elif cache_adjustment < -0.05:
            cache_factor = "cache_pressure_penalty"
        else:
            cache_factor = "cache_neutral"

        if admitted:
            if cache_pressure > 0.8:
                return f"admitted_despite_cache_pressure_{cache_factor}"
            else:
                return f"admitted_with_{cache_factor}"
        else:
            if cache_pressure > 0.8:
                return f"rejected_due_to_cache_pressure_{cache_factor}"
            else:
                return f"rejected_with_{cache_factor}"
        """Get admission controller statistics."""

        if not self.admission_history:
            return {
                "total_decisions": 0,
                "admission_rate": 0.0,
                "average_score": 0.0,
                "average_load": 0.0,
            }

        total_decisions = len(self.admission_history)
        admissions = sum(1 for d in self.admission_history if d["admitted"])
        admission_rate = admissions / total_decisions

        avg_score = (
            sum(d["adjusted_score"] for d in self.admission_history) / total_decisions
        )
        avg_load = (
            sum(self.load_history) / len(self.load_history)
            if self.load_history
            else 0.0
        )

        return {
            "total_decisions": total_decisions,
            "admission_rate": admission_rate,
            "average_score": avg_score,
            "average_load": avg_load,
            "current_policy": self.policy.value,
            "current_threshold": self.criteria.min_salience_threshold,
        }


# TODO: Production enhancements needed:
# - Implement machine learning-based salience prediction
# - Add semantic similarity calculation using embeddings
# - Implement personalized admission thresholds
# - Add support for temporal relevance patterns
# - Implement multi-objective optimization for admission decisions
# - Add integration with attention mechanisms
# - Implement admission policy recommendation system

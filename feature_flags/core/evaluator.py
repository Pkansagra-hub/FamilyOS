"""
Feature Flag Evaluator
======================

High-performance flag evaluation engine with cognitive awareness.
Handles flag evaluation with caching, load awareness, and brain-inspired
processing context integration.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import Environment, FlagConfig, FlagDefinition


@dataclass
class EvaluationContext:
    """Context for flag evaluation including cognitive state."""

    # Environment context
    environment: Environment = Environment.DEVELOPMENT
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Cognitive context
    cognitive_load: float = 0.0
    working_memory_load: float = 0.0
    attention_queue_depth: int = 0
    neural_pathway: Optional[str] = None
    brain_region: Optional[str] = None

    # Performance context
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # System context
    system_load: float = 0.0
    memory_pressure: float = 0.0
    cpu_utilization: float = 0.0


@dataclass
class EvaluationResult:
    """Result of flag evaluation with metadata."""

    flag_name: str
    value: Any
    rule_applied: str
    evaluation_time_ms: float
    cache_hit: bool = False
    cognitive_override: bool = False
    reason: Optional[str] = None


class FlagEvaluator:
    """
    High-performance feature flag evaluator with cognitive awareness.

    Provides fast flag evaluation with sophisticated rules including:
    - Environment-specific overrides
    - Cognitive load-aware evaluation
    - Neural pathway-specific rules
    - Performance budget enforcement
    - Caching for optimal performance
    """

    def __init__(self, config: FlagConfig):
        self.config = config
        self.evaluation_cache: Dict[str, Dict[str, Any]] = {}
        self.evaluation_stats: Dict[str, int] = {
            "total_evaluations": 0,
            "cache_hits": 0,
            "cognitive_overrides": 0,
            "load_based_overrides": 0,
        }

    async def evaluate_flag(
        self, flag_name: str, context: EvaluationContext
    ) -> EvaluationResult:
        """
        Evaluate a feature flag with cognitive awareness.

        Args:
            flag_name: Name of the flag to evaluate
            context: Evaluation context including cognitive state

        Returns:
            EvaluationResult with value and metadata
        """
        start_time = time.perf_counter()
        self.evaluation_stats["total_evaluations"] += 1

        # Check cache first
        cache_key = self._generate_cache_key(flag_name, context)
        cached_result = self._get_cached_result(cache_key)

        if cached_result is not None:
            self.evaluation_stats["cache_hits"] += 1
            evaluation_time = (time.perf_counter() - start_time) * 1000
            return EvaluationResult(
                flag_name=flag_name,
                value=cached_result["value"],
                rule_applied=cached_result["rule"],
                evaluation_time_ms=evaluation_time,
                cache_hit=True,
                reason="Retrieved from cache",
            )

        # Get flag definition
        flag = self.config.get_flag(flag_name)
        if flag is None:
            evaluation_time = (time.perf_counter() - start_time) * 1000
            return EvaluationResult(
                flag_name=flag_name,
                value=False,
                rule_applied="flag_not_found",
                evaluation_time_ms=evaluation_time,
                reason=f"Flag '{flag_name}' not found",
            )

        # Check if flag is enabled
        if not flag.enabled:
            result_value = False
            rule_applied = "flag_disabled"
            reason = "Flag is globally disabled"
        else:
            # Apply evaluation rules in priority order
            result_value, rule_applied, reason = await self._apply_evaluation_rules(
                flag, context
            )

        evaluation_time = (time.perf_counter() - start_time) * 1000

        # Cache the result
        self._cache_result(cache_key, result_value, rule_applied)

        return EvaluationResult(
            flag_name=flag_name,
            value=result_value,
            rule_applied=rule_applied,
            evaluation_time_ms=evaluation_time,
            cognitive_override=rule_applied.startswith("cognitive_"),
            reason=reason,
        )

    async def evaluate_multiple_flags(
        self, flag_names: List[str], context: EvaluationContext
    ) -> Dict[str, EvaluationResult]:
        """Evaluate multiple flags efficiently."""
        results = {}

        for flag_name in flag_names:
            results[flag_name] = await self.evaluate_flag(flag_name, context)

        return results

    async def get_flags_by_category(
        self, category: str, context: EvaluationContext
    ) -> Dict[str, EvaluationResult]:
        """Get all flags in a category with their evaluated values."""
        category_flags = self.config.get_flags_by_category(category)
        flag_names = list(category_flags.keys())
        return await self.evaluate_multiple_flags(flag_names, context)

    async def get_cognitive_flags(
        self, context: EvaluationContext
    ) -> Dict[str, EvaluationResult]:
        """Get all cognitive-aware flags with their evaluated values."""
        cognitive_flags = self.config.get_cognitive_flags()
        flag_names = list(cognitive_flags.keys())
        return await self.evaluate_multiple_flags(flag_names, context)

    async def _apply_evaluation_rules(
        self, flag: FlagDefinition, context: EvaluationContext
    ) -> tuple[Any, str, str]:
        """Apply evaluation rules in priority order."""

        # Rule 1: Cognitive load override (highest priority)
        if flag.is_cognitive_aware() and flag.cognitive_context.load_aware:
            cognitive_result = await self._evaluate_cognitive_load_rule(flag, context)
            if cognitive_result is not None:
                self.evaluation_stats["cognitive_overrides"] += 1
                return cognitive_result

        # Rule 2: Neural pathway-specific rules
        if flag.is_cognitive_aware() and context.neural_pathway:
            pathway_result = await self._evaluate_neural_pathway_rule(flag, context)
            if pathway_result is not None:
                return pathway_result

        # Rule 3: System performance rules
        if context.system_load > 0.8 or context.memory_pressure > 0.9:
            performance_result = await self._evaluate_performance_rule(flag, context)
            if performance_result is not None:
                self.evaluation_stats["load_based_overrides"] += 1
                return performance_result

        # Rule 4: Environment-specific value
        env_value = flag.get_value(context.environment)
        return (
            env_value,
            "environment_default",
            f"Using {context.environment.value} environment value",
        )

    async def _evaluate_cognitive_load_rule(
        self, flag: FlagDefinition, context: EvaluationContext
    ) -> Optional[tuple[Any, str, str]]:
        """Evaluate cognitive load-based rules."""
        cognitive_ctx = flag.cognitive_context

        if context.cognitive_load > cognitive_ctx.cognitive_load_threshold:
            # High cognitive load - apply performance-preserving rules

            if cognitive_ctx.performance_impact == "high":
                # Disable high-impact features under load
                return (
                    False,
                    "cognitive_load_high_impact_disabled",
                    f"Disabled due to high cognitive load ({context.cognitive_load:.2f} > {cognitive_ctx.cognitive_load_threshold})",
                )

            elif cognitive_ctx.performance_impact == "medium":
                # Conditionally disable medium-impact features
                if context.cognitive_load > 0.9:
                    return (
                        False,
                        "cognitive_load_medium_impact_disabled",
                        f"Disabled due to very high cognitive load ({context.cognitive_load:.2f})",
                    )

        # Working memory specific rules
        if context.working_memory_load > 0.8 and "working_memory" in flag.category:
            if "l3_cache" in flag.name:
                return (
                    False,
                    "cognitive_working_memory_l3_disabled",
                    "L3 cache disabled due to working memory pressure",
                )
            elif "complex" in flag.name or "advanced" in flag.name:
                return (
                    False,
                    "cognitive_working_memory_complexity_reduced",
                    "Complex features disabled due to working memory load",
                )

        # Attention queue specific rules
        if context.attention_queue_depth > 100 and "attention_gate" in flag.category:
            if "detailed_analysis" in flag.name:
                return (
                    False,
                    "cognitive_attention_queue_analysis_disabled",
                    "Detailed analysis disabled due to attention queue backlog",
                )

        return None

    async def _evaluate_neural_pathway_rule(
        self, flag: FlagDefinition, context: EvaluationContext
    ) -> Optional[tuple[Any, str, str]]:
        """Evaluate neural pathway-specific rules."""
        cognitive_ctx = flag.cognitive_context

        # Match neural pathway context
        if cognitive_ctx.neural_pathway and context.neural_pathway:
            if cognitive_ctx.neural_pathway == context.neural_pathway:
                # Pathway match - potentially boost performance
                if cognitive_ctx.performance_impact == "low":
                    return (
                        True,
                        "neural_pathway_optimized",
                        f"Enabled for optimized {context.neural_pathway} pathway",
                    )
            else:
                # Pathway mismatch - potentially reduce overhead
                if cognitive_ctx.performance_impact == "high":
                    return (
                        False,
                        "neural_pathway_mismatch",
                        f"Disabled for non-matching pathway ({context.neural_pathway})",
                    )

        # Brain region specific optimizations
        if cognitive_ctx.brain_region and context.brain_region:
            if cognitive_ctx.brain_region == context.brain_region:
                return (
                    True,
                    "brain_region_optimized",
                    f"Enabled for {context.brain_region} processing",
                )

        return None

    async def _evaluate_performance_rule(
        self, flag: FlagDefinition, context: EvaluationContext
    ) -> Optional[tuple[Any, str, str]]:
        """Evaluate system performance-based rules."""

        # Under high system load, disable expensive features
        if context.system_load > 0.8:
            if (
                flag.is_cognitive_aware()
                and flag.cognitive_context.performance_impact == "high"
            ):
                return (
                    False,
                    "system_load_high_impact_disabled",
                    f"Disabled due to high system load ({context.system_load:.2f})",
                )

        # Under memory pressure, disable memory-intensive features
        if context.memory_pressure > 0.9:
            if "cache" in flag.name or "buffer" in flag.name:
                return (
                    False,
                    "memory_pressure_cache_disabled",
                    f"Cache features disabled due to memory pressure ({context.memory_pressure:.2f})",
                )

        return None

    def _generate_cache_key(self, flag_name: str, context: EvaluationContext) -> str:
        """Generate cache key for evaluation result."""
        # Include relevant context that affects evaluation
        key_parts = [
            flag_name,
            context.environment.value,
            f"load_{context.cognitive_load:.1f}",
            f"mem_{context.working_memory_load:.1f}",
            f"queue_{context.attention_queue_depth}",
            context.neural_pathway or "none",
            context.brain_region or "none",
        ]
        return "|".join(key_parts)

    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached evaluation result if available and valid."""
        if cache_key in self.evaluation_cache:
            cached = self.evaluation_cache[cache_key]

            # Check if cache is still valid (1 minute TTL)
            cache_age = time.time() - cached["timestamp"]
            if cache_age < 60:  # 1 minute TTL
                return cached
            else:
                # Remove expired cache entry
                del self.evaluation_cache[cache_key]

        return None

    def _cache_result(self, cache_key: str, value: Any, rule: str) -> None:
        """Cache evaluation result."""
        self.evaluation_cache[cache_key] = {
            "value": value,
            "rule": rule,
            "timestamp": time.time(),
        }

        # Simple cache size management
        if len(self.evaluation_cache) > 1000:
            # Remove oldest 20% of entries
            sorted_keys = sorted(
                self.evaluation_cache.keys(),
                key=lambda k: self.evaluation_cache[k]["timestamp"],
            )
            for key in sorted_keys[:200]:
                del self.evaluation_cache[key]

    def get_evaluation_stats(self) -> Dict[str, Any]:
        """Get evaluation performance statistics."""
        total = self.evaluation_stats["total_evaluations"]
        if total == 0:
            return self.evaluation_stats

        cache_hit_rate = (self.evaluation_stats["cache_hits"] / total) * 100
        cognitive_override_rate = (
            self.evaluation_stats["cognitive_overrides"] / total
        ) * 100
        load_override_rate = (
            self.evaluation_stats["load_based_overrides"] / total
        ) * 100

        return {
            **self.evaluation_stats,
            "cache_hit_rate_percent": cache_hit_rate,
            "cognitive_override_rate_percent": cognitive_override_rate,
            "load_override_rate_percent": load_override_rate,
            "cache_size": len(self.evaluation_cache),
        }

    def clear_cache(self) -> None:
        """Clear evaluation cache."""
        self.evaluation_cache.clear()

    def reset_stats(self) -> None:
        """Reset evaluation statistics."""
        self.evaluation_stats = {
            "total_evaluations": 0,
            "cache_hits": 0,
            "cognitive_overrides": 0,
            "load_based_overrides": 0,
        }

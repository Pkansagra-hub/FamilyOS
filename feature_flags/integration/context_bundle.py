"""
Context Bundle Integration
==========================

Feature flag integration for Context Bundle Builder system.
Provides hippocampal recall-aware flag evaluation for context assembly operations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from ..flag_manager import CognitiveFlagManager


class DiversificationStrategy(Enum):
    """Context diversification strategies."""

    MMR = "maximal_marginal_relevance"
    SEMANTIC_CLUSTERING = "semantic_clustering"
    TEMPORAL_WEIGHTING = "temporal_weighting"
    RANDOM_SAMPLING = "random_sampling"
    NONE = "none"


class BundleSizingStrategy(Enum):
    """Bundle sizing strategies."""

    FIXED = "fixed"
    ADAPTIVE = "adaptive"
    COGNITIVE_LOAD_AWARE = "cognitive_load_aware"
    PERFORMANCE_OPTIMIZED = "performance_optimized"


@dataclass
class ContextBundleMetrics:
    """Context bundle performance metrics for flag evaluation."""

    # Bundle metrics
    average_bundle_size: int = 0
    bundle_creation_time_ms: float = 0.0
    bundle_relevance_score: float = 0.0

    # Diversification metrics
    semantic_diversity: float = 0.0
    temporal_spread: float = 0.0
    mmr_efficiency: float = 0.0

    # Load metrics
    cognitive_load: float = 0.0
    hippocampus_activity: float = 0.0
    recall_complexity: float = 0.0

    # Performance metrics
    assembly_latency_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cache_hit_rate: float = 0.0

    # Quality metrics
    context_coherence: float = 0.0
    relevance_precision: float = 0.0
    relevance_recall: float = 0.0


class ContextBundleFlagAdapter:
    """
    Feature flag adapter for Context Bundle Builder system.

    Provides cognitive-aware flag evaluation for:
    - MMR (Maximal Marginal Relevance) diversification
    - Semantic clustering algorithms
    - Temporal weighting strategies
    - Multi-modal fusion capabilities
    - Adaptive bundle sizing
    """

    def __init__(self, cognitive_manager: CognitiveFlagManager):
        self.cognitive_manager = cognitive_manager
        self.current_metrics = ContextBundleMetrics()

        # Flag mappings to specific context bundle features
        self.flag_features = {
            "context_bundle.enable_mmr_diversification": "mmr_diversification",
            "context_bundle.enable_semantic_clustering": "semantic_clustering",
            "context_bundle.enable_temporal_weighting": "temporal_weighting",
            "context_bundle.enable_multi_modal_fusion": "multi_modal_fusion",
            "context_bundle.enable_adaptive_sizing": "adaptive_sizing",
        }

    async def get_diversification_flags(
        self,
        cognitive_load: float = 0.0,
        hippocampus_activity: float = 0.0,
        semantic_complexity: float = 0.0,
    ) -> Dict[str, bool]:
        """Get diversification flags based on cognitive state."""

        # Update metrics
        self.current_metrics.cognitive_load = cognitive_load
        self.current_metrics.hippocampus_activity = hippocampus_activity
        self.current_metrics.recall_complexity = semantic_complexity

        flags = await self.cognitive_manager.get_context_bundle_flags(
            cognitive_load=cognitive_load,
            hippocampus_activity=hippocampus_activity,
            semantic_complexity=semantic_complexity,
            bundle_size=self.current_metrics.average_bundle_size,
        )

        # Filter to diversification-related flags
        diversification_flags = {
            "mmr_diversification": flags.get(
                "context_bundle.enable_mmr_diversification", False
            ),
            "semantic_clustering": flags.get(
                "context_bundle.enable_semantic_clustering", False
            ),
            "temporal_weighting": flags.get(
                "context_bundle.enable_temporal_weighting", False
            ),
        }

        return diversification_flags

    async def get_assembly_flags(
        self,
        cognitive_load: float = 0.0,
        assembly_complexity: float = 0.0,
        memory_pressure: float = 0.0,
    ) -> Dict[str, bool]:
        """Get context assembly flags based on system state."""

        # Update metrics
        self.current_metrics.cognitive_load = cognitive_load
        self.current_metrics.memory_usage_mb = (
            memory_pressure * 1000
        )  # Convert to MB estimate

        flags = await self.cognitive_manager.get_context_bundle_flags(
            cognitive_load=cognitive_load,
            hippocampus_activity=self.current_metrics.hippocampus_activity,
            semantic_complexity=assembly_complexity,
            bundle_size=self.current_metrics.average_bundle_size,
        )

        # Filter to assembly-related flags
        assembly_flags = {
            "multi_modal_fusion": flags.get(
                "context_bundle.enable_multi_modal_fusion", False
            ),
            "adaptive_sizing": flags.get(
                "context_bundle.enable_adaptive_sizing", False
            ),
        }

        return assembly_flags

    async def get_diversification_strategy(
        self,
        cognitive_load: float,
        available_contexts: int,
        target_diversity: float = 0.7,
        time_budget_ms: float = 100.0,
    ) -> Dict[str, Any]:
        """Get appropriate context diversification strategy."""

        diversification_flags = await self.get_diversification_flags(
            cognitive_load=cognitive_load,
            hippocampus_activity=self.current_metrics.hippocampus_activity,
            semantic_complexity=available_contexts / 100.0,  # Normalize complexity
        )

        # Determine strategy based on flags and constraints
        mmr_enabled = diversification_flags.get("mmr_diversification", False)
        semantic_enabled = diversification_flags.get("semantic_clustering", False)
        temporal_enabled = diversification_flags.get("temporal_weighting", False)

        if not any([mmr_enabled, semantic_enabled, temporal_enabled]):
            return {
                "strategy": DiversificationStrategy.NONE.value,
                "parameters": {},
                "expected_diversity": 0.0,
                "reason": "All diversification strategies disabled",
            }

        # Choose strategy based on cognitive load and time budget
        if cognitive_load > 0.8 or time_budget_ms < 50.0:
            # High load or tight budget - use fastest strategy
            if temporal_enabled:
                strategy = DiversificationStrategy.TEMPORAL_WEIGHTING
                parameters = {
                    "temporal_decay": 0.9,
                    "max_time_span_hours": 24,
                    "weight_function": "exponential",
                }
                expected_diversity = min(target_diversity, 0.5)
                reason = "Fast temporal weighting for high cognitive load"
            else:
                strategy = DiversificationStrategy.RANDOM_SAMPLING
                parameters = {
                    "sample_size": min(10, available_contexts),
                    "seed": None,  # Random seed
                }
                expected_diversity = 0.3
                reason = "Fallback to random sampling"

        elif cognitive_load > 0.5 or time_budget_ms < 200.0:
            # Medium load - use semantic clustering
            if semantic_enabled:
                strategy = DiversificationStrategy.SEMANTIC_CLUSTERING
                parameters = {
                    "cluster_count": min(5, available_contexts // 10),
                    "similarity_threshold": 0.7,
                    "max_cluster_size": 20,
                }
                expected_diversity = min(target_diversity, 0.7)
                reason = "Semantic clustering for medium cognitive load"
            elif temporal_enabled:
                strategy = DiversificationStrategy.TEMPORAL_WEIGHTING
                parameters = {
                    "temporal_decay": 0.8,
                    "max_time_span_hours": 72,
                    "weight_function": "linear",
                }
                expected_diversity = 0.6
                reason = "Temporal weighting fallback"
            else:
                strategy = DiversificationStrategy.RANDOM_SAMPLING
                parameters = {"sample_size": min(15, available_contexts)}
                expected_diversity = 0.4
                reason = "Random sampling fallback"

        else:
            # Low load - use optimal MMR strategy
            if mmr_enabled:
                strategy = DiversificationStrategy.MMR
                parameters = {
                    "lambda_param": 0.7,  # Balance relevance vs diversity
                    "similarity_function": "cosine",
                    "max_iterations": min(100, available_contexts),
                    "convergence_threshold": 0.01,
                }
                expected_diversity = target_diversity
                reason = "Optimal MMR for low cognitive load"
            elif semantic_enabled:
                strategy = DiversificationStrategy.SEMANTIC_CLUSTERING
                parameters = {
                    "cluster_count": min(8, available_contexts // 5),
                    "similarity_threshold": 0.6,
                    "max_cluster_size": 15,
                }
                expected_diversity = 0.8
                reason = "Enhanced semantic clustering"
            else:
                strategy = DiversificationStrategy.TEMPORAL_WEIGHTING
                parameters = {
                    "temporal_decay": 0.7,
                    "max_time_span_hours": 168,  # 1 week
                    "weight_function": "exponential",
                }
                expected_diversity = 0.6
                reason = "Temporal weighting fallback"

        return {
            "strategy": strategy.value,
            "parameters": parameters,
            "expected_diversity": expected_diversity,
            "time_budget_ms": time_budget_ms,
            "cognitive_load": cognitive_load,
            "available_contexts": available_contexts,
            "reason": reason,
        }

    async def get_bundle_sizing_strategy(
        self,
        cognitive_load: float,
        query_complexity: float,
        available_memory: float,
        target_accuracy: float = 0.8,
    ) -> Dict[str, Any]:
        """Get appropriate bundle sizing strategy."""

        assembly_flags = await self.get_assembly_flags(
            cognitive_load=cognitive_load,
            assembly_complexity=query_complexity,
            memory_pressure=1.0 - available_memory,
        )

        adaptive_sizing = assembly_flags.get("adaptive_sizing", False)

        if not adaptive_sizing:
            # Fixed sizing when adaptive is disabled
            base_size = 10 if cognitive_load > 0.7 else 20
            return {
                "strategy": BundleSizingStrategy.FIXED.value,
                "bundle_size": base_size,
                "size_bounds": {"min": base_size, "max": base_size},
                "reason": "Adaptive sizing disabled - using fixed size",
            }

        # Adaptive sizing based on cognitive state
        if cognitive_load > 0.8:
            # High load - performance optimized (small bundles)
            strategy = BundleSizingStrategy.PERFORMANCE_OPTIMIZED
            base_size = 5
            size_bounds = {"min": 3, "max": 10}
            reason = "Performance optimized for high cognitive load"

        elif cognitive_load > 0.5:
            # Medium load - cognitive load aware
            strategy = BundleSizingStrategy.COGNITIVE_LOAD_AWARE
            base_size = int(15 * (1.0 - cognitive_load))  # Inversely related to load
            size_bounds = {"min": 5, "max": 25}
            reason = f"Cognitive load aware sizing for load {cognitive_load:.2f}"

        else:
            # Low load - full adaptive strategy
            strategy = BundleSizingStrategy.ADAPTIVE
            # Size based on query complexity and target accuracy
            complexity_factor = min(2.0, query_complexity + 1.0)
            accuracy_factor = target_accuracy * 1.5
            base_size = int(20 * complexity_factor * accuracy_factor)
            size_bounds = {"min": 10, "max": 50}
            reason = "Full adaptive sizing for optimal accuracy"

        # Apply memory constraints
        memory_factor = available_memory
        adjusted_size = int(base_size * memory_factor)
        adjusted_max = int(size_bounds["max"] * memory_factor)

        # Ensure minimum viable size
        final_size = max(3, min(adjusted_size, adjusted_max))
        final_bounds = {
            "min": max(3, int(size_bounds["min"] * memory_factor)),
            "max": adjusted_max,
        }

        return {
            "strategy": strategy.value,
            "bundle_size": final_size,
            "size_bounds": final_bounds,
            "factors": {
                "cognitive_load": cognitive_load,
                "query_complexity": query_complexity,
                "available_memory": available_memory,
                "target_accuracy": target_accuracy,
            },
            "reason": reason,
        }

    async def get_multi_modal_fusion_config(
        self, cognitive_load: float, modality_count: int, fusion_complexity: float
    ) -> Dict[str, Any]:
        """Get multi-modal fusion configuration."""

        assembly_flags = await self.get_assembly_flags(
            cognitive_load=cognitive_load,
            assembly_complexity=fusion_complexity,
            memory_pressure=modality_count / 10.0,  # Normalize modality pressure
        )

        fusion_enabled = assembly_flags.get("multi_modal_fusion", False)

        if not fusion_enabled or modality_count < 2:
            return {
                "enabled": False,
                "fusion_strategy": "none",
                "modality_weights": {},
                "reason": "Multi-modal fusion disabled or insufficient modalities",
            }

        # Configure fusion based on cognitive load
        if cognitive_load > 0.8:
            # High load - simple weighted average
            fusion_strategy = "weighted_average"
            modality_weights = {
                f"modality_{i}": 1.0 / modality_count for i in range(modality_count)
            }
            max_modalities = min(3, modality_count)
            reason = "Simple weighted fusion for high cognitive load"

        elif cognitive_load > 0.5:
            # Medium load - attention-based fusion
            fusion_strategy = "attention_weighted"
            # Give higher weights to first few modalities (attention mechanism)
            weights = []
            for i in range(modality_count):
                weight = 1.0 / (i + 1)  # Decreasing weights
                weights.append(weight)

            # Normalize weights
            total_weight = sum(weights)
            modality_weights = {
                f"modality_{i}": weights[i] / total_weight
                for i in range(modality_count)
            }
            max_modalities = min(5, modality_count)
            reason = "Attention-weighted fusion for medium cognitive load"

        else:
            # Low load - sophisticated cross-modal attention
            fusion_strategy = "cross_modal_attention"
            # Use learned attention weights (simulated here)
            attention_scores = [0.8, 0.6, 0.7, 0.5, 0.4][:modality_count]
            total_attention = sum(attention_scores)
            modality_weights = {
                f"modality_{i}": attention_scores[i] / total_attention
                for i in range(len(attention_scores))
            }
            max_modalities = modality_count
            reason = "Cross-modal attention fusion for optimal accuracy"

        return {
            "enabled": True,
            "fusion_strategy": fusion_strategy,
            "modality_weights": modality_weights,
            "max_modalities": max_modalities,
            "fusion_complexity": fusion_complexity,
            "cognitive_load": cognitive_load,
            "reason": reason,
        }

    def update_metrics(self, metrics: ContextBundleMetrics) -> None:
        """Update current context bundle metrics."""
        self.current_metrics = metrics

    def get_current_metrics(self) -> ContextBundleMetrics:
        """Get current context bundle metrics."""
        return self.current_metrics

    async def get_adaptive_configuration(self) -> Dict[str, Any]:
        """Get complete adaptive configuration for context bundle builder."""

        # Get all context bundle flags
        flags = await self.cognitive_manager.get_context_bundle_flags(
            cognitive_load=self.current_metrics.cognitive_load,
            hippocampus_activity=self.current_metrics.hippocampus_activity,
            semantic_complexity=self.current_metrics.recall_complexity,
            bundle_size=self.current_metrics.average_bundle_size,
        )

        # Get specific configurations
        diversification_config = await self.get_diversification_strategy(
            cognitive_load=self.current_metrics.cognitive_load,
            available_contexts=100,  # Default available contexts
            target_diversity=0.7,
            time_budget_ms=self.current_metrics.assembly_latency_ms or 100.0,
        )

        sizing_config = await self.get_bundle_sizing_strategy(
            cognitive_load=self.current_metrics.cognitive_load,
            query_complexity=self.current_metrics.recall_complexity,
            available_memory=1.0 - (self.current_metrics.memory_usage_mb / 1000.0),
            target_accuracy=0.8,
        )

        fusion_config = await self.get_multi_modal_fusion_config(
            cognitive_load=self.current_metrics.cognitive_load,
            modality_count=3,  # Default modality count
            fusion_complexity=self.current_metrics.recall_complexity,
        )

        return {
            "flags": flags,
            "configurations": {
                "diversification": diversification_config,
                "bundle_sizing": sizing_config,
                "multi_modal_fusion": fusion_config,
                "quality_thresholds": {
                    "min_relevance_score": 0.5,
                    "min_diversity_score": 0.3,
                    "max_assembly_time_ms": 500.0,
                },
            },
            "metrics": self.current_metrics,
            "adaptive_rules": {
                "description": "Context bundle adaptive configuration",
                "cognitive_load_threshold": 0.8,
                "hippocampus_activity_threshold": 0.7,
                "optimization_target": "context_quality",
            },
        }

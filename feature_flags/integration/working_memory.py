"""
Working Memory Integration
==========================

Feature flag integration for Working Memory Manager.
Provides cognitive load-aware flag evaluation for working memory operations.
"""

from dataclasses import dataclass
from typing import Any, Dict

from ..flag_manager import CognitiveFlagManager


@dataclass
class WorkingMemoryMetrics:
    """Working memory performance metrics for flag evaluation."""

    # Cache metrics
    l1_cache_hit_rate: float = 0.0
    l2_cache_hit_rate: float = 0.0
    l3_cache_hit_rate: float = 0.0
    cache_eviction_rate: float = 0.0

    # Load metrics
    cognitive_load: float = 0.0
    working_memory_load: float = 0.0
    prefrontal_cortex_load: float = 0.0

    # Performance metrics
    operation_latency_ms: float = 0.0
    memory_pressure: float = 0.0
    cache_memory_usage_mb: float = 0.0

    # Processing metrics
    active_contexts: int = 0
    pending_operations: int = 0
    compression_ratio: float = 1.0


class WorkingMemoryFlagAdapter:
    """
    Feature flag adapter for Working Memory Manager.

    Provides cognitive-aware flag evaluation for:
    - Hierarchical cache management (L1/L2/L3)
    - Complex operation handling
    - Predictive prefetching
    - Memory compression
    - Performance optimization
    """

    def __init__(self, cognitive_manager: CognitiveFlagManager):
        self.cognitive_manager = cognitive_manager
        self.current_metrics = WorkingMemoryMetrics()

        # Flag mappings to specific working memory features
        self.flag_features = {
            "working_memory.enable_hierarchical_cache": "hierarchical_cache",
            "working_memory.enable_l3_cache": "l3_cache",
            "working_memory.enable_complex_operations": "complex_operations",
            "working_memory.enable_predictive_prefetch": "predictive_prefetch",
            "working_memory.enable_compression": "compression",
        }

    async def get_cache_flags(
        self,
        cache_hit_rate: float = 0.0,
        memory_pressure: float = 0.0,
        cognitive_load: float = 0.0,
    ) -> Dict[str, bool]:
        """Get cache-related flags based on current performance."""

        # Update metrics
        self.current_metrics.l1_cache_hit_rate = cache_hit_rate
        self.current_metrics.memory_pressure = memory_pressure
        self.current_metrics.cognitive_load = cognitive_load

        # High memory pressure or low cache performance may disable L3
        cache_pressure = memory_pressure
        if cache_hit_rate < 0.7:  # Poor cache performance
            cache_pressure = min(1.0, cache_pressure + 0.2)

        flags = await self.cognitive_manager.get_working_memory_flags(
            cognitive_load=cognitive_load,
            working_memory_load=memory_pressure,
            prefrontal_cortex_load=cognitive_load,
            cache_pressure=cache_pressure,
        )

        # Filter to cache-related flags
        cache_flags = {
            "hierarchical_cache": flags.get(
                "working_memory.enable_hierarchical_cache", False
            ),
            "l3_cache": flags.get("working_memory.enable_l3_cache", False),
        }

        return cache_flags

    async def get_operation_flags(
        self,
        cognitive_load: float = 0.0,
        operation_complexity: float = 0.0,
        pending_operations: int = 0,
    ) -> Dict[str, bool]:
        """Get operation-related flags based on cognitive state."""

        # Update metrics
        self.current_metrics.cognitive_load = cognitive_load
        self.current_metrics.pending_operations = pending_operations

        # Adjust working memory load based on operation complexity and queue
        working_memory_load = min(
            1.0, (pending_operations / 100.0) + operation_complexity
        )

        flags = await self.cognitive_manager.get_working_memory_flags(
            cognitive_load=cognitive_load,
            working_memory_load=working_memory_load,
            prefrontal_cortex_load=cognitive_load,
        )

        # Filter to operation-related flags
        operation_flags = {
            "complex_operations": flags.get(
                "working_memory.enable_complex_operations", False
            ),
            "predictive_prefetch": flags.get(
                "working_memory.enable_predictive_prefetch", False
            ),
            "compression": flags.get("working_memory.enable_compression", False),
        }

        return operation_flags

    async def should_enable_l3_cache(
        self,
        current_memory_usage: float,
        cache_performance: float,
        cognitive_load: float,
    ) -> bool:
        """Determine if L3 cache should be enabled based on current conditions."""

        cache_flags = await self.get_cache_flags(
            cache_hit_rate=cache_performance,
            memory_pressure=current_memory_usage,
            cognitive_load=cognitive_load,
        )

        return cache_flags.get("l3_cache", False)

    async def should_enable_complex_operations(
        self,
        cognitive_load: float,
        operation_queue_depth: int,
        available_capacity: float,
    ) -> bool:
        """Determine if complex operations should be enabled."""

        # Calculate operation complexity based on queue and capacity
        operation_complexity = (operation_queue_depth / 50.0) * (
            1.0 - available_capacity
        )

        operation_flags = await self.get_operation_flags(
            cognitive_load=cognitive_load,
            operation_complexity=operation_complexity,
            pending_operations=operation_queue_depth,
        )

        return operation_flags.get("complex_operations", False)

    async def get_compression_strategy(
        self, memory_pressure: float, cognitive_load: float, data_complexity: float
    ) -> Dict[str, Any]:
        """Get appropriate compression strategy based on current state."""

        operation_flags = await self.get_operation_flags(
            cognitive_load=cognitive_load,
            operation_complexity=data_complexity,
            pending_operations=int(memory_pressure * 100),
        )

        compression_enabled = operation_flags.get("compression", False)

        if not compression_enabled:
            return {
                "enabled": False,
                "strategy": "none",
                "reason": "Compression disabled due to cognitive load or memory pressure",
            }

        # Determine compression strategy based on load
        if cognitive_load > 0.8:
            strategy = "fast"
            compression_level = 1
        elif cognitive_load > 0.5:
            strategy = "balanced"
            compression_level = 3
        else:
            strategy = "optimal"
            compression_level = 6

        return {
            "enabled": True,
            "strategy": strategy,
            "compression_level": compression_level,
            "reason": f"Using {strategy} compression for cognitive load {cognitive_load:.2f}",
        }

    async def get_prefetch_configuration(
        self, cognitive_load: float, cache_hit_rate: float, bandwidth_available: float
    ) -> Dict[str, Any]:
        """Get predictive prefetch configuration."""

        operation_flags = await self.get_operation_flags(
            cognitive_load=cognitive_load,
            operation_complexity=1.0 - cache_hit_rate,  # Poor cache = more complex
            pending_operations=int((1.0 - bandwidth_available) * 50),
        )

        prefetch_enabled = operation_flags.get("predictive_prefetch", False)

        if not prefetch_enabled:
            return {
                "enabled": False,
                "prefetch_distance": 0,
                "aggressive_mode": False,
                "reason": "Prefetch disabled due to cognitive load or bandwidth",
            }

        # Configure prefetch based on cognitive state
        if cognitive_load < 0.3:
            # Low load - aggressive prefetching
            prefetch_distance = 10
            aggressive_mode = True
        elif cognitive_load < 0.6:
            # Medium load - moderate prefetching
            prefetch_distance = 5
            aggressive_mode = False
        else:
            # High load - conservative prefetching
            prefetch_distance = 2
            aggressive_mode = False

        return {
            "enabled": True,
            "prefetch_distance": prefetch_distance,
            "aggressive_mode": aggressive_mode,
            "reason": f"Configured for cognitive load {cognitive_load:.2f}",
        }

    def update_metrics(self, metrics: WorkingMemoryMetrics) -> None:
        """Update current working memory metrics."""
        self.current_metrics = metrics

    def get_current_metrics(self) -> WorkingMemoryMetrics:
        """Get current working memory metrics."""
        return self.current_metrics

    async def get_adaptive_configuration(self) -> Dict[str, Any]:
        """Get complete adaptive configuration for working memory."""

        # Get all working memory flags
        flags = await self.cognitive_manager.get_working_memory_flags(
            cognitive_load=self.current_metrics.cognitive_load,
            working_memory_load=self.current_metrics.working_memory_load,
            prefrontal_cortex_load=self.current_metrics.prefrontal_cortex_load,
            cache_pressure=self.current_metrics.memory_pressure,
        )

        # Get specific configurations
        compression_config = await self.get_compression_strategy(
            memory_pressure=self.current_metrics.memory_pressure,
            cognitive_load=self.current_metrics.cognitive_load,
            data_complexity=1.0 - self.current_metrics.l1_cache_hit_rate,
        )

        prefetch_config = await self.get_prefetch_configuration(
            cognitive_load=self.current_metrics.cognitive_load,
            cache_hit_rate=self.current_metrics.l1_cache_hit_rate,
            bandwidth_available=1.0 - self.current_metrics.memory_pressure,
        )

        return {
            "flags": flags,
            "configurations": {
                "compression": compression_config,
                "prefetch": prefetch_config,
                "cache_hierarchy": {
                    "l1_enabled": True,  # Always enabled
                    "l2_enabled": flags.get(
                        "working_memory.enable_hierarchical_cache", False
                    ),
                    "l3_enabled": flags.get("working_memory.enable_l3_cache", False),
                },
            },
            "metrics": self.current_metrics,
            "adaptive_rules": {
                "description": "Working memory adaptive configuration",
                "cognitive_load_threshold": 0.8,
                "memory_pressure_threshold": 0.9,
                "optimization_target": "cognitive_efficiency",
            },
        }

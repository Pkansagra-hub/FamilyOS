"""
Memory Steward Integration
==========================

Feature flag integration for Memory Steward system.
Provides hippocampal-aware flag evaluation for memory management operations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from ..flag_manager import CognitiveFlagManager


class ConsolidationStrategy(Enum):
    """Memory consolidation strategies."""

    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    ADAPTIVE = "adaptive"
    NONE = "none"


class ForgettingStrategy(Enum):
    """Memory forgetting strategies."""

    EXPONENTIAL_DECAY = "exponential_decay"
    PRIORITY_BASED = "priority_based"
    USAGE_BASED = "usage_based"
    INTERFERENCE = "interference"
    NONE = "none"


@dataclass
class MemoryStewardMetrics:
    """Memory steward performance metrics for flag evaluation."""

    # Hippocampus metrics
    hippocampus_activity: float = 0.0
    consolidation_queue_depth: int = 0
    memory_formation_rate: float = 0.0

    # Memory metrics
    total_memories: int = 0
    active_memories: int = 0
    forgotten_memories: int = 0
    memory_retrieval_accuracy: float = 0.0

    # Load metrics
    cognitive_load: float = 0.0
    memory_pressure: float = 0.0
    consolidation_latency_ms: float = 0.0

    # Performance metrics
    recall_latency_ms: float = 0.0
    storage_efficiency: float = 0.0
    compression_ratio: float = 1.0

    # Priority metrics
    high_priority_memories: int = 0
    low_priority_memories: int = 0
    priority_elevation_rate: float = 0.0


class MemoryStewardFlagAdapter:
    """
    Feature flag adapter for Memory Steward system.

    Provides cognitive-aware flag evaluation for:
    - Hippocampal memory formation integration
    - Automatic memory consolidation
    - Predictive memory prefetching
    - Forgetting algorithms
    - Priority elevation mechanisms
    """

    def __init__(self, cognitive_manager: CognitiveFlagManager):
        self.cognitive_manager = cognitive_manager
        self.current_metrics = MemoryStewardMetrics()

        # Flag mappings to specific memory steward features
        self.flag_features = {
            "memory_steward.enable_hippocampus_integration": "hippocampus_integration",
            "memory_steward.enable_auto_consolidation": "auto_consolidation",
            "memory_steward.enable_predictive_prefetch": "predictive_prefetch",
            "memory_steward.enable_forgetting_algorithms": "forgetting_algorithms",
            "memory_steward.enable_priority_elevation": "priority_elevation",
        }

    async def get_consolidation_flags(
        self,
        hippocampus_activity: float = 0.0,
        cognitive_load: float = 0.0,
        consolidation_queue_depth: int = 0,
    ) -> Dict[str, bool]:
        """Get memory consolidation flags based on hippocampal state."""

        # Update metrics
        self.current_metrics.hippocampus_activity = hippocampus_activity
        self.current_metrics.cognitive_load = cognitive_load
        self.current_metrics.consolidation_queue_depth = consolidation_queue_depth

        # Calculate memory pressure based on queue and activity
        memory_pressure = min(
            1.0, (consolidation_queue_depth / 100.0) + (hippocampus_activity * 0.5)
        )

        flags = await self.cognitive_manager.get_memory_steward_flags(
            cognitive_load=cognitive_load,
            hippocampus_activity=hippocampus_activity,
            consolidation_pressure=memory_pressure,
            memory_pressure=memory_pressure,
        )

        # Filter to consolidation-related flags
        consolidation_flags = {
            "hippocampus_integration": flags.get(
                "memory_steward.enable_hippocampus_integration", False
            ),
            "auto_consolidation": flags.get(
                "memory_steward.enable_auto_consolidation", False
            ),
            "predictive_prefetch": flags.get(
                "memory_steward.enable_predictive_prefetch", False
            ),
        }

        return consolidation_flags

    async def get_management_flags(
        self,
        cognitive_load: float = 0.0,
        memory_pressure: float = 0.0,
        priority_pressure: float = 0.0,
    ) -> Dict[str, bool]:
        """Get memory management flags based on system state."""

        # Update metrics
        self.current_metrics.cognitive_load = cognitive_load
        self.current_metrics.memory_pressure = memory_pressure

        flags = await self.cognitive_manager.get_memory_steward_flags(
            cognitive_load=cognitive_load,
            hippocampus_activity=self.current_metrics.hippocampus_activity,
            memory_pressure=memory_pressure,
        )

        # Filter to management-related flags
        management_flags = {
            "forgetting_algorithms": flags.get(
                "memory_steward.enable_forgetting_algorithms", False
            ),
            "priority_elevation": flags.get(
                "memory_steward.enable_priority_elevation", False
            ),
        }

        return management_flags

    async def get_consolidation_strategy(
        self,
        cognitive_load: float,
        hippocampus_activity: float,
        memory_importance: float,
        urgency: float = 0.0,
    ) -> Dict[str, Any]:
        """Get appropriate memory consolidation strategy."""

        consolidation_flags = await self.get_consolidation_flags(
            hippocampus_activity=hippocampus_activity,
            cognitive_load=cognitive_load,
            consolidation_queue_depth=self.current_metrics.consolidation_queue_depth,
        )

        hippocampus_enabled = consolidation_flags.get("hippocampus_integration", False)
        auto_consolidation = consolidation_flags.get("auto_consolidation", False)

        if not hippocampus_enabled:
            return {
                "strategy": ConsolidationStrategy.NONE.value,
                "delay_ms": 0,
                "priority": "normal",
                "reason": "Hippocampus integration disabled",
            }

        # Determine strategy based on cognitive state and memory importance
        if urgency > 0.8 or memory_importance > 0.9:
            # Critical memories - immediate consolidation
            strategy = ConsolidationStrategy.IMMEDIATE
            delay_ms = 0
            priority = "high"
            reason = "Critical memory - immediate consolidation"

        elif cognitive_load > 0.8:
            # High cognitive load - defer consolidation
            if auto_consolidation:
                strategy = ConsolidationStrategy.DELAYED
                delay_ms = 5000  # 5 second delay
                priority = "low"
                reason = "High cognitive load - delayed consolidation"
            else:
                strategy = ConsolidationStrategy.NONE
                delay_ms = 0
                priority = "normal"
                reason = "High cognitive load - consolidation disabled"

        elif hippocampus_activity > 0.7:
            # High hippocampus activity - adaptive strategy
            strategy = ConsolidationStrategy.ADAPTIVE
            delay_ms = int(
                (1.0 - memory_importance) * 2000
            )  # 0-2 second adaptive delay
            priority = "normal" if memory_importance > 0.5 else "low"
            reason = f"Adaptive consolidation for hippocampus activity {hippocampus_activity:.2f}"

        else:
            # Normal conditions - standard consolidation
            if auto_consolidation:
                strategy = ConsolidationStrategy.DELAYED
                delay_ms = 1000  # 1 second standard delay
                priority = "normal"
                reason = "Standard delayed consolidation"
            else:
                strategy = ConsolidationStrategy.IMMEDIATE
                delay_ms = 0
                priority = "normal"
                reason = "Manual immediate consolidation"

        return {
            "strategy": strategy.value,
            "delay_ms": delay_ms,
            "priority": priority,
            "memory_importance": memory_importance,
            "hippocampus_activity": hippocampus_activity,
            "cognitive_load": cognitive_load,
            "reason": reason,
        }

    async def get_forgetting_strategy(
        self,
        cognitive_load: float,
        memory_pressure: float,
        total_memories: int,
        target_reduction: float = 0.1,
    ) -> Dict[str, Any]:
        """Get appropriate forgetting strategy to reduce memory pressure."""

        management_flags = await self.get_management_flags(
            cognitive_load=cognitive_load, memory_pressure=memory_pressure
        )

        forgetting_enabled = management_flags.get("forgetting_algorithms", False)

        if not forgetting_enabled or memory_pressure < 0.7:
            return {
                "strategy": ForgettingStrategy.NONE.value,
                "target_count": 0,
                "aggressiveness": 0.0,
                "reason": "Forgetting disabled or memory pressure acceptable",
            }

        # Calculate target memories to forget
        target_count = int(total_memories * target_reduction)

        # Determine strategy based on pressure and cognitive load
        if memory_pressure > 0.9 and cognitive_load > 0.8:
            # Critical pressure - aggressive forgetting
            strategy = ForgettingStrategy.PRIORITY_BASED
            aggressiveness = 0.9
            target_count = int(target_count * 1.5)  # Forget more
            reason = "Critical memory pressure - priority-based forgetting"

        elif memory_pressure > 0.85:
            # High pressure - usage-based forgetting
            strategy = ForgettingStrategy.USAGE_BASED
            aggressiveness = 0.7
            reason = "High memory pressure - usage-based forgetting"

        elif cognitive_load > 0.7:
            # High cognitive load - exponential decay
            strategy = ForgettingStrategy.EXPONENTIAL_DECAY
            aggressiveness = 0.5
            reason = "High cognitive load - exponential decay forgetting"

        else:
            # Moderate pressure - interference-based
            strategy = ForgettingStrategy.INTERFERENCE
            aggressiveness = 0.3
            target_count = int(target_count * 0.5)  # Conservative
            reason = "Moderate pressure - interference-based forgetting"

        return {
            "strategy": strategy.value,
            "target_count": target_count,
            "aggressiveness": aggressiveness,
            "memory_pressure": memory_pressure,
            "cognitive_load": cognitive_load,
            "reason": reason,
        }

    async def get_prefetch_configuration(
        self,
        cognitive_load: float,
        recall_patterns: Dict[str, float],
        available_bandwidth: float,
    ) -> Dict[str, Any]:
        """Get predictive memory prefetch configuration."""

        consolidation_flags = await self.get_consolidation_flags(
            hippocampus_activity=self.current_metrics.hippocampus_activity,
            cognitive_load=cognitive_load,
        )

        prefetch_enabled = consolidation_flags.get("predictive_prefetch", False)

        if not prefetch_enabled or available_bandwidth < 0.3:
            return {
                "enabled": False,
                "prefetch_depth": 0,
                "confidence_threshold": 1.0,
                "reason": "Prefetch disabled or insufficient bandwidth",
            }

        # Configure prefetch based on cognitive load and bandwidth
        if cognitive_load < 0.3 and available_bandwidth > 0.8:
            # Low load, high bandwidth - aggressive prefetching
            prefetch_depth = 10
            confidence_threshold = 0.3
            batch_size = 5
            reason = "Aggressive prefetch - low load, high bandwidth"

        elif cognitive_load < 0.6 and available_bandwidth > 0.5:
            # Medium load - moderate prefetching
            prefetch_depth = 5
            confidence_threshold = 0.5
            batch_size = 3
            reason = "Moderate prefetch - medium load"

        else:
            # High load or low bandwidth - conservative prefetching
            prefetch_depth = 2
            confidence_threshold = 0.8
            batch_size = 1
            reason = "Conservative prefetch - high load or low bandwidth"

        # Filter patterns by confidence threshold
        high_confidence_patterns = {
            pattern: confidence
            for pattern, confidence in recall_patterns.items()
            if confidence >= confidence_threshold
        }

        return {
            "enabled": True,
            "prefetch_depth": prefetch_depth,
            "confidence_threshold": confidence_threshold,
            "batch_size": batch_size,
            "high_confidence_patterns": high_confidence_patterns,
            "available_bandwidth": available_bandwidth,
            "cognitive_load": cognitive_load,
            "reason": reason,
        }

    async def get_priority_elevation_strategy(
        self,
        cognitive_load: float,
        memory_access_frequency: Dict[str, int],
        importance_scores: Dict[str, float],
    ) -> Dict[str, Any]:
        """Get priority elevation strategy for memory management."""

        management_flags = await self.get_management_flags(
            cognitive_load=cognitive_load,
            memory_pressure=self.current_metrics.memory_pressure,
        )

        elevation_enabled = management_flags.get("priority_elevation", False)

        if not elevation_enabled:
            return {
                "enabled": False,
                "elevation_rate": 0.0,
                "criteria": {},
                "reason": "Priority elevation disabled",
            }

        # Configure elevation based on cognitive load
        if cognitive_load > 0.8:
            # High load - conservative elevation
            elevation_rate = 0.1  # 10% of eligible memories
            access_threshold = 10  # High access requirement
            importance_threshold = 0.8  # High importance requirement
            reason = "Conservative elevation - high cognitive load"

        elif cognitive_load > 0.5:
            # Medium load - balanced elevation
            elevation_rate = 0.2  # 20% of eligible memories
            access_threshold = 5  # Medium access requirement
            importance_threshold = 0.6  # Medium importance requirement
            reason = "Balanced elevation - medium cognitive load"

        else:
            # Low load - aggressive elevation
            elevation_rate = 0.3  # 30% of eligible memories
            access_threshold = 3  # Low access requirement
            importance_threshold = 0.4  # Low importance requirement
            reason = "Aggressive elevation - low cognitive load"

        # Identify memories eligible for elevation
        eligible_memories = []
        for memory_id in memory_access_frequency:
            access_count = memory_access_frequency.get(memory_id, 0)
            importance = importance_scores.get(memory_id, 0.0)

            if access_count >= access_threshold and importance >= importance_threshold:
                eligible_memories.append(
                    {
                        "memory_id": memory_id,
                        "access_count": access_count,
                        "importance": importance,
                        "elevation_score": access_count * importance,
                    }
                )

        # Sort by elevation score and select top candidates
        eligible_memories.sort(key=lambda x: x["elevation_score"], reverse=True)
        target_count = int(len(eligible_memories) * elevation_rate)
        elevation_candidates = eligible_memories[:target_count]

        return {
            "enabled": True,
            "elevation_rate": elevation_rate,
            "criteria": {
                "access_threshold": access_threshold,
                "importance_threshold": importance_threshold,
            },
            "eligible_count": len(eligible_memories),
            "target_count": target_count,
            "elevation_candidates": elevation_candidates,
            "cognitive_load": cognitive_load,
            "reason": reason,
        }

    def update_metrics(self, metrics: MemoryStewardMetrics) -> None:
        """Update current memory steward metrics."""
        self.current_metrics = metrics

    def get_current_metrics(self) -> MemoryStewardMetrics:
        """Get current memory steward metrics."""
        return self.current_metrics

    async def get_adaptive_configuration(self) -> Dict[str, Any]:
        """Get complete adaptive configuration for memory steward."""

        # Get all memory steward flags
        flags = await self.cognitive_manager.get_memory_steward_flags(
            cognitive_load=self.current_metrics.cognitive_load,
            hippocampus_activity=self.current_metrics.hippocampus_activity,
            memory_pressure=self.current_metrics.memory_pressure,
        )

        # Get specific configurations
        consolidation_strategy = await self.get_consolidation_strategy(
            cognitive_load=self.current_metrics.cognitive_load,
            hippocampus_activity=self.current_metrics.hippocampus_activity,
            memory_importance=0.5,  # Default importance
        )

        forgetting_strategy = await self.get_forgetting_strategy(
            cognitive_load=self.current_metrics.cognitive_load,
            memory_pressure=self.current_metrics.memory_pressure,
            total_memories=self.current_metrics.total_memories,
        )

        return {
            "flags": flags,
            "configurations": {
                "consolidation": consolidation_strategy,
                "forgetting": forgetting_strategy,
                "memory_thresholds": {
                    "consolidation_queue_limit": 100,
                    "memory_pressure_threshold": 0.8,
                    "hippocampus_activity_threshold": 0.7,
                },
            },
            "metrics": self.current_metrics,
            "adaptive_rules": {
                "description": "Memory steward adaptive configuration",
                "cognitive_load_threshold": 0.8,
                "memory_pressure_threshold": 0.8,
                "optimization_target": "memory_efficiency",
            },
        }

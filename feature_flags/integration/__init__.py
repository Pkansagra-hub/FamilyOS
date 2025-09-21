"""
Cognitive Integration Module
============================

Integration adapters for MemoryOS cognitive components.
Provides specialized feature flag management for brain-inspired systems.
"""

from .attention_gate import (
    AttentionGateFlagAdapter,
    AttentionGateMetrics,
    AttentionState,
)
from .cognitive_events import (
    CognitiveEventsFlagAdapter,
    CognitiveEventsMetrics,
    EventPriority,
    RoutingStrategy,
)
from .context_bundle import (
    BundleSizingStrategy,
    ContextBundleFlagAdapter,
    ContextBundleMetrics,
    DiversificationStrategy,
)
from .memory_steward import (
    ConsolidationStrategy,
    ForgettingStrategy,
    MemoryStewardFlagAdapter,
    MemoryStewardMetrics,
)
from .working_memory import WorkingMemoryFlagAdapter, WorkingMemoryMetrics

__all__ = [
    # Working Memory
    "WorkingMemoryFlagAdapter",
    "WorkingMemoryMetrics",
    # Attention Gate
    "AttentionGateFlagAdapter",
    "AttentionGateMetrics",
    "AttentionState",
    # Memory Steward
    "MemoryStewardFlagAdapter",
    "MemoryStewardMetrics",
    "ConsolidationStrategy",
    "ForgettingStrategy",
    # Context Bundle
    "ContextBundleFlagAdapter",
    "ContextBundleMetrics",
    "DiversificationStrategy",
    "BundleSizingStrategy",
    # Cognitive Events
    "CognitiveEventsFlagAdapter",
    "CognitiveEventsMetrics",
    "RoutingStrategy",
    "EventPriority",
]

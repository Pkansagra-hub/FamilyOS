"""
MemoryOS Feature Flag System
============================

Brain-inspired feature flag system with cognitive awareness.
Provides adaptive flag evaluation based on cognitive load and neural pathway routing.
"""

from .brain_inspired import (
    # Adaptive Learning Engine
    AdaptiveLearningEngine,
    BrainRegion,
    CognitiveContextType,
    CognitiveTrace,
    # Cognitive Trace Enricher
    CognitiveTraceEnricher,
    CorrelationResult,
    CorrelationType,
    LearningAlgorithm,
    LearningParameters,
    NeuralEvent,
    NeuralPathway,
    # Neural Pathway Correlator
    NeuralPathwayCorrelator,
    OptimizationTarget,
    PerformanceMetrics,
    TraceDetailLevel,
    TraceEnrichmentConfig,
    # Brain-inspired utilities
    create_brain_inspired_suite,
    get_brain_inspired_capabilities,
    initialize_brain_inspired_features,
)
from .core import (
    DEFAULT_COGNITIVE_FLAGS,
    # Configuration
    CognitiveContext,
    ConfigLoader,
    Environment,
    # Evaluation
    EvaluationContext,
    EvaluationResult,
    # Management
    FeatureFlagManager,
    FlagConfig,
    FlagDefinition,
    FlagEvaluator,
    FlagType,
    create_context,
    get_flag_value,
    get_global_manager,
    initialize_global_manager,
    is_enabled,
)
from .flag_manager import (
    CognitiveFlagContext,
    CognitiveFlagManager,
    get_attention_gate_flags,
    get_cognitive_events_flags,
    get_cognitive_manager,
    get_context_bundle_flags,
    get_memory_steward_flags,
    get_working_memory_flags,
    initialize_cognitive_manager,
)
from .integration import (
    # Attention Gate
    AttentionGateFlagAdapter,
    AttentionGateMetrics,
    AttentionState,
    BundleSizingStrategy,
    # Cognitive Events
    CognitiveEventsFlagAdapter,
    CognitiveEventsMetrics,
    ConsolidationStrategy,
    # Context Bundle
    ContextBundleFlagAdapter,
    ContextBundleMetrics,
    DiversificationStrategy,
    EventPriority,
    ForgettingStrategy,
    # Memory Steward
    MemoryStewardFlagAdapter,
    MemoryStewardMetrics,
    RoutingStrategy,
    # Working Memory
    WorkingMemoryFlagAdapter,
    WorkingMemoryMetrics,
)

__version__ = "1.0.0"
__author__ = "MemoryOS Team"
__license__ = "Proprietary"

__all__ = [
    # Core system
    "CognitiveContext",
    "ConfigLoader",
    "Environment",
    "FlagConfig",
    "FlagDefinition",
    "FlagType",
    "DEFAULT_COGNITIVE_FLAGS",
    "EvaluationContext",
    "EvaluationResult",
    "FlagEvaluator",
    "FeatureFlagManager",
    "initialize_global_manager",
    "get_global_manager",
    "is_enabled",
    "get_flag_value",
    "create_context",
    # Cognitive management
    "CognitiveFlagManager",
    "CognitiveFlagContext",
    "initialize_cognitive_manager",
    "get_cognitive_manager",
    "get_working_memory_flags",
    "get_attention_gate_flags",
    "get_memory_steward_flags",
    "get_context_bundle_flags",
    "get_cognitive_events_flags",
    # Integration adapters
    "WorkingMemoryFlagAdapter",
    "WorkingMemoryMetrics",
    "AttentionGateFlagAdapter",
    "AttentionGateMetrics",
    "AttentionState",
    "MemoryStewardFlagAdapter",
    "MemoryStewardMetrics",
    "ConsolidationStrategy",
    "ForgettingStrategy",
    "ContextBundleFlagAdapter",
    "ContextBundleMetrics",
    "DiversificationStrategy",
    "BundleSizingStrategy",
    "CognitiveEventsFlagAdapter",
    "CognitiveEventsMetrics",
    "RoutingStrategy",
    "EventPriority",
    # Brain-inspired features
    "NeuralPathwayCorrelator",
    "CorrelationType",
    "NeuralPathway",
    "BrainRegion",
    "NeuralEvent",
    "CorrelationResult",
    "CognitiveTraceEnricher",
    "TraceDetailLevel",
    "CognitiveContextType",
    "CognitiveTrace",
    "TraceEnrichmentConfig",
    "AdaptiveLearningEngine",
    "LearningAlgorithm",
    "OptimizationTarget",
    "LearningParameters",
    "PerformanceMetrics",
    "create_brain_inspired_suite",
    "initialize_brain_inspired_features",
    "get_brain_inspired_capabilities",
]

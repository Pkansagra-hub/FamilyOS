"""
Brain-Inspired Feature Flag Module
===================================

Advanced brain-inspired cognitive features for MemoryOS feature flag system.
Provides neural pathway correlation, cognitive trace enrichment, and adaptive
learning capabilities based on neuroscience research.

Components:
-----------
1. Neural Pathway Correlator: Analyzes correlations across multiple dimensions
2. Cognitive Trace Enricher: Enriches traces with brain-region context
3. Adaptive Learning Engine: Neural network-inspired optimization algorithms

Key Features:
-------------
- 5 types of correlation analysis (temporal, spatial, causal, semantic, functional)
- 8 major brain region mappings with hemisphere activity tracking
- Hebbian learning, reinforcement learning, and genetic optimization
- Neural plasticity adaptation based on cognitive context
- Experience replay and homeostatic scaling
- Real-time cognitive load adaptation

Usage:
------
```python
from feature_flags.brain_inspired import (
    NeuralPathwayCorrelator,
    CognitiveTraceEnricher,
    AdaptiveLearningEngine
)

# Initialize brain-inspired components
correlator = NeuralPathwayCorrelator(cognitive_manager)
enricher = CognitiveTraceEnricher(cognitive_manager, correlator)
learner = AdaptiveLearningEngine(cognitive_manager)

# Analyze neural pathways
correlations = await correlator.analyze_pathway_correlations(events)

# Enrich cognitive traces
enriched_trace = await enricher.enrich_trace(trace, events)

# Optimize thresholds with adaptive learning
optimization_result = await learner.optimize_cognitive_thresholds()
```

Architecture:
-------------
This module integrates with the main cognitive flag manager to provide
brain-inspired intelligence for feature flag optimization. The components
work together to:

1. Analyze neural pathway patterns in cognitive events
2. Correlate cognitive traces with brain region activity
3. Adapt system parameters based on performance patterns
4. Optimize cognitive load thresholds using neural algorithms

The module is designed to be modular and can be enabled/disabled based on
cognitive load and system configuration.
"""

from .adaptive_learning import (
    # Main learning engine
    AdaptiveLearningEngine,
    # Enums for learning
    LearningAlgorithm,
    # Data structures
    LearningParameters,
    LearningState,
    OptimizationTarget,
    PerformanceMetrics,
)
from .cognitive_trace import (
    CognitiveContextType,
    # Data structures
    CognitiveTrace,
    # Main enricher class
    CognitiveTraceEnricher,
    # Enums for trace analysis
    TraceDetailLevel,
    TraceEnrichmentConfig,
)
from .neural_correlator import (
    BrainRegion,
    CorrelationResult,
    # Enums for neural analysis
    CorrelationType,
    # Data structures
    NeuralEvent,
    NeuralPathway,
    # Main correlator class
    NeuralPathwayCorrelator,
)

# Export all components for easy access
__all__ = [
    # Neural Pathway Correlator
    "NeuralPathwayCorrelator",
    "CorrelationType",
    "NeuralPathway",
    "BrainRegion",
    "NeuralEvent",
    "CorrelationResult",
    # Cognitive Trace Enricher
    "CognitiveTraceEnricher",
    "TraceDetailLevel",
    "CognitiveContextType",
    "CognitiveTrace",
    "TraceEnrichmentConfig",
    # Adaptive Learning Engine
    "AdaptiveLearningEngine",
    "LearningAlgorithm",
    "OptimizationTarget",
    "LearningParameters",
    "PerformanceMetrics",
    "LearningState",
]

# Module configuration
BRAIN_INSPIRED_VERSION = "1.0.0"
SUPPORTED_CORRELATIONS = 5
SUPPORTED_BRAIN_REGIONS = 8
SUPPORTED_LEARNING_ALGORITHMS = 5

# Default configurations
DEFAULT_CORRELATION_CONFIG = {
    "temporal_threshold": 0.7,
    "spatial_threshold": 0.6,
    "causal_threshold": 0.8,
    "semantic_threshold": 0.75,
    "functional_threshold": 0.65,
    "min_correlation_strength": 0.5,
    "max_correlation_distance": 1000.0,
    "enable_cross_hemisphere": True,
    "enable_pathway_efficiency": True,
}

DEFAULT_ENRICHMENT_CONFIG = {
    "detail_level": "COMPREHENSIVE",
    "max_trace_depth": 10,
    "correlation_threshold": 0.6,
    "brain_region_mapping": True,
    "neural_pathway_analysis": True,
    "cognitive_load_adaptation": True,
    "enable_cross_correlation": True,
}

DEFAULT_LEARNING_CONFIG = {
    "learning_rate": 0.01,
    "exploration_rate": 0.1,
    "decay_rate": 0.95,
    "memory_size": 1000,
    "convergence_threshold": 0.001,
    "enable_hebbian_learning": True,
    "enable_reinforcement_learning": True,
    "enable_genetic_optimization": False,  # Disabled by default due to computational cost
    "enable_neural_plasticity": True,
}


def create_brain_inspired_suite(cognitive_manager):
    """
    Create a complete brain-inspired feature flag suite.

    Args:
        cognitive_manager: The main cognitive flag manager instance

    Returns:
        Dictionary containing all brain-inspired components
    """

    # Create neural pathway correlator
    correlator = NeuralPathwayCorrelator(cognitive_manager)

    # Create cognitive trace enricher
    enricher = CognitiveTraceEnricher(cognitive_manager)

    # Create adaptive learning engine
    learner = AdaptiveLearningEngine(cognitive_manager)

    return {
        "neural_correlator": correlator,
        "cognitive_enricher": enricher,
        "adaptive_learner": learner,
        "version": BRAIN_INSPIRED_VERSION,
        "capabilities": {
            "correlation_types": SUPPORTED_CORRELATIONS,
            "brain_regions": SUPPORTED_BRAIN_REGIONS,
            "learning_algorithms": SUPPORTED_LEARNING_ALGORITHMS,
        },
    }


async def initialize_brain_inspired_features(
    cognitive_manager,
    enable_real_time: bool = True,
    enable_learning: bool = True,
    enable_enrichment: bool = True,
):
    """
    Initialize brain-inspired features with optional component selection.

    Args:
        cognitive_manager: The main cognitive flag manager
        enable_real_time: Enable real-time correlation analysis
        enable_learning: Enable adaptive learning
        enable_enrichment: Enable cognitive trace enrichment

    Returns:
        Initialized brain-inspired suite with enabled components
    """

    suite = create_brain_inspired_suite(cognitive_manager)

    # Configure components based on flags
    if not enable_real_time:
        # Disable real-time analysis (if the component supports it)
        pass

    if not enable_learning:
        suite["adaptive_learner"].learning_params.learning_rate = 0.0

    if not enable_enrichment:
        # Disable enrichment (if the component supports it)
        pass

    return suite


def get_brain_inspired_capabilities():
    """Get information about brain-inspired capabilities."""

    return {
        "version": BRAIN_INSPIRED_VERSION,
        "correlation_types": [t.value for t in CorrelationType],
        "neural_pathways": [p.value for p in NeuralPathway],
        "brain_regions": [r.value for r in BrainRegion],
        "learning_algorithms": [a.value for a in LearningAlgorithm],
        "optimization_targets": [t.value for t in OptimizationTarget],
        "trace_detail_levels": [level.value for level in TraceDetailLevel],
        "cognitive_context_types": [c.value for c in CognitiveContextType],
        "default_configs": {
            "correlation": DEFAULT_CORRELATION_CONFIG,
            "enrichment": DEFAULT_ENRICHMENT_CONFIG,
            "learning": DEFAULT_LEARNING_CONFIG,
        },
    }


def validate_brain_inspired_config(config):
    """
    Validate brain-inspired configuration.

    Args:
        config: Configuration dictionary to validate

    Returns:
        Tuple of (is_valid, error_messages)
    """

    errors = []

    # Validate correlation config
    if "correlation" in config:
        corr_config = config["correlation"]

        # Check threshold ranges
        for threshold_key in [
            "temporal_threshold",
            "spatial_threshold",
            "causal_threshold",
        ]:
            if threshold_key in corr_config:
                value = corr_config[threshold_key]
                if not (0.0 <= value <= 1.0):
                    errors.append(
                        f"Correlation {threshold_key} must be between 0.0 and 1.0, got {value}"
                    )

    # Validate learning config
    if "learning" in config:
        learning_config = config["learning"]

        # Check learning rate
        if "learning_rate" in learning_config:
            lr = learning_config["learning_rate"]
            if not (0.0 <= lr <= 1.0):
                errors.append(f"Learning rate must be between 0.0 and 1.0, got {lr}")

        # Check memory size
        if "memory_size" in learning_config:
            mem_size = learning_config["memory_size"]
            if mem_size < 10:
                errors.append(f"Memory size must be at least 10, got {mem_size}")

    # Validate enrichment config
    if "enrichment" in config:
        enrich_config = config["enrichment"]

        # Check max trace depth
        if "max_trace_depth" in enrich_config:
            depth = enrich_config["max_trace_depth"]
            if depth < 1 or depth > 100:
                errors.append(f"Max trace depth must be between 1 and 100, got {depth}")

    return len(errors) == 0, errors


# Module metadata
__version__ = BRAIN_INSPIRED_VERSION
__author__ = "MemoryOS Brain-Inspired Team"
__description__ = (
    "Advanced brain-inspired cognitive features for feature flag optimization"
)
__license__ = "MIT"

# Configuration constants
MIN_COGNITIVE_LOAD_FOR_BRAIN_FEATURES = 0.3  # Don't enable under low cognitive load
MAX_COGNITIVE_LOAD_FOR_LEARNING = 0.8  # Disable learning under high cognitive load
BRAIN_REGION_CORRELATION_THRESHOLD = 0.6  # Minimum correlation for brain region mapping
NEURAL_PATHWAY_EFFICIENCY_THRESHOLD = 0.7  # Minimum efficiency for pathway optimization

# Performance constants
MAX_CORRELATION_BATCH_SIZE = 1000  # Maximum events to correlate at once
MAX_ENRICHMENT_BATCH_SIZE = 500  # Maximum traces to enrich at once
MAX_LEARNING_ITERATIONS = 100  # Maximum learning iterations per cycle
CORRELATION_CACHE_TTL_SECONDS = 300  # Cache correlation results for 5 minutes

# Debug and monitoring flags
ENABLE_BRAIN_INSPIRED_METRICS = True
ENABLE_CORRELATION_CACHING = True
ENABLE_LEARNING_PERSISTENCE = True
ENABLE_TRACE_ENRICHMENT_CACHE = True

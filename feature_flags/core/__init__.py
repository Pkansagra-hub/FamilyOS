"""
Feature Flag Core Module
========================

Core components for the MemoryOS feature flag system.
Provides configuration, evaluation, and management capabilities
with brain-inspired cognitive awareness.
"""

from .config import (
    DEFAULT_COGNITIVE_FLAGS,
    CognitiveContext,
    ConfigLoader,
    Environment,
    FlagConfig,
    FlagDefinition,
    FlagType,
)
from .evaluator import EvaluationContext, EvaluationResult, FlagEvaluator
from .manager import (
    FeatureFlagManager,
    create_context,
    get_flag_value,
    get_global_manager,
    initialize_global_manager,
    is_enabled,
)

__all__ = [
    # Configuration
    "CognitiveContext",
    "ConfigLoader",
    "Environment",
    "FlagConfig",
    "FlagDefinition",
    "FlagType",
    "DEFAULT_COGNITIVE_FLAGS",
    # Evaluation
    "EvaluationContext",
    "EvaluationResult",
    "FlagEvaluator",
    # Management
    "FeatureFlagManager",
    "initialize_global_manager",
    "get_global_manager",
    "is_enabled",
    "get_flag_value",
    "create_context",
]

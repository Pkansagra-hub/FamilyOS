"""
Enhanced ABAC Package for MemoryOS
Issue #27: Complete ABAC implementation

This package provides the enhanced Attribute-Based Access Control (ABAC) system
with contract-driven attribute evaluation, context-aware decisions, and conflict resolution.
"""

# Import from legacy abac.py file for compatibility
try:
    import sys
    from pathlib import Path

    # Add parent directory to path to import abac.py
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))

    from abac import AbacEngine  # Legacy engine

    sys.path.remove(str(parent_dir))

except ImportError:
    # Fallback to EnhancedAttributeEngine if abac.py not available
    from .attribute_engine import EnhancedAttributeEngine as AbacEngine

from .attribute_engine import (
    AttributeCategory,
    AttributeCombinationRule,
    AttributeEvaluationResult,
    BandEscalationReason,
    EnhancedAttributeEngine,
)
from .types import (  # Core types; Protocols
    AbacContext,
    ActorAttrs,
    Band,
    CacheBackend,
    ConflictRecord,
    Decision,
    DecisionOutcome,
    DeviceAttrs,
    EnvAttrs,
    HistoricalContext,
    ObligationsDict,
    ObligationSpec,
    PerformanceMetrics,
    RealtimeContext,
    RequestContext,
    SafetyPipeline,
    TrustLevel,
)

__all__ = [
    # Core types
    "Band",
    "TrustLevel",
    "Decision",
    "ObligationsDict",
    "ActorAttrs",
    "DeviceAttrs",
    "EnvAttrs",
    "AbacContext",
    "RequestContext",
    "HistoricalContext",
    "RealtimeContext",
    "DecisionOutcome",
    "ObligationSpec",
    "PerformanceMetrics",
    "ConflictRecord",
    # Protocols
    "SafetyPipeline",
    "CacheBackend",
    # Enhanced engines
    "AbacEngine",  # Legacy compatibility
    "EnhancedAttributeEngine",
    "AttributeEvaluationResult",
    "AttributeCategory",
    "BandEscalationReason",
    "AttributeCombinationRule",
]

__version__ = "1.0.0"
__author__ = "MemoryOS Team"
__description__ = "Enhanced ABAC implementation for Issue #27"

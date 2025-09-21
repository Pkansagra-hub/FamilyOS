"""
Enhanced ABAC Package for MemoryOS
Issue #27: Complete ABAC implementation

This package provides the enhanced Attribute-Based Access Control (ABAC) system
with contract-driven attribute evaluation, context-aware decisions, and conflict resolution.
"""

from .types import (
    # Core types
    Band,
    TrustLevel, 
    Decision,
    ObligationsDict,
    ActorAttrs,
    DeviceAttrs,
    EnvAttrs,
    AbacContext,
    RequestContext,
    HistoricalContext,
    RealtimeContext,
    DecisionOutcome,
    ObligationSpec,
    PerformanceMetrics,
    ConflictRecord,
    
    # Protocols
    SafetyPipeline,
    CacheBackend,
)

from .attribute_engine import (
    EnhancedAttributeEngine,
    AttributeEvaluationResult,
    AttributeCategory,
    BandEscalationReason,
    AttributeCombinationRule,
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
    "EnhancedAttributeEngine",
    "AttributeEvaluationResult", 
    "AttributeCategory",
    "BandEscalationReason",
    "AttributeCombinationRule",
]

__version__ = "1.0.0"
__author__ = "MemoryOS Team"
__description__ = "Enhanced ABAC implementation for Issue #27"

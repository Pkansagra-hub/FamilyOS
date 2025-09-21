"""
Attention Gate Package - Thalamus-Inspired Smart-Path Admission Control

Future-ready architecture supporting:
- Phase 1: Hardcoded explainable formulas (production-safe)
- Phase 2: Light calibration and A/B testing
- Phase 3: Online learning and weight adaptation
- Phase 4: Neural models with safety guardrails

Core Components:
- gate_service.py: Main admission control logic
- salience.py: Priority scoring with learning hooks
- intent_rules.py: Intent derivation engine
- backpressure.py: Load and circuit breaker management
- policy_bridge.py: ABAC/RBAC integration
- trace.py: Observability and decision tracing
- config/: Configuration system with learning integration
"""

"""
Attention Gate Package - Thalamus-Inspired Smart-Path Admission Control

Future-ready architecture supporting:
- Phase 1: Hardcoded explainable formulas (production-safe)
- Phase 2: Light calibration and A/B testing
- Phase 3: Online learning and weight adaptation
- Phase 4: Neural models with safety guardrails

Core Components:
- gate_service.py: Main admission control logic
- salience.py: Priority scoring with learning hooks
- intent_rules.py: Intent derivation engine
- backpressure.py: Load and circuit breaker management
- policy_bridge.py: ABAC/RBAC integration
- trace.py: Observability and decision tracing
- config/: Configuration system with learning integration
"""

from .config import AttentionGateConfig, get_config

# Core imports
from .gate_service import AttentionGate, create_attention_gate
from .salience import SalienceCalculator

# Type imports
from .types import (
    DerivedIntent,
    GateAction,
    GateDecision,
    GateDecisionTrace,
    GateRequest,
    GateResponse,
    IntentConfidence,
    IntentType,
    SalienceFeatures,
    SalienceWeights,
)

__version__ = "1.0.0"
__all__ = [
    # Main service
    "AttentionGate",
    "create_attention_gate",
    # Core components
    "SalienceCalculator",
    # Request/Response types
    "GateRequest",
    "GateResponse",
    "GateDecision",
    "GateAction",
    # Intent types
    "DerivedIntent",
    "IntentType",
    "IntentConfidence",
    # Salience types
    "SalienceFeatures",
    "SalienceWeights",
    # Tracing
    "GateDecisionTrace",
    # Configuration
    "get_config",
    "AttentionGateConfig",
]

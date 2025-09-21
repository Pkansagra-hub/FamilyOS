"""
Family AI – Policy Layer (v0.9.4)

This package provides a stable, minimal-dependency policy engine for
roles, attributes, sharing rules, redaction, consent, and tombstones.
"""

from .abac import (
    AbacContext,
    AbacEngine,  # Legacy engine from abac.py
    ActorAttrs,
    DeviceAttrs,
    EnhancedAttributeEngine,  # Available engine from ABAC
    EnvAttrs,
)
from .audit import AuditLogger
from .config_loader import PolicyConfig, load_policy_config, resolve_band_for_space
from .consent import ConsentRecord, ConsentStore
from .decision import Decision, Obligation, PolicyDecision
from .decision_engine import DecisionContext, PolicyDecisionEngine, PolicyRequest
from .errors import ConsentError, PolicyError, RBACError, StorageError
from .rbac import Binding, RbacEngine, RoleDef
from .redactor import RedactionResult, Redactor
from .security_bridge import SecurityContextBridge
from .service import PolicyService
from .space_policy import Band, ShareOp, ShareRequest, SpacePolicy
from .tombstones import Tombstone, TombstoneStore

__all__ = [
    "PolicyDecision",
    "Obligation",
    "Decision",
    "RbacEngine",
    "RoleDef",
    "Binding",
    "EnhancedAttributeEngine",
    "AbacContext",
    "ActorAttrs",
    "DeviceAttrs",
    "EnvAttrs",
    "SpacePolicy",
    "Band",
    "ShareOp",
    "ShareRequest",
    "ConsentStore",
    "ConsentRecord",
    "Redactor",
    "RedactionResult",
    "TombstoneStore",
    "Tombstone",
    "AuditLogger",
    "PolicyService",
    "PolicyDecisionEngine",
    "PolicyRequest",
    "DecisionContext",
    "SecurityContextBridge",
    "PolicyConfig",
    "load_policy_config",
    "resolve_band_for_space",
    "PolicyError",
    "RBACError",
    "ConsentError",
    "StorageError",
]
__version__ = "0.9.4"

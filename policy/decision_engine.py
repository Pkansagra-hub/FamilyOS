"""
Basic Policy Decision Logic - Sub-issue #7.3

This module implements simplified policy decision logic that orchestrates
RBAC, ABAC, and SpacePolicy engines to provide easy-to-use decision methods
with conflict resolution and default behaviors.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .abac import AbacContext
from .abac import EnhancedAttributeEngine as AbacEngine
from .consent import ConsentStore
from .decision import Obligation, PolicyDecision
from .rbac import RbacEngine
from .space_policy import ShareRequest, SpacePolicy

logger = logging.getLogger(__name__)


@dataclass
class PolicyRequest:
    """Simplified request for basic policy decisions."""

    actor_id: str
    operation: str
    resource: str
    space_id: str
    context: Optional[AbacContext] = None
    band: str = "GREEN"
    tags: Optional[List[str]] = None


@dataclass
class DecisionContext:
    """Context information for policy decisions."""

    rbac_result: bool
    rbac_caps: List[str]
    abac_decision: str
    abac_obligations: Dict[str, Any]
    space_decision: Optional[PolicyDecision] = None
    conflicts: Optional[List[str]] = None


class PolicyDecisionEngine:
    """
    Basic Policy Decision Logic Engine

    Provides simplified methods for common authorization patterns:
    - Basic allow/deny decisions
    - Conflict resolution between policy engines
    - Default fallback behaviors
    - Decision aggregation logic
    """

    def __init__(
        self,
        rbac: RbacEngine,
        abac: AbacEngine,
        space_policy: SpacePolicy,
        consent: ConsentStore,
    ):
        self.rbac = rbac
        self.abac = abac
        self.space_policy = space_policy
        self.consent = consent

        # Default policy behaviors
        self.default_band = "GREEN"
        self.default_decision = "DENY"
        self.strict_mode = True  # When True, any engine denial results in DENY

        logger.info("PolicyDecisionEngine initialized")

    @classmethod
    def create_default(cls) -> "PolicyDecisionEngine":
        """
        Create a PolicyDecisionEngine with default sub-engines.

        This is useful for testing and simple use cases where you don't need
        complex engine configurations. Uses temporary files for storage.
        """
        import os
        import tempfile

        # Create temporary directory for engine storage
        temp_dir = tempfile.mkdtemp(prefix="policy_engine_")

        # Import here to avoid circular imports
        from .abac import AbacEngine
        from .consent import ConsentStore
        from .rbac import RbacEngine
        from .space_policy import SpacePolicy

        # Create engines with temporary storage
        rbac_path = os.path.join(temp_dir, "rbac.json")
        consent_path = os.path.join(temp_dir, "consent.json")

        rbac = RbacEngine(rbac_path)
        abac = AbacEngine()  # ABAC doesn't require file storage
        consent = ConsentStore(consent_path)

        # SpacePolicy requires other engines
        space_policy = SpacePolicy(rbac, abac, consent)

        return cls(rbac, abac, space_policy, consent)

    # -------------------------------------------------------------------------
    # Core Basic Decision Methods
    # -------------------------------------------------------------------------

    def can_access(
        self,
        actor_id: str,
        capability: str,
        space_id: str,
        context: Optional[AbacContext] = None,
    ) -> bool:
        """
        Basic access check - simplified boolean result.

        Returns True if actor can perform capability in space.
        Combines RBAC + ABAC with conflict resolution.
        """
        try:
            decision = self.evaluate_access(
                PolicyRequest(
                    actor_id=actor_id,
                    operation=capability,
                    resource=space_id,
                    space_id=space_id,
                    context=context,
                )
            )
            return decision.decision == "ALLOW"
        except Exception as e:
            logger.error(f"Access check failed: {e}")
            return False

    def evaluate_access(self, request: PolicyRequest) -> PolicyDecision:
        """
        Comprehensive access evaluation with full decision context.

        This is the main orchestration method that combines all policy engines
        and applies conflict resolution logic.
        """
        try:
            # Step 1: Gather decisions from all engines
            context = self._gather_decision_context(request)

            # Step 2: Apply conflict resolution
            decision = self._resolve_conflicts(context, request)

            # Step 3: Apply default behaviors if needed
            if not decision:
                decision = self._apply_defaults(context, request)

            # Step 4: Finalize obligations
            decision = self._finalize_obligations(decision, context)

            logger.debug(
                f"Policy decision for {request.actor_id}:{request.operation} = {decision.decision}"
            )
            return decision

        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}")
            return PolicyDecision(
                decision="DENY",
                reasons=[f"evaluation_error: {str(e)}"],
                obligations=Obligation(log_audit=True),
            )

    def check_operation(
        self,
        actor_id: str,
        operation: str,
        from_space: str,
        to_space: Optional[str] = None,
        band: str = "GREEN",
        context: Optional[AbacContext] = None,
    ) -> PolicyDecision:
        """
        Check space operation (REFER, PROJECT, DETACH, UNDO).

        This method handles space-specific operations and automatically
        maps them to the appropriate capabilities and share requests.
        """
        try:
            # Map operation to share request
            share_req = ShareRequest(
                op=operation,  # type: ignore
                actor_id=actor_id,
                from_space=from_space,
                to_space=to_space,
                band=band,  # type: ignore
                tags=[],
            )

            # Use context or create default
            if not context:
                context = self._create_default_context(actor_id)

            # Delegate to space policy
            return self.space_policy.evaluate_share(share_req, context)

        except Exception as e:
            logger.error(f"Operation check failed: {e}")
            return PolicyDecision(
                decision="DENY",
                reasons=[f"operation_error: {str(e)}"],
                obligations=Obligation(log_audit=True),
            )

    # -------------------------------------------------------------------------
    # Conflict Resolution Logic
    # -------------------------------------------------------------------------

    def _gather_decision_context(self, request: PolicyRequest) -> DecisionContext:
        """Gather decisions from all policy engines."""

        # RBAC evaluation
        rbac_result = self.rbac.has_cap(
            request.actor_id, request.space_id, request.operation
        )
        rbac_caps = list(self.rbac.list_caps(request.actor_id, request.space_id))

        # ABAC evaluation
        context = request.context or self._create_default_context(request.actor_id)
        abac_decision, abac_reasons, abac_obligations = self.abac.evaluate(
            request.operation, context
        )

        return DecisionContext(
            rbac_result=rbac_result,
            rbac_caps=rbac_caps,
            abac_decision=abac_decision,
            abac_obligations=abac_obligations,
            conflicts=[],
        )

    def _resolve_conflicts(
        self, context: DecisionContext, request: PolicyRequest
    ) -> Optional[PolicyDecision]:
        """
        Resolve conflicts between policy engines.

        Conflict resolution rules:
        1. If RBAC denies, always DENY (no capability)
        2. If ABAC denies and strict_mode=True, DENY
        3. If ABAC allows with redaction, ALLOW_REDACTED
        4. Otherwise, continue to space policy evaluation
        """
        conflicts = []

        # Rule 1: RBAC denial is final
        if not context.rbac_result:
            return PolicyDecision(
                decision="DENY",
                reasons=[f"rbac_missing_capability: {request.operation}"],
                obligations=Obligation(log_audit=True),
            )

        # Rule 2: ABAC denial in strict mode
        if context.abac_decision == "DENY" and self.strict_mode:
            return PolicyDecision(
                decision="DENY",
                reasons=["abac_denial_strict_mode"],
                obligations=Obligation(log_audit=True),
            )

        # Rule 3: ABAC conflicts
        if context.abac_decision == "DENY" and context.rbac_result:
            conflicts.append("rbac_allows_abac_denies")

        if conflicts:
            context.conflicts = conflicts
        return None  # Continue to space policy

    def _apply_defaults(
        self, context: DecisionContext, request: PolicyRequest
    ) -> PolicyDecision:
        """Apply default policy behaviors."""

        # Default ALLOW if RBAC passes and no conflicts
        if context.rbac_result and not context.conflicts:
            return PolicyDecision(
                decision="ALLOW",
                reasons=["rbac_capability_check", "no_conflicts"],
                effective_caps=[request.operation],
            )

        # Default DENY with conflict information
        reasons = ["default_deny"]
        if context.conflicts:
            reasons.extend(context.conflicts)

        return PolicyDecision(
            decision="DENY", reasons=reasons, obligations=Obligation(log_audit=True)
        )

    def _finalize_obligations(
        self, decision: PolicyDecision, context: DecisionContext
    ) -> PolicyDecision:
        """Merge obligations from all engines."""

        # Start with existing obligations
        final_obligations = decision.obligations

        # Merge ABAC obligations
        if context.abac_obligations:
            if context.abac_obligations.get("redact"):
                final_obligations.redact.extend(context.abac_obligations["redact"])
                # Upgrade to ALLOW_REDACTED if we have redactions
                if decision.decision == "ALLOW":
                    decision.decision = "ALLOW_REDACTED"

            if context.abac_obligations.get("band_min"):
                final_obligations.band_min = context.abac_obligations["band_min"]

            if context.abac_obligations.get("reason_tags"):
                final_obligations.reason_tags.extend(
                    context.abac_obligations["reason_tags"]
                )

        decision.obligations = final_obligations
        return decision

    # -------------------------------------------------------------------------
    # Helper Methods for Common Patterns
    # -------------------------------------------------------------------------

    def can_read(
        self, actor_id: str, space_id: str, context: Optional[AbacContext] = None
    ) -> bool:
        """Check if actor can read from space."""
        return self.can_access(actor_id, "memory.read", space_id, context)

    def can_write(
        self, actor_id: str, space_id: str, context: Optional[AbacContext] = None
    ) -> bool:
        """Check if actor can write to space."""
        return self.can_access(actor_id, "memory.write", space_id, context)

    def can_project(
        self,
        actor_id: str,
        from_space: str,
        to_space: str,
        context: Optional[AbacContext] = None,
    ) -> bool:
        """Check if actor can project from one space to another."""
        decision = self.check_operation(
            actor_id, "PROJECT", from_space, to_space, context=context
        )
        return decision.decision in ("ALLOW", "ALLOW_REDACTED")

    def can_manage_privacy(
        self, actor_id: str, space_id: str, context: Optional[AbacContext] = None
    ) -> bool:
        """Check if actor can manage privacy (delete, undo) in space."""
        return self.can_access(
            actor_id, "privacy.delete", space_id, context
        ) or self.can_access(actor_id, "privacy.undo", space_id, context)

    def requires_consent(
        self, from_space: str, to_space: str, operation: str = "PROJECT"
    ) -> bool:
        """Check if operation between spaces requires consent."""
        # Check if consent is already granted
        return not self.consent.has_consent(from_space, to_space, operation.lower())

    # -------------------------------------------------------------------------
    # Batch Operations
    # -------------------------------------------------------------------------

    def check_multiple_operations(
        self,
        actor_id: str,
        operations: List[Tuple[str, str]],  # [(operation, space_id), ...]
        context: Optional[AbacContext] = None,
    ) -> Dict[str, bool]:
        """Check multiple operations efficiently."""
        results: Dict[str, bool] = {}

        for operation, space_id in operations:
            key = f"{operation}:{space_id}"
            results[key] = self.can_access(actor_id, operation, space_id, context)

        return results

    def get_effective_capabilities(
        self, actor_id: str, space_id: str, context: Optional[AbacContext] = None
    ) -> List[str]:
        """Get list of capabilities actor effectively has in space (after ABAC filtering)."""
        rbac_caps = self.rbac.list_caps(actor_id, space_id)
        effective_caps: List[str] = []

        for cap in rbac_caps:
            if self.can_access(actor_id, cap, space_id, context):
                effective_caps.append(cap)

        return effective_caps

    # -------------------------------------------------------------------------
    # Context Management
    # -------------------------------------------------------------------------

    def _create_default_context(self, actor_id: str) -> AbacContext:
        """Create default ABAC context when none provided."""
        from .abac import ActorAttrs, DeviceAttrs, EnvAttrs

        return AbacContext(
            actor=ActorAttrs(actor_id=actor_id),
            device=DeviceAttrs(device_id="default", trust="trusted"),
            env=EnvAttrs(time_of_day_hours=12.0),
        )

    # -------------------------------------------------------------------------
    # Configuration Methods
    # -------------------------------------------------------------------------

    def set_strict_mode(self, enabled: bool):
        """Enable/disable strict mode for conflict resolution."""
        self.strict_mode = enabled
        logger.info(f"Strict mode {'enabled' if enabled else 'disabled'}")

    def set_default_behavior(self, decision: str):
        """Set default decision when policies are unclear."""
        if decision not in ("ALLOW", "DENY"):
            raise ValueError("Default decision must be ALLOW or DENY")
        self.default_decision = decision
        logger.info(f"Default decision set to {decision}")

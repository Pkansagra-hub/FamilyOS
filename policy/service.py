"""
Family OS Policy Service - PDP/PEP Integration Bridge

This module provides the Policy Decision Point (PDP) bridge that integrates
the policy/ package with all Family OS modules as Policy Enforcement Points (PEPs).

Architecture:
- PDP (Policy Decision Point) = policy/ package (RbacEngine, AbacEngine, SpacePolicy)
- PEP (Policy Enforcement Point) = API, Events, Memory (enforce decisions + obligations)

Integration Points:
1. API Layer - FastAPI middleware for HTTP request authorization
2. Event Bus - Middleware for event publish/subscribe authorization
3. Memory Service - Authorization for memory operations
4. Context Propagation - Actor, device, environment context across layers
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

# Integration imports
from api.schemas import SecurityContext
from events.types import Event

# Policy engine imports
from .abac import AbacContext, AbacEngine, ActorAttrs, DeviceAttrs, EnvAttrs
from .audit import AuditLogger
from .config_loader import PolicyConfig, load_policy_config
from .consent import ConsentStore
from .decision import Obligation, PolicyDecision
from .decision_engine import PolicyDecisionEngine
from .rbac import RbacEngine
from .redactor import Redactor
from .security_bridge import SecurityContextBridge
from .space_policy import Band, ShareRequest, SpacePolicy
from .tombstones import TombstoneStore

logger = logging.getLogger(__name__)


class PolicyService:
    """
    Policy Decision Point (PDP) for Family OS.

    Provides async bridge between policy/ package and enforcement points:
    - API middleware (FastAPI routes)
    - Event bus middleware (publish/subscribe)
    - Memory service operations
    - Context propagation and caching
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        storage_dir: str = "./workspace/policy",
        cache_ttl: int = 120,  # RBAC cache TTL in seconds
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = cache_ttl

        # Load configuration
        if config_path:
            self.config = load_policy_config(config_path)
        else:
            # Default configuration
            self.config = PolicyConfig(
                roles={
                    "admin": [
                        "memory.read",
                        "memory.write",
                        "memory.project",
                        "memory.refer",
                        "memory.detach",
                        "privacy.redact",
                        "privacy.delete",
                        "privacy.undo",
                        "prospective.manage",
                        "tools.run",
                    ],
                    "guardian": [
                        "memory.read",
                        "memory.write",
                        "memory.project",
                        "memory.refer",
                        "memory.detach",
                        "privacy.redact",
                        "privacy.delete",
                        "privacy.undo",
                        "prospective.manage",
                    ],
                    "member": ["memory.read", "memory.write", "prospective.manage"],
                    "viewer": ["memory.read"],
                    "guest": ["memory.read"],
                },
                redaction_categories=[
                    "pii.email",
                    "pii.phone",
                    "pii.cc",
                    "pii.address",
                    "pii.ssn",
                ],
                band_defaults={"shared:household": "GREEN", "interfamily:*": "AMBER"},
                minor_night_curfew_hours=[22, 23, 0, 1, 2, 3, 4, 5],
            )

        # Initialize policy engines
        self.rbac = RbacEngine(str(self.storage_dir / "roles.json"))
        self.consent = ConsentStore(str(self.storage_dir / "consent.json"))
        self.tombstones = TombstoneStore(self.storage_dir / "tombstones.json")
        self.abac = AbacEngine()
        self.space_policy = SpacePolicy(
            self.rbac, self.abac, self.consent, band_defaults=self.config.band_defaults
        )
        self.redactor = Redactor(categories=self.config.redaction_categories)
        self.audit = AuditLogger(str(self.storage_dir / "audit"))

        # Initialize basic decision engine
        self.decision_engine = PolicyDecisionEngine(
            self.rbac, self.abac, self.space_policy, self.consent
        )

        # Initialize security context bridge
        self.security_bridge = SecurityContextBridge(self.rbac)

        # RBAC capability cache (short TTL)
        self._caps_cache: Dict[str, tuple[float, set[str]]] = {}

        logger.info(f"PolicyService initialized with storage: {self.storage_dir}")

    async def initialize_default_roles(self):
        """Initialize default roles and admin user."""
        from policy.rbac import Binding, RoleDef

        # Define roles from config
        for role_name, caps in self.config.roles.items():
            self.rbac.define_role(RoleDef(role_name, caps))

        # Define additional test roles if not already in config
        if "member" not in self.config.roles:
            # Create member role with memory access capabilities for testing
            member_caps = [
                "memory.read",
                "memory.write",
                "memory.project",
                "memory.refer",
            ]
            self.rbac.define_role(RoleDef("member", member_caps))
            logger.info("Created member role with capabilities: %s", member_caps)

        if "admin" not in self.config.roles:
            # Create admin role with all capabilities for testing
            admin_caps = [
                "memory.read",
                "memory.write",
                "memory.project",
                "memory.refer",
                "memory.detach",
                "privacy.redact",
                "privacy.delete",
                "privacy.undo",
                "prospective.manage",
                "system.admin",
            ]
            self.rbac.define_role(RoleDef("admin", admin_caps))
            logger.info("Created admin role with capabilities: %s", admin_caps)

        if "child" not in self.config.roles:
            # Create child role with limited capabilities for family safety
            child_caps = [
                "memory.read",
                "memory.write",
            ]
            self.rbac.define_role(RoleDef("child", child_caps))
            logger.info("Created child role with capabilities: %s", child_caps)

        if "guest" not in self.config.roles:
            # Create guest role with minimal read-only access
            guest_caps = [
                "memory.read",
            ]
            self.rbac.define_role(RoleDef("guest", guest_caps))
            logger.info("Created guest role with capabilities: %s", guest_caps)

        # Create default admin binding (customize as needed)
        self.rbac.bind(Binding("system_admin", "admin", "shared:household"))

        # Create test user bindings for integration tests
        self.rbac.bind(Binding("testuser", "member", "shared:household"))
        self.rbac.bind(Binding("integration_user", "admin", "shared:household"))

        logger.info("Default roles and test user bindings initialized")

    # -------------------------------------------------------------------------
    # Core Policy Decision Methods
    # -------------------------------------------------------------------------

    async def check_api_operation(
        self,
        security_context: SecurityContext,
        operation: str,
        resource: str,
        band: str = "GREEN",
        tags: Optional[List[str]] = None,
    ) -> PolicyDecision:
        """
        Check API operation permissions.

        Args:
            security_context: From FastAPI auth middleware
            operation: REFER, PROJECT, DETACH, UNDO
            resource: Target resource/space
            band: Risk band of the operation
            tags: Resource tags for context
        """
        try:
            # Convert SecurityContext to ABAC context using the bridge
            abac_ctx = self.security_bridge.to_abac_context(security_context)

            # Map operation to share request
            req = ShareRequest(
                op=operation,  # Remove cast since we changed ShareRequest.op to str
                actor_id=security_context.user_id,
                from_space="shared:household",  # Default space for now
                to_space=resource if operation in ("PROJECT", "DETACH") else None,
                band=cast(Band, band),
                tags=tags or [],
            )

            decision = self.space_policy.evaluate_share(req, abac_ctx)

            # Audit logging
            await self._audit_decision(
                "API", operation, security_context.user_id, req, decision
            )

            return decision

        except Exception as e:
            logger.error(f"Policy check failed: {e}")
            return PolicyDecision(
                decision="DENY",
                reasons=[f"policy_error: {str(e)}"],
                obligations=Obligation(log_audit=True),
            )

    async def check_event_operation(
        self, event: Event, operation: str = "REFER"
    ) -> PolicyDecision:
        """
        Check event bus operation permissions.

        Args:
            event: Event being published/consumed
            operation: REFER (subscribe), PROJECT (publish cross-space)
        """
        try:
            # Extract context from event metadata
            abac_ctx = self._event_to_abac_context(event)

            # Get actor ID in proper format
            actor_id = "system"
            if event.meta.actor:
                if hasattr(event.meta.actor, "user_id"):
                    actor_id = event.meta.actor.user_id
                else:
                    actor_id = str(event.meta.actor)

            req = ShareRequest(
                op=operation,  # Remove cast since we changed ShareRequest.op to str
                actor_id=actor_id,
                from_space=event.meta.space_id or "shared:household",
                to_space=None,  # Events are typically within-space
                band=cast(Band, "GREEN"),  # Default for events, override if needed
                tags=[],
            )

            decision = self.space_policy.evaluate_share(req, abac_ctx)

            # Audit logging
            await self._audit_decision("EVENT", operation, req.actor_id, req, decision)

            return decision

        except Exception as e:
            logger.error(f"Event policy check failed: {e}")
            return PolicyDecision(
                decision="DENY",
                reasons=[f"event_policy_error: {str(e)}"],
                obligations=Obligation(log_audit=True),
            )

    async def check_memory_operation(
        self,
        actor_id: str,
        operation: str,
        space_id: str,
        device_context: Optional[Dict[str, Any]] = None,
        env_context: Optional[Dict[str, Any]] = None,
        band: str = "GREEN",
        tags: Optional[List[str]] = None,
    ) -> PolicyDecision:
        """
        Check memory service operation permissions.

        Args:
            actor_id: User performing the operation
            operation: REFER, PROJECT, DETACH, etc.
            space_id: Target space
            device_context: Device attributes
            env_context: Environment attributes
            band: Risk band
            tags: Content tags
        """
        try:
            # Build ABAC context
            abac_ctx = AbacContext(
                actor=ActorAttrs(actor_id=actor_id),
                device=DeviceAttrs(
                    device_id=(
                        device_context.get("device_id", "unknown")
                        if device_context
                        else "unknown"
                    ),
                    trust=(
                        device_context.get("trust", "trusted")
                        if device_context
                        else "trusted"
                    ),
                ),
                env=EnvAttrs(
                    time_of_day_hours=(
                        env_context.get("time_of_day_hours", 12.0)
                        if env_context
                        else 12.0
                    ),
                    arousal=env_context.get("arousal") if env_context else None,
                    safety_pressure=(
                        env_context.get("safety_pressure") if env_context else None
                    ),
                ),
            )

            req = ShareRequest(
                op=operation,  # Remove cast since we changed ShareRequest.op to str
                actor_id=actor_id,
                from_space=space_id,
                to_space=None,
                band=cast(Band, band),
                tags=tags or [],
            )

            decision = self.space_policy.evaluate_share(req, abac_ctx)

            # Audit logging
            await self._audit_decision("MEMORY", operation, actor_id, req, decision)

            return decision

        except Exception as e:
            logger.error(f"Memory policy check failed: {e}")
            return PolicyDecision(
                decision="DENY",
                reasons=[f"memory_policy_error: {str(e)}"],
                obligations=Obligation(log_audit=True),
            )

    # -------------------------------------------------------------------------
    # Obligation Enforcement Helpers
    # -------------------------------------------------------------------------

    async def apply_redaction(self, content: str, redact_categories: List[str]) -> str:
        """Apply redaction based on policy obligations."""
        if not redact_categories:
            return content

        redactor = Redactor(categories=redact_categories)
        result = redactor.redact_text(content)
        return result.text

    async def apply_payload_redaction(
        self,
        payload: Dict[str, Any],
        redact_categories: List[str],
        key_policies: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Apply redaction to structured payload."""
        if not redact_categories:
            return payload

        redactor = Redactor(categories=redact_categories)
        return redactor.redact_payload(payload, key_policies or {})

    def check_band_minimum(self, current_band: str, required_band: str) -> bool:
        """Check if current band meets minimum requirement."""
        band_order = {"GREEN": 0, "AMBER": 1, "RED": 2, "BLACK": 3}
        return band_order.get(current_band, 0) >= band_order.get(required_band, 0)

    # -------------------------------------------------------------------------
    # Context Conversion Helpers
    # -------------------------------------------------------------------------

    def _event_to_abac_context(self, event: Event) -> AbacContext:
        """Extract ABAC context from event metadata."""
        actor_id = "system"
        if event.meta.actor:
            if hasattr(event.meta.actor, "user_id"):
                actor_id = event.meta.actor.user_id
            else:
                actor_id = str(event.meta.actor)

        return AbacContext(
            actor=ActorAttrs(actor_id=actor_id),
            device=DeviceAttrs(device_id="event_system", trust="trusted"),
            env=EnvAttrs(time_of_day_hours=12.0),
        )

    # -------------------------------------------------------------------------
    # Caching and Performance
    # -------------------------------------------------------------------------

    def _get_cached_caps(self, actor_id: str, space_id: str) -> Optional[set[str]]:
        """Get cached capabilities if not expired."""
        cache_key = f"{actor_id}:{space_id}"
        if cache_key in self._caps_cache:
            timestamp, caps = self._caps_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return caps
            else:
                del self._caps_cache[cache_key]
        return None

    def _cache_caps(self, actor_id: str, space_id: str, caps: set[str]):
        """Cache capabilities with timestamp."""
        cache_key = f"{actor_id}:{space_id}"
        self._caps_cache[cache_key] = (time.time(), caps)

        # Cleanup old entries (simple LRU)
        if len(self._caps_cache) > 1000:
            oldest = min(self._caps_cache.items(), key=lambda x: x[1][0])
            del self._caps_cache[oldest[0]]

    # -------------------------------------------------------------------------
    # Audit Logging
    # -------------------------------------------------------------------------

    async def _audit_decision(
        self,
        layer: str,
        operation: str,
        actor_id: str,
        request: ShareRequest,
        decision: PolicyDecision,
    ):
        """Audit policy decisions."""
        try:
            self.audit.log(
                {
                    "type": "POLICY_DECISION",
                    "layer": layer,
                    "operation": operation,
                    "actor_id": actor_id,
                    "from_space": request.from_space,
                    "to_space": request.to_space,
                    "band": request.band,
                    "decision": decision.decision,
                    "reasons": decision.reasons,
                    "has_redaction": bool(decision.obligations.redact),
                    "band_min": decision.obligations.band_min,
                    "model_version": decision.model_version,
                }
            )
        except Exception as e:
            logger.error(f"Audit logging failed: {e}")


# -------------------------------------------------------------------------
# Capability Mapping (Single Source of Truth)
# -------------------------------------------------------------------------

CAPABILITY_MAP: Dict[str, Optional[str]] = {
    # API Routes -> Capabilities
    "GET:/v1/recall": "memory.read",
    "POST:/v1/events/write": "memory.write",
    "POST:/v1/events/project": "memory.project",
    "POST:/v1/events/detach": "memory.detach",
    "POST:/v1/privacy/undo": "privacy.undo",
    "POST:/v1/tools/run": "tools.run",
    "GET:/v1/health": None,  # No capability required
    # Event Types -> Capabilities
    "HIPPO_ENCODE": "memory.write",
    "ACTION_DECISION": "memory.read",
    "ACTION_EXECUTED": "memory.write",
    "SCHEDULED_TICK": "prospective.manage",
    "DSAR_EXPORT_READY": "privacy.delete",
    # Memory Operations -> Capabilities
    "memory.encode": "memory.write",
    "memory.retrieve": "memory.read",
    "memory.project": "memory.project",
    "memory.detach": "memory.detach",
}


def get_required_capability(operation: str) -> Optional[str]:
    """Get required capability for an operation."""
    return CAPABILITY_MAP.get(operation)


# -------------------------------------------------------------------------
# Singleton Instance (for dependency injection)
# -------------------------------------------------------------------------

_policy_service_instance: Optional[PolicyService] = None


def get_policy_service() -> PolicyService:
    """Get the singleton PolicyService instance."""
    global _policy_service_instance
    if _policy_service_instance is None:
        raise RuntimeError(
            "PolicyService not initialized. Call initialize_policy_service() first."
        )
    return _policy_service_instance


def initialize_policy_service(
    config_path: Optional[str] = None, storage_dir: str = "./workspace/policy"
) -> PolicyService:
    """Initialize the global PolicyService instance."""
    global _policy_service_instance
    _policy_service_instance = PolicyService(config_path, storage_dir)
    return _policy_service_instance

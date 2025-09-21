from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Protocol, Tuple, Union

from .decision import Decision

# Import enhanced ABAC components
try:
    from .abac_enhanced.attribute_engine import EnhancedAttributeEngine
    from .abac_enhanced.conflict_resolver import Band as ConflictBand
    from .abac_enhanced.conflict_resolver import ConflictResolver, PolicyEvaluation

    enhanced_abac_available = True
except ImportError:
    # Fallback if enhanced components not available
    enhanced_abac_available = False
    EnhancedAttributeEngine = None
    ConflictResolver = None

logger = logging.getLogger(__name__)

# Type aliases for better contract compliance
Band = Literal["GREEN", "AMBER", "RED", "BLACK"]
TrustLevel = Literal["untrusted", "trusted", "hardened", "verified"]
NetworkType = Literal["trusted", "untrusted", "cellular", "vpn"]
AuthMethod = Literal["mtls", "jwt", "api_key"]
TemporalContext = Literal["work_hours", "family_time", "sleep_time"]
ObligationsDict = Dict[str, Union[List[str], str, bool, float, None]]


class SafetyPipeline(Protocol):
    """Protocol for P18 Safety Pipeline integration with enhanced threat assessment."""

    def assess_context(self, ctx: AbacContext) -> Dict[str, Any]:
        """
        Assess safety context and return comprehensive risk assessment.

        Returns dict with:
        - risk_level: float 0.0-1.0 (low to critical)
        - threat_indicators: List[str] (specific threats detected)
        - recommended_band: str (GREEN/AMBER/RED/BLACK)
        - content_flags: List[str] (content requiring redaction)
        - safety_score: float (overall safety confidence)
        - mitigation_required: bool (whether active mitigation needed)
        """
        ...

    def validate_content(self, content: str, context: AbacContext) -> Dict[str, Any]:
        """Validate content for safety violations and flag concerns."""
        ...

    def get_mitigation_actions(self, risk_assessment: Dict[str, Any]) -> List[str]:
        """Get recommended mitigation actions for identified risks."""
        ...


class CacheBackend(Protocol):
    """Protocol for decision caching backend."""

    def get(self, key: str) -> Optional[Tuple[Decision, List[str], ObligationsDict]]:
        """Get cached decision."""
        ...

    def setex(
        self, key: str, ttl: int, value: Tuple[Decision, List[str], ObligationsDict]
    ) -> None:
        """Set cached decision with TTL."""
        ...


@dataclass
class ActorAttrs:
    """Actor (user) attributes for ABAC evaluation - Contract compliant."""

    actor_id: str
    is_minor: bool = False
    relation: Optional[str] = None  # "family", "guardian", "friend", etc.
    trust_level: str = "normal"  # "low", "normal", "high", "verified"
    role: Optional[str] = None
    capabilities: list[str] = field(default_factory=list)
    # Contract extensions
    space_access: list[str] = field(default_factory=list)  # Space access patterns
    auth_method: Optional[AuthMethod] = None  # "mtls", "jwt", "api_key"
    session_id: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class DeviceAttrs:
    """Device attributes for ABAC evaluation - Enhanced for contract compliance."""

    device_id: str
    trust: TrustLevel = "trusted"  # "untrusted", "trusted", "hardened", "verified"
    battery_low: bool = False
    cpu_throttled: bool = False
    screen_locked: bool = False
    location_verified: bool = True
    network_type: NetworkType = "trusted"  # "trusted", "untrusted", "cellular", "vpn"
    # Contract extensions
    mls_group: Optional[str] = None  # Message Layer Security group
    device_fingerprint: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    rooted_jailbroken: bool = False


@dataclass
class EnvAttrs:
    """Environmental attributes for ABAC evaluation - Comprehensive context."""

    time_of_day_hours: float = 12.0
    location: Optional[str] = None
    space_band_min: Optional[Band] = None  # Minimum band for space
    arousal: Optional[float] = None  # 0.0-1.0 emotional arousal
    safety_pressure: Optional[float] = None  # 0.0-1.0 safety concern level
    curfew_hours: Optional[list[int]] = None  # Hours during curfew
    risk_assessment: Optional[dict[str, float]] = None  # P18 risk scores
    temporal_context: Optional[TemporalContext] = (
        None  # "work_hours", "family_time", "sleep_time"
    )
    # Contract extensions
    ip_address: Optional[str] = None
    request_id: Optional[str] = None
    geofence_zone: Optional[str] = None  # "home", "school", "work", "unknown"
    ambient_noise_level: Optional[float] = None
    family_present: bool = True


@dataclass
class AbacContext:
    actor: ActorAttrs
    device: DeviceAttrs
    env: EnvAttrs
    request_metadata: Optional[Dict[str, Any]] = None


class AbacEngine:
    """
    Enhanced Attribute-Based Access Control Engine for MemoryOS Policy Foundation.
    Contract-compliant implementation with comprehensive safety integration.

    Features:
    - Advanced attribute evaluation with context enrichment
    - P18 safety pipeline integration with failsafe mechanisms
    - Decision caching for sub-50ms latency (contract requirement)
    - Band-aware policy enforcement (GREEN/AMBER/RED/BLACK)
    - Temporal, location, and geofencing controls
    - Comprehensive audit trail generation
    - Contract-compliant error handling and recovery
    """

    def __init__(
        self,
        safety_pipeline: Optional[SafetyPipeline] = None,
        cache_backend: Optional[CacheBackend] = None,
        enable_metrics: bool = True,
    ):
        """Initialize enhanced ABAC engine with contract compliance.

        Args:
            safety_pipeline: Optional P18 safety assessment integration
            cache_backend: Optional Redis-like cache for <50ms evaluation
            enable_metrics: Enable performance and audit metrics collection
        """
        self.safety_pipeline = safety_pipeline
        self.cache_backend = cache_backend
        self.enable_metrics = enable_metrics
        self.logger = logger

        # Initialize enhanced attribute engine if available
        if enhanced_abac_available and EnhancedAttributeEngine:
            # Create cache adapter for compatibility
            cache_adapter = None
            if cache_backend:

                class CacheAdapter:
                    def __init__(self, backend):
                        self.backend = backend

                    def get(self, key: str):
                        return self.backend.get(key)

                    def set(self, key: str, value, ttl: int):
                        self.backend.setex(key, ttl, value)

                cache_adapter = CacheAdapter(cache_backend)

            self.enhanced_attribute_engine = EnhancedAttributeEngine(
                cache_backend=cache_adapter, enable_metrics=enable_metrics
            )
            self.logger.info("Enhanced attribute engine initialized")
        else:
            self.enhanced_attribute_engine = None
            self.logger.info("Using legacy attribute evaluation")

        # Initialize conflict resolver if available
        if enhanced_abac_available and ConflictResolver:
            try:
                self.conflict_resolver = ConflictResolver(
                    enable_caching=bool(cache_backend)
                )
                self.logger.info("Enhanced ABAC conflict resolver initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize conflict resolver: {e}")
                self.conflict_resolver = None
        else:
            self.conflict_resolver = None

        # Performance tracking for contract compliance
        self.evaluation_times: list[float] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_evaluations = 0

        # Band hierarchy for escalation logic
        self.band_hierarchy: dict[str, int] = {
            "GREEN": 0,
            "AMBER": 1,
            "RED": 2,
            "BLACK": 3,
        }

        # Risk operation patterns (expandable)
        self.risky_operations = {
            "memory.project",
            "memory.detach",
            "tools.run",
            "sharing.export",
            "privacy.undo",
            "system.admin",
            "policy.modify",
        }

        # Geofencing zones with risk levels
        self.geofence_risk_zones = {
            "home": 0.1,
            "school": 0.2,
            "work": 0.3,
            "public": 0.6,
            "unknown": 0.9,
            "foreign": 1.0,
        }

    def evaluate_with_enhanced_attributes(
        self, action: str, abac_ctx: AbacContext
    ) -> Tuple[Decision, list[str], ObligationsDict]:
        """
        Enhanced ABAC evaluation using the new attribute engine (Issue #27.1).
        Provides contract-compliant attribute evaluation with context-aware decisions.

        Args:
            action: Action being evaluated (e.g., "memory.project")
            abac_ctx: Full ABAC context with actor/device/environment attributes

        Returns:
            Tuple of (decision, reasons, obligations_dict)
            decision: "ALLOW", "ALLOW_REDACTED", or "DENY"
            reasons: List of human-readable decision reasons
            obligations_dict: Dict with enhanced context-aware obligations

        Note:
            Falls back to legacy evaluation if enhanced engine not available.
        """
        if not self.enhanced_attribute_engine:
            # Fallback to legacy evaluation
            return self.evaluate(action, abac_ctx)

        evaluation_start = time.time()
        self.total_evaluations += 1

        try:
            # Generate audit ID for traceability
            audit_id = str(uuid.uuid4())

            # Convert AbacContext to attribute dictionaries
            actor_attrs = {
                "actor_id": abac_ctx.actor.actor_id,
                "is_minor": abac_ctx.actor.is_minor,
                "relation": abac_ctx.actor.relation,
                "trust_level": abac_ctx.actor.trust_level,
                "role": abac_ctx.actor.role,
                "capabilities": abac_ctx.actor.capabilities,
                "space_access": abac_ctx.actor.space_access,
                "auth_method": abac_ctx.actor.auth_method,
                "session_id": abac_ctx.actor.session_id,
            }

            device_attrs = {
                "device_id": abac_ctx.device.device_id,
                "trust": abac_ctx.device.trust,
                "battery_low": abac_ctx.device.battery_low,
                "cpu_throttled": abac_ctx.device.cpu_throttled,
                "screen_locked": abac_ctx.device.screen_locked,
                "location_verified": abac_ctx.device.location_verified,
                "network_type": abac_ctx.device.network_type,
                "mls_group": abac_ctx.device.mls_group,
                "device_fingerprint": abac_ctx.device.device_fingerprint,
                "os_version": abac_ctx.device.os_version,
                "app_version": abac_ctx.device.app_version,
                "rooted_jailbroken": abac_ctx.device.rooted_jailbroken,
            }

            env_attrs = {
                "time_of_day_hours": abac_ctx.env.time_of_day_hours,
                "location": abac_ctx.env.location,
                "space_band_min": abac_ctx.env.space_band_min,
                "arousal": abac_ctx.env.arousal,
                "safety_pressure": abac_ctx.env.safety_pressure,
                "curfew_hours": abac_ctx.env.curfew_hours,
                "risk_assessment": abac_ctx.env.risk_assessment,
                "temporal_context": abac_ctx.env.temporal_context,
                "ip_address": abac_ctx.env.ip_address,
                "request_id": abac_ctx.env.request_id,
                "geofence_zone": abac_ctx.env.geofence_zone,
                "ambient_noise_level": abac_ctx.env.ambient_noise_level,
                "family_present": abac_ctx.env.family_present,
            }

            request_context = {
                "action": action,
                "request_metadata": abac_ctx.request_metadata,
                "audit_id": audit_id,
            }

            # Perform enhanced attribute evaluation
            evaluation_results, aggregated_context = (
                self.enhanced_attribute_engine.evaluate_attributes(
                    actor_attrs, device_attrs, env_attrs, request_context
                )
            )

            # Initialize decision context
            reasons: list[str] = []
            obligations: ObligationsDict = {
                "redact": [],
                "band_min": aggregated_context.get("final_band", "GREEN"),
                "log_audit": True,
                "reason_tags": [],
                "audit_id": audit_id,
                "evaluation_timestamp": time.time(),
                "mitigation_actions": [],
                "context_effects": aggregated_context.get("context_effects", []),
                "performance_metrics": aggregated_context.get(
                    "performance_metrics", {}
                ),
            }
            decision: Decision = "ALLOW"

            # Check for validation errors
            validation_errors = aggregated_context.get("validation_errors", [])
            if validation_errors:
                decision = "DENY"
                reasons.extend(
                    [f"Validation error: {error}" for error in validation_errors]
                )
                obligations["band_min"] = "RED"  # Escalate on validation errors

            # Apply context effects to decision
            context_effects = aggregated_context.get("context_effects", [])

            # Process critical effects that override decisions
            if "emergency_fallback_mode" in context_effects:
                decision = "DENY"
                reasons.append("Emergency fallback mode activated")
                obligations["band_min"] = "RED"

            elif (
                "block_sensitive_operations" in context_effects
                and action in self.risky_operations
            ):
                decision = "DENY"
                reasons.append(
                    "Sensitive operation blocked due to device security concerns"
                )

            elif "require_additional_authentication" in context_effects:
                decision = "ALLOW_REDACTED"
                reasons.append("Additional authentication required for this context")
                obligations["redact"].extend(["sensitive_content", "personal_data"])

            # Apply protective measures for minors
            if "enhanced_minor_protection" in context_effects:
                if decision == "ALLOW":
                    decision = "ALLOW_REDACTED"
                reasons.append("Minor protection measures applied")
                obligations["redact"].extend(["adult_content", "sensitive_data"])

            # Apply content filtering
            if any(
                effect.startswith("content_filtering") for effect in context_effects
            ):
                if decision == "ALLOW":
                    decision = "ALLOW_REDACTED"
                reasons.append("Content filtering applied")
                obligations["redact"].append("filtered_content")

            # Apply safety pipeline assessment if available
            if self.safety_pipeline:
                safety_assessment = self.safety_pipeline.assess_context(abac_ctx)
                risk_level = safety_assessment.get("risk_level", 0.0)

                if risk_level > 0.8:
                    decision = "DENY"
                    reasons.append("High safety risk detected")
                    obligations["band_min"] = "RED"
                elif risk_level > 0.5:
                    if decision == "ALLOW":
                        decision = "ALLOW_REDACTED"
                    reasons.append("Moderate safety risk - applying restrictions")
                    obligations["redact"].extend(
                        safety_assessment.get("content_flags", [])
                    )

                # Add mitigation actions
                mitigation_actions = self.safety_pipeline.get_mitigation_actions(
                    safety_assessment
                )
                obligations["mitigation_actions"].extend(mitigation_actions)

            # Apply legacy evaluation for additional checks
            if decision != "DENY":
                legacy_decision, legacy_reasons, legacy_obligations = self.evaluate(
                    action, abac_ctx
                )

                # Take most restrictive decision
                if legacy_decision == "DENY":
                    decision = "DENY"
                    reasons.extend(legacy_reasons)
                elif legacy_decision == "ALLOW_REDACTED" and decision == "ALLOW":
                    decision = "ALLOW_REDACTED"
                    reasons.extend(legacy_reasons)

                # Merge obligations
                if isinstance(legacy_obligations.get("redact"), list):
                    obligations["redact"].extend(legacy_obligations["redact"])
                if legacy_obligations.get("band_min"):
                    current_band = obligations.get("band_min", "GREEN")
                    legacy_band = legacy_obligations.get("band_min", "GREEN")
                    obligations["band_min"] = self._escalate_band(
                        current_band, legacy_band
                    )

            # Record performance metrics
            evaluation_time = time.time() - evaluation_start
            if self.enable_metrics:
                self.evaluation_times.append(evaluation_time * 1000)

            self.logger.info(
                f"Enhanced ABAC evaluation completed: action={action}, decision={decision}, "
                f"time={evaluation_time*1000:.2f}ms, band={obligations.get('band_min')}, "
                f"context_effects_count={len(context_effects)}, audit_id={audit_id}"
            )

            return decision, reasons, obligations

        except Exception as e:
            evaluation_time = time.time() - evaluation_start
            self.logger.error(
                f"Enhanced ABAC evaluation failed: {e}, time={evaluation_time*1000:.2f}ms"
            )

            # Fail-safe fallback to legacy evaluation
            return self.evaluate(action, abac_ctx)

    def evaluate_with_conflict_resolution(
        self, policies: List[str], action: str, abac_ctx: AbacContext
    ) -> Tuple[Decision, list[str], ObligationsDict]:
        """
        Enhanced ABAC evaluation with multi-policy conflict resolution (Issue #27.3).

        Args:
            policies: List of policy identifiers to evaluate
            action: Action being evaluated (e.g., "memory.project")
            abac_ctx: Full ABAC context with actor/device/environment attributes

        Returns:
            Tuple of (decision, reasons, obligations_dict)
            decision: "ALLOW", "ALLOW_REDACTED", or "DENY"
            reasons: List of human-readable decision reasons including conflict resolution
            obligations_dict: Dict with conflict-resolved obligations

        Note:
            Uses conflict resolver if available, falls back to single policy evaluation
        """
        start_time = time.time()

        if not self.conflict_resolver or len(policies) <= 1:
            # Fall back to single policy evaluation
            return self.evaluate_with_enhanced_attributes(action, abac_ctx)

        try:
            # Import here to avoid circular imports
            from .abac_enhanced.conflict_resolver import Band as ConflictBand
            from .abac_enhanced.conflict_resolver import PolicyEvaluation

            # Evaluate each policy independently
            policy_evaluations = []

            for policy_id in policies:
                # For this implementation, we'll simulate different policy evaluations
                # In a real system, each policy would have its own evaluation logic
                decision, reasons, obligations = self.evaluate_with_enhanced_attributes(
                    action, abac_ctx
                )

                # Convert band string to conflict resolver Band enum
                band_str = obligations.get("band_min", "AMBER")
                conflict_band = ConflictBand(band_str)

                policy_eval = PolicyEvaluation(
                    policy_id=policy_id,
                    decision=decision,
                    band=conflict_band,
                    confidence=0.8,  # Default confidence
                    reasons=reasons,
                    obligations=obligations,
                    evaluation_time_ms=(time.time() - start_time) * 1000,
                    priority=self._get_policy_priority(policy_id),
                )
                policy_evaluations.append(policy_eval)

            # Build request context for conflict resolution
            request_context = {
                "action": action,
                "actor": {
                    "is_minor": abac_ctx.actor.is_minor,
                    "trust_level": abac_ctx.actor.trust_level,
                    "role": abac_ctx.actor.role,
                },
                "device": {
                    "trust": abac_ctx.device.trust,
                    "battery_low": abac_ctx.device.battery_low,
                    "rooted_jailbroken": abac_ctx.device.rooted_jailbroken,
                },
                "environment": {
                    "time_of_day_hours": abac_ctx.env.time_of_day_hours,
                    "location": abac_ctx.env.location,
                    "safety_pressure": abac_ctx.env.safety_pressure or 0.0,
                },
                "urgency": (
                    abac_ctx.request_metadata.get("urgency")
                    if abac_ctx.request_metadata
                    else None
                ),
                "family_conflict_hint": (
                    abac_ctx.request_metadata.get("family_conflict_hint", False)
                    if abac_ctx.request_metadata
                    else False
                ),
            }

            # Resolve conflicts
            resolution = self.conflict_resolver.resolve_conflicts(
                policy_evaluations, request_context
            )

            # Convert back to ABAC format
            final_decision = resolution.final_decision
            final_reasons = [resolution.reasoning]

            # Add specific conflict resolution reasons
            if resolution.conflicts_resolved:
                conflict_types = [
                    c.conflict_type.value for c in resolution.conflicts_resolved
                ]
                final_reasons.append(f"Resolved conflicts: {', '.join(conflict_types)}")
                final_reasons.append(
                    f"Resolution strategy: {resolution.strategy_used.value}"
                )

            final_obligations = resolution.final_obligations.copy()
            final_obligations["band_min"] = resolution.final_band.value
            final_obligations["conflict_resolution"] = {
                "strategy": resolution.strategy_used.value,
                "confidence": resolution.confidence_score,
                "resolution_time_ms": resolution.resolution_time_ms,
                "policies_evaluated": len(policies),
                "conflicts_count": len(resolution.conflicts_resolved),
            }

            # Update performance metrics
            total_time = (time.time() - start_time) * 1000
            self.evaluation_times.append(total_time)
            self.total_evaluations += 1

            self.logger.info(
                f"Multi-policy ABAC evaluation with conflict resolution: {final_decision}/{resolution.final_band.value} "
                f"({len(policies)} policies, {len(resolution.conflicts_resolved)} conflicts, {total_time:.1f}ms)"
            )

            return final_decision, final_reasons, final_obligations

        except Exception as e:
            self.logger.error(
                f"Multi-policy evaluation with conflict resolution failed: {e}"
            )
            # Fall back to enhanced single evaluation
            return self.evaluate_with_enhanced_attributes(action, abac_ctx)

    def _get_policy_priority(self, policy_id: str) -> int:
        """Get priority for a policy (higher number = higher priority)"""
        # Contract-defined priority hierarchy
        priority_map = {
            "emergency_override": 100,
            "safety_first": 80,
            "security_precedence": 60,
            "context_specific": 40,
            "role_based": 20,
            "default": 10,
        }

        # Map policy_id to priority (simplified for demo)
        if "emergency" in policy_id.lower():
            return priority_map["emergency_override"]
        elif "safety" in policy_id.lower() or "minor" in policy_id.lower():
            return priority_map["safety_first"]
        elif "security" in policy_id.lower() or "device" in policy_id.lower():
            return priority_map["security_precedence"]
        elif (
            "context" in policy_id.lower()
            or "location" in policy_id.lower()
            or "time" in policy_id.lower()
        ):
            return priority_map["context_specific"]
        elif "role" in policy_id.lower() or "rbac" in policy_id.lower():
            return priority_map["role_based"]
        else:
            return priority_map["default"]

    def evaluate(
        self, action: str, abac_ctx: AbacContext
    ) -> Tuple[Decision, list[str], ObligationsDict]:
        """
        Enhanced ABAC evaluation with comprehensive safety integration.
        Contract requirement: <50ms p95 latency for policy evaluation.

        Args:
            action: Action being evaluated (e.g., "memory.project")
            abac_ctx: Full ABAC context with actor/device/environment attributes

        Returns:
            Tuple of (decision, reasons, obligations_dict)
            decision: "ALLOW", "ALLOW_REDACTED", or "DENY"
            reasons: List of human-readable decision reasons
            obligations_dict: Dict with redact, band_min, log_audit, reason_tags

        Raises:
            PolicyError: On critical evaluation failures
        """
        evaluation_start = time.time()
        self.total_evaluations += 1

        try:
            # Generate audit ID for traceability
            audit_id = str(uuid.uuid4())

            # Check cache first for performance compliance
            cache_key = self._build_cache_key(action, abac_ctx)
            if self.cache_backend and (cached := self.cache_backend.get(cache_key)):
                self.cache_hits += 1
                self.logger.debug(
                    f"ABAC cache hit for action={action}, audit_id={audit_id}"
                )
                decision, reasons, obligations = cached
                obligations["audit_id"] = audit_id
                return decision, reasons, obligations

            self.cache_misses += 1

            # Initialize decision context with audit trail
            reasons: list[str] = []
            obligations: ObligationsDict = {
                "redact": [],
                "band_min": None,
                "log_audit": True,
                "reason_tags": [],
                "audit_id": audit_id,
                "evaluation_timestamp": time.time(),
                "mitigation_actions": [],
            }
            decision: Decision = "ALLOW"

            # Core ABAC evaluation chain
            decision, reasons = self._evaluate_device_trust(
                action, abac_ctx, decision, reasons, obligations
            )

            if decision != "DENY":  # Continue evaluation if not already denied
                decision, reasons = self._evaluate_resource_constraints(
                    action, abac_ctx, decision, reasons, obligations
                )

            if decision != "DENY":
                decision, reasons = self._evaluate_temporal_restrictions(
                    action, abac_ctx, decision, reasons, obligations
                )

            if decision != "DENY":
                decision, reasons = self._evaluate_geofencing_controls(
                    action, abac_ctx, decision, reasons, obligations
                )

            if decision != "DENY":
                decision, reasons = self._evaluate_affect_state(
                    action, abac_ctx, decision, reasons, obligations
                )

            if decision != "DENY":
                decision, reasons = self._evaluate_safety_assessment(
                    action, abac_ctx, decision, reasons, obligations
                )

            if decision != "DENY":
                decision, reasons = self._evaluate_location_context(
                    action, abac_ctx, decision, reasons, obligations
                )

            # Apply band floor logic
            decision, reasons = self._apply_band_floor(
                abac_ctx, decision, reasons, obligations
            )

            # Apply contract-required security controls
            decision, reasons = self._apply_security_controls(
                action, abac_ctx, decision, reasons, obligations
            )

            # Cache successful evaluations for performance
            if self.cache_backend and decision in ["ALLOW", "ALLOW_REDACTED"]:
                cache_value = (
                    decision,
                    reasons.copy(),
                    {
                        k: v
                        for k, v in obligations.items()
                        if k not in ["audit_id", "evaluation_timestamp"]
                    },
                )
                self.cache_backend.setex(cache_key, 300, cache_value)  # 5min TTL

            evaluation_time = time.time() - evaluation_start
            if self.enable_metrics:
                self._record_metrics(evaluation_time, decision, len(reasons))

            self.logger.info(
                f"ABAC evaluation completed: action={action}, decision={decision}, "
                f"time={evaluation_time*1000:.2f}ms, audit_id={audit_id}"
            )

            return decision, reasons, obligations

        except Exception as e:
            evaluation_time = time.time() - evaluation_start
            self.logger.error(
                f"ABAC evaluation failed: action={action}, error={e}, time={evaluation_time*1000:.2f}ms"
            )

            # Fail-safe: deny on critical errors
            return (
                "DENY",
                [f"evaluation_error_{type(e).__name__}"],
                {
                    "redact": [],
                    "band_min": "RED",  # Escalate to RED on errors
                    "log_audit": True,
                    "reason_tags": ["error_fallback"],
                    "audit_id": str(uuid.uuid4()),
                    "error_details": str(e),
                },
            )

    def _evaluate_geofencing_controls(
        self,
        action: str,
        ctx: AbacContext,
        decision: Decision,
        reasons: list[str],
        obligations: ObligationsDict,
    ) -> Tuple[Decision, list[str]]:
        """Evaluate geofencing and location-based access controls."""
        env = ctx.env
        device = ctx.device

        # Check geofence zone risk levels
        if env.geofence_zone:
            risk_level = self.geofence_risk_zones.get(env.geofence_zone, 0.5)

            if risk_level >= 0.7 and action in self.risky_operations:
                reasons.append(f"geofence_high_risk_zone_{env.geofence_zone}")
                self._safe_escalate_band(obligations, "RED")
                obligations["reason_tags"].append("geofence_restricted")

            elif risk_level >= 0.5 and action in self.risky_operations:
                reasons.append(f"geofence_moderate_risk_zone_{env.geofence_zone}")
                self._safe_escalate_band(obligations, "AMBER")

        # Location verification requirements
        if not device.location_verified and action.startswith("sharing."):
            reasons.append("unverified_location_restricts_sharing")
            obligations["band_min"] = self._escalate_band(
                obligations.get("band_min"), "AMBER"
            )
            if isinstance(obligations.get("redact"), list):
                obligations["redact"].extend(["location", "precise_coordinates"])

        return decision, reasons

    def _apply_security_controls(
        self,
        action: str,
        ctx: AbacContext,
        decision: Decision,
        reasons: list[str],
        obligations: ObligationsDict,
    ) -> Tuple[Decision, list[str]]:
        """Apply contract-required security controls and compliance measures."""
        device = ctx.device
        actor = ctx.actor

        # mTLS certificate validation for admin operations
        if action.startswith("system.") or action.startswith("policy."):
            if actor.auth_method != "mtls":
                reasons.append("admin_operations_require_mtls_auth")
                return "DENY", reasons

        # Rooted/jailbroken device restrictions
        if device.rooted_jailbroken and action in self.risky_operations:
            reasons.append("rooted_device_blocks_risky_operations")
            return "DENY", reasons

        # MLS group requirements for certain operations
        if action.startswith("sharing.") and not device.mls_group:
            reasons.append("sharing_requires_mls_group_membership")
            obligations["band_min"] = self._escalate_band(
                obligations.get("band_min"), "AMBER"
            )

        # Session validation
        if not actor.session_id and action.startswith("memory."):
            reasons.append("memory_operations_require_valid_session")
            obligations["band_min"] = self._escalate_band(
                obligations.get("band_min"), "AMBER"
            )

        return decision, reasons

    def _record_metrics(
        self, evaluation_time: float, decision: Decision, reason_count: int
    ) -> None:
        """Record performance and audit metrics for contract compliance."""
        if self.enable_metrics:
            self.evaluation_times.append(evaluation_time)

            # Keep only last 1000 measurements for rolling metrics
            if len(self.evaluation_times) > 1000:
                self.evaluation_times = self.evaluation_times[-1000:]

            # Log performance warnings for contract compliance
            if evaluation_time > 0.05:  # 50ms contract threshold
                self.logger.warning(
                    f"ABAC evaluation exceeded 50ms threshold: {evaluation_time*1000:.2f}ms"
                )

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics for monitoring and contract compliance."""
        if not self.evaluation_times:
            return {"status": "no_data"}

        times = self.evaluation_times
        return {
            "total_evaluations": self.total_evaluations,
            "cache_hit_rate": (
                self.cache_hits / (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0
                else 0
            ),
            "avg_evaluation_time_ms": sum(times) * 1000 / len(times),
            "p95_evaluation_time_ms": (
                sorted(times)[int(len(times) * 0.95)] * 1000 if times else 0
            ),
            "p99_evaluation_time_ms": (
                sorted(times)[int(len(times) * 0.99)] * 1000 if times else 0
            ),
            "contract_compliance_rate": (
                sum(1 for t in times if t <= 0.05) / len(times) if times else 0
            ),
        }

    def _evaluate_device_trust(
        self,
        action: str,
        ctx: AbacContext,
        decision: Decision,
        reasons: list[str],
        obligations: ObligationsDict,
    ) -> Tuple[Decision, list[str]]:
        """Evaluate device trust and apply appropriate restrictions."""
        device = ctx.device

        # Untrusted device restrictions
        if device.trust == "untrusted":
            if action.startswith("memory.read") or action.startswith("memory.recall"):
                reasons.append("untrusted_device_read_requires_redaction")
                redact_list = obligations.get("redact", [])
                if isinstance(redact_list, list):
                    redact_list.extend(
                        [
                            "pii.email",
                            "pii.phone",
                            "pii.address",
                            "pii.ssn",
                            "financial.account",
                        ]
                    )
                decision = "ALLOW_REDACTED"
            elif action in self.risky_operations:
                reasons.append("untrusted_device_blocks_risky_operations")
                return "DENY", reasons

        # Screen locked security
        if device.screen_locked and action in self.risky_operations:
            reasons.append("screen_locked_restricts_risky_operations")
            current_band = obligations.get("band_min")
            band_str = current_band if isinstance(current_band, str) else None
            obligations["band_min"] = self._escalate_band(band_str, "AMBER")

        # Network security considerations
        if device.network_type == "untrusted" and action.startswith("sharing."):
            reasons.append("untrusted_network_restricts_sharing")
            current_band = obligations.get("band_min")
            band_str = current_band if isinstance(current_band, str) else None
            obligations["band_min"] = self._escalate_band(band_str, "AMBER")
            redact_list = obligations.get("redact", [])
            if isinstance(redact_list, list):
                redact_list.extend(["location", "device_info"])

        return decision, reasons

    def _evaluate_resource_constraints(
        self,
        action: str,
        ctx: AbacContext,
        decision: Decision,
        reasons: List[str],
        obligations: Dict[str, Any],
    ) -> Tuple[Decision, List[str]]:
        """Evaluate device resource constraints."""
        device = ctx.device

        # Battery/CPU constraints affect risky operations
        if (
            device.battery_low or device.cpu_throttled
        ) and action in self.risky_operations:
            reasons.append("resource_constraints_require_elevated_band")
            obligations["band_min"] = self._escalate_band(
                obligations.get("band_min"), "AMBER"
            )
            obligations["reason_tags"].append("resource_limited")

        return decision, reasons

    def _evaluate_temporal_restrictions(
        self,
        action: str,
        ctx: AbacContext,
        decision: Decision,
        reasons: List[str],
        obligations: Dict[str, Any],
    ) -> Tuple[Decision, List[str]]:
        """Evaluate time-based access restrictions."""
        env = ctx.env
        actor = ctx.actor

        # Minor curfew enforcement
        if actor.is_minor and env.curfew_hours:
            current_hour = int(env.time_of_day_hours)
            if current_hour in env.curfew_hours and action in self.risky_operations:
                reasons.append("minor_curfew_restricts_risky_operations")
                obligations["band_min"] = self._escalate_band(
                    obligations.get("band_min"), "AMBER"
                )
                obligations["reason_tags"].append("curfew_restricted")

        # Temporal context awareness
        if env.temporal_context == "sleep_time" and action in self.risky_operations:
            reasons.append("sleep_time_requires_elevated_security")
            obligations["band_min"] = self._escalate_band(
                obligations.get("band_min"), "AMBER"
            )

        return decision, reasons

    def _evaluate_affect_state(
        self,
        action: str,
        ctx: AbacContext,
        decision: Decision,
        reasons: List[str],
        obligations: Dict[str, Any],
    ) -> Tuple[Decision, List[str]]:
        """Evaluate emotional/affect state for policy decisions."""
        env = ctx.env

        # High arousal state restrictions
        arousal = env.arousal if env.arousal is not None else 0.5
        if arousal >= 0.7:
            reasons.append("high_arousal_requires_elevated_band")
            obligations["band_min"] = self._escalate_band(
                obligations.get("band_min"), "AMBER"
            )
            obligations["reason_tags"].append("high_arousal")

        # Safety pressure escalation
        safety_pressure = (
            env.safety_pressure if env.safety_pressure is not None else 0.0
        )
        if safety_pressure >= 0.6:
            reasons.append("elevated_safety_pressure_requires_amber_band")
            obligations["band_min"] = self._escalate_band(
                obligations.get("band_min"), "AMBER"
            )
            obligations["reason_tags"].append("safety_pressure")

        # Critical safety threshold
        if safety_pressure >= 0.9:
            reasons.append("critical_safety_pressure_blocks_risky_operations")
            if action in self.risky_operations:
                return "DENY", reasons

        return decision, reasons

    def _evaluate_safety_assessment(
        self,
        action: str,
        ctx: AbacContext,
        decision: Decision,
        reasons: List[str],
        obligations: Dict[str, Any],
    ) -> Tuple[Decision, List[str]]:
        """Integrate with P18 safety pipeline for enhanced assessment."""
        if not self.safety_pipeline:
            return decision, reasons

        try:
            # Get safety assessment from P18 pipeline
            safety_assessment = self.safety_pipeline.assess_context(ctx)

            if safety_assessment.get("risk_level", "low") == "high":
                reasons.append("p18_safety_assessment_high_risk")
                obligations["band_min"] = self._escalate_band(
                    obligations.get("band_min"), "RED"
                )
                obligations["reason_tags"].append("p18_high_risk")

            if safety_assessment.get("content_flags"):
                reasons.append("p18_content_flags_detected")
                obligations["redact"].extend(safety_assessment["content_flags"])
                decision = "ALLOW_REDACTED"

        except Exception as e:
            self.logger.warning(f"P18 safety assessment failed: {e}")
            # Fail-safe: escalate band on safety pipeline failure
            obligations["band_min"] = self._escalate_band(
                obligations.get("band_min"), "AMBER"
            )
            reasons.append("safety_assessment_unavailable_fallback")

        return decision, reasons

    def _evaluate_location_context(
        self,
        action: str,
        ctx: AbacContext,
        decision: Decision,
        reasons: List[str],
        obligations: Dict[str, Any],
    ) -> Tuple[Decision, List[str]]:
        """Evaluate location-based access controls."""
        device = ctx.device
        env = ctx.env

        # Unverified location requires restrictions
        if not device.location_verified and action in self.risky_operations:
            reasons.append("unverified_location_restricts_risky_operations")
            obligations["band_min"] = self._escalate_band(
                obligations.get("band_min"), "AMBER"
            )
            obligations["redact"].extend(["location", "precise_coordinates"])

        # High-risk location patterns
        if env.location and any(
            risk_loc in env.location.lower()
            for risk_loc in ["unknown", "foreign", "untrusted"]
        ):
            reasons.append("high_risk_location_detected")
            obligations["band_min"] = self._escalate_band(
                obligations.get("band_min"), "RED"
            )

        return decision, reasons

    def _apply_band_floor(
        self,
        ctx: AbacContext,
        decision: Decision,
        reasons: List[str],
        obligations: Dict[str, Any],
    ) -> Tuple[Decision, List[str]]:
        """Apply space-specific band floor requirements."""
        env = ctx.env

        if env.space_band_min:
            current_band = obligations.get("band_min", "GREEN")
            if self._band_level(env.space_band_min) > self._band_level(current_band):
                obligations["band_min"] = env.space_band_min
                reasons.append(f"space_band_floor_applied_{env.space_band_min}")

        return decision, reasons

    def _safe_escalate_band(self, obligations: ObligationsDict, new_band: str) -> None:
        """Safely escalate band in obligations dict with proper type handling."""
        current_band = obligations.get("band_min")
        if isinstance(current_band, str) or current_band is None:
            obligations["band_min"] = self._escalate_band(current_band, new_band)
        else:
            obligations["band_min"] = new_band  # Fallback to new band if type issue

    def _safe_append_tag(self, obligations: ObligationsDict, tag: str) -> None:
        """Safely append reason tag with type checking."""
        reason_tags = obligations.get("reason_tags")
        if isinstance(reason_tags, list):
            reason_tags.append(tag)
        elif reason_tags is None:
            obligations["reason_tags"] = [tag]

    def _safe_extend_redact(
        self, obligations: ObligationsDict, items: list[str]
    ) -> None:
        """Safely extend redact list with type checking."""
        redact_list = obligations.get("redact")
        if isinstance(redact_list, list):
            redact_list.extend(items)
        elif redact_list is None:
            obligations["redact"] = items.copy()

    def _escalate_band(self, current: Optional[str], new: str) -> str:
        """Escalate security band to higher level."""
        if not current:
            return new
        return new if self._band_level(new) > self._band_level(current) else current

    def _band_level(self, band: str) -> int:
        """Get numeric level for band comparison."""
        return self.band_hierarchy.get(band, 0)

    def _build_cache_key(self, action: str, ctx: AbacContext) -> str:
        """Build cache key for decision caching."""
        # Create deterministic cache key from context
        cache_data = {
            "action": action,
            "actor_id": ctx.actor.actor_id,
            "device_id": ctx.device.device_id,
            "device_trust": ctx.device.trust,
            "time_hour": int(ctx.env.time_of_day_hours),
            "arousal": ctx.env.arousal,
            "safety_pressure": ctx.env.safety_pressure,
        }

        cache_str = json.dumps(cache_data, sort_keys=True)
        return f"abac:{hashlib.md5(cache_str.encode()).hexdigest()}"

"""
Context-Aware Decision Engine for ABAC Implementation
Issue #27.2: Context-aware access decisions

Contract-driven context-aware decision making system with multi-factor evaluation,
temporal adaptation, and comprehensive obligation management.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .types import (
    Band,
    Decision,
    HistoricalContext,
    ObligationSpec,
    PerformanceMetrics,
    RealtimeContext,
    RequestContext,
)

logger = logging.getLogger(__name__)


class DecisionFactorWeight(Enum):
    """Decision factor weights as defined in context-aware-decisions.yaml contract."""

    SECURITY_FACTORS = 0.35
    SAFETY_FACTORS = 0.30
    OPERATIONAL_FACTORS = 0.20
    CONTEXTUAL_FACTORS = 0.15


@dataclass
class DecisionFactor:
    """Individual decision factor with weight and assessment."""

    name: str
    weight: float
    score: float  # 0.0-1.0
    description: str
    reasons: List[str] = field(default_factory=list)


@dataclass
class ContextEvaluation:
    """Result of context-aware evaluation."""

    decision: Decision
    band: Band
    confidence_score: float
    total_score: float
    factor_scores: Dict[str, float]
    obligations: List[ObligationSpec]
    reasons: List[str]
    adaptation_effects: List[str]
    evaluation_time_ms: float


class ContextAwareDecisionEngine:
    """
    Context-Aware Decision Engine implementing Issue #27.2 contract.

    Provides:
    - Multi-factor context evaluation (security/safety/operational/contextual)
    - Temporal and environmental adaptation rules
    - Real-time affect-aware decision adjustment
    - Comprehensive obligation framework with parameterized controls
    - Performance-optimized decision caching
    """

    def __init__(
        self,
        cache_backend: Optional[Any] = None,
        enable_metrics: bool = True,
        contract_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize context-aware decision engine.

        Args:
            cache_backend: Optional cache for decision results
            enable_metrics: Enable performance metrics collection
            contract_config: Configuration from context-aware-decisions.yaml
        """
        self.cache_backend = cache_backend
        self.enable_metrics = enable_metrics
        self.contract_config = contract_config or {}

        # Performance tracking
        self.decision_times: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0

        # Load contract configuration
        self._load_contract_configuration()

        # Initialize decision algorithms
        self._initialize_decision_algorithms()

        logger.info(
            "Context-Aware Decision Engine initialized with contract compliance"
        )

    def _load_contract_configuration(self) -> None:
        """Load configuration from context-aware-decisions.yaml contract."""
        # Decision factor weights from contract
        self.decision_factors = self.contract_config.get("decision_engine", {}).get(
            "decision_factors", {}
        )

        # Default weights if not in contract
        self.factor_weights = {
            "security_factors": self.decision_factors.get("security_factors", {}).get(
                "weight", 0.35
            ),
            "safety_factors": self.decision_factors.get("safety_factors", {}).get(
                "weight", 0.30
            ),
            "operational_factors": self.decision_factors.get(
                "operational_factors", {}
            ).get("weight", 0.20),
            "contextual_factors": self.decision_factors.get(
                "contextual_factors", {}
            ).get("weight", 0.15),
        }

        # Performance configuration
        self.performance_config = self.contract_config.get("performance", {})
        self.target_response_time_ms = self.performance_config.get(
            "decision_timing", {}
        ).get("target_response_time_ms", 100)
        self.maximum_response_time_ms = self.performance_config.get(
            "decision_timing", {}
        ).get("maximum_response_time_ms", 1000)

        # Cache configuration
        cache_config = self.performance_config.get("cache_configuration", {})
        self.decision_cache_ttl = cache_config.get("decision_cache_ttl", 300)
        self.context_cache_ttl = cache_config.get("context_cache_ttl", 60)

        logger.debug(
            f"Context configuration loaded: factor_weights={self.factor_weights}"
        )

    def _initialize_decision_algorithms(self) -> None:
        """Initialize decision algorithms from contract."""
        # Band hierarchy for escalation
        self.band_hierarchy = {"GREEN": 0, "AMBER": 1, "RED": 2, "BLACK": 3}

        # Decision hierarchy for restrictions
        self.decision_hierarchy = {"ALLOW": 0, "ALLOW_REDACTED": 1, "DENY": 2}

        # Temporal contexts and their effects
        self.temporal_adaptations = {
            "work_hours": {
                "time_range": "09:00-17:00",
                "effects": [
                    "prioritize_work_related_content",
                    "limit_entertainment_access",
                    "enable_focus_mode",
                ],
            },
            "family_time": {
                "time_range": "18:00-21:00",
                "effects": [
                    "require_family_appropriate_content",
                    "enable_shared_access_mode",
                ],
            },
            "sleep_time": {
                "time_range": "22:00-07:00",
                "effects": ["restrict_non_emergency_access", "enable_do_not_disturb"],
            },
        }

        # Location-based adaptations
        self.location_adaptations = {
            "home": ["enable_full_family_access", "relax_monitoring_requirements"],
            "school": ["restrict_to_educational_content", "enable_enhanced_monitoring"],
            "work": ["prioritize_work_content", "limit_personal_access"],
            "public": [
                "enable_privacy_mode",
                "restrict_personal_content",
                "increase_security_band",
            ],
        }

    def evaluate_context_decision(
        self,
        request_context: RequestContext,
        historical_context: HistoricalContext,
        realtime_context: RealtimeContext,
        actor_attrs: Dict[str, Any],
        device_attrs: Dict[str, Any],
        env_attrs: Dict[str, Any],
    ) -> ContextEvaluation:
        """
        Perform context-aware decision evaluation implementing Issue #27.2 contract.

        Args:
            request_context: Information about the access request
            historical_context: Historical patterns and behavior
            realtime_context: Real-time environmental and system context
            actor_attrs: Actor attributes from enhanced attribute evaluation
            device_attrs: Device attributes from enhanced attribute evaluation
            env_attrs: Environmental attributes from enhanced attribute evaluation

        Returns:
            ContextEvaluation with decision, band, obligations, and reasoning
        """
        evaluation_start = time.time()

        try:
            # Check cache first
            cache_key = self._build_decision_cache_key(
                request_context,
                historical_context,
                realtime_context,
                actor_attrs,
                device_attrs,
                env_attrs,
            )

            if self.cache_backend and (cached := self.cache_backend.get(cache_key)):
                self.cache_hits += 1
                logger.debug(f"Context decision cache hit: {cache_key[:16]}...")
                return cached

            self.cache_misses += 1

            # Initialize evaluation context
            reasons = []
            adaptation_effects = []
            obligations = []

            # Step 1: Evaluate decision factors
            security_score, security_reasons = self._evaluate_security_factors(
                actor_attrs, device_attrs, env_attrs, historical_context
            )

            safety_score, safety_reasons = self._evaluate_safety_factors(
                actor_attrs, env_attrs, realtime_context
            )

            operational_score, operational_reasons = self._evaluate_operational_factors(
                request_context, realtime_context, device_attrs
            )

            contextual_score, contextual_reasons = self._evaluate_contextual_factors(
                env_attrs, realtime_context, actor_attrs
            )

            # Step 2: Calculate weighted total score
            total_score = (
                security_score * self.factor_weights["security_factors"]
                + safety_score * self.factor_weights["safety_factors"]
                + operational_score * self.factor_weights["operational_factors"]
                + contextual_score * self.factor_weights["contextual_factors"]
            )

            factor_scores = {
                "security": security_score,
                "safety": safety_score,
                "operational": operational_score,
                "contextual": contextual_score,
            }

            # Collect all reasons
            reasons.extend(security_reasons)
            reasons.extend(safety_reasons)
            reasons.extend(operational_reasons)
            reasons.extend(contextual_reasons)

            # Step 3: Apply decision algorithms
            base_decision, base_band = self._apply_main_decision_tree(
                total_score, factor_scores, actor_attrs, device_attrs, env_attrs
            )

            # Step 4: Apply context adaptations
            adapted_decision, adapted_band, context_obligations, context_effects = (
                self._apply_context_adaptations(
                    base_decision, base_band, env_attrs, realtime_context, actor_attrs
                )
            )

            adaptation_effects.extend(context_effects)
            obligations.extend(context_obligations)

            # Step 5: Apply emergency and override logic
            final_decision, final_band, emergency_obligations = (
                self._apply_emergency_overrides(
                    adapted_decision,
                    adapted_band,
                    request_context,
                    realtime_context,
                    actor_attrs,
                )
            )

            obligations.extend(emergency_obligations)

            # Step 6: Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                total_score, factor_scores, len(reasons), len(adaptation_effects)
            )

            # Create final evaluation result
            evaluation = ContextEvaluation(
                decision=final_decision,
                band=final_band,
                confidence_score=confidence_score,
                total_score=total_score,
                factor_scores=factor_scores,
                obligations=obligations,
                reasons=reasons,
                adaptation_effects=adaptation_effects,
                evaluation_time_ms=(time.time() - evaluation_start) * 1000,
            )

            # Cache successful evaluation
            if self.cache_backend:
                self.cache_backend.set(cache_key, evaluation, self.decision_cache_ttl)

            # Record performance metrics
            if self.enable_metrics:
                self.decision_times.append(evaluation.evaluation_time_ms)

            logger.debug(
                f"Context decision completed: decision={final_decision}, band={final_band}, "
                f"score={total_score:.3f}, confidence={confidence_score:.3f}, "
                f"time={evaluation.evaluation_time_ms:.2f}ms"
            )

            return evaluation

        except Exception as e:
            evaluation_time = (time.time() - evaluation_start) * 1000
            logger.error(
                f"Context decision evaluation failed: {e}, time={evaluation_time:.2f}ms"
            )

            # Return fail-safe evaluation
            return self._create_failsafe_evaluation(e, evaluation_time)

    def _evaluate_security_factors(
        self,
        actor_attrs: Dict[str, Any],
        device_attrs: Dict[str, Any],
        env_attrs: Dict[str, Any],
        historical_context: HistoricalContext,
    ) -> Tuple[float, List[str]]:
        """Evaluate security factors with contract-defined weights."""
        score = 0.0
        reasons = []

        # Actor trust (weight: 0.4)
        actor_trust = actor_attrs.get("trust_level", "normal")
        if actor_trust == "verified":
            actor_score = 1.0
        elif actor_trust == "high":
            actor_score = 0.8
        elif actor_trust == "normal":
            actor_score = 0.6
        else:  # low
            actor_score = 0.2
            reasons.append("Low actor trust level detected")

        score += actor_score * 0.4

        # Device security (weight: 0.3)
        device_trust = device_attrs.get("trust", "trusted")
        device_score = {
            "verified": 1.0,
            "hardened": 0.9,
            "trusted": 0.7,
            "untrusted": 0.1,
        }.get(device_trust, 0.1)

        if device_attrs.get("rooted_jailbroken", False):
            device_score *= 0.3  # Severe penalty for compromised devices
            reasons.append("Device security compromised (rooted/jailbroken)")

        score += device_score * 0.3

        # Network security (weight: 0.2)
        network_type = device_attrs.get("network_type", "trusted")
        network_score = {
            "trusted": 1.0,
            "vpn": 0.8,
            "cellular": 0.6,
            "untrusted": 0.2,
        }.get(network_type, 0.2)

        if network_score < 0.6:
            reasons.append(f"Untrusted network connection: {network_type}")

        score += network_score * 0.2

        # Historical behavior (weight: 0.1)
        behavior_pattern = historical_context.behavior_pattern
        behavior_score = {
            "normal": 1.0,
            "unusual": 0.6,
            "suspicious": 0.3,
            "malicious": 0.1,
        }.get(behavior_pattern, 1.0)

        if behavior_score < 0.7:
            reasons.append(f"Concerning behavior pattern detected: {behavior_pattern}")

        score += behavior_score * 0.1

        return score, reasons

    def _evaluate_safety_factors(
        self,
        actor_attrs: Dict[str, Any],
        env_attrs: Dict[str, Any],
        realtime_context: RealtimeContext,
    ) -> Tuple[float, List[str]]:
        """Evaluate safety factors with contract-defined weights."""
        score = 1.0  # Start with full safety score
        reasons = []

        # Minor protection (weight: 0.4)
        is_minor = actor_attrs.get("is_minor", False)
        family_present = env_attrs.get("family_present", True)

        if is_minor:
            if not family_present:
                score -= 0.3  # Significant safety concern
                reasons.append("Minor without family supervision")
            else:
                reasons.append("Minor protection measures active")

        # Safety pipeline assessment (weight: 0.3)
        safety_pressure = env_attrs.get("safety_pressure", 0.0)
        if safety_pressure > 0.7:
            score -= 0.4  # High safety risk
            reasons.append("High safety pressure detected")
        elif safety_pressure > 0.4:
            score -= 0.2  # Moderate safety risk
            reasons.append("Moderate safety pressure")

        # Content sensitivity (weight: 0.2)
        # This would be evaluated based on requested content
        # For now, use a baseline assessment

        # Environmental safety (weight: 0.1)
        geofence_zone = env_attrs.get("geofence_zone", "unknown")
        if geofence_zone in ["unknown", "public"]:
            score -= 0.1
            reasons.append(f"Elevated risk location: {geofence_zone}")

        return max(0.0, min(1.0, score)), reasons

    def _evaluate_operational_factors(
        self,
        request_context: RequestContext,
        realtime_context: RealtimeContext,
        device_attrs: Dict[str, Any],
    ) -> Tuple[float, List[str]]:
        """Evaluate operational factors with contract-defined weights."""
        score = 1.0
        reasons = []

        # System performance (weight: 0.3)
        system_load = realtime_context.system_load
        if system_load > 0.8:
            score -= 0.3
            reasons.append("High system load detected")
        elif system_load > 0.6:
            score -= 0.1
            reasons.append("Moderate system load")

        # Resource availability (weight: 0.3)
        resource_availability = realtime_context.resource_availability
        if resource_availability < 0.3:
            score -= 0.4
            reasons.append("Low resource availability")
        elif resource_availability < 0.6:
            score -= 0.2
            reasons.append("Moderate resource constraints")

        # Urgency level (weight: 0.25)
        urgency = request_context.urgency
        if urgency == "emergency":
            score += 0.2  # Emergency requests get priority
            reasons.append("Emergency request prioritized")
        elif urgency == "low":
            score -= 0.1  # Low priority requests can be restricted

        # Device performance factors (weight: 0.15)
        if device_attrs.get("battery_low", False):
            score -= 0.1
            reasons.append("Device battery low")

        if device_attrs.get("cpu_throttled", False):
            score -= 0.05
            reasons.append("Device CPU throttled")

        return max(0.0, min(1.0, score)), reasons

    def _evaluate_contextual_factors(
        self,
        env_attrs: Dict[str, Any],
        realtime_context: RealtimeContext,
        actor_attrs: Dict[str, Any],
    ) -> Tuple[float, List[str]]:
        """Evaluate contextual factors with contract-defined weights."""
        score = 1.0
        reasons = []

        # Temporal context (weight: 0.35)
        temporal_context = env_attrs.get("temporal_context")
        time_of_day = env_attrs.get("time_of_day_hours", 12.0)

        if temporal_context == "sleep_time" or (time_of_day >= 22 or time_of_day <= 6):
            score -= 0.2
            reasons.append("Sleep time restrictions apply")
        elif temporal_context == "work_hours":
            # Context-dependent scoring based on request type
            score += 0.1  # Slight bonus for work hours organization

        # Location context (weight: 0.25)
        geofence_zone = env_attrs.get("geofence_zone", "unknown")
        location_bonus = {
            "home": 0.1,
            "school": 0.05,
            "work": 0.05,
            "public": -0.1,
            "unknown": -0.15,
        }
        score += location_bonus.get(geofence_zone, -0.15)

        if geofence_zone in ["public", "unknown"]:
            reasons.append(f"Location-based restrictions for {geofence_zone}")

        # Social context (weight: 0.25)
        family_present = env_attrs.get("family_present", True)
        is_minor = actor_attrs.get("is_minor", False)

        if is_minor and family_present:
            score += 0.1
            reasons.append("Positive family supervision context")
        elif is_minor and not family_present:
            score -= 0.2
            reasons.append("Unsupervised minor context")

        # Affect context (weight: 0.15)
        affect_state = realtime_context.affect_state
        if affect_state:
            arousal = affect_state.get("arousal", 0.0)
            if arousal > 0.8:
                score -= 0.1
                reasons.append("High arousal state detected")

        return max(0.0, min(1.0, score)), reasons

    def _apply_main_decision_tree(
        self,
        total_score: float,
        factor_scores: Dict[str, float],
        actor_attrs: Dict[str, Any],
        device_attrs: Dict[str, Any],
        env_attrs: Dict[str, Any],
    ) -> Tuple[Decision, Band]:
        """Apply main decision tree algorithm from contract."""

        # Emergency bypass check
        # (handled in emergency overrides)

        # Score-based decision thresholds
        if total_score >= 0.8:
            decision = "ALLOW"
            band = "GREEN"
        elif total_score >= 0.6:
            decision = "ALLOW"
            band = "AMBER"
        elif total_score >= 0.4:
            decision = "ALLOW_REDACTED"
            band = "AMBER"
        elif total_score >= 0.2:
            decision = "ALLOW_REDACTED"
            band = "RED"
        else:
            decision = "DENY"
            band = "RED"

        # Factor-specific overrides
        if factor_scores["security"] < 0.3:
            decision = "DENY" if decision == "ALLOW" else decision
            band = max(band, "RED", key=lambda x: self.band_hierarchy[x])

        if factor_scores["safety"] < 0.4:
            if decision == "ALLOW":
                decision = "ALLOW_REDACTED"
            band = max(band, "AMBER", key=lambda x: self.band_hierarchy[x])

        return decision, band

    def _apply_context_adaptations(
        self,
        decision: Decision,
        band: Band,
        env_attrs: Dict[str, Any],
        realtime_context: RealtimeContext,
        actor_attrs: Dict[str, Any],
    ) -> Tuple[Decision, Band, List[ObligationSpec], List[str]]:
        """Apply context adaptation rules from contract."""
        obligations = []
        adaptation_effects = []

        # Temporal adaptations
        temporal_context = env_attrs.get("temporal_context")
        time_of_day = env_attrs.get("time_of_day_hours", 12.0)

        if temporal_context == "sleep_time" or (time_of_day >= 22 or time_of_day <= 6):
            obligations.append(
                ObligationSpec(
                    name="time_limits",
                    description="Sleep time access restrictions",
                    parameters={
                        "max_duration_minutes": 30,
                        "warning_threshold_minutes": 20,
                    },
                )
            )
            adaptation_effects.append("sleep_time_restrictions")

        # Location adaptations
        geofence_zone = env_attrs.get("geofence_zone", "unknown")

        if geofence_zone == "public":
            obligations.append(
                ObligationSpec(
                    name="content_redaction",
                    description="Privacy mode for public locations",
                    parameters={
                        "redaction_level": "moderate",
                        "redaction_markers": False,
                    },
                )
            )
            adaptation_effects.append("public_location_privacy")

            # Escalate band for public locations
            band = max(band, "AMBER", key=lambda x: self.band_hierarchy[x])

        elif geofence_zone == "home":
            adaptation_effects.append("home_environment_relaxed")

        # Affect-based adaptations
        affect_state = realtime_context.affect_state
        if affect_state:
            arousal = affect_state.get("arousal", 0.0)
            safety_pressure = affect_state.get("safety_pressure", 0.0)

            if arousal > 0.7:
                obligations.append(
                    ObligationSpec(
                        name="content_filtering",
                        description="Calming content filter for high arousal",
                        parameters={
                            "filter_level": "moderate",
                            "categories": ["stimulating", "intense"],
                        },
                    )
                )
                adaptation_effects.append("high_arousal_filtering")

            if safety_pressure > 0.6:
                band = max(band, "RED", key=lambda x: self.band_hierarchy[x])
                obligations.append(
                    ObligationSpec(
                        name="enhanced_monitoring",
                        description="Enhanced monitoring for safety concerns",
                        parameters={
                            "monitoring_level": "comprehensive",
                            "duration_minutes": 60,
                        },
                    )
                )
                adaptation_effects.append("safety_pressure_monitoring")

        return decision, band, obligations, adaptation_effects

    def _apply_emergency_overrides(
        self,
        decision: Decision,
        band: Band,
        request_context: RequestContext,
        realtime_context: RealtimeContext,
        actor_attrs: Dict[str, Any],
    ) -> Tuple[Decision, Band, List[ObligationSpec]]:
        """Apply emergency and override logic."""
        obligations = []

        # Emergency bypass
        if request_context.urgency == "emergency":
            decision = "ALLOW"
            band = "RED"  # Emergency with enhanced monitoring
            obligations.append(
                ObligationSpec(
                    name="emergency_logging",
                    description="Enhanced logging for emergency access",
                    parameters={"log_level": "detailed", "alert_administrators": True},
                )
            )

            if actor_attrs.get("is_minor", False):
                obligations.append(
                    ObligationSpec(
                        name="adult_notification",
                        description="Immediate adult notification for minor emergency access",
                        parameters={
                            "notification_urgency": "immediate",
                            "notification_method": ["sms", "push"],
                        },
                    )
                )

        # Critical security alert override
        if realtime_context.security_alert_level == "critical":
            if decision == "ALLOW":
                decision = "ALLOW_REDACTED"
            band = max(band, "RED", key=lambda x: self.band_hierarchy[x])
            obligations.append(
                ObligationSpec(
                    name="enhanced_monitoring",
                    description="Critical security alert monitoring",
                    parameters={
                        "monitoring_level": "comprehensive",
                        "duration_minutes": 120,
                    },
                )
            )

        # Maintenance mode restrictions
        if realtime_context.maintenance_mode:
            if request_context.urgency not in ["high", "emergency"]:
                decision = "DENY"
                obligations.append(
                    ObligationSpec(
                        name="maintenance_notification",
                        description="System maintenance notification",
                        parameters={"retry_after_minutes": 30},
                    )
                )

        return decision, band, obligations

    def _calculate_confidence_score(
        self,
        total_score: float,
        factor_scores: Dict[str, float],
        reason_count: int,
        adaptation_count: int,
    ) -> float:
        """Calculate confidence score for the decision."""
        # Base confidence from score consistency
        score_variance = sum(
            (score - total_score) ** 2 for score in factor_scores.values()
        ) / len(factor_scores)
        consistency_score = max(0.0, 1.0 - score_variance * 2)

        # Information richness bonus
        info_bonus = min(0.2, (reason_count + adaptation_count) * 0.02)

        # Distance from decision boundaries penalty
        decision_boundaries = [0.2, 0.4, 0.6, 0.8]
        boundary_penalty = min(
            0.1, min(abs(total_score - boundary) for boundary in decision_boundaries)
        )

        confidence = consistency_score + info_bonus - boundary_penalty
        return max(0.0, min(1.0, confidence))

    def _build_decision_cache_key(
        self,
        request_context: RequestContext,
        historical_context: HistoricalContext,
        realtime_context: RealtimeContext,
        actor_attrs: Dict[str, Any],
        device_attrs: Dict[str, Any],
        env_attrs: Dict[str, Any],
    ) -> str:
        """Build cache key for context decision."""
        import hashlib

        # Create deterministic hash of all context factors
        combined_context = {
            "request": {
                "resource_type": request_context.resource_type,
                "action": request_context.action,
                "urgency": request_context.urgency,
                "purpose": request_context.purpose,
            },
            "actor_key_attrs": {
                "actor_id": actor_attrs.get("actor_id"),
                "is_minor": actor_attrs.get("is_minor"),
                "trust_level": actor_attrs.get("trust_level"),
            },
            "device_key_attrs": {
                "device_id": device_attrs.get("device_id"),
                "trust": device_attrs.get("trust"),
                "rooted_jailbroken": device_attrs.get("rooted_jailbroken"),
            },
            "env_key_attrs": {
                "geofence_zone": env_attrs.get("geofence_zone"),
                "temporal_context": env_attrs.get("temporal_context"),
                "family_present": env_attrs.get("family_present"),
            },
        }

        context_str = str(sorted(combined_context.items()))
        return hashlib.sha256(context_str.encode()).hexdigest()

    def _create_failsafe_evaluation(
        self, error: Exception, evaluation_time: float
    ) -> ContextEvaluation:
        """Create fail-safe evaluation for error conditions."""
        return ContextEvaluation(
            decision="DENY",
            band="RED",
            confidence_score=0.0,
            total_score=0.0,
            factor_scores={
                "security": 0.0,
                "safety": 0.0,
                "operational": 0.0,
                "contextual": 0.0,
            },
            obligations=[
                ObligationSpec(
                    name="error_logging",
                    description="Critical evaluation failure logging",
                    parameters={"error_details": str(error), "escalate": True},
                )
            ],
            reasons=[f"Critical evaluation failure: {str(error)}"],
            adaptation_effects=["emergency_fallback_mode"],
            evaluation_time_ms=evaluation_time,
        )

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics for monitoring."""
        total_decisions = self.cache_hits + self.cache_misses

        return PerformanceMetrics(
            total_evaluations=total_decisions,
            cache_hit_rate=(
                self.cache_hits / total_decisions if total_decisions > 0 else 0.0
            ),
            cache_hits=self.cache_hits,
            cache_misses=self.cache_misses,
            average_evaluation_time_ms=(
                sum(self.decision_times) / len(self.decision_times)
                if self.decision_times
                else 0.0
            ),
            p95_evaluation_time_ms=(
                sorted(self.decision_times)[int(len(self.decision_times) * 0.95)]
                if len(self.decision_times) >= 20
                else 0.0
            ),
            evaluation_count=len(self.decision_times),
        )

"""
Enhanced Attribute Engine for ABAC Implementation
Issue #27.1: Attribute-based policy evaluation

Contract-driven attribute evaluation system with multi-category support,
performance optimization, and comprehensive context integration.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)


class AttributeCategory(Enum):
    """Attribute categories as defined in attribute-evaluation.yaml contract."""

    ACTOR = "actor"
    DEVICE = "device"
    ENVIRONMENT = "environment"


class BandEscalationReason(Enum):
    """Reasons for band escalation as per contract."""

    MINOR_PROTECTION = "minor_protection"
    LOW_TRUST_DEVICE = "low_trust_device"
    HIGH_RISK_ENVIRONMENT = "high_risk_environment"
    DEVICE_SECURITY_CONCERN = "device_security_concern"
    TEMPORAL_RESTRICTION = "temporal_restriction"
    SAFETY_PIPELINE_ESCALATION = "safety_pipeline_escalation"


@dataclass
class AttributeEvaluationResult:
    """Result of attribute evaluation with contract compliance."""

    category: AttributeCategory
    attributes: Dict[str, Any]
    validation_errors: List[str] = field(default_factory=list)
    band_escalation: Optional[str] = None
    escalation_reason: Optional[BandEscalationReason] = None
    context_effects: List[str] = field(default_factory=list)
    cache_key: Optional[str] = None
    evaluation_time_ms: float = 0.0


@dataclass
class AttributeCombinationRule:
    """Contract-defined attribute combination rules."""

    name: str
    description: str
    condition: str  # Python expression to evaluate
    effects: List[str]
    priority: int = 1


class AttributeCache(Protocol):
    """Protocol for attribute caching backend."""

    def get(self, key: str) -> Optional[Any]:
        """Get cached attribute value."""
        ...

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set cached attribute value with TTL."""
        ...


class EnhancedAttributeEngine:
    """
    Enhanced Attribute Evaluation Engine implementing Issue #27.1 contract.

    Provides:
    - Multi-category attribute evaluation (actor/device/environment)
    - Contract-driven validation and processing
    - Band escalation logic with comprehensive rules
    - Performance-optimized caching (target: <100ms evaluation)
    - Context-aware attribute assessment
    """

    def __init__(
        self,
        cache_backend: Optional[AttributeCache] = None,
        enable_metrics: bool = True,
        contract_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize enhanced attribute engine.

        Args:
            cache_backend: Optional cache for attribute evaluation results
            enable_metrics: Enable performance metrics collection
            contract_config: Configuration loaded from attribute-evaluation.yaml
        """
        self.cache_backend = cache_backend
        self.enable_metrics = enable_metrics
        self.contract_config = contract_config or {}

        # Performance tracking
        self.evaluation_times: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0

        # Load contract configuration
        self._load_contract_configuration()

        # Initialize attribute combination rules
        self._initialize_combination_rules()

        logger.info("Enhanced Attribute Engine initialized with contract compliance")

    def _load_contract_configuration(self) -> None:
        """Load configuration from attribute-evaluation.yaml contract."""
        # Default contract configuration if not provided
        self.cache_ttl = self.contract_config.get("performance", {}).get(
            "cache_ttl", {}
        )
        self.cache_ttl.setdefault("attribute_evaluation", 300)  # 5 minutes
        self.cache_ttl.setdefault("context_assessment", 60)  # 1 minute
        self.cache_ttl.setdefault("band_calculation", 180)  # 3 minutes

        self.timeout_limits = self.contract_config.get("performance", {}).get(
            "timeout_limits", {}
        )
        self.timeout_limits.setdefault("attribute_collection", 1000)  # 1 second
        self.timeout_limits.setdefault("evaluation_processing", 2000)  # 2 seconds

        # Band hierarchy for escalation
        self.band_hierarchy = {"GREEN": 0, "AMBER": 1, "RED": 2, "BLACK": 3}

        logger.debug(f"Contract configuration loaded: cache_ttl={self.cache_ttl}")

    def _initialize_combination_rules(self) -> None:
        """Initialize attribute combination rules from contract."""
        self.combination_rules = [
            AttributeCombinationRule(
                name="minor_protection",
                description="Enhanced protection for minors",
                condition="actor.is_minor == True",
                effects=[
                    "require_family_present",
                    "restrict_to_green_band",
                    "enable_enhanced_monitoring",
                ],
                priority=1,
            ),
            AttributeCombinationRule(
                name="low_trust_device",
                description="Restrictions for low trust devices",
                condition="device.trust in ['untrusted', 'low']",
                effects=[
                    "require_additional_auth",
                    "limit_access_scope",
                    "enable_enhanced_logging",
                ],
                priority=2,
            ),
            AttributeCombinationRule(
                name="high_risk_environment",
                description="Restrictions for high-risk environments",
                condition="environment.safety_pressure > 0.7",
                effects=[
                    "escalate_to_amber_band",
                    "require_adult_supervision",
                    "enable_content_filtering",
                ],
                priority=1,
            ),
        ]

        # Sort by priority (highest first)
        self.combination_rules.sort(key=lambda rule: rule.priority)

    def evaluate_attributes(
        self,
        actor_attrs: Dict[str, Any],
        device_attrs: Dict[str, Any],
        env_attrs: Dict[str, Any],
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[AttributeEvaluationResult], Dict[str, Any]]:
        """
        Enhanced attribute evaluation implementing Issue #27.1 contract.

        Args:
            actor_attrs: Actor (user) attributes
            device_attrs: Device security and trust attributes
            env_attrs: Environmental and contextual attributes
            request_context: Additional request metadata

        Returns:
            Tuple of (evaluation_results, aggregated_context)
            evaluation_results: List of per-category evaluation results
            aggregated_context: Combined context for decision making
        """
        evaluation_start = time.time()

        try:
            # Check cache first
            cache_key = self._build_cache_key(actor_attrs, device_attrs, env_attrs)
            if self.cache_backend and (cached := self.cache_backend.get(cache_key)):
                self.cache_hits += 1
                logger.debug(f"Attribute evaluation cache hit: {cache_key[:16]}...")
                return cached

            self.cache_misses += 1

            # Evaluate each attribute category
            results = []

            # Actor attribute evaluation
            actor_result = self._evaluate_actor_attributes(actor_attrs)
            results.append(actor_result)

            # Device attribute evaluation
            device_result = self._evaluate_device_attributes(device_attrs)
            results.append(device_result)

            # Environment attribute evaluation
            env_result = self._evaluate_environment_attributes(env_attrs)
            results.append(env_result)

            # Apply attribute combination rules
            combination_effects = self._apply_combination_rules(
                actor_attrs, device_attrs, env_attrs, results
            )

            # Calculate band escalation
            final_band = self._calculate_band_escalation(results, combination_effects)

            # Build aggregated context
            aggregated_context = self._build_aggregated_context(
                results, combination_effects, final_band, request_context
            )

            # Cache successful evaluation
            if self.cache_backend:
                cache_value = (results, aggregated_context)
                ttl = self.cache_ttl["attribute_evaluation"]
                self.cache_backend.set(cache_key, cache_value, ttl)

            evaluation_time = (time.time() - evaluation_start) * 1000
            if self.enable_metrics:
                self.evaluation_times.append(evaluation_time)

            logger.debug(
                f"Attribute evaluation completed: {evaluation_time:.2f}ms, "
                f"band={final_band}, cache_key={cache_key[:16]}..."
            )

            return results, aggregated_context

        except Exception as e:
            evaluation_time = (time.time() - evaluation_start) * 1000
            logger.error(
                f"Attribute evaluation failed: {e}, time={evaluation_time:.2f}ms"
            )

            # Return fail-safe result
            return self._create_failsafe_result(e)

    def _evaluate_actor_attributes(
        self, attrs: Dict[str, Any]
    ) -> AttributeEvaluationResult:
        """Evaluate actor (user) attributes according to contract."""
        evaluation_start = time.time()
        validation_errors = []
        band_escalation = None
        escalation_reason = None
        context_effects = []

        # Validate required attributes
        if not attrs.get("actor_id"):
            validation_errors.append("actor_id is required")

        # Validate actor_id format (contract: ^[a-zA-Z0-9_-]+$)
        actor_id = attrs.get("actor_id", "")
        if actor_id and not all(c.isalnum() or c in "_-" for c in actor_id):
            validation_errors.append("actor_id format invalid")

        # Trust level validation
        trust_level = attrs.get("trust_level", "normal")
        if trust_level not in ["low", "normal", "high", "verified"]:
            validation_errors.append(f"Invalid trust_level: {trust_level}")

        # Assess minor protection requirements
        is_minor = attrs.get("is_minor", False)
        if is_minor:
            band_escalation = "AMBER"  # Minimum AMBER for minors
            escalation_reason = BandEscalationReason.MINOR_PROTECTION
            context_effects.extend(
                [
                    "require_family_present",
                    "enhanced_content_filtering",
                    "time_based_restrictions",
                ]
            )

        # Trust level escalation
        if trust_level == "low":
            band_escalation = (
                "AMBER"
                if not band_escalation
                else max(band_escalation, "AMBER", key=lambda x: self.band_hierarchy[x])
            )
            context_effects.append("enhanced_monitoring_required")

        # Relation-based context
        relation = attrs.get("relation")
        if relation in ["unknown", "untrusted"]:
            context_effects.append("limit_sensitive_access")

        evaluation_time = (time.time() - evaluation_start) * 1000

        return AttributeEvaluationResult(
            category=AttributeCategory.ACTOR,
            attributes=attrs,
            validation_errors=validation_errors,
            band_escalation=band_escalation,
            escalation_reason=escalation_reason,
            context_effects=context_effects,
            evaluation_time_ms=evaluation_time,
        )

    def _evaluate_device_attributes(
        self, attrs: Dict[str, Any]
    ) -> AttributeEvaluationResult:
        """Evaluate device attributes according to contract."""
        evaluation_start = time.time()
        validation_errors = []
        band_escalation = None
        escalation_reason = None
        context_effects = []

        # Validate required attributes
        if not attrs.get("device_id"):
            validation_errors.append("device_id is required")

        # Trust level assessment
        trust = attrs.get("trust", "trusted")
        if trust not in ["untrusted", "trusted", "hardened", "verified"]:
            validation_errors.append(f"Invalid device trust: {trust}")

        # Device security escalation
        if trust == "untrusted":
            band_escalation = "RED"
            escalation_reason = BandEscalationReason.LOW_TRUST_DEVICE
            context_effects.extend(
                [
                    "require_additional_authentication",
                    "limit_access_scope",
                    "enhanced_logging",
                ]
            )
        elif trust == "trusted":
            band_escalation = "AMBER"
            context_effects.append("standard_monitoring")

        # Rooted/jailbroken device escalation
        if attrs.get("rooted_jailbroken", False):
            band_escalation = "RED"
            escalation_reason = BandEscalationReason.DEVICE_SECURITY_CONCERN
            context_effects.extend(
                ["block_sensitive_operations", "enhanced_security_monitoring"]
            )

        # Network security assessment
        network_type = attrs.get("network_type", "trusted")
        if network_type in ["untrusted", "cellular"]:
            context_effects.append("network_security_monitoring")

        # Device status considerations
        if attrs.get("battery_low", False):
            context_effects.append("reduce_processing_intensive_operations")

        if attrs.get("screen_locked", False):
            context_effects.append("limit_notification_display")

        evaluation_time = (time.time() - evaluation_start) * 1000

        return AttributeEvaluationResult(
            category=AttributeCategory.DEVICE,
            attributes=attrs,
            validation_errors=validation_errors,
            band_escalation=band_escalation,
            escalation_reason=escalation_reason,
            context_effects=context_effects,
            evaluation_time_ms=evaluation_time,
        )

    def _evaluate_environment_attributes(
        self, attrs: Dict[str, Any]
    ) -> AttributeEvaluationResult:
        """Evaluate environmental attributes according to contract."""
        evaluation_start = time.time()
        validation_errors = []
        band_escalation = None
        escalation_reason = None
        context_effects = []

        # Time-based validation
        time_of_day = attrs.get("time_of_day_hours", 12.0)
        if not 0.0 <= time_of_day <= 24.0:
            validation_errors.append("time_of_day_hours must be 0.0-24.0")

        # Safety pressure assessment
        safety_pressure = attrs.get("safety_pressure", 0.0)
        if safety_pressure is not None:
            if not 0.0 <= safety_pressure <= 1.0:
                validation_errors.append("safety_pressure must be 0.0-1.0")
            elif safety_pressure > 0.7:
                band_escalation = "RED"
                escalation_reason = BandEscalationReason.HIGH_RISK_ENVIRONMENT
                context_effects.extend(
                    [
                        "enable_protective_measures",
                        "require_adult_supervision",
                        "content_filtering_strict",
                    ]
                )
            elif safety_pressure > 0.3:
                band_escalation = "AMBER"
                context_effects.append("enhanced_monitoring")

        # Arousal level assessment
        arousal = attrs.get("arousal", 0.0)
        if arousal is not None:
            if not 0.0 <= arousal <= 1.0:
                validation_errors.append("arousal must be 0.0-1.0")
            elif arousal > 0.8:
                context_effects.extend(
                    ["calming_content_recommendations", "reduce_stimulating_content"]
                )

        # Temporal context evaluation
        temporal_context = attrs.get("temporal_context")
        if temporal_context == "sleep_time":
            context_effects.extend(
                ["restrict_non_emergency_access", "enable_do_not_disturb"]
            )
        elif temporal_context == "work_hours":
            context_effects.extend(
                ["limit_personal_content", "prioritize_work_capabilities"]
            )

        # Geofence zone assessment
        geofence_zone = attrs.get("geofence_zone", "unknown")
        if geofence_zone == "public":
            context_effects.extend(
                ["restrict_sensitive_content", "privacy_mode_enabled"]
            )
        elif geofence_zone == "unknown":
            band_escalation = (
                "AMBER"
                if not band_escalation
                else max(band_escalation, "AMBER", key=lambda x: self.band_hierarchy[x])
            )
            context_effects.append("location_verification_required")

        # Family presence consideration
        family_present = attrs.get("family_present", True)
        if not family_present:
            context_effects.append("enhanced_minor_protection")

        evaluation_time = (time.time() - evaluation_start) * 1000

        return AttributeEvaluationResult(
            category=AttributeCategory.ENVIRONMENT,
            attributes=attrs,
            validation_errors=validation_errors,
            band_escalation=band_escalation,
            escalation_reason=escalation_reason,
            context_effects=context_effects,
            evaluation_time_ms=evaluation_time,
        )

    def _apply_combination_rules(
        self,
        actor_attrs: Dict[str, Any],
        device_attrs: Dict[str, Any],
        env_attrs: Dict[str, Any],
        results: List[AttributeEvaluationResult],
    ) -> List[str]:
        """Apply attribute combination rules from contract."""
        combination_effects = []

        # Create evaluation context for rule conditions
        context = {
            "actor": actor_attrs,
            "device": device_attrs,
            "environment": env_attrs,
        }

        for rule in self.combination_rules:
            try:
                # Safely evaluate rule condition
                if self._evaluate_rule_condition(rule.condition, context):
                    combination_effects.extend(rule.effects)
                    logger.debug(f"Applied combination rule: {rule.name}")
            except Exception as e:
                logger.warning(f"Failed to evaluate rule {rule.name}: {e}")

        return combination_effects

    def _evaluate_rule_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate rule condition with context."""
        try:
            # Create safe evaluation namespace with proper attribute access
            safe_globals = {
                "__builtins__": {},
                "actor": SimpleNamespace(**context.get("actor", {})),
                "device": SimpleNamespace(**context.get("device", {})),
                "environment": SimpleNamespace(**context.get("environment", {})),
            }

            # Evaluate condition
            return eval(condition, safe_globals)
        except Exception as e:
            logger.warning(f"Rule condition evaluation failed: {condition}, error: {e}")
            return False

    def _calculate_band_escalation(
        self, results: List[AttributeEvaluationResult], combination_effects: List[str]
    ) -> str:
        """Calculate final band escalation from all results."""
        escalations = []

        # Collect all band escalations
        for result in results:
            if result.band_escalation:
                escalations.append(result.band_escalation)

        # Check combination effects for band requirements
        if "escalate_to_amber_band" in combination_effects:
            escalations.append("AMBER")
        if "escalate_to_red_band" in combination_effects:
            escalations.append("RED")
        if "restrict_to_green_band" in combination_effects:
            escalations.append("GREEN")

        # Return highest escalation or GREEN default
        if not escalations:
            return "GREEN"

        return max(escalations, key=lambda x: self.band_hierarchy[x])

    def _build_aggregated_context(
        self,
        results: List[AttributeEvaluationResult],
        combination_effects: List[str],
        final_band: str,
        request_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build aggregated context for decision making."""
        # Collect all context effects
        all_effects = combination_effects.copy()
        for result in results:
            all_effects.extend(result.context_effects)

        # Collect all validation errors
        all_errors = []
        for result in results:
            all_errors.extend(result.validation_errors)

        # Calculate total evaluation time
        total_evaluation_time = sum(result.evaluation_time_ms for result in results)

        return {
            "final_band": final_band,
            "context_effects": list(set(all_effects)),  # Remove duplicates
            "validation_errors": all_errors,
            "evaluation_results": results,
            "performance_metrics": {
                "total_evaluation_time_ms": total_evaluation_time,
                "cache_hit_rate": (
                    self.cache_hits / (self.cache_hits + self.cache_misses)
                    if (self.cache_hits + self.cache_misses) > 0
                    else 0.0
                ),
                "average_evaluation_time_ms": (
                    sum(self.evaluation_times) / len(self.evaluation_times)
                    if self.evaluation_times
                    else 0.0
                ),
            },
            "request_context": request_context or {},
        }

    def _build_cache_key(
        self,
        actor_attrs: Dict[str, Any],
        device_attrs: Dict[str, Any],
        env_attrs: Dict[str, Any],
    ) -> str:
        """Build cache key for attribute evaluation."""
        # Create deterministic hash of all attributes
        combined_attrs = {
            "actor": actor_attrs,
            "device": device_attrs,
            "environment": env_attrs,
        }

        attrs_str = str(sorted(combined_attrs.items()))
        return hashlib.sha256(attrs_str.encode()).hexdigest()

    def _create_failsafe_result(
        self, error: Exception
    ) -> Tuple[List[AttributeEvaluationResult], Dict[str, Any]]:
        """Create fail-safe result for error conditions."""
        failsafe_result = AttributeEvaluationResult(
            category=AttributeCategory.ACTOR,  # Default category
            attributes={},
            validation_errors=[f"Evaluation failed: {str(error)}"],
            band_escalation="RED",  # Fail-safe to RED band
            escalation_reason=BandEscalationReason.SAFETY_PIPELINE_ESCALATION,
            context_effects=["emergency_fallback_mode"],
            evaluation_time_ms=0.0,
        )

        aggregated_context = {
            "final_band": "RED",
            "context_effects": ["emergency_fallback_mode", "enhanced_logging"],
            "validation_errors": [f"Critical evaluation failure: {str(error)}"],
            "evaluation_results": [failsafe_result],
            "performance_metrics": {
                "total_evaluation_time_ms": 0.0,
                "cache_hit_rate": 0.0,
                "average_evaluation_time_ms": 0.0,
            },
            "request_context": {},
        }

        return [failsafe_result], aggregated_context

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring."""
        total_evaluations = self.cache_hits + self.cache_misses

        return {
            "total_evaluations": total_evaluations,
            "cache_hit_rate": (
                self.cache_hits / total_evaluations if total_evaluations > 0 else 0.0
            ),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "average_evaluation_time_ms": (
                sum(self.evaluation_times) / len(self.evaluation_times)
                if self.evaluation_times
                else 0.0
            ),
            "p95_evaluation_time_ms": (
                sorted(self.evaluation_times)[int(len(self.evaluation_times) * 0.95)]
                if len(self.evaluation_times) >= 20
                else 0.0
            ),
            "evaluation_count": len(self.evaluation_times),
        }

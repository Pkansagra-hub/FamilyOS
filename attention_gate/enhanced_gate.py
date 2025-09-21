"""
Enhanced Attention Gate with Complete Policy Integration and Cognitive Load Balancing
====================================================================================

This module provides advanced attention gate functionality with comprehensive
policy integration, cognitive load awareness, and adaptive decision-making
capabilities for optimal system performance and compliance.

**Key Enhancements:**
- Complete policy framework integration with real-time evaluation
- Cognitive load-aware admission control and backpressure management
- Advanced decision tracking and learning integration hooks
- Real-time performance monitoring and adaptive threshold adjustment
- Comprehensive observability and audit trail capabilities

**Brain-Inspired Features:**
- Thalamic relay patterns for selective attention and information filtering
- Adaptive thresholds based on cognitive load and system performance
- Homeostatic regulation for stable processing capacity management
- Multi-factor decision-making with explainable reasoning paths

The enhanced gate provides production-ready attention control with enterprise-grade
policy compliance and adaptive performance optimization.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from observability.logging import get_json_logger
from observability.trace import start_span
from policy.decision import PolicyService

from .gate_service import AttentionGate as BaseAttentionGate
from .types import GateAction, GateDecision, GateRequest, GateResponse

logger = get_json_logger(__name__)


@dataclass
class CognitiveLoadMetrics:
    """Metrics for cognitive load assessment."""

    current_load: float = 0.0
    attention_pressure: float = 0.0
    processing_capacity: float = 1.0
    queue_depth: int = 0
    decision_latency_ms: float = 0.0
    error_rate: float = 0.0

    def is_overloaded(self) -> bool:
        """Check if system is cognitively overloaded."""
        return (
            self.current_load > 0.8
            or self.attention_pressure > 0.85
            or self.queue_depth > 100
            or self.decision_latency_ms > 200.0
            or self.error_rate > 0.1
        )

    def get_load_level(self) -> str:
        """Get categorical load level."""
        if self.current_load < 0.3:
            return "low"
        elif self.current_load < 0.6:
            return "moderate"
        elif self.current_load < 0.8:
            return "high"
        else:
            return "critical"


@dataclass
class PolicyEvaluationResult:
    """Enhanced policy evaluation result with cognitive context."""

    allowed: bool
    reasons: List[str]
    obligations: List[str]
    restrictions: Dict[str, Any]
    confidence: float
    evaluation_time_ms: float
    policy_version: str
    risk_score: float = 0.0

    def requires_enhanced_monitoring(self) -> bool:
        """Check if request requires enhanced monitoring."""
        return (
            self.risk_score > 0.7
            or "high_risk" in self.reasons
            or "audit_required" in self.obligations
        )


@dataclass
class AdaptiveThresholds:
    """Adaptive thresholds for cognitive load-aware decisions."""

    admit_threshold: float = 0.6
    boost_threshold: float = 0.8
    drop_threshold: float = 0.2
    defer_threshold: float = 0.4

    # Adaptation parameters
    adaptation_rate: float = 0.05
    load_sensitivity: float = 0.2
    performance_window_size: int = 20

    def adapt_to_load(
        self, cognitive_load: float, performance_metrics: Dict[str, Any]
    ) -> None:
        """Adapt thresholds based on cognitive load and performance."""

        # Increase thresholds under high load (be more selective)
        if cognitive_load > 0.8:
            load_adjustment = (cognitive_load - 0.8) * self.load_sensitivity
            self.admit_threshold = min(0.9, self.admit_threshold + load_adjustment)
            self.boost_threshold = min(0.95, self.boost_threshold + load_adjustment)

        # Decrease thresholds under low load (be more permissive)
        elif cognitive_load < 0.3:
            load_adjustment = (0.3 - cognitive_load) * self.load_sensitivity * 0.5
            self.admit_threshold = max(0.4, self.admit_threshold - load_adjustment)
            self.boost_threshold = max(0.6, self.boost_threshold - load_adjustment)

        # Adjust based on error rate
        error_rate = performance_metrics.get("error_rate", 0.0)
        if error_rate > 0.05:  # More than 5% error rate
            # Increase thresholds to reduce load
            error_adjustment = error_rate * 0.5
            self.admit_threshold = min(0.9, self.admit_threshold + error_adjustment)

        # Adjust based on latency
        avg_latency = performance_metrics.get("avg_latency_ms", 0.0)
        if avg_latency > 100.0:  # More than 100ms average
            latency_adjustment = (avg_latency - 100.0) / 1000.0  # Normalize
            self.admit_threshold = min(0.9, self.admit_threshold + latency_adjustment)


class EnhancedAttentionGate(BaseAttentionGate):
    """
    Enhanced attention gate with comprehensive policy integration and cognitive load balancing.

    Extends the base attention gate with:
    - Real-time policy evaluation and compliance
    - Cognitive load-aware decision making
    - Adaptive threshold management
    - Enhanced observability and audit trails
    - Learning integration for continuous improvement
    """

    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path)

        # Enhanced components
        self.policy_service = PolicyService()
        self.cognitive_load_metrics = CognitiveLoadMetrics()
        self.adaptive_thresholds = AdaptiveThresholds()

        # Enhanced tracking
        self.policy_evaluations: deque = deque(maxlen=1000)
        self.cognitive_load_history: deque = deque(maxlen=200)
        self.performance_metrics: deque = deque(maxlen=100)

        # Real-time monitoring
        self.monitoring_enabled = True
        self.monitoring_task: Optional[asyncio.Task] = None

        # Adaptive learning
        self.learning_enabled = False
        self.adaptation_history: List[Dict[str, Any]] = []

        logger.info(
            "Enhanced Attention Gate initialized",
            extra={
                "policy_integration": True,
                "cognitive_load_awareness": True,
                "adaptive_thresholds": True,
                "monitoring_enabled": self.monitoring_enabled,
            },
        )

    async def start_monitoring(self) -> None:
        """Start real-time monitoring and adaptive adjustment."""
        if self.monitoring_task is not None:
            return

        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Enhanced attention gate monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop monitoring and adaptive adjustment."""
        if self.monitoring_task is not None:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None

        logger.info("Enhanced attention gate monitoring stopped")

    async def process_request_enhanced(self, request: GateRequest) -> GateResponse:
        """
        Enhanced request processing with policy integration and cognitive load awareness.

        Args:
            request: Gate request to process

        Returns:
            Enhanced gate response with comprehensive decision context
        """
        with start_span("attention_gate.process_enhanced") as span:
            start_time = time.perf_counter()

            try:
                # Update cognitive load metrics
                await self._update_cognitive_load_metrics()

                # Stage 1: Enhanced Policy Evaluation
                policy_result = await self._evaluate_policy_comprehensive(request)

                if not policy_result.allowed:
                    response = await self._create_policy_denied_response(
                        request, policy_result
                    )
                    await self._record_enhanced_decision(
                        request, response, policy_result, start_time
                    )
                    return response

                # Stage 2: Cognitive Load Assessment
                load_impact = await self._assess_cognitive_load_impact(request)

                # Stage 3: Adaptive Threshold Application
                await self._adapt_thresholds_if_needed()

                # Stage 4: Enhanced Salience Calculation
                salience_result = await self._calculate_enhanced_salience(
                    request, load_impact
                )

                # Stage 5: Cognitive Load-Aware Decision Making
                gate_decision = await self._make_enhanced_gate_decision(
                    request, salience_result, policy_result, load_impact
                )

                # Stage 6: Enhanced Response Creation
                response = await self._create_enhanced_response(
                    request, gate_decision, policy_result, salience_result, start_time
                )

                # Stage 7: Decision Recording and Learning
                await self._record_enhanced_decision(
                    request, response, policy_result, start_time
                )

                # Update performance metrics
                await self._update_performance_metrics(response, start_time)

                if span:
                    span.set_attribute("action", gate_decision.action.value)
                    span.set_attribute(
                        "cognitive_load", self.cognitive_load_metrics.current_load
                    )
                    span.set_attribute("policy_compliant", policy_result.allowed)
                    span.set_attribute("enhanced_processing", True)

                return response

            except Exception as e:
                logger.error(
                    "Enhanced request processing failed",
                    extra={
                        "request_id": request.request_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )

                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))

                # Return safe fallback response
                return await self._create_error_response_enhanced(request, e)

    async def _evaluate_policy_comprehensive(
        self, request: GateRequest
    ) -> PolicyEvaluationResult:
        """Comprehensive policy evaluation with enhanced context."""

        policy_start = time.perf_counter()

        try:
            # Create policy decision request
            policy_decision = await self.policy_service.evaluate_request(
                actor_id=request.actor.person_id,
                resource_type="attention_gate",
                action="admit",
                resource_attributes={
                    "space_id": request.space_id,
                    "band": request.policy.band,
                    "content_type": (
                        getattr(request.content, "type", None)
                        if request.content
                        else None
                    ),
                },
                context={
                    "cognitive_load": self.cognitive_load_metrics.current_load,
                    "queue_depth": self.cognitive_load_metrics.queue_depth,
                    "request_source": getattr(request, "source", "unknown"),
                },
            )

            # Calculate risk score based on policy factors
            risk_score = self._calculate_request_risk_score(request, policy_decision)

            evaluation_time = (time.perf_counter() - policy_start) * 1000

            result = PolicyEvaluationResult(
                allowed=policy_decision.decision == "PERMIT",
                reasons=policy_decision.reasons or [],
                obligations=policy_decision.obligations or [],
                restrictions=policy_decision.advice or {},
                confidence=getattr(policy_decision, "confidence", 1.0),
                evaluation_time_ms=evaluation_time,
                policy_version=getattr(policy_decision, "version", "1.0"),
                risk_score=risk_score,
            )

            # Record policy evaluation
            self.policy_evaluations.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request.request_id,
                    "allowed": result.allowed,
                    "risk_score": risk_score,
                    "evaluation_time_ms": evaluation_time,
                }
            )

            return result

        except Exception as e:
            logger.error(
                "Policy evaluation failed",
                extra={
                    "request_id": request.request_id,
                    "error": str(e),
                },
                exc_info=True,
            )

            # Return safe default (deny with audit)
            return PolicyEvaluationResult(
                allowed=False,
                reasons=["policy_evaluation_error"],
                obligations=["audit_policy_error"],
                restrictions={},
                confidence=1.0,
                evaluation_time_ms=(time.perf_counter() - policy_start) * 1000,
                policy_version="error",
                risk_score=1.0,
            )

    async def _assess_cognitive_load_impact(
        self, request: GateRequest
    ) -> Dict[str, Any]:
        """Assess cognitive load impact of processing this request."""

        # Estimate processing complexity
        complexity_factors = {
            "content_size": (
                len(getattr(request.content, "text", "")) if request.content else 0
            ),
            "intent_complexity": self._estimate_intent_complexity(request),
            "policy_complexity": len(getattr(request.policy, "obligations", [])),
            "space_complexity": 1 if request.space_id.startswith("shared:") else 0,
        }

        # Calculate estimated load impact
        base_impact = 0.1  # Base processing cost
        content_impact = min(
            0.3, complexity_factors["content_size"] / 10000
        )  # Normalize content size
        intent_impact = complexity_factors["intent_complexity"] * 0.2
        policy_impact = complexity_factors["policy_complexity"] * 0.05
        space_impact = complexity_factors["space_complexity"] * 0.1

        total_impact = (
            base_impact + content_impact + intent_impact + policy_impact + space_impact
        )

        return {
            "estimated_load_impact": min(1.0, total_impact),
            "complexity_factors": complexity_factors,
            "processing_time_estimate_ms": total_impact * 100,  # Rough estimate
        }

    async def _adapt_thresholds_if_needed(self) -> None:
        """Adapt decision thresholds based on current system state."""

        # Get recent performance metrics
        if len(self.performance_metrics) < 10:
            return

        recent_metrics = list(self.performance_metrics)[-10:]

        # Calculate performance summary
        avg_latency = sum(m.get("latency_ms", 0) for m in recent_metrics) / len(
            recent_metrics
        )
        error_rate = sum(1 for m in recent_metrics if m.get("error", False)) / len(
            recent_metrics
        )

        performance_summary = {
            "avg_latency_ms": avg_latency,
            "error_rate": error_rate,
            "queue_depth": self.cognitive_load_metrics.queue_depth,
        }

        # Adapt thresholds
        old_thresholds = {
            "admit": self.adaptive_thresholds.admit_threshold,
            "boost": self.adaptive_thresholds.boost_threshold,
        }

        self.adaptive_thresholds.adapt_to_load(
            self.cognitive_load_metrics.current_load, performance_summary
        )

        # Log significant changes
        if (
            abs(old_thresholds["admit"] - self.adaptive_thresholds.admit_threshold)
            > 0.05
        ):
            logger.info(
                "Adaptive thresholds adjusted",
                extra={
                    "old_admit": old_thresholds["admit"],
                    "new_admit": self.adaptive_thresholds.admit_threshold,
                    "cognitive_load": self.cognitive_load_metrics.current_load,
                    "performance": performance_summary,
                },
            )

    async def _calculate_enhanced_salience(
        self, request: GateRequest, load_impact: Dict[str, Any]
    ) -> Any:
        """Calculate salience with cognitive load considerations."""

        # Get base salience
        base_salience = self.salience_calculator.calculate_salience(request)

        # Apply cognitive load adjustments
        load_adjustment = 0.0
        current_load = self.cognitive_load_metrics.current_load

        # Reduce salience under high load for non-critical items
        if current_load > 0.7:
            priority_protection = getattr(request, "priority", 1.0)
            if priority_protection < 0.8:  # Not high priority
                load_penalty = (current_load - 0.7) * 0.3  # Up to 9% penalty
                load_adjustment -= load_penalty

        # Boost salience under low load
        elif current_load < 0.3:
            load_bonus = (0.3 - current_load) * 0.1  # Up to 3% bonus
            load_adjustment += load_bonus

        # Apply processing cost consideration
        processing_cost = load_impact.get("estimated_load_impact", 0.0)
        if processing_cost > 0.5:  # High processing cost
            cost_penalty = (processing_cost - 0.5) * 0.2
            load_adjustment -= cost_penalty

        # Create enhanced salience result
        adjusted_score = max(
            0.0, min(1.0, base_salience.calibrated_priority + load_adjustment)
        )

        # Update salience result with cognitive load context
        base_salience.calibrated_priority = adjusted_score
        base_salience.features.raw_features["cognitive_load_adjustment"] = (
            load_adjustment
        )
        base_salience.features.raw_features["processing_cost"] = processing_cost

        return base_salience

    async def _make_enhanced_gate_decision(
        self,
        request: GateRequest,
        salience_result: Any,
        policy_result: PolicyEvaluationResult,
        load_impact: Dict[str, Any],
    ) -> GateDecision:
        """Make gate decision with cognitive load awareness."""

        priority = salience_result.calibrated_priority
        current_load = self.cognitive_load_metrics.current_load
        reasons = []

        # Use adaptive thresholds
        admit_threshold = self.adaptive_thresholds.admit_threshold
        boost_threshold = self.adaptive_thresholds.boost_threshold
        drop_threshold = self.adaptive_thresholds.drop_threshold

        # Apply load-aware threshold adjustments
        if current_load > 0.8:
            # Under high load, increase thresholds further
            dynamic_admit = min(0.9, admit_threshold + 0.1)
            dynamic_boost = min(0.95, boost_threshold + 0.05)
            reasons.append("high_cognitive_load_threshold_adjustment")
        else:
            dynamic_admit = admit_threshold
            dynamic_boost = boost_threshold

        # Decision logic with enhanced reasoning
        if priority < drop_threshold:
            reasons.extend(
                ["priority_below_drop_threshold", "cognitive_load_protection"]
            )
            action = GateAction.DROP

        elif priority >= dynamic_boost:
            reasons.append("priority_exceeds_boost_threshold")

            # Additional boost conditions with load awareness
            if current_load < 0.5:  # Only boost under moderate load
                if policy_result.requires_enhanced_monitoring():
                    reasons.append("high_risk_requires_boost")
                if getattr(request, "urgency", 0.0) > 0.8:
                    reasons.append("high_urgency_boost")
                action = GateAction.BOOST
            else:
                # Downgrade to admit under high load
                reasons.append("load_limited_boost_to_admit")
                action = GateAction.ADMIT

        elif priority >= dynamic_admit:
            reasons.append("priority_exceeds_admit_threshold")

            # Load-aware admission checks
            if current_load > 0.9:
                # Very high load - consider defer instead
                reasons.append("high_load_defer_consideration")
                action = GateAction.DEFER
            else:
                action = GateAction.ADMIT

        else:
            reasons.append("priority_below_admit_threshold")

            # Calculate defer TTL based on load and priority
            base_ttl = 30000  # 30 seconds
            load_multiplier = 1.0 + current_load  # Longer defer under high load
            priority_multiplier = max(0.5, priority)  # Higher priority = shorter defer
            ttl_ms = int(base_ttl * load_multiplier / priority_multiplier)

            reasons.append(f"deferred_for_{ttl_ms}ms")
            action = GateAction.DEFER

        # Create enhanced decision
        decision = GateDecision(
            action=action,
            priority=priority,
            reasons=reasons,
            obligations=policy_result.obligations,
            confidence=salience_result.confidence,
            uncertainty=getattr(salience_result, "uncertainty", 0.0),
            ttl_ms=ttl_ms if action == GateAction.DEFER else None,
        )

        # Add cognitive load context to decision
        if hasattr(decision, "metadata"):
            decision.metadata.update(
                {
                    "cognitive_load": current_load,
                    "adaptive_thresholds": {
                        "admit": dynamic_admit,
                        "boost": dynamic_boost,
                    },
                    "load_impact": load_impact,
                }
            )

        return decision

    async def _create_enhanced_response(
        self,
        request: GateRequest,
        gate_decision: GateDecision,
        policy_result: PolicyEvaluationResult,
        salience_result: Any,
        start_time: float,
    ) -> GateResponse:
        """Create enhanced response with comprehensive context."""

        # Create base response using parent method
        base_response = self._create_response_from_decision(
            request, gate_decision, salience_result
        )

        # Enhance with policy and cognitive load context
        if hasattr(base_response, "policy_context"):
            base_response.policy_context = {
                "evaluation_time_ms": policy_result.evaluation_time_ms,
                "risk_score": policy_result.risk_score,
                "restrictions": policy_result.restrictions,
                "policy_version": policy_result.policy_version,
            }

        if hasattr(base_response, "cognitive_context"):
            base_response.cognitive_context = {
                "load_level": self.cognitive_load_metrics.get_load_level(),
                "current_load": self.cognitive_load_metrics.current_load,
                "queue_depth": self.cognitive_load_metrics.queue_depth,
                "adaptive_thresholds": {
                    "admit": self.adaptive_thresholds.admit_threshold,
                    "boost": self.adaptive_thresholds.boost_threshold,
                },
            }

        return base_response

    async def _record_enhanced_decision(
        self,
        request: GateRequest,
        response: GateResponse,
        policy_result: PolicyEvaluationResult,
        start_time: float,
    ) -> None:
        """Record enhanced decision with comprehensive context."""

        # Record base decision
        super()._record_decision(request, response, None)

        # Record enhanced context
        decision_record = {
            "request_id": request.request_id,
            "timestamp": datetime.now().isoformat(),
            "action": response.gate_decision.action.value,
            "priority": response.gate_decision.priority,
            "cognitive_load": self.cognitive_load_metrics.current_load,
            "policy_risk_score": policy_result.risk_score,
            "policy_evaluation_time_ms": policy_result.evaluation_time_ms,
            "total_processing_time_ms": (time.perf_counter() - start_time) * 1000,
            "adaptive_thresholds": {
                "admit": self.adaptive_thresholds.admit_threshold,
                "boost": self.adaptive_thresholds.boost_threshold,
            },
            "obligations_count": len(policy_result.obligations),
            "enhanced_processing": True,
        }

        # Add to enhanced decision history
        if not hasattr(self, "enhanced_decision_history"):
            self.enhanced_decision_history = deque(maxlen=1000)

        self.enhanced_decision_history.append(decision_record)

    async def _update_cognitive_load_metrics(self) -> None:
        """Update current cognitive load metrics."""

        # Calculate current metrics
        recent_latencies = [
            m.get("latency_ms", 0) for m in list(self.performance_metrics)[-20:]
        ]
        avg_latency = (
            sum(recent_latencies) / len(recent_latencies) if recent_latencies else 0.0
        )

        recent_errors = [
            m.get("error", False) for m in list(self.performance_metrics)[-50:]
        ]
        error_rate = sum(recent_errors) / len(recent_errors) if recent_errors else 0.0

        # Update cognitive load metrics
        self.cognitive_load_metrics.decision_latency_ms = avg_latency
        self.cognitive_load_metrics.error_rate = error_rate

        # Calculate overall cognitive load
        load_factors = [
            min(1.0, avg_latency / 200.0),  # Latency factor
            error_rate * 5.0,  # Error factor (amplified)
            min(1.0, self.cognitive_load_metrics.queue_depth / 100.0),  # Queue factor
            min(1.0, len(self.decision_history) / 1000.0),  # Activity factor
        ]

        self.cognitive_load_metrics.current_load = min(
            1.0, sum(load_factors) / len(load_factors)
        )

        # Update attention pressure (queue-specific metric)
        self.cognitive_load_metrics.attention_pressure = min(
            1.0, self.cognitive_load_metrics.queue_depth / 80.0
        )

        # Record cognitive load history
        self.cognitive_load_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "current_load": self.cognitive_load_metrics.current_load,
                "attention_pressure": self.cognitive_load_metrics.attention_pressure,
                "queue_depth": self.cognitive_load_metrics.queue_depth,
                "avg_latency_ms": avg_latency,
                "error_rate": error_rate,
            }
        )

    async def _update_performance_metrics(
        self, response: GateResponse, start_time: float
    ) -> None:
        """Update performance tracking metrics."""

        processing_time = (time.perf_counter() - start_time) * 1000

        metric_record = {
            "timestamp": datetime.now().isoformat(),
            "latency_ms": processing_time,
            "action": response.gate_decision.action.value,
            "priority": response.gate_decision.priority,
            "error": False,  # No error if we got here
            "cognitive_load": self.cognitive_load_metrics.current_load,
        }

        self.performance_metrics.append(metric_record)

    async def _monitoring_loop(self) -> None:
        """Background monitoring and adaptive adjustment loop."""

        while self.monitoring_enabled:
            try:
                await asyncio.sleep(30)  # Monitor every 30 seconds

                # Update cognitive load metrics
                await self._update_cognitive_load_metrics()

                # Adapt thresholds if needed
                await self._adapt_thresholds_if_needed()

                # Check for alerts
                await self._check_cognitive_load_alerts()

                # Log monitoring status
                logger.debug(
                    "Attention gate monitoring cycle",
                    extra={
                        "cognitive_load": self.cognitive_load_metrics.current_load,
                        "load_level": self.cognitive_load_metrics.get_load_level(),
                        "queue_depth": self.cognitive_load_metrics.queue_depth,
                        "attention_pressure": self.cognitive_load_metrics.attention_pressure,
                        "adaptive_admit_threshold": self.adaptive_thresholds.admit_threshold,
                    },
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Monitoring loop error", extra={"error": str(e)}, exc_info=True
                )
                await asyncio.sleep(60)  # Wait longer on error

    async def _check_cognitive_load_alerts(self) -> None:
        """Check for cognitive load alerts and trigger responses."""

        if self.cognitive_load_metrics.is_overloaded():
            alert_data = {
                "alert_type": "cognitive_overload",
                "current_load": self.cognitive_load_metrics.current_load,
                "attention_pressure": self.cognitive_load_metrics.attention_pressure,
                "queue_depth": self.cognitive_load_metrics.queue_depth,
                "recommendations": self._generate_load_reduction_recommendations(),
            }

            logger.warning("Cognitive load alert triggered", extra=alert_data)

            # TODO: Trigger load reduction mechanisms
            # await self._trigger_load_reduction()

    def _generate_load_reduction_recommendations(self) -> List[str]:
        """Generate recommendations for reducing cognitive load."""

        recommendations = []

        if self.cognitive_load_metrics.queue_depth > 100:
            recommendations.append("reduce_queue_depth")
            recommendations.append("increase_processing_capacity")

        if self.cognitive_load_metrics.decision_latency_ms > 200:
            recommendations.append("optimize_decision_processing")
            recommendations.append("implement_fast_path_routing")

        if self.cognitive_load_metrics.error_rate > 0.1:
            recommendations.append("investigate_error_sources")
            recommendations.append("implement_error_recovery")

        if self.cognitive_load_metrics.current_load > 0.9:
            recommendations.append("implement_emergency_load_shedding")
            recommendations.append("increase_drop_thresholds")

        return recommendations

    def _estimate_intent_complexity(self, request: GateRequest) -> float:
        """Estimate complexity of intent processing."""

        # Simple heuristic based on request characteristics
        complexity = 0.0

        # Content complexity
        if request.content:
            content_length = len(getattr(request.content, "text", ""))
            complexity += min(0.5, content_length / 5000)  # Normalize to 5KB

        # Policy complexity
        if request.policy:
            obligations_count = len(getattr(request.policy, "obligations", []))
            complexity += min(0.3, obligations_count * 0.1)

        # Context complexity
        if hasattr(request, "context") and request.context:
            context_items = len(request.context)
            complexity += min(0.2, context_items * 0.05)

        return min(1.0, complexity)

    def _calculate_request_risk_score(
        self, request: GateRequest, policy_decision: Any
    ) -> float:
        """Calculate risk score for the request."""

        risk_factors = []

        # Band-based risk
        band_risk_map = {"BLACK": 1.0, "RED": 0.8, "AMBER": 0.4, "GREEN": 0.1}
        band_risk = band_risk_map.get(request.policy.band, 0.5)
        risk_factors.append(band_risk)

        # Policy decision risk
        if policy_decision.decision == "DENY":
            risk_factors.append(1.0)
        elif len(getattr(policy_decision, "obligations", [])) > 2:
            risk_factors.append(0.6)
        else:
            risk_factors.append(0.2)

        # Content risk (simple heuristic)
        if request.content:
            content_text = getattr(request.content, "text", "").lower()
            risky_keywords = ["password", "secret", "private", "confidential", "ssn"]
            if any(keyword in content_text for keyword in risky_keywords):
                risk_factors.append(0.8)
            else:
                risk_factors.append(0.1)

        # Calculate average risk score
        return sum(risk_factors) / len(risk_factors) if risk_factors else 0.5

    def _create_response_from_decision(
        self, request: GateRequest, decision: GateDecision, salience_result: Any
    ) -> GateResponse:
        """Create response from decision (placeholder for base class method)."""
        # This would call the parent class method or implement response creation
        return GateResponse(
            gate_decision=decision,
            derived_intents=[],
            routing=None,
            trace=None,
            timestamp=datetime.now(),
        )

    async def _create_policy_denied_response(
        self, request: GateRequest, policy_result: PolicyEvaluationResult
    ) -> GateResponse:
        """Create response for policy-denied requests."""

        decision = GateDecision(
            action=GateAction.DROP,
            priority=0.0,
            reasons=["policy_denied"] + policy_result.reasons,
            obligations=policy_result.obligations,
            confidence=policy_result.confidence,
        )

        return await self._create_enhanced_response(
            request, decision, policy_result, None, time.perf_counter()
        )

    async def _create_error_response_enhanced(
        self, request: GateRequest, error: Exception
    ) -> GateResponse:
        """Create enhanced error response."""

        decision = GateDecision(
            action=GateAction.DROP,
            priority=0.0,
            reasons=["processing_error", str(error)],
            obligations=["audit_processing_error"],
            confidence=1.0,
        )

        return GateResponse(
            gate_decision=decision,
            derived_intents=[],
            routing=None,
            trace=None,
            timestamp=datetime.now(),
        )

    async def get_enhanced_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics including cognitive load."""

        base_metrics = self.get_performance_metrics()

        # Enhanced metrics
        enhanced_metrics = {
            **base_metrics,
            "cognitive_load": {
                "current_load": self.cognitive_load_metrics.current_load,
                "load_level": self.cognitive_load_metrics.get_load_level(),
                "attention_pressure": self.cognitive_load_metrics.attention_pressure,
                "queue_depth": self.cognitive_load_metrics.queue_depth,
                "processing_capacity": self.cognitive_load_metrics.processing_capacity,
            },
            "adaptive_thresholds": {
                "admit": self.adaptive_thresholds.admit_threshold,
                "boost": self.adaptive_thresholds.boost_threshold,
                "drop": self.adaptive_thresholds.drop_threshold,
                "defer": self.adaptive_thresholds.defer_threshold,
            },
            "policy_metrics": {
                "evaluations_count": len(self.policy_evaluations),
                "average_evaluation_time_ms": self._calculate_avg_policy_evaluation_time(),
                "average_risk_score": self._calculate_avg_risk_score(),
            },
            "enhancement_features": {
                "policy_integration": True,
                "cognitive_load_awareness": True,
                "adaptive_thresholds": True,
                "monitoring_enabled": self.monitoring_enabled,
                "learning_enabled": self.learning_enabled,
            },
        }

        return enhanced_metrics

    def _calculate_avg_policy_evaluation_time(self) -> float:
        """Calculate average policy evaluation time."""
        recent_evaluations = list(self.policy_evaluations)[-50:]
        if not recent_evaluations:
            return 0.0

        total_time = sum(eval["evaluation_time_ms"] for eval in recent_evaluations)
        return total_time / len(recent_evaluations)

    def _calculate_avg_risk_score(self) -> float:
        """Calculate average risk score."""
        recent_evaluations = list(self.policy_evaluations)[-50:]
        if not recent_evaluations:
            return 0.0

        total_risk = sum(eval["risk_score"] for eval in recent_evaluations)
        return total_risk / len(recent_evaluations)

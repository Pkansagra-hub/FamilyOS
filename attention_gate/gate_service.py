"""
Attention Gate Service - Main Admission Control Logic

Future-ready architecture with pluggable components:
- Phase 1: Rule-based decisions (production-safe)
- Phase 2: Light calibration and A/B testing
- Phase 3: Learning integration
- Phase 4: Neural models with safety guardrails

This is the smart-path filter that decides ADMIT/DEFER/BOOST/DROP
for events that didn't qualify for fast-path routing.
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .backpressure import BackpressureManager
from .config import get_config
from .intent_rules import IntentDeriver
from .policy_bridge import PolicyBridge
from .salience import SalienceCalculator, SalienceResult
from .trace import DecisionTracer
from .types import (
    AttentionGateError,
    BackpressureError,
    DerivedIntent,
    GateAction,
    GateDecision,
    GateDecisionTrace,
    GateRequest,
    GateResponse,
    IntentType,
    PolicyViolationError,
    RoutingInfo,
)


class AttentionGate:
    """
    Main attention gate service implementing thalamus-inspired admission control.

    Processes requests that require smart-path analysis and makes 4-action decisions:
    - ADMIT: Process immediately with normal priority
    - BOOST: Process immediately with elevated priority
    - DEFER: Queue for later processing (backpressure)
    - DROP: Reject with audit trail (policy/resource limits)

    Designed for learning integration while maintaining production safety.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path

        # Core components (pluggable for testing and learning)
        self.salience_calculator = SalienceCalculator(config_path)
        self.intent_deriver = IntentDeriver(config_path)
        self.backpressure_manager = BackpressureManager(config_path)
        self.policy_bridge = PolicyBridge(config_path)
        self.decision_tracer = DecisionTracer(config_path)

        # Learning integration state
        self.decision_history: List[Dict[str, Any]] = []
        self.adaptation_enabled = False

        # Performance tracking
        self.request_count = 0
        self.decision_latencies: List[float] = []

    def process_request(self, request: GateRequest) -> GateResponse:
        """
        Process attention gate request with full decision pipeline.

        Returns complete response with decision, derived intents, routing,
        and trace information for explainability and learning.
        """
        start_time = time.perf_counter()

        try:
            # Track request
            self.request_count += 1

            # Stage 1: Policy & Schema Validation (hard gates)
            self._validate_request(request)
            policy_result = self.policy_bridge.evaluate_policy(request)

            if policy_result.should_drop:
                return self._create_drop_response(request, policy_result.reasons)

            # Stage 2: Backpressure Check
            backpressure_result = self.backpressure_manager.check_capacity(request)

            if backpressure_result.should_defer:
                return self._create_defer_response(request, backpressure_result.reasons)

            if backpressure_result.should_drop:
                return self._create_drop_response(request, backpressure_result.reasons)

            # Stage 3: Intent Derivation (when missing/ambiguous)
            derived_intents = self.intent_deriver.derive_intents(request)

            # Stage 4: Salience Scoring & Cost Analysis
            salience_result = self.salience_calculator.calculate_salience(request)

            # Stage 5: Action Selection (core decision logic)
            gate_decision = self._make_gate_decision(
                request, salience_result, policy_result, backpressure_result
            )

            # Stage 6: Routing Configuration
            routing = self._create_routing_info(request, derived_intents, gate_decision)

            # Stage 7: Decision Tracing
            trace = self._create_decision_trace(
                request,
                salience_result,
                gate_decision,
                time.perf_counter() - start_time,
            )

            # Create response
            response = GateResponse(
                gate_decision=gate_decision,
                derived_intents=derived_intents,
                routing=routing,
                trace=trace,
                timestamp=datetime.now(),
            )

            # Record for learning integration
            self._record_decision(request, response, salience_result)

            # Update performance metrics
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            self.decision_latencies.append(execution_time_ms)

            return response

        except PolicyViolationError as e:
            return self._create_error_response(request, "POLICY_VIOLATION", str(e))
        except BackpressureError as e:
            return self._create_error_response(request, "BACKPRESSURE", str(e))
        except Exception as e:
            return self._create_error_response(request, "INTERNAL_ERROR", str(e))

    def _validate_request(self, request: GateRequest) -> None:
        """Validate request structure and required fields"""
        if not request.request_id:
            raise AttentionGateError("Missing request_id")

        if not request.space_id:
            raise AttentionGateError("Missing space_id")

        if not request.actor or not request.actor.person_id:
            raise AttentionGateError("Missing actor information")

        if not request.policy or not request.policy.band:
            raise AttentionGateError("Missing policy band")

    def _make_gate_decision(
        self,
        request: GateRequest,
        salience_result: SalienceResult,
        policy_result: Any,
        backpressure_result: Any,
    ) -> GateDecision:
        """
        Core gate decision logic implementing 4-action selection.

        Uses salience score, policy constraints, and resource availability
        to determine ADMIT/BOOST/DEFER/DROP with explainable reasoning.
        """
        config = get_config()
        priority = salience_result.calibrated_priority
        reasons = []

        # Apply policy band modifiers
        band = request.policy.band
        if band in config.band_modifiers:
            band_config = config.band_modifiers[band]
            max_priority = band_config.get("max_priority", 1.0)
            priority = min(priority, max_priority)

            if priority < salience_result.calibrated_priority:
                reasons.append(f"priority_capped_by_{band}_band")

        # Decision thresholds
        thresholds = config.thresholds

        # DROP decision (lowest priority)
        if priority < thresholds.drop:
            reasons.append("priority_below_drop_threshold")
            return GateDecision(
                action=GateAction.DROP,
                priority=priority,
                reasons=reasons + ["low_salience"],
                obligations=policy_result.obligations,
            )

        # BOOST decision (highest priority)
        boost_threshold = thresholds.boost

        # Band-specific boost requirements
        if band in config.band_modifiers:
            band_boost_threshold = config.band_modifiers[band].get("boost_threshold")
            if band_boost_threshold:
                boost_threshold = band_boost_threshold

        if priority >= boost_threshold:
            reasons.append("priority_exceeds_boost_threshold")

            # Additional boost conditions
            if request.affect and "urgent" in request.affect.tags:
                reasons.append("urgent_affect_signal")

            if salience_result.features.urgency > 0.8:
                reasons.append("high_urgency_score")

            return GateDecision(
                action=GateAction.BOOST,
                priority=priority,
                reasons=reasons,
                obligations=policy_result.obligations,
                confidence=salience_result.confidence,
                uncertainty=salience_result.uncertainty,
            )

        # ADMIT decision (normal processing)
        if priority >= thresholds.admit:
            reasons.append("priority_exceeds_admit_threshold")

            # Quality checks for admission
            if salience_result.confidence > 0.7:
                reasons.append("high_confidence_score")

            if salience_result.features.value > 0.6:
                reasons.append("estimated_high_value")

            return GateDecision(
                action=GateAction.ADMIT,
                priority=priority,
                reasons=reasons,
                obligations=policy_result.obligations,
                confidence=salience_result.confidence,
                uncertainty=salience_result.uncertainty,
            )

        # DEFER decision (default for mid-range scores)
        reasons.append("priority_below_admit_threshold")
        reasons.append("deferred_for_capacity_management")

        # Calculate defer TTL based on priority
        base_ttl = 30000  # 30 seconds
        priority_multiplier = max(0.5, priority)  # Higher priority = shorter defer
        ttl_ms = int(base_ttl * (2.0 - priority_multiplier))

        return GateDecision(
            action=GateAction.DEFER,
            priority=priority,
            reasons=reasons,
            obligations=policy_result.obligations,
            ttl_ms=ttl_ms,
            confidence=salience_result.confidence,
            uncertainty=salience_result.uncertainty,
        )

    def _create_routing_info(
        self,
        request: GateRequest,
        derived_intents: List[DerivedIntent],
        gate_decision: GateDecision,
    ) -> RoutingInfo:
        """Create routing configuration for downstream processing"""

        # Default routing
        topic = "bus.attention_gate.admitted"
        priority = 0

        # Route based on primary derived intent
        if derived_intents:
            primary_intent = derived_intents[0]

            if primary_intent.intent == IntentType.PROSPECTIVE_SCHEDULE:
                topic = "bus.prospective.schedule"
                priority = 1
            elif primary_intent.intent == IntentType.RECALL:
                topic = "bus.retrieval.query"
                priority = 2
            elif primary_intent.intent == IntentType.WRITE:
                topic = "bus.write.ingest"
                priority = 1
            elif primary_intent.intent == IntentType.PROJECT:
                topic = "bus.planning.project"
                priority = 1
            elif primary_intent.intent == IntentType.HIPPO_ENCODE:
                topic = "bus.hippocampus.encode"
                priority = 3

        # Adjust priority based on gate decision
        if gate_decision.action == GateAction.BOOST:
            priority += 2
        elif gate_decision.action == GateAction.DEFER:
            priority = max(0, priority - 1)

        # Set deadline for time-sensitive requests
        deadline = None
        if gate_decision.ttl_ms < 60000:  # Less than 1 minute
            deadline = datetime.now() + timedelta(milliseconds=gate_decision.ttl_ms)

        return RoutingInfo(
            topic=topic,
            priority=priority,
            deadline=deadline,
            retry_policy={
                "max_retries": 3 if gate_decision.action == GateAction.BOOST else 1,
                "backoff_multiplier": 1.5,
            },
        )

    def _create_decision_trace(
        self,
        request: GateRequest,
        salience_result: SalienceResult,
        gate_decision: GateDecision,
        execution_time: float,
    ) -> GateDecisionTrace:
        """Create comprehensive decision trace for explainability"""
        config = get_config()

        return GateDecisionTrace(
            trace_id=request.trace_id,
            features=salience_result.features,
            weights=salience_result.weights,
            raw_score=salience_result.raw_score,
            calibrated_priority=salience_result.calibrated_priority,
            thresholds={
                "admit": config.thresholds.admit,
                "boost": config.thresholds.boost,
                "drop": config.thresholds.drop,
            },
            decision_path=[
                "policy_validation",
                "backpressure_check",
                "intent_derivation",
                "salience_calculation",
                "action_selection",
            ],
            execution_time_ms=execution_time * 1000,
            adaptation_context={
                "config_version": config.config_version,
                "adaptation_count": config.adaptation_count,
            },
        )

    def _create_drop_response(
        self, request: GateRequest, reasons: List[str]
    ) -> GateResponse:
        """Create response for DROP decisions"""
        gate_decision = GateDecision(
            action=GateAction.DROP,
            priority=0.0,
            reasons=reasons,
            confidence=1.0,  # High confidence in drop decisions
        )

        return GateResponse(
            gate_decision=gate_decision,
            derived_intents=[],
            routing=RoutingInfo(topic="bus.attention_gate.dropped"),
            trace=GateDecisionTrace(
                trace_id=request.trace_id,
                features=None,  # No feature extraction for drops
                weights=None,
                raw_score=0.0,
                calibrated_priority=0.0,
                thresholds={},
                decision_path=["policy_violation"],
                execution_time_ms=0.0,
            ),
        )

    def _create_defer_response(
        self, request: GateRequest, reasons: List[str]
    ) -> GateResponse:
        """Create response for DEFER decisions"""
        gate_decision = GateDecision(
            action=GateAction.DEFER,
            priority=0.3,  # Medium-low priority
            reasons=reasons,
            ttl_ms=60000,  # 1 minute defer
            confidence=0.8,
        )

        return GateResponse(
            gate_decision=gate_decision,
            derived_intents=[],
            routing=RoutingInfo(
                topic="bus.attention_gate.deferred",
                deadline=datetime.now() + timedelta(milliseconds=60000),
            ),
            trace=GateDecisionTrace(
                trace_id=request.trace_id,
                features=None,
                weights=None,
                raw_score=0.0,
                calibrated_priority=0.3,
                thresholds={"defer_threshold": 0.4},
                decision_path=["backpressure_limit"],
                execution_time_ms=0.0,
            ),
        )

    def _create_error_response(
        self, request: GateRequest, error_type: str, error_msg: str
    ) -> GateResponse:
        """Create response for error conditions"""
        gate_decision = GateDecision(
            action=GateAction.DROP,
            priority=0.0,
            reasons=[f"error_{error_type.lower()}", error_msg],
            confidence=1.0,
        )

        return GateResponse(
            gate_decision=gate_decision,
            derived_intents=[],
            routing=RoutingInfo(topic="bus.attention_gate.error"),
            trace=GateDecisionTrace(
                trace_id=request.trace_id or "unknown",
                features=None,
                weights=None,
                raw_score=0.0,
                calibrated_priority=0.0,
                thresholds={},
                decision_path=["error_handling"],
                execution_time_ms=0.0,
            ),
        )

    def _record_decision(
        self,
        request: GateRequest,
        response: GateResponse,
        salience_result: SalienceResult,
    ) -> None:
        """Record decision for learning integration (Phase 3)"""
        if len(self.decision_history) > 1000:
            # Keep only recent decisions
            self.decision_history = self.decision_history[-500:]

        self.decision_history.append(
            {
                "request_id": request.request_id,
                "space_id": request.space_id,
                "timestamp": datetime.now().isoformat(),
                "action": response.gate_decision.action.value,
                "priority": response.gate_decision.priority,
                "confidence": response.gate_decision.confidence,
                "features": salience_result.features.raw_features,
                "execution_time_ms": response.trace.execution_time_ms,
            }
        )

    # Learning Integration Methods (Future Phases)

    def enable_adaptation(self) -> None:
        """Enable learning adaptation (Phase 3)"""
        self.adaptation_enabled = True

        # TODO: Register learning hooks when learning system is implemented
        # self.salience_calculator.register_outcome_callback(self._process_outcome)

    def _process_outcome(
        self, request_id: str, outcome: str, metrics: Dict[str, Any]
    ) -> None:
        """Process outcome for learning (Phase 3)"""
        if not self.adaptation_enabled:
            return

        # Find corresponding decision
        decision_record = None
        for record in reversed(self.decision_history):
            if record["request_id"] == request_id:
                decision_record = record
                break

        if decision_record:
            # This would feed into learning system
            # For now, just track for future implementation
            decision_record["outcome"] = outcome
            decision_record["outcome_metrics"] = metrics

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if not self.decision_latencies:
            return {"status": "no_data"}

        latencies = self.decision_latencies[-100:]  # Last 100 requests

        return {
            "request_count": self.request_count,
            "latency_p50": sorted(latencies)[len(latencies) // 2],
            "latency_p95": sorted(latencies)[int(len(latencies) * 0.95)],
            "average_latency": sum(latencies) / len(latencies),
            "decision_distribution": self._get_decision_distribution(),
        }

    def _get_decision_distribution(self) -> Dict[str, int]:
        """Get distribution of recent decisions"""
        distribution = {"ADMIT": 0, "BOOST": 0, "DEFER": 0, "DROP": 0}

        recent_decisions = self.decision_history[-100:]  # Last 100
        for record in recent_decisions:
            action = record.get("action", "UNKNOWN")
            if action in distribution:
                distribution[action] += 1

        return distribution


# Factory function for dependency injection
def create_attention_gate(config_path: Optional[str] = None) -> AttentionGate:
    """Create attention gate instance with configuration"""
    return AttentionGate(config_path)

"""
Decision Tracing for Attention Gate

Provides comprehensive tracing and explainability for gate decisions.

Future-ready for learning integration:
- Phase 1: Static decision tracing
- Phase 2: Calibrated confidence tracking
- Phase 3: Learning from decision outcomes
- Phase 4: Neural decision explanation
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .types import GateDecisionTrace, GateRequest, SalienceFeatures, SalienceWeights


class DecisionTracer:
    """
    Traces gate decisions for explainability and learning.

    Captures detailed information about decision process for audit,
    debugging, and future learning integration.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path

        # Trace storage
        self.trace_history: List[Dict[str, Any]] = []

        # Learning integration (Phase 3)
        self.learning_enabled = False

    def create_trace(
        self,
        request: GateRequest,
        features: Optional[SalienceFeatures],
        weights: Optional[SalienceWeights],
        raw_score: float,
        calibrated_priority: float,
        thresholds: Dict[str, float],
        decision_path: List[str],
        execution_time_ms: float,
    ) -> GateDecisionTrace:
        """
        Create comprehensive decision trace.

        Captures all information needed for explainability and learning.
        """
        trace = GateDecisionTrace(
            trace_id=request.trace_id or f"trace_{int(time.time() * 1000)}",
            features=features,
            weights=weights,
            raw_score=raw_score,
            calibrated_priority=calibrated_priority,
            thresholds=thresholds,
            decision_path=decision_path,
            execution_time_ms=execution_time_ms,
            adaptation_context={
                "request_timestamp": (
                    request.timestamp.isoformat() if request.timestamp else None
                ),
                "gate_version": request.version,
                "learning_phase": "1",  # Phase 1: Rule-based
            },
        )

        # Store trace for analysis
        self._store_trace(request, trace)

        return trace

    def _store_trace(self, request: GateRequest, trace: GateDecisionTrace) -> None:
        """Store trace for analysis and learning"""
        if len(self.trace_history) > 10000:
            # Keep only recent traces
            self.trace_history = self.trace_history[-5000:]

        trace_record = {
            "trace_id": trace.trace_id,
            "request_id": request.request_id,
            "actor_id": request.actor.person_id,
            "space_id": request.space_id,
            "band": request.policy.band,
            "raw_score": trace.raw_score,
            "calibrated_priority": trace.calibrated_priority,
            "execution_time_ms": trace.execution_time_ms,
            "decision_path": trace.decision_path,
            "timestamp": datetime.now().isoformat(),
        }

        # Add feature summary if available
        if trace.features:
            trace_record["feature_summary"] = {
                "urgency": trace.features.urgency,
                "value": trace.features.value,
                "complexity": trace.features.complexity,
                "confidence": trace.features.confidence,
            }

        self.trace_history.append(trace_record)

    def get_trace_analytics(self) -> Dict[str, Any]:
        """Get analytics on decision traces"""
        if not self.trace_history:
            return {"status": "no_data"}

        recent_traces = self.trace_history[-1000:]  # Last 1000 traces

        # Performance metrics
        execution_times = [t["execution_time_ms"] for t in recent_traces]
        avg_execution_time = sum(execution_times) / len(execution_times)

        # Score distribution
        scores = [t["raw_score"] for t in recent_traces]
        avg_score = sum(scores) / len(scores)

        priorities = [t["calibrated_priority"] for t in recent_traces]
        avg_priority = sum(priorities) / len(priorities)

        # Decision path analysis
        path_counts = {}
        for trace in recent_traces:
            path_key = " -> ".join(trace["decision_path"])
            path_counts[path_key] = path_counts.get(path_key, 0) + 1

        # Band analysis
        band_stats = {}
        for trace in recent_traces:
            band = trace["band"]
            if band not in band_stats:
                band_stats[band] = {"count": 0, "avg_score": 0, "avg_priority": 0}

            band_stats[band]["count"] += 1
            band_stats[band]["avg_score"] += trace["raw_score"]
            band_stats[band]["avg_priority"] += trace["calibrated_priority"]

        # Calculate averages
        for band, stats in band_stats.items():
            count = stats["count"]
            stats["avg_score"] /= count
            stats["avg_priority"] /= count

        return {
            "total_traces": len(recent_traces),
            "performance": {
                "avg_execution_time_ms": avg_execution_time,
                "p95_execution_time_ms": sorted(execution_times)[
                    int(len(execution_times) * 0.95)
                ],
            },
            "scoring": {
                "avg_raw_score": avg_score,
                "avg_calibrated_priority": avg_priority,
            },
            "decision_paths": sorted(
                path_counts.items(), key=lambda x: x[1], reverse=True
            )[:10],
            "band_analysis": band_stats,
        }

    def get_trace_by_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get specific trace by ID"""
        for trace in reversed(self.trace_history):
            if trace["trace_id"] == trace_id:
                return trace
        return None

    def get_traces_for_request(self, request_id: str) -> List[Dict[str, Any]]:
        """Get all traces for a specific request"""
        return [
            trace for trace in self.trace_history if trace["request_id"] == request_id
        ]

    def explain_decision(self, trace_id: str) -> Dict[str, Any]:
        """Generate human-readable explanation of decision"""
        trace = self.get_trace_by_id(trace_id)
        if not trace:
            return {"error": "trace_not_found"}

        explanation = {
            "summary": f"Request scored {trace['raw_score']:.3f}, calibrated to priority {trace['calibrated_priority']:.3f}",
            "execution_time": f"Decision took {trace['execution_time_ms']:.1f}ms",
            "decision_process": [],
        }

        # Explain decision path
        for step in trace["decision_path"]:
            step_explanation = self._explain_decision_step(step, trace)
            if step_explanation:
                explanation["decision_process"].append(step_explanation)

        # Feature analysis
        if "feature_summary" in trace:
            features = trace["feature_summary"]
            explanation["key_factors"] = [
                f"Urgency: {features['urgency']:.2f}",
                f"Value: {features['value']:.2f}",
                f"Complexity: {features['complexity']:.2f}",
                f"Confidence: {features['confidence']:.2f}",
            ]

        return explanation

    def _explain_decision_step(self, step: str, trace: Dict[str, Any]) -> Optional[str]:
        """Explain individual decision step"""
        explanations = {
            "policy_validation": "Checked policy constraints and band restrictions",
            "backpressure_check": "Evaluated system capacity and load",
            "intent_derivation": "Analyzed content to derive likely intents",
            "salience_calculation": f"Calculated salience score: {trace['raw_score']:.3f}",
            "action_selection": f"Selected action based on priority: {trace['calibrated_priority']:.3f}",
            "policy_violation": "Request violated policy constraints",
            "backpressure_limit": "Request deferred due to capacity limits",
            "error_handling": "Request dropped due to processing error",
        }

        return explanations.get(step)

    # Learning Integration Methods (Future Phases)

    def enable_learning_tracing(self) -> None:
        """Enable enhanced tracing for learning (Phase 3)"""
        self.learning_enabled = True

    def record_outcome(
        self, trace_id: str, outcome: str, metrics: Dict[str, Any]
    ) -> None:
        """Record decision outcome for learning (Phase 3)"""
        if not self.learning_enabled:
            return

        # Find trace and update with outcome
        for trace in reversed(self.trace_history):
            if trace["trace_id"] == trace_id:
                trace["outcome"] = outcome
                trace["outcome_metrics"] = metrics
                trace["outcome_timestamp"] = datetime.now().isoformat()
                break

    def get_learning_dataset(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get dataset for learning training (Phase 3)"""
        if not self.learning_enabled:
            return []

        # Return traces with outcomes for learning
        learning_traces = []
        for trace in reversed(self.trace_history):
            if "outcome" in trace and len(learning_traces) < limit:
                learning_traces.append(
                    {
                        "features": trace.get("feature_summary", {}),
                        "raw_score": trace["raw_score"],
                        "calibrated_priority": trace["calibrated_priority"],
                        "outcome": trace["outcome"],
                        "outcome_metrics": trace.get("outcome_metrics", {}),
                    }
                )

        return learning_traces

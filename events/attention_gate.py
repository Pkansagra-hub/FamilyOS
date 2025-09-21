"""
Attention Gate Bridge - Connect to Attention Gate Service
========================================================

This module bridges the events system to the full attention gate service
that handles smart-path processing for events that need intelligent routing.

Responsibilities:
- Bridge events/attention_gate.py to attention_gate/gate_service.py
- Handle smart-path events from intent router
- Apply salience scoring and admission control
- Return routing decisions (ADMIT/BOOST/DEFER/DROP)
- Generate derived intents for pipelines
"""

import logging
from typing import Any, Dict, Optional

# Import the full attention gate service
from attention_gate.gate_service import AttentionGate as AttentionGateService
from attention_gate.types import GateAction, GateRequest, GateResponse

logger = logging.getLogger(__name__)


class AttentionGate:
    """
    Bridge to the full Attention Gate Service for smart-path processing.

    This connects the events system to the comprehensive attention gate
    that implements thalamus-inspired admission control with salience,
    backpressure, and policy integration.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize attention gate bridge with service connection."""
        try:
            # Initialize the full attention gate service
            self.gate_service = AttentionGateService(config_path)
            logger.info("Attention gate bridge connected to gate service")
        except Exception as e:
            logger.error(f"Failed to initialize attention gate service: {e}")
            self.gate_service = None

    def process_smart_path_event(
        self, event_data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process an event through the smart path attention gate.

        Args:
            event_data: Event data from intent router
            metadata: Request metadata including security context

        Returns:
            Gate response with routing decision and derived intents
        """
        if not self.gate_service:
            logger.warning("Attention gate service not available, defaulting to ADMIT")
            return {
                "decision": "ADMIT",
                "reason": "gate_service_unavailable",
                "priority": "normal",
                "derived_intents": [],
            }

        try:
            # Convert event data to GateRequest format
            gate_request = self._convert_to_gate_request(event_data, metadata)

            # Process through attention gate service
            gate_response = self.gate_service.process_request(gate_request)

            # Convert response to events system format
            return self._convert_gate_response(gate_response)

        except Exception as e:
            logger.error(f"Attention gate processing error: {e}")
            # Fail-safe: admit with normal priority
            return {
                "decision": "ADMIT",
                "reason": f"processing_error: {str(e)}",
                "priority": "normal",
                "derived_intents": [],
            }

    def _convert_to_gate_request(
        self, event_data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> GateRequest:
        """Convert event data to GateRequest format."""
        from attention_gate.types import Actor, PolicyContext, RequestContent

        # Extract actor information
        actor = Actor(
            person_id=metadata.get("actor_id", "unknown"),
            role=metadata.get("actor_role", "user"),
        )

        # Extract policy context
        policy = PolicyContext(
            band=metadata.get("band", "GREEN"),
            abac=metadata.get("abac", {}),
            obligations=metadata.get("obligations", []),
        )

        # Prepare content
        content_text = ""
        data = event_data.get("data", {})
        if isinstance(data.get("content"), str):
            content_text = data["content"]
        elif isinstance(data.get("query"), str):
            content_text = data["query"]

        content = (
            RequestContent(
                text=content_text,
                content_type="text/plain",
                metadata={"operation": event_data.get("operation", "unknown")},
            )
            if content_text
            else None
        )

        return GateRequest(
            request_id=metadata.get("request_id", f"event_{hash(str(event_data))}"),
            actor=actor,
            space_id=metadata.get("space_id", "default"),
            policy=policy,
            payload=event_data,
            content=content,
            declared_intent=event_data.get("operation"),
            trace_id=metadata.get("trace_id", "unknown"),
        )

    def _convert_gate_response(self, response: GateResponse) -> Dict[str, Any]:
        """Convert GateResponse to events system format."""
        # Map gate actions to event system decisions
        decision_map = {
            GateAction.ADMIT: "ADMIT",
            GateAction.BOOST: "BOOST",
            GateAction.DEFER: "DEFER",
            GateAction.DROP: "DROP",
        }

        # Extract action from gate_decision
        action = response.gate_decision.action
        reasons = response.gate_decision.reasons

        return {
            "decision": decision_map.get(action, "ADMIT"),
            "reason": "; ".join(reasons) if reasons else "unknown",
            "priority": "high" if action == GateAction.BOOST else "normal",
            "derived_intents": [
                {
                    "intent": intent.intent.value,
                    "confidence": intent.confidence.score,
                    "reasoning": intent.reasoning,
                }
                for intent in response.derived_intents
            ],
            "salience_score": (
                response.trace.calibrated_priority if response.trace.features else None
            ),
            "execution_time_ms": response.trace.execution_time_ms,
            "trace": {
                "trace_id": response.trace.trace_id,
                "decision_path": response.trace.decision_path,
                "raw_score": response.trace.raw_score,
            },
        }

    def _extract_urgency_hints(self, event_data: Dict[str, Any]) -> Dict[str, bool]:
        """Extract urgency indicators from event data."""
        hints: Dict[str, bool] = {}

        # Check for urgency markers in headers or metadata
        headers = event_data.get("headers", {})
        if headers.get("X-Urgent") or headers.get("Priority") == "high":
            hints["urgent_header"] = True

        # Check for time-sensitive operations
        operation = event_data.get("operation", "")
        if "schedule" in operation.lower() or "remind" in operation.lower():
            hints["time_sensitive"] = True

        # Check for emotional indicators (if affect system data present)
        if "affect" in event_data.get("data", {}):
            affect_data = event_data["data"]["affect"]
            if affect_data.get("arousal", 0) > 0.7:
                hints["high_arousal"] = True

        return hints

    def _extract_complexity_hints(self, event_data: Dict[str, Any]) -> Dict[str, bool]:
        """Extract complexity indicators from event data."""
        hints: Dict[str, bool] = {}

        # Check content complexity
        data = event_data.get("data", {})
        content = data.get("content", "") or data.get("query", "")

        if isinstance(content, str):
            if len(content) > 1000:
                hints["long_content"] = True
            if content.count("?") > 3:
                hints["multi_question"] = True

        # Check for complex operations
        operation = event_data.get("operation", "")
        complex_ops = ["project", "schedule", "recall", "search"]
        if any(op in operation.lower() for op in complex_ops):
            hints["complex_operation"] = True

        return hints

    # Legacy interface methods for backward compatibility
    def admit(self, *args: Any, **kwargs: Any) -> Any:
        """Legacy admit method - routes to process_smart_path_event."""
        event_data = kwargs.get("event_data", {})
        metadata = kwargs.get("metadata", {})
        result = self.process_smart_path_event(event_data, metadata)
        return result["decision"] == "ADMIT"

    def defer(self, *args: Any, **kwargs: Any) -> Any:
        """Legacy defer method - routes to process_smart_path_event."""
        event_data = kwargs.get("event_data", {})
        metadata = kwargs.get("metadata", {})
        result = self.process_smart_path_event(event_data, metadata)
        return result["decision"] == "DEFER"

    def boost(self, *args: Any, **kwargs: Any) -> Any:
        """Legacy boost method - routes to process_smart_path_event."""
        event_data = kwargs.get("event_data", {})
        metadata = kwargs.get("metadata", {})
        result = self.process_smart_path_event(event_data, metadata)
        return result["decision"] == "BOOST"

    def drop(self, *args: Any, **kwargs: Any) -> Any:
        """Legacy drop method - routes to process_smart_path_event."""
        event_data = kwargs.get("event_data", {})
        metadata = kwargs.get("metadata", {})
        result = self.process_smart_path_event(event_data, metadata)
        return result["decision"] == "DROP"


# Global instance for dependency injection
default_attention_gate = AttentionGate()

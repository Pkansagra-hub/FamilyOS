"""
Test fixtures for Thalamic Relay System testing.

Provides fixtures for testing thalamic relay operations including
attention gate, salience detection, and coordination with working memory.
"""

from typing import Any, Dict, List


# Re-export MockThalamicRelaySystem from working_memory_fixtures
# to avoid circular imports
class MockThalamicRelaySystem:
    """Mock thalamic relay system for testing."""

    def __init__(self) -> None:
        self.gate_state = {
            "threshold": 0.5,
            "selectivity": 0.7,
            "attention_allocation": {
                "verbal": 0.33,
                "visuospatial": 0.33,
                "episodic": 0.34,
            },
        }
        self.performance_metrics = {
            "accuracy": 0.85,
            "efficiency": 0.82,
            "response_time": 300,
        }
        self.learning_state = {"adaptation_active": True, "learning_rate": 0.1}
        self.coordination_state = {"working_memory_coordinated": False}
        self.event_handlers: List[Any] = []

    async def process_stimulus(self, stimulus: Dict[str, Any]) -> Dict[str, Any]:
        """Process stimulus through attention gate."""

        salience = stimulus.get("salience_score", stimulus.get("salience", 0.5))

        # Gate decision based on salience and current threshold
        if salience > self.gate_state["threshold"]:
            decision = "pass"
            attention_allocation = min(salience, 1.0)

            # Determine target buffer
            modality = stimulus.get("modality", "verbal")
            if modality in ["verbal", "auditory", "text"]:
                target_buffer = "verbal"
            elif modality in ["visual", "visuospatial", "spatial"]:
                target_buffer = "visuospatial"
            else:
                target_buffer = "episodic"
        else:
            decision = "block"
            attention_allocation = 0.0
            target_buffer = None

        return {
            "gate_decision": decision,
            "attention_allocation": attention_allocation,
            "working_memory_target": target_buffer,
            "gate_priorities": {stimulus.get("stimulus_id", "unknown"): salience},
        }

    async def handle_working_memory_conflict(
        self, conflict_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle conflict from working memory."""

        # Adjust gate settings for conflict resolution
        if conflict_info["severity"] > 0.6:
            self.gate_state["selectivity"] += 0.1
            self.gate_state["threshold"] += 0.05

            return {
                "attention_reallocation": True,
                "conflict_resolution_support": True,
                "gate_adjustment": {"sensitivity": self.gate_state["selectivity"]},
            }

        return {"attention_reallocation": False}

    async def coordinate_with_executive_control(
        self, executive_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coordinate with executive control."""

        if executive_state.get("attention_control_active"):
            return {
                "gate_aligned": True,
                "focus_enhancement": {"visuospatial": 0.8},
                "distractor_suppression": 0.7,
            }

        return {"gate_aligned": False}

    async def handle_capacity_limit(
        self, capacity_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle working memory capacity limits."""

        if capacity_state.get("capacity_limit_reached"):
            self.gate_state["selectivity"] += 0.2
            self.gate_state["threshold"] += 0.1

            return {
                "gate_selectivity_increased": True,
                "threshold_raised": True,
                "low_priority_blocking": True,
            }

        return {"gate_selectivity_increased": False}

    async def configure_performance_monitoring(self, config: Dict[str, Any]) -> None:
        """Configure performance monitoring."""
        self.performance_config = config

    async def provide_performance_support(
        self, performance_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Provide performance support."""

        if performance_state.get("alert_triggered"):
            return {
                "support_provided": True,
                "gate_optimization": True,
                "attention_focus_enhancement": True,
            }

        return {"support_provided": False}

    async def update_learning_parameters(self, results: List[Dict[str, Any]]) -> None:
        """Update learning parameters."""
        pass  # Simplified for testing

    async def get_learning_state(self) -> Dict[str, Any]:
        """Get learning state."""
        return self.learning_state.copy()

    async def subscribe_to_events(self, handler: Any) -> None:
        """Subscribe to events."""
        self.event_handlers.append(handler)

    async def handle_working_memory_event(
        self, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle working memory event."""

        if event["type"] == "cognitive_conflict_detected":
            return {
                "event_handled": True,
                "gate_adjusted": True,
                "selectivity_increased": True,
            }

        return {"event_handled": False}

    async def check_coordination_status(self) -> Dict[str, Any]:
        """Check coordination status."""
        return {
            "working_memory_coordinated": self.coordination_state[
                "working_memory_coordinated"
            ]
        }

    async def establish_working_memory_coordination(self, wm_system: Any) -> None:
        """Establish working memory coordination."""
        self.coordination_state["working_memory_coordinated"] = True

    async def get_state(self) -> Dict[str, Any]:
        """Get current state."""
        return {
            "attention_allocation": self.gate_state["attention_allocation"],
            "gate_priorities": {"item1": 0.8, "item2": 0.6},
            "performance": self.performance_metrics,
        }

    async def get_final_state(self) -> Dict[str, Any]:
        """Get final state."""
        return {
            "attention": self.gate_state["attention_allocation"],
            "resources": {"utilization": 0.6, "efficiency": 0.85},
            "performance": self.performance_metrics,
            "stability": 0.88,
            "efficiency": 0.85,
        }

    async def check_system_health(self) -> Dict[str, Any]:
        """Check system health."""
        return {"status": "healthy", "issues": []}

    async def get_resilience_metrics(self) -> Dict[str, Any]:
        """Get resilience metrics."""
        return {"error_recovery_time": 400}  # ms


def attention_gate_factory():
    """Factory for creating attention gate states."""

    def create_attention_gate(
        threshold: float = 0.5, selectivity: float = 0.7, is_open: bool = True
    ) -> Dict[str, Any]:
        return {
            "threshold": threshold,
            "selectivity": selectivity,
            "is_open": is_open,
            "last_decision": "pass" if is_open else "block",
        }

    return create_attention_gate


def salience_detector_factory():
    """Factory for creating salience detector states."""

    def create_salience_detector(
        sensitivity: float = 0.8, adaptation_rate: float = 0.1
    ) -> Dict[str, Any]:
        return {
            "sensitivity": sensitivity,
            "adaptation_rate": adaptation_rate,
            "recent_detections": [],
        }

    return create_salience_detector

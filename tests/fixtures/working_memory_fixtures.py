"""
Test fixtures for Working Memory System testing.

Provides fixtures for testing working memory operations including
buffer states, executive control, attention coordination, and
conflict resolution systems.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest


class MockWorkingMemorySystem:
    """Mock working memory system for testing."""

    def __init__(self):
        self.buffers = {
            "verbal": {"items": [], "capacity": 7, "utilization": 0.0},
            "visuospatial": {"items": [], "capacity": 4, "utilization": 0.0},
            "episodic": {"items": [], "capacity": 5, "utilization": 0.0},
        }
        self.executive_state = {
            "active": False,
            "control_level": 0.0,
            "attention_control": False,
            "conflict_monitoring": True,
        }
        self.attention_state = {"verbal": 0.33, "visuospatial": 0.33, "episodic": 0.34}
        self.performance_metrics = {
            "accuracy": 0.85,
            "efficiency": 0.80,
            "response_time": 500,
        }
        self.learning_state = {
            "adaptation_active": True,
            "learning_rate": 0.1,
            "performance_history": [],
        }
        self.coordination_state = {
            "thalamic_coordinated": False,
            "attention_gate_sync": False,
            "priority_alignment": False,
        }
        self.event_handlers = []

    async def receive_gated_content(
        self, content: Dict[str, Any], attention_allocation: float, target_buffer: str
    ) -> Dict[str, Any]:
        """Simulate receiving content from thalamic gate."""

        buffer = self.buffers.get(target_buffer, self.buffers["verbal"])

        # Simulate buffer update
        if len(buffer["items"]) < buffer["capacity"]:
            buffer["items"].append(
                {
                    "content": content,
                    "attention_allocation": attention_allocation,
                    "timestamp": datetime.now(),
                }
            )
            buffer["utilization"] = len(buffer["items"]) / buffer["capacity"]

            return {
                "buffer_updated": True,
                "priority_level": (
                    "critical" if attention_allocation > 0.8 else "normal"
                ),
                "executive_control_engaged": attention_allocation > 0.7,
            }
        else:
            return {
                "buffer_updated": False,
                "reason": "buffer_full",
                "eviction_required": True,
            }

    async def get_thalamic_coordination(self) -> Dict[str, Any]:
        """Get thalamic coordination state."""
        return {
            "attention_gate_sync": self.coordination_state["attention_gate_sync"],
            "priority_alignment": self.coordination_state["priority_alignment"],
            "buffer_coordination": {
                "verbal": {"aligned": True},
                "visuospatial": {"aligned": True},
                "episodic": {"aligned": True},
            },
        }

    async def add_buffer_content(
        self, buffer_type: str, content: str, priority: str
    ) -> Dict[str, Any]:
        """Add content to specified buffer."""

        buffer = self.buffers.get(buffer_type, self.buffers["verbal"])

        if len(buffer["items"]) < buffer["capacity"]:
            buffer["items"].append(
                {"content": content, "priority": priority, "timestamp": datetime.now()}
            )
            buffer["utilization"] = len(buffer["items"]) / buffer["capacity"]
            return {"success": True, "buffer_state": buffer}
        else:
            return {"success": False, "reason": "buffer_full"}

    async def monitor_conflicts(self) -> Dict[str, Any]:
        """Monitor for cognitive conflicts."""

        # Simulate conflict detection based on buffer contents
        verbal_items = self.buffers["verbal"]["items"]

        if len(verbal_items) > 1:
            priorities = [item.get("priority", "normal") for item in verbal_items]
            if "critical" in priorities and "high" in priorities:
                return {
                    "conflict_type": "priority_conflict",
                    "severity": 0.8,
                    "conflict_id": "conflict_001",
                    "affected_buffers": ["verbal"],
                }

        return {"conflict_type": None, "severity": 0.0}

    async def resolve_conflict_with_thalamic_support(
        self, conflict_id: str, thalamic_support: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve conflict with thalamic system support."""

        return {
            "resolution_success": True,
            "thalamic_coordination": True,
            "resolution_method": "priority_rebalancing",
        }

    async def apply_executive_control(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Apply executive control."""

        self.executive_state["active"] = True
        self.executive_state["control_level"] = request.get("control_intensity", 0.5)
        self.executive_state["attention_control"] = (
            request.get("control_type") == "attention_control"
        )

        return {
            "control_applied": True,
            "attention_control_active": self.executive_state["attention_control"],
            "executive_state": self.executive_state.copy(),
        }

    async def get_capacity_state(self) -> Dict[str, Any]:
        """Get current capacity state."""

        total_items = sum(len(buffer["items"]) for buffer in self.buffers.values())
        total_capacity = sum(buffer["capacity"] for buffer in self.buffers.values())
        utilization_rate = total_items / total_capacity

        return {
            "utilization_rate": utilization_rate,
            "capacity_limit_reached": utilization_rate > 0.9,
            "available_capacity": total_capacity - total_items,
        }

    async def configure_performance_monitoring(self, config: Dict[str, Any]) -> None:
        """Configure performance monitoring."""
        self.performance_config = config

    async def simulate_performance_degradation(self, scenario: Dict[str, Any]) -> None:
        """Simulate performance degradation."""

        self.performance_metrics["accuracy"] -= scenario.get("accuracy_drop", 0)
        self.performance_metrics["response_time"] += scenario.get(
            "response_time_increase", 0
        )
        # Cognitive load increase would be handled by specific metrics

    async def check_performance_alerts(self) -> Dict[str, Any]:
        """Check for performance alerts."""

        if self.performance_metrics["accuracy"] < 0.85:
            return {
                "alert_triggered": True,
                "alert_type": "performance_decline",
                "metrics": self.performance_metrics.copy(),
            }

        return {"alert_triggered": False}

    async def apply_thalamic_performance_support(
        self, support: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply thalamic performance support."""

        return {
            "performance_improved": True,
            "coordination_effective": True,
            "improvement_metrics": {"accuracy": 0.05, "response_time": -50},
        }

    async def update_learning_parameters(self, results: List[Dict[str, Any]]) -> None:
        """Update learning parameters based on results."""

        self.learning_state["performance_history"].extend(results)

        # Simple learning adaptation
        if len(results) > 0:
            avg_performance = sum(
                r.get("coordination_score", 0.5) for r in results
            ) / len(results)
            if avg_performance > 0.7:
                self.learning_state["learning_rate"] *= 1.1
            else:
                self.learning_state["learning_rate"] *= 0.9

    async def get_learning_state(self) -> Dict[str, Any]:
        """Get current learning state."""
        return self.learning_state.copy()

    async def process_with_thalamic_input(
        self, stimulus: Dict[str, Any], thalamic_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process stimulus with thalamic input."""

        if thalamic_result.get("gate_decision") == "pass":
            target_buffer = thalamic_result.get("working_memory_target", "verbal")
            attention_allocation = thalamic_result.get("attention_allocation", 0.5)

            result = await self.receive_gated_content(
                stimulus, attention_allocation, target_buffer
            )

            return {
                "processed": True,
                "buffer_target": target_buffer,
                "priority_level": result.get("priority_level", "normal"),
                "coordination_score": attention_allocation,
            }
        else:
            return {
                "processed": False,
                "reason": "thalamic_gate_blocked",
                "coordination_score": 0.0,
            }

    async def subscribe_to_events(self, handler) -> None:
        """Subscribe to system events."""
        self.event_handlers.append(handler)

    async def handle_thalamic_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle event from thalamic system."""

        if event["type"] == "attention_overload_detected":
            self.executive_state["control_level"] += 0.2
            return {
                "event_handled": True,
                "executive_control_increased": True,
                "capacity_optimization_triggered": True,
            }

        return {"event_handled": False}

    async def check_coordination_status(self) -> Dict[str, Any]:
        """Check coordination status."""
        return {"thalamic_coordinated": self.coordination_state["thalamic_coordinated"]}

    async def establish_thalamic_coordination(self, thalamic_system) -> None:
        """Establish coordination with thalamic system."""
        self.coordination_state["thalamic_coordinated"] = True
        self.coordination_state["attention_gate_sync"] = True
        self.coordination_state["priority_alignment"] = True

    async def get_state(self) -> Dict[str, Any]:
        """Get current system state."""
        return {
            "buffers": self.buffers,
            "executive_state": self.executive_state,
            "attention_state": self.attention_state,
            "performance": self.performance_metrics,
            "coordination": self.coordination_state,
        }

    async def get_final_state(self) -> Dict[str, Any]:
        """Get final system state after processing."""
        return {
            "attention": self.attention_state,
            "resources": {"utilization": 0.7, "efficiency": 0.8},
            "performance": self.performance_metrics,
            "stability": 0.85,
            "efficiency": 0.80,
        }

    async def check_system_health(self) -> Dict[str, Any]:
        """Check system health status."""
        return {"status": "healthy", "issues": []}

    async def get_resilience_metrics(self) -> Dict[str, Any]:
        """Get resilience metrics."""
        return {"error_recovery_time": 500}  # ms


class MockThalamicRelaySystem:
    """Mock thalamic relay system for testing."""

    def __init__(self):
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
        self.event_handlers = []

    async def process_stimulus(self, stimulus: Dict[str, Any]) -> Dict[str, Any]:
        """Process stimulus through attention gate."""

        salience = stimulus.get("salience_score", stimulus.get("salience", 0.5))
        priority = stimulus.get("priority", "normal")

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

    async def subscribe_to_events(self, handler) -> None:
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

    async def establish_working_memory_coordination(self, wm_system) -> None:
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


# Pytest fixtures


@pytest.fixture
def working_memory_system():
    """Fixture providing mock working memory system."""
    return MockWorkingMemorySystem()


@pytest.fixture
def thalamic_relay_system():
    """Fixture providing mock thalamic relay system."""
    return MockThalamicRelaySystem()


@pytest.fixture
def buffer_state_factory():
    """Factory for creating buffer states."""

    def create_buffer_state(
        buffer_type: str = "verbal",
        capacity: int = 7,
        items: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return {
            "type": buffer_type,
            "capacity": capacity,
            "items": items or [],
            "utilization": len(items or []) / capacity,
            "last_updated": datetime.now(),
        }

    return create_buffer_state


@pytest.fixture
def executive_state_factory():
    """Factory for creating executive states."""

    def create_executive_state(
        active: bool = True,
        control_level: float = 0.8,
        control_type: str = "attention_control",
    ) -> Dict[str, Any]:
        return {
            "active": active,
            "control_level": control_level,
            "control_type": control_type,
            "timestamp": datetime.now(),
        }

    return create_executive_state


@pytest.fixture
def attention_state_factory():
    """Factory for creating attention states."""

    def create_attention_state(
        verbal: float = 0.4, visuospatial: float = 0.4, episodic: float = 0.2
    ) -> Dict[str, Any]:
        return {
            "verbal": verbal,
            "visuospatial": visuospatial,
            "episodic": episodic,
            "total": verbal + visuospatial + episodic,
        }

    return create_attention_state


@pytest.fixture
def conflict_state_factory():
    """Factory for creating conflict states."""

    def create_conflict_state(
        conflict_type: str = "priority_conflict",
        severity: float = 0.7,
        affected_buffers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return {
            "conflict_type": conflict_type,
            "severity": severity,
            "affected_buffers": affected_buffers or ["verbal"],
            "detection_time": datetime.now(),
            "conflict_id": f"conflict_{datetime.now().timestamp()}",
        }

    return create_conflict_state


@pytest.fixture
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


@pytest.fixture
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

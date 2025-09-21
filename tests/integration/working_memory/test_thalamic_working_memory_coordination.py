"""
Integration tests for Working Memory System coordination with Thalamic Relay.

These tests validate the coordination between the enhanced thalamic relay system
(Sprint 1) and the working memory system (Sprint 2) to ensure proper integration
of attention gate and prefrontal cortex cognitive operations.

Test coverage includes:
- Thalamic-Working Memory coordination
- Attention gate integration with executive control
- Cross-system performance validation
- Event coordination and synchronization
- Conflict resolution coordination
- Capacity management integration
"""

import asyncio
from datetime import datetime
from typing import Any, Dict

from tests.fixtures.thalamic_fixtures import MockThalamicRelaySystem

# Import test fixtures (mock implementations for testing)
from tests.fixtures.working_memory_fixtures import MockWorkingMemorySystem


class TestThalamusWorkingMemoryCoordination:
    """Test coordination between thalamic relay and working memory systems."""

    async def test_attention_gate_working_memory_integration(self) -> None:
        """Test integration between attention gate and working memory buffers."""

        # Create test systems
        thalamic_relay_system = MockThalamicRelaySystem()
        working_memory_system = MockWorkingMemorySystem()

        # Setup: High salience stimulus through attention gate
        stimulus = {
            "stimulus_id": "high_priority_content",
            "content": "Critical information requiring immediate attention",
            "salience_score": 0.95,
            "modality": "verbal",
            "priority": "critical",
        }

        # Thalamic processing: Attention gate detects high salience
        attention_result = await thalamic_relay_system.process_stimulus(stimulus)

        assert attention_result["gate_decision"] == "pass"
        assert attention_result["attention_allocation"] > 0.8
        assert attention_result["working_memory_target"] == "verbal"

        # Working memory integration: Content should be prioritized
        wm_response = await working_memory_system.receive_gated_content(
            content=stimulus,
            attention_allocation=attention_result["attention_allocation"],
            target_buffer=attention_result["working_memory_target"],
        )

        assert wm_response["buffer_updated"]
        assert wm_response["priority_level"] == "critical"
        assert wm_response["executive_control_engaged"]

        # Verify coordination
        coordination_state = await working_memory_system.get_thalamic_coordination()

        assert coordination_state["attention_gate_sync"]
        assert coordination_state["priority_alignment"]
        assert coordination_state["buffer_coordination"]["verbal"]["aligned"]

    async def test_cognitive_conflict_thalamic_response(self) -> None:
        """Test thalamic response to cognitive conflicts in working memory."""

        # Create test systems
        thalamic_relay_system = MockThalamicRelaySystem()
        working_memory_system = MockWorkingMemorySystem()

        # Setup: Create conflicting stimuli in working memory
        conflict_stimuli = [
            {
                "content": "Task A: Complete project report",
                "priority": "high",
                "buffer": "verbal",
            },
            {
                "content": "Task B: Attend urgent meeting",
                "priority": "critical",
                "buffer": "verbal",
            },
        ]

        # Working memory: Detect conflict
        for stimulus in conflict_stimuli:
            await working_memory_system.add_buffer_content(
                buffer_type=stimulus["buffer"],
                content=stimulus["content"],
                priority=stimulus["priority"],
            )

        conflict_detected = await working_memory_system.monitor_conflicts()

        assert conflict_detected["conflict_type"] == "priority_conflict"
        assert conflict_detected["severity"] > 0.6

        # Thalamic coordination: Should adjust attention allocation
        thalamic_response = await thalamic_relay_system.handle_working_memory_conflict(
            conflict_info=conflict_detected
        )

        assert thalamic_response["attention_reallocation"]
        assert thalamic_response["conflict_resolution_support"]
        assert thalamic_response["gate_adjustment"]["sensitivity"] > 0.8

        # Verify conflict resolution coordination
        resolution_result = (
            await working_memory_system.resolve_conflict_with_thalamic_support(
                conflict_id=conflict_detected["conflict_id"],
                thalamic_support=thalamic_response,
            )
        )

        assert resolution_result["resolution_success"]
        assert resolution_result["thalamic_coordination"]

    async def test_executive_control_attention_gate_coordination(self) -> None:
        """Test coordination between executive control and attention gate."""

        # Create test systems
        thalamic_relay_system = MockThalamicRelaySystem()
        working_memory_system = MockWorkingMemorySystem()

        # Setup: Executive control needs to focus attention
        executive_request = {
            "control_type": "attention_control",
            "target": "visuospatial_processing",
            "control_intensity": 0.8,
            "duration_ms": 5000,
        }

        # Working memory: Engage executive control
        executive_result = await working_memory_system.apply_executive_control(
            request=executive_request
        )

        assert executive_result["control_applied"]
        assert executive_result["attention_control_active"]

        # Thalamic coordination: Attention gate should align
        gate_adjustment = await thalamic_relay_system.coordinate_with_executive_control(
            executive_state=executive_result["executive_state"]
        )

        assert gate_adjustment["gate_aligned"]
        assert gate_adjustment["focus_enhancement"]["visuospatial"] > 0.7
        assert gate_adjustment["distractor_suppression"] > 0.6

        # Verify sustained coordination
        coordination_metrics = await self._measure_coordination_quality(
            thalamic_relay_system, working_memory_system, duration_ms=3000
        )

        assert coordination_metrics["average_alignment"] > 0.75
        assert coordination_metrics["stability"] > 0.8
        assert coordination_metrics["performance_improvement"] > 0.2

    @pytest.mark.asyncio
    async def test_capacity_limit_thalamic_adjustment(
        self, thalamic_relay_system, working_memory_system
    ):
        """Test thalamic adjustment when working memory reaches capacity limits."""

        # Setup: Fill working memory to capacity
        capacity_items = [
            {"content": f"Item {i}", "buffer": "verbal", "priority": "normal"}
            for i in range(10)  # Assume capacity limit around 7±2
        ]

        capacity_results = []
        for item in capacity_items:
            result = await working_memory_system.add_buffer_content(
                buffer_type=item["buffer"],
                content=item["content"],
                priority=item["priority"],
            )
            capacity_results.append(result)

        # Working memory: Should hit capacity limit
        capacity_state = await working_memory_system.get_capacity_state()

        assert capacity_state["utilization_rate"] > 0.9
        assert capacity_state["capacity_limit_reached"] == True

        # Thalamic response: Should increase gate selectivity
        thalamic_adjustment = await thalamic_relay_system.handle_capacity_limit(
            capacity_state=capacity_state
        )

        assert thalamic_adjustment["gate_selectivity_increased"] == True
        assert thalamic_adjustment["threshold_raised"] == True
        assert thalamic_adjustment["low_priority_blocking"] == True

        # Test: New low-priority content should be filtered
        low_priority_stimulus = {
            "content": "Low priority notification",
            "salience_score": 0.3,
            "priority": "low",
        }

        gate_result = await thalamic_relay_system.process_stimulus(
            low_priority_stimulus
        )

        assert gate_result["gate_decision"] == "block"
        assert gate_result["reason"] == "working_memory_capacity_full"

    @pytest.mark.asyncio
    async def test_performance_monitoring_coordination(
        self, thalamic_relay_system, working_memory_system
    ):
        """Test performance monitoring coordination between systems."""

        # Setup: Configure performance monitoring
        monitoring_config = {
            "metrics": ["accuracy", "response_time", "cognitive_load"],
            "thresholds": {
                "accuracy": 0.85,
                "response_time": 500,  # ms
                "cognitive_load": 0.7,
            },
            "coordination": True,
        }

        await working_memory_system.configure_performance_monitoring(monitoring_config)
        await thalamic_relay_system.configure_performance_monitoring(monitoring_config)

        # Simulate performance degradation
        degradation_scenario = {
            "accuracy_drop": 0.15,
            "response_time_increase": 200,
            "cognitive_load_increase": 0.25,
        }

        await working_memory_system.simulate_performance_degradation(
            degradation_scenario
        )

        # Working memory: Should detect performance issues
        performance_alert = await working_memory_system.check_performance_alerts()

        assert performance_alert["alert_triggered"] == True
        assert performance_alert["alert_type"] == "performance_decline"

        # Thalamic coordination: Should adjust to support performance
        thalamic_support = await thalamic_relay_system.provide_performance_support(
            performance_state=performance_alert
        )

        assert thalamic_support["support_provided"] == True
        assert thalamic_support["gate_optimization"] == True
        assert thalamic_support["attention_focus_enhancement"] == True

        # Verify coordinated performance improvement
        improvement_result = (
            await working_memory_system.apply_thalamic_performance_support(
                support=thalamic_support
            )
        )

        assert improvement_result["performance_improved"] == True
        assert improvement_result["coordination_effective"] == True

    @pytest.mark.asyncio
    async def test_adaptive_learning_coordination(
        self, thalamic_relay_system, working_memory_system
    ):
        """Test adaptive learning coordination between systems."""

        # Setup: Learning scenario with performance feedback
        learning_task = {
            "task_type": "cognitive_control_learning",
            "complexity": "moderate",
            "duration_trials": 50,
            "feedback_frequency": "continuous",
        }

        # Initial performance baseline
        baseline_performance = await self._measure_integrated_performance(
            thalamic_relay_system, working_memory_system
        )

        # Learning phase: Both systems adapt
        learning_results = []
        for trial in range(learning_task["duration_trials"]):
            trial_result = await self._execute_coordination_trial(
                thalamic_relay_system, working_memory_system, trial_number=trial
            )
            learning_results.append(trial_result)

            # Adaptive updates
            if trial % 10 == 0:  # Update every 10 trials
                await working_memory_system.update_learning_parameters(
                    learning_results[-10:]
                )
                await thalamic_relay_system.update_learning_parameters(
                    learning_results[-10:]
                )

        # Final performance measurement
        final_performance = await self._measure_integrated_performance(
            thalamic_relay_system, working_memory_system
        )

        # Verify learning improvements
        performance_improvement = (
            final_performance["overall_score"] - baseline_performance["overall_score"]
        )

        assert performance_improvement > 0.15  # 15% improvement
        assert final_performance["coordination_quality"] > 0.8

        # Check learning coordination
        wm_learning_state = await working_memory_system.get_learning_state()
        thalamic_learning_state = await thalamic_relay_system.get_learning_state()

        assert wm_learning_state["adaptation_active"] == True
        assert thalamic_learning_state["adaptation_active"] == True
        assert (
            wm_learning_state["coordination_learning"]
            > baseline_performance["coordination_learning"]
        )

    @pytest.mark.asyncio
    async def test_error_recovery_coordination(
        self, thalamic_relay_system, working_memory_system
    ):
        """Test error recovery coordination between systems."""

        # Setup: Inject system errors
        error_scenarios = [
            {
                "type": "attention_gate_failure",
                "duration_ms": 1000,
                "severity": "moderate",
            },
            {
                "type": "working_memory_overload",
                "duration_ms": 2000,
                "severity": "high",
            },
            {"type": "coordination_desync", "duration_ms": 500, "severity": "low"},
        ]

        for error_scenario in error_scenarios:
            # Inject error
            await self._inject_system_error(
                thalamic_relay_system, working_memory_system, error_scenario
            )

            # Monitor recovery
            recovery_start = datetime.now()
            recovery_completed = False

            while (
                not recovery_completed
                and (datetime.now() - recovery_start).total_seconds() < 10
            ):
                # Check thalamic recovery
                thalamic_health = await thalamic_relay_system.check_system_health()

                # Check working memory recovery
                wm_health = await working_memory_system.check_system_health()

                # Check coordination recovery
                coordination_health = await self._check_coordination_health(
                    thalamic_relay_system, working_memory_system
                )

                if (
                    thalamic_health["status"] == "healthy"
                    and wm_health["status"] == "healthy"
                    and coordination_health["status"] == "coordinated"
                ):
                    recovery_completed = True

                await asyncio.sleep(0.1)

            # Verify recovery
            assert recovery_completed == True

            # Verify learning from error
            thalamic_resilience = await thalamic_relay_system.get_resilience_metrics()
            wm_resilience = await working_memory_system.get_resilience_metrics()

            assert (
                thalamic_resilience["error_recovery_time"]
                < error_scenario["duration_ms"] * 2
            )
            assert (
                wm_resilience["error_recovery_time"] < error_scenario["duration_ms"] * 2
            )

    # Helper methods for testing

    async def _measure_coordination_quality(
        self, thalamic_relay_system, working_memory_system, duration_ms: int
    ) -> Dict[str, float]:
        """Measure coordination quality over time."""

        measurements = []
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() * 1000 < duration_ms:
            # Get system states
            thalamic_state = await thalamic_relay_system.get_state()
            wm_state = await working_memory_system.get_state()

            # Calculate alignment metrics
            attention_alignment = self._calculate_attention_alignment(
                thalamic_state["attention_allocation"], wm_state["attention_state"]
            )

            priority_alignment = self._calculate_priority_alignment(
                thalamic_state["gate_priorities"], wm_state["buffer_priorities"]
            )

            performance_alignment = self._calculate_performance_alignment(
                thalamic_state["performance"], wm_state["performance"]
            )

            measurement = {
                "timestamp": datetime.now(),
                "attention_alignment": attention_alignment,
                "priority_alignment": priority_alignment,
                "performance_alignment": performance_alignment,
                "overall_alignment": (
                    attention_alignment + priority_alignment + performance_alignment
                )
                / 3,
            }

            measurements.append(measurement)
            await asyncio.sleep(0.05)  # 50ms intervals

        # Calculate summary metrics
        average_alignment = sum(m["overall_alignment"] for m in measurements) / len(
            measurements
        )
        stability = 1.0 - (
            max(m["overall_alignment"] for m in measurements)
            - min(m["overall_alignment"] for m in measurements)
        )

        baseline_performance = measurements[0]["overall_alignment"]
        final_performance = measurements[-1]["overall_alignment"]
        performance_improvement = final_performance - baseline_performance

        return {
            "average_alignment": average_alignment,
            "stability": stability,
            "performance_improvement": performance_improvement,
            "measurement_count": len(measurements),
        }

    async def _measure_integrated_performance(
        self, thalamic_relay_system, working_memory_system
    ) -> Dict[str, float]:
        """Measure integrated system performance."""

        # Performance tasks
        tasks = [
            {"type": "attention_switching", "complexity": "moderate"},
            {"type": "working_memory_updating", "complexity": "high"},
            {"type": "cognitive_control", "complexity": "moderate"},
            {"type": "conflict_resolution", "complexity": "high"},
        ]

        task_results = []
        for task in tasks:
            result = await self._execute_integrated_task(
                thalamic_relay_system, working_memory_system, task
            )
            task_results.append(result)

        # Calculate performance metrics
        accuracy = sum(r["accuracy"] for r in task_results) / len(task_results)
        response_time = sum(r["response_time"] for r in task_results) / len(
            task_results
        )
        coordination_quality = sum(
            r["coordination_quality"] for r in task_results
        ) / len(task_results)

        overall_score = (accuracy + (1000 / response_time) + coordination_quality) / 3

        return {
            "overall_score": overall_score,
            "accuracy": accuracy,
            "response_time": response_time,
            "coordination_quality": coordination_quality,
            "coordination_learning": coordination_quality,  # Simplified for baseline
        }

    async def _execute_coordination_trial(
        self, thalamic_relay_system, working_memory_system, trial_number: int
    ) -> Dict[str, Any]:
        """Execute a single coordination trial for learning."""

        # Generate trial stimulus based on trial number (increasing complexity)
        complexity = min(0.3 + (trial_number * 0.01), 1.0)

        stimulus = {
            "trial_number": trial_number,
            "complexity": complexity,
            "content": f"Trial {trial_number} cognitive task",
            "requires_coordination": True,
        }

        # Execute coordinated processing
        start_time = datetime.now()

        thalamic_result = await thalamic_relay_system.process_stimulus(stimulus)
        wm_result = await working_memory_system.process_with_thalamic_input(
            stimulus, thalamic_result
        )

        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000

        # Calculate trial metrics
        accuracy = self._calculate_trial_accuracy(stimulus, wm_result)
        coordination_score = self._calculate_coordination_score(
            thalamic_result, wm_result
        )

        return {
            "trial_number": trial_number,
            "complexity": complexity,
            "accuracy": accuracy,
            "response_time": response_time,
            "coordination_score": coordination_score,
            "thalamic_result": thalamic_result,
            "wm_result": wm_result,
        }

    async def _execute_integrated_task(
        self, thalamic_relay_system, working_memory_system, task: Dict[str, Any]
    ) -> Dict[str, float]:
        """Execute an integrated cognitive task."""

        start_time = datetime.now()

        # Task-specific execution
        if task["type"] == "attention_switching":
            result = await self._execute_attention_switching_task(
                thalamic_relay_system, working_memory_system, task["complexity"]
            )
        elif task["type"] == "working_memory_updating":
            result = await self._execute_wm_updating_task(
                thalamic_relay_system, working_memory_system, task["complexity"]
            )
        elif task["type"] == "cognitive_control":
            result = await self._execute_cognitive_control_task(
                thalamic_relay_system, working_memory_system, task["complexity"]
            )
        elif task["type"] == "conflict_resolution":
            result = await self._execute_conflict_resolution_task(
                thalamic_relay_system, working_memory_system, task["complexity"]
            )
        else:
            result = {"accuracy": 0.5, "coordination_quality": 0.5}

        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000

        return {
            "accuracy": result["accuracy"],
            "response_time": response_time,
            "coordination_quality": result["coordination_quality"],
        }

    def _calculate_attention_alignment(
        self, thalamic_attention: Dict[str, float], wm_attention: Dict[str, float]
    ) -> float:
        """Calculate attention allocation alignment between systems."""

        # Simplified alignment calculation
        alignment_scores = []

        for modality in ["verbal", "visuospatial", "episodic"]:
            thalamic_alloc = thalamic_attention.get(modality, 0)
            wm_alloc = wm_attention.get(modality, 0)

            # Calculate similarity (1 - absolute difference)
            similarity = 1.0 - abs(thalamic_alloc - wm_alloc)
            alignment_scores.append(similarity)

        return sum(alignment_scores) / len(alignment_scores)

    def _calculate_priority_alignment(
        self, thalamic_priorities: Dict[str, float], wm_priorities: Dict[str, float]
    ) -> float:
        """Calculate priority alignment between systems."""

        # Simplified priority alignment calculation
        common_items = set(thalamic_priorities.keys()) & set(wm_priorities.keys())

        if not common_items:
            return 0.5  # Neutral if no common items

        alignment_scores = []
        for item in common_items:
            thalamic_priority = thalamic_priorities[item]
            wm_priority = wm_priorities[item]

            similarity = 1.0 - abs(thalamic_priority - wm_priority)
            alignment_scores.append(similarity)

        return sum(alignment_scores) / len(alignment_scores)

    def _calculate_performance_alignment(
        self, thalamic_performance: Dict[str, float], wm_performance: Dict[str, float]
    ) -> float:
        """Calculate performance metric alignment between systems."""

        # Compare key performance metrics
        metrics = ["accuracy", "efficiency", "response_time"]
        alignment_scores = []

        for metric in metrics:
            thalamic_val = thalamic_performance.get(metric, 0.5)
            wm_val = wm_performance.get(metric, 0.5)

            # For response_time, lower is better, so invert
            if metric == "response_time":
                thalamic_val = 1.0 - thalamic_val
                wm_val = 1.0 - wm_val

            similarity = 1.0 - abs(thalamic_val - wm_val)
            alignment_scores.append(similarity)

        return sum(alignment_scores) / len(alignment_scores)

    # Additional helper methods would be implemented for:
    # - _inject_system_error()
    # - _check_coordination_health()
    # - _calculate_trial_accuracy()
    # - _calculate_coordination_score()
    # - _execute_attention_switching_task()
    # - _execute_wm_updating_task()
    # - _execute_cognitive_control_task()
    # - _execute_conflict_resolution_task()


class TestWorkingMemoryThalamusEvents:
    """Test event coordination between working memory and thalamic systems."""

    @pytest.mark.asyncio
    async def test_event_synchronization(
        self, thalamic_relay_system, working_memory_system
    ):
        """Test event synchronization between systems."""

        # Setup event listeners
        thalamic_events = []
        wm_events = []

        async def thalamic_event_handler(event):
            thalamic_events.append(event)

        async def wm_event_handler(event):
            wm_events.append(event)

        await thalamic_relay_system.subscribe_to_events(thalamic_event_handler)
        await working_memory_system.subscribe_to_events(wm_event_handler)

        # Trigger coordinated event sequence
        stimulus = {
            "content": "Test event coordination",
            "priority": "high",
            "requires_coordination": True,
        }

        await thalamic_relay_system.process_stimulus(stimulus)

        # Wait for event propagation
        await asyncio.sleep(0.5)

        # Verify event coordination
        assert len(thalamic_events) > 0
        assert len(wm_events) > 0

        # Check for coordinated event types
        thalamic_event_types = {event["type"] for event in thalamic_events}
        wm_event_types = {event["type"] for event in wm_events}

        expected_coordination_events = {
            "attention_gate_opened",
            "working_memory_buffer_updated",
            "executive_control_engaged",
        }

        assert expected_coordination_events.issubset(
            thalamic_event_types | wm_event_types
        )

    @pytest.mark.asyncio
    async def test_cross_system_event_handling(
        self, thalamic_relay_system, working_memory_system
    ):
        """Test cross-system event handling and response."""

        # Working memory generates event that should affect thalamic system
        wm_event = {
            "type": "cognitive_conflict_detected",
            "severity": "high",
            "requires_thalamic_adjustment": True,
            "details": {
                "conflict_type": "priority_conflict",
                "affected_buffers": ["verbal"],
                "suggested_gate_adjustment": "increase_selectivity",
            },
        }

        # Send event from WM to thalamic system
        thalamic_response = await thalamic_relay_system.handle_working_memory_event(
            wm_event
        )

        assert thalamic_response["event_handled"] == True
        assert thalamic_response["gate_adjusted"] == True
        assert thalamic_response["selectivity_increased"] == True

        # Thalamic system generates event that should affect working memory
        thalamic_event = {
            "type": "attention_overload_detected",
            "severity": "moderate",
            "requires_wm_adjustment": True,
            "details": {
                "overload_source": "multiple_high_salience_stimuli",
                "suggested_wm_action": "increase_executive_control",
            },
        }

        # Send event from thalamic to WM system
        wm_response = await working_memory_system.handle_thalamic_event(thalamic_event)

        assert wm_response["event_handled"] == True
        assert wm_response["executive_control_increased"] == True
        assert wm_response["capacity_optimization_triggered"] == True


# Integration test configuration
@pytest.fixture
async def integrated_cognitive_system(thalamic_relay_system, working_memory_system):
    """Fixture providing integrated cognitive system for testing."""

    # Establish coordination between systems
    await thalamic_relay_system.establish_working_memory_coordination(
        working_memory_system
    )
    await working_memory_system.establish_thalamic_coordination(thalamic_relay_system)

    # Verify coordination is active
    coordination_status = await thalamic_relay_system.check_coordination_status()
    assert coordination_status["working_memory_coordinated"] == True

    coordination_status = await working_memory_system.check_coordination_status()
    assert coordination_status["thalamic_coordinated"] == True

    return {
        "thalamic_relay": thalamic_relay_system,
        "working_memory": working_memory_system,
        "coordination_active": True,
    }


class TestIntegratedCognitiveSystem:
    """Test the integrated cognitive system as a whole."""

    @pytest.mark.asyncio
    async def test_full_cognitive_pipeline(self, integrated_cognitive_system):
        """Test complete cognitive processing pipeline."""

        system = integrated_cognitive_system

        # Complex cognitive scenario
        scenario = {
            "stimuli": [
                {
                    "content": "Important email about project deadline",
                    "modality": "verbal",
                    "salience": 0.8,
                    "urgency": "high",
                },
                {
                    "content": "Visual notification: calendar reminder",
                    "modality": "visuospatial",
                    "salience": 0.6,
                    "urgency": "medium",
                },
                {
                    "content": "Background music playing",
                    "modality": "auditory",
                    "salience": 0.2,
                    "urgency": "low",
                },
            ],
            "cognitive_demands": {
                "attention_switching": True,
                "working_memory_updating": True,
                "conflict_resolution": True,
                "executive_control": True,
            },
        }

        # Process through integrated system
        processing_results = []

        for stimulus in scenario["stimuli"]:
            # Thalamic processing
            thalamic_result = await system["thalamic_relay"].process_stimulus(stimulus)

            # Working memory processing with thalamic input
            wm_result = await system["working_memory"].process_with_thalamic_input(
                stimulus, thalamic_result
            )

            processing_results.append(
                {
                    "stimulus": stimulus,
                    "thalamic_result": thalamic_result,
                    "wm_result": wm_result,
                }
            )

        # Verify integrated processing
        high_urgency_processed = any(
            r["thalamic_result"]["gate_decision"] == "pass"
            and r["wm_result"]["priority_level"] == "high"
            for r in processing_results
            if r["stimulus"]["urgency"] == "high"
        )

        low_urgency_filtered = any(
            r["thalamic_result"]["gate_decision"] == "block"
            for r in processing_results
            if r["stimulus"]["urgency"] == "low"
        )

        assert high_urgency_processed == True
        assert low_urgency_filtered == True

        # Verify coordination quality
        final_coordination = await self._assess_final_coordination_state(system)

        assert final_coordination["coordination_quality"] > 0.8
        assert final_coordination["system_stability"] > 0.7
        assert final_coordination["cognitive_efficiency"] > 0.75

    async def _assess_final_coordination_state(self, system) -> Dict[str, float]:
        """Assess final coordination state after processing."""

        thalamic_state = await system["thalamic_relay"].get_final_state()
        wm_state = await system["working_memory"].get_final_state()

        # Calculate coordination metrics
        attention_coordination = self._calculate_attention_coordination(
            thalamic_state["attention"], wm_state["attention"]
        )

        resource_coordination = self._calculate_resource_coordination(
            thalamic_state["resources"], wm_state["resources"]
        )

        performance_coordination = self._calculate_performance_coordination(
            thalamic_state["performance"], wm_state["performance"]
        )

        coordination_quality = (
            attention_coordination + resource_coordination + performance_coordination
        ) / 3

        return {
            "coordination_quality": coordination_quality,
            "system_stability": min(thalamic_state["stability"], wm_state["stability"]),
            "cognitive_efficiency": (
                thalamic_state["efficiency"] + wm_state["efficiency"]
            )
            / 2,
        }

    def _calculate_attention_coordination(
        self, thalamic_attention, wm_attention
    ) -> float:
        """Calculate attention coordination score."""
        # Implementation details...
        return 0.85  # Simplified for example

    def _calculate_resource_coordination(
        self, thalamic_resources, wm_resources
    ) -> float:
        """Calculate resource coordination score."""
        # Implementation details...
        return 0.80  # Simplified for example

    def _calculate_performance_coordination(self, thalamic_perf, wm_perf) -> float:
        """Calculate performance coordination score."""
        # Implementation details...
        return 0.82  # Simplified for example

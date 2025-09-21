"""
Additional integration test utilities for Working Memory System.

Provides helper classes and functions for comprehensive testing
of working memory system integration with other cognitive systems.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict


class IntegrationTestUtils:
    """Utility class for integration testing."""

    @staticmethod
    async def inject_system_error(
        thalamic_relay_system: Any,
        working_memory_system: Any,
        error_scenario: Dict[str, Any],
    ) -> None:
        """Inject system error for testing error recovery."""

        error_type = error_scenario["type"]
        duration_ms = error_scenario["duration_ms"]
        severity = error_scenario["severity"]

        if error_type == "attention_gate_failure":
            # Simulate attention gate failure
            await thalamic_relay_system._simulate_gate_failure(duration_ms, severity)
        elif error_type == "working_memory_overload":
            # Simulate working memory overload
            await working_memory_system._simulate_overload(duration_ms, severity)
        elif error_type == "coordination_desync":
            # Simulate coordination desynchronization
            await IntegrationTestUtils._simulate_coordination_desync(
                thalamic_relay_system, working_memory_system, duration_ms, severity
            )

    @staticmethod
    async def check_coordination_health(
        thalamic_relay_system: Any, working_memory_system: Any
    ) -> Dict[str, Any]:
        """Check coordination health between systems."""

        # Get individual system health
        thalamic_health = await thalamic_relay_system.check_system_health()
        wm_health = await working_memory_system.check_system_health()

        # Check coordination metrics
        coordination_metrics = await IntegrationTestUtils._measure_coordination_metrics(
            thalamic_relay_system, working_memory_system
        )

        # Determine overall coordination health
        if (
            thalamic_health["status"] == "healthy"
            and wm_health["status"] == "healthy"
            and coordination_metrics["alignment"] > 0.7
        ):
            status = "coordinated"
        else:
            status = "degraded"

        return {
            "status": status,
            "thalamic_health": thalamic_health,
            "wm_health": wm_health,
            "coordination_metrics": coordination_metrics,
        }

    @staticmethod
    async def _simulate_coordination_desync(
        thalamic_relay_system: Any,
        working_memory_system: Any,
        duration_ms: int,
        severity: str,
    ) -> None:
        """Simulate coordination desynchronization."""

        # Temporarily disrupt coordination signals
        if hasattr(thalamic_relay_system, "_coordination_disrupted"):
            thalamic_relay_system._coordination_disrupted = True
        if hasattr(working_memory_system, "_coordination_disrupted"):
            working_memory_system._coordination_disrupted = True

        # Wait for disruption duration
        await asyncio.sleep(duration_ms / 1000.0)

        # Restore coordination
        if hasattr(thalamic_relay_system, "_coordination_disrupted"):
            thalamic_relay_system._coordination_disrupted = False
        if hasattr(working_memory_system, "_coordination_disrupted"):
            working_memory_system._coordination_disrupted = False

    @staticmethod
    async def _measure_coordination_metrics(
        thalamic_relay_system: Any, working_memory_system: Any
    ) -> Dict[str, float]:
        """Measure coordination metrics between systems."""

        # Get current states
        thalamic_state = await thalamic_relay_system.get_state()
        wm_state = await working_memory_system.get_state()

        # Calculate basic alignment metrics
        attention_alignment = IntegrationTestUtils._calculate_attention_alignment(
            thalamic_state.get("attention_allocation", {}),
            wm_state.get("attention_state", {}),
        )

        # Calculate response time correlation
        thalamic_rt = thalamic_state.get("performance", {}).get("response_time", 500)
        wm_rt = wm_state.get("performance", {}).get("response_time", 500)
        rt_correlation = 1.0 - abs(thalamic_rt - wm_rt) / max(thalamic_rt, wm_rt)

        overall_alignment = (attention_alignment + rt_correlation) / 2

        return {
            "alignment": overall_alignment,
            "attention_alignment": attention_alignment,
            "response_time_correlation": rt_correlation,
        }

    @staticmethod
    def _calculate_attention_alignment(
        thalamic_attention: Dict[str, Any], wm_attention: Dict[str, Any]
    ) -> float:
        """Calculate attention allocation alignment."""

        if not thalamic_attention or not wm_attention:
            return 0.5  # Neutral if no data

        # Compare attention allocations for each modality
        modalities = ["verbal", "visuospatial", "episodic"]
        alignment_scores = []

        for modality in modalities:
            thalamic_alloc = thalamic_attention.get(modality, 0.33)
            wm_alloc = wm_attention.get(modality, 0.33)

            # Calculate similarity (1 - absolute difference)
            similarity = 1.0 - abs(float(thalamic_alloc) - float(wm_alloc))
            alignment_scores.append(similarity)

        return sum(alignment_scores) / len(alignment_scores)


class CognitiveTaskRunner:
    """Helper class for running cognitive tasks in integration tests."""

    def __init__(self, thalamic_system: Any, working_memory_system: Any):
        self.thalamic_system = thalamic_system
        self.working_memory_system = working_memory_system

    async def execute_attention_switching_task(
        self, complexity: str
    ) -> Dict[str, float]:
        """Execute attention switching task."""

        # Define task parameters based on complexity
        if complexity == "moderate":
            switch_frequency = 2  # switches per second
            task_duration = 3.0  # seconds
            accuracy_target = 0.85
        else:  # high complexity
            switch_frequency = 4
            task_duration = 5.0
            accuracy_target = 0.75

        start_time = datetime.now()
        switches_completed = 0
        correct_responses = 0

        # Simulate attention switching
        for i in range(int(switch_frequency * task_duration)):
            # Alternate between verbal and visuospatial attention
            target_modality = "verbal" if i % 2 == 0 else "visuospatial"

            # Request attention switch through thalamic system
            switch_stimulus = {
                "type": "attention_switch_cue",
                "target_modality": target_modality,
                "salience": 0.8,
            }

            thalamic_result = await self.thalamic_system.process_stimulus(
                switch_stimulus
            )

            if thalamic_result.get("gate_decision") == "pass":
                # Process through working memory
                wm_result = (
                    await self.working_memory_system.process_with_thalamic_input(
                        switch_stimulus, thalamic_result
                    )
                )

                switches_completed += 1

                # Simulate response accuracy based on coordination quality
                coordination_quality = wm_result.get("coordination_score", 0.5)
                if coordination_quality > 0.6:
                    correct_responses += 1

            # Wait for next switch
            await asyncio.sleep(1.0 / switch_frequency)

        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000

        accuracy = correct_responses / max(switches_completed, 1)
        coordination_quality = accuracy  # Simplified measure

        return {"accuracy": accuracy, "coordination_quality": coordination_quality}

    async def execute_wm_updating_task(self, complexity: str) -> Dict[str, float]:
        """Execute working memory updating task."""

        # Define task parameters
        if complexity == "moderate":
            update_frequency = 1  # updates per second
            task_duration = 4.0
            accuracy_target = 0.80
        else:  # high complexity
            update_frequency = 2
            task_duration = 6.0
            accuracy_target = 0.70

        start_time = datetime.now()
        updates_completed = 0
        correct_updates = 0

        # Simulate working memory updating
        for i in range(int(update_frequency * task_duration)):
            # Create update stimulus
            update_stimulus = {
                "type": "memory_update",
                "content": f"Update item {i}",
                "operation": "replace" if i % 3 == 0 else "add",
                "priority": "high" if i % 2 == 0 else "normal",
                "salience": 0.7,
            }

            # Process through systems
            thalamic_result = await self.thalamic_system.process_stimulus(
                update_stimulus
            )

            if thalamic_result.get("gate_decision") == "pass":
                wm_result = (
                    await self.working_memory_system.process_with_thalamic_input(
                        update_stimulus, thalamic_result
                    )
                )

                updates_completed += 1

                # Check if update was successful
                if wm_result.get("processed", False):
                    correct_updates += 1

            await asyncio.sleep(1.0 / update_frequency)

        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000

        accuracy = correct_updates / max(updates_completed, 1)
        coordination_quality = accuracy * 0.9  # Slightly lower for complexity

        return {"accuracy": accuracy, "coordination_quality": coordination_quality}

    async def execute_cognitive_control_task(self, complexity: str) -> Dict[str, float]:
        """Execute cognitive control task."""

        # Simulate Stroop-like interference task
        if complexity == "moderate":
            interference_level = 0.3
            task_duration = 3.0
        else:  # high complexity
            interference_level = 0.6
            task_duration = 5.0

        start_time = datetime.now()
        trials_completed = 0
        correct_responses = 0

        # Simulate cognitive control trials
        for i in range(10):  # Fixed number of trials
            # Create interference stimulus
            interference_stimulus = {
                "type": "interference_task",
                "interference_level": interference_level,
                "requires_control": True,
                "salience": 0.8,
            }

            # Engage executive control
            control_request = {
                "control_type": "cognitive_control",
                "control_intensity": 0.8,
                "target": "interference_resolution",
            }

            executive_result = await self.working_memory_system.apply_executive_control(
                control_request
            )

            # Process with thalamic coordination
            thalamic_result = (
                await self.thalamic_system.coordinate_with_executive_control(
                    executive_result["executive_state"]
                )
            )

            trials_completed += 1

            # Success based on coordination quality
            if executive_result.get("control_applied", False) and thalamic_result.get(
                "gate_aligned", False
            ):
                # Higher success rate with better coordination
                success_probability = 0.9 - (interference_level * 0.3)
                if success_probability > 0.6:  # Simplified
                    correct_responses += 1

            await asyncio.sleep(task_duration / 10)

        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000

        accuracy = correct_responses / max(trials_completed, 1)
        coordination_quality = accuracy * (1 - interference_level * 0.2)

        return {"accuracy": accuracy, "coordination_quality": coordination_quality}

    async def execute_conflict_resolution_task(
        self, complexity: str
    ) -> Dict[str, float]:
        """Execute conflict resolution task."""

        # Simulate competing task demands
        if complexity == "moderate":
            conflict_intensity = 0.4
            resolution_threshold = 0.7
        else:  # high complexity
            conflict_intensity = 0.7
            resolution_threshold = 0.8

        start_time = datetime.now()
        conflicts_detected = 0
        conflicts_resolved = 0

        # Simulate conflict scenarios
        for i in range(5):  # Multiple conflict scenarios
            # Create conflicting stimuli
            conflict_stimuli = [
                {
                    "type": "task_demand_A",
                    "priority": "high",
                    "urgency": "immediate",
                    "salience": 0.8,
                },
                {
                    "type": "task_demand_B",
                    "priority": "critical",
                    "urgency": "immediate",
                    "salience": 0.9,
                },
            ]

            # Process conflicting stimuli
            for stimulus in conflict_stimuli:
                thalamic_result = await self.thalamic_system.process_stimulus(stimulus)
                await self.working_memory_system.process_with_thalamic_input(
                    stimulus, thalamic_result
                )

            # Monitor for conflicts
            conflict_detected = await self.working_memory_system.monitor_conflicts()

            if conflict_detected.get("conflict_type"):
                conflicts_detected += 1

                # Attempt resolution with thalamic support
                thalamic_support = (
                    await self.thalamic_system.handle_working_memory_conflict(
                        conflict_detected
                    )
                )

                resolution_result = await self.working_memory_system.resolve_conflict_with_thalamic_support(
                    conflict_detected.get("conflict_id", "unknown"), thalamic_support
                )

                if resolution_result.get("resolution_success", False):
                    conflicts_resolved += 1

            await asyncio.sleep(0.5)  # Brief pause between scenarios

        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000

        accuracy = conflicts_resolved / max(conflicts_detected, 1)
        coordination_quality = accuracy * (1 - conflict_intensity * 0.1)

        return {"accuracy": accuracy, "coordination_quality": coordination_quality}


# Helper functions for trial calculations


def calculate_trial_accuracy(
    stimulus: Dict[str, Any], wm_result: Dict[str, Any]
) -> float:
    """Calculate accuracy for a single trial."""

    complexity = stimulus.get("complexity", 0.5)
    coordination_score = wm_result.get("coordination_score", 0.5)

    # Base accuracy depends on coordination quality
    base_accuracy = coordination_score

    # Adjust for complexity
    complexity_penalty = complexity * 0.2
    final_accuracy = max(0.0, base_accuracy - complexity_penalty)

    return final_accuracy


def calculate_coordination_score(
    thalamic_result: Dict[str, Any], wm_result: Dict[str, Any]
) -> float:
    """Calculate coordination score between thalamic and WM results."""

    # Check if both systems processed successfully
    thalamic_success = thalamic_result.get("gate_decision") == "pass"
    wm_success = wm_result.get("processed", False)

    if not (thalamic_success and wm_success):
        return 0.0

    # Calculate based on attention allocation alignment
    thalamic_attention = thalamic_result.get("attention_allocation", 0.5)
    wm_attention = wm_result.get("coordination_score", 0.5)

    # Coordination quality is similarity between attention allocations
    coordination = 1.0 - abs(thalamic_attention - wm_attention)

    return coordination

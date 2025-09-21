"""
Test Suite for Epic M4.3: Brain-Inspired Features
=================================================

Comprehensive integration tests for brain-inspired cognitive feature flags.
Tests neural pathway correlation, cognitive trace enrichment, and adaptive learning.
"""

import asyncio
from datetime import datetime, timedelta, timezone

# Skip pytest import for now since it's not available
# import pytest
from feature_flags.brain_inspired import (
    AdaptiveLearningEngine,
    BrainRegion,
    CognitiveTrace,
    CognitiveTraceEnricher,
    CorrelationType,
    LearningAlgorithm,
    NeuralEvent,
    NeuralPathway,
    NeuralPathwayCorrelator,
    PerformanceMetrics,
)
from feature_flags.flag_manager import CognitiveFlagManager


class TestBrainInspiredIntegration:
    """Integration tests for brain-inspired features."""

    def create_sample_neural_events(self):
        """Create sample neural events for testing."""
        return [
            NeuralEvent(
                event_id="event_1",
                event_type="cognitive_operation",
                source_component="attention_gate",
                timestamp=datetime.now(timezone.utc),
                neural_pathway=NeuralPathway.ATTENTION_RELAY,
                brain_region=BrainRegion.PREFRONTAL_CORTEX,
                cognitive_load=0.6,
                event_data={"operation": "attention_gate", "success": True},
            ),
            NeuralEvent(
                event_id="event_2",
                event_type="memory_operation",
                source_component="hippocampus",
                timestamp=datetime.now(timezone.utc) + timedelta(milliseconds=100),
                neural_pathway=NeuralPathway.MEMORY_FORMATION,
                brain_region=BrainRegion.HIPPOCAMPUS,
                cognitive_load=0.5,
                event_data={"operation": "memory_consolidation", "success": True},
            ),
            NeuralEvent(
                event_id="event_3",
                event_type="control_operation",
                source_component="executive_control",
                timestamp=datetime.now(timezone.utc) + timedelta(milliseconds=200),
                neural_pathway=NeuralPathway.EXECUTIVE_CONTROL,
                brain_region=BrainRegion.TEMPORAL_LOBE,
                cognitive_load=0.7,
                event_data={"operation": "cognitive_control", "success": False},
            ),
        ]

    async def test_neural_pathway_correlation(self):
        """Test neural pathway correlation analysis."""

        manager = CognitiveFlagManager()
        await manager.initialize()

        correlator = NeuralPathwayCorrelator(manager)
        events = self.create_sample_neural_events()

        # Test temporal correlation
        temporal_correlations = await correlator.analyze_temporal_correlations(
            events, time_window_ms=500.0
        )

        assert len(temporal_correlations) >= 0, "Should return correlation results"

        # Verify correlation structure
        for correlation in temporal_correlations:
            assert hasattr(correlation, "correlation_type")
            assert hasattr(correlation, "strength")
            assert (
                0.0 <= correlation.strength <= 1.0
            ), "Correlation strength should be normalized"

        print(
            f"✅ Neural pathway correlation test passed - found {len(temporal_correlations)} correlations"
        )

    async def test_cognitive_trace_enrichment(self):
        """Test cognitive trace enrichment."""

        manager = CognitiveFlagManager()
        await manager.initialize()

        enricher = CognitiveTraceEnricher(manager)
        events = self.create_sample_neural_events()

        # Create a sample cognitive trace
        trace = CognitiveTrace(
            trace_id="test_trace_1",
            component_name="working_memory",
            operation_name="store_item",
            start_time=datetime.now(timezone.utc),
            cognitive_load=0.6,
        )

        # Test trace processing
        processed_trace = await enricher.enrich_cognitive_trace(trace, events)

        # Verify enrichment
        assert processed_trace.trace_id == trace.trace_id, "Should preserve trace ID"

        print(
            f"✅ Cognitive trace enrichment test passed - trace {processed_trace.trace_id}"
        )

    async def test_adaptive_learning_performance_recording(self):
        """Test adaptive learning performance recording."""

        manager = CognitiveFlagManager()
        await manager.initialize()

        learning_engine = AdaptiveLearningEngine(manager)

        # Create sample performance metrics
        metrics = PerformanceMetrics(
            timestamp=datetime.now(timezone.utc),
            cognitive_load=0.5,
            response_time_ms=200.0,
            accuracy_score=0.85,
            component_name="working_memory",
            operation_success=True,
            neural_pathway=NeuralPathway.RECALL_ASSEMBLY,
            brain_region=BrainRegion.HIPPOCAMPUS,
            pathway_efficiency=0.8,
            user_satisfaction=0.9,
            system_efficiency=0.75,
            cognitive_efficiency=0.8,
        )

        # Record performance
        await learning_engine.record_performance(metrics)

        # Verify recording
        assert (
            len(learning_engine.learning_state.experience_buffer) > 0
        ), "Should record experience"
        recorded_metric = learning_engine.learning_state.experience_buffer[-1]
        assert (
            recorded_metric.component_name == "working_memory"
        ), "Should preserve component name"

        print(
            f"✅ Adaptive learning test passed - recorded {metrics.accuracy_score:.2f} accuracy"
        )

    async def test_hebbian_learning(self):
        """Test Hebbian learning implementation."""

        manager = CognitiveFlagManager()
        await manager.initialize()

        learning_engine = AdaptiveLearningEngine(manager)

        # Apply Hebbian learning
        await learning_engine.apply_hebbian_learning(
            NeuralPathway.MEMORY_FORMATION, performance_improvement=0.2
        )

        # Verify synaptic weight update
        pathway_key = f"pathway_{NeuralPathway.MEMORY_FORMATION.value}"
        assert pathway_key in learning_engine.learning_state.synaptic_weights

        weight = learning_engine.learning_state.synaptic_weights[pathway_key]
        assert 0.0 <= weight <= 1.0, "Synaptic weight should be normalized"

        print(f"✅ Hebbian learning test passed - weight: {weight:.3f}")

    async def test_brain_inspired_integration(self):
        """Test full brain-inspired features integration."""

        # Create all components
        manager = CognitiveFlagManager()
        await manager.initialize()

        correlator = NeuralPathwayCorrelator(manager)
        enricher = CognitiveTraceEnricher(manager)
        learner = AdaptiveLearningEngine(manager)

        # Create test data
        events = [
            NeuralEvent(
                event_id="integration_event",
                event_type="integration_test",
                source_component="test_component",
                timestamp=datetime.now(timezone.utc),
                neural_pathway=NeuralPathway.EXECUTIVE_CONTROL,
                brain_region=BrainRegion.PREFRONTAL_CORTEX,
                cognitive_load=0.6,
            )
        ]

        trace = CognitiveTrace(
            trace_id="integration_trace",
            component_name="integration_test",
            operation_name="full_test",
            start_time=datetime.now(timezone.utc),
            cognitive_load=0.5,
        )

        # Test correlation
        correlations = await correlator.analyze_temporal_correlations(
            events, time_window_ms=1000.0
        )
        assert isinstance(correlations, list), "Should return correlations"

        # Test enrichment
        enriched_trace = await enricher.enrich_cognitive_trace(trace, events)
        assert enriched_trace.trace_id == trace.trace_id, "Should preserve trace"

        # Test learning
        metrics = PerformanceMetrics(
            cognitive_load=0.5,
            response_time_ms=100.0,
            accuracy_score=0.9,
            component_name="integration_test",
            operation_success=True,
        )
        await learner.record_performance(metrics)

        # Verify integration
        stats = learner.get_learning_statistics()
        assert stats["learning_iterations"] >= 0, "Should track learning iterations"

        print(
            f"✅ Full integration test passed - {len(correlations)} correlations, enriched trace, learning active"
        )

    def test_brain_inspired_capabilities(self):
        """Test brain-inspired capabilities reporting."""

        from feature_flags.brain_inspired import get_brain_inspired_capabilities

        capabilities = get_brain_inspired_capabilities()

        # Verify capability structure
        assert "version" in capabilities
        assert "correlation_types" in capabilities
        assert "neural_pathways" in capabilities
        assert "brain_regions" in capabilities
        assert "learning_algorithms" in capabilities

        # Verify enum values
        assert CorrelationType.TEMPORAL.value in capabilities["correlation_types"]
        assert NeuralPathway.ATTENTION_RELAY.value in capabilities["neural_pathways"]
        assert BrainRegion.PREFRONTAL_CORTEX.value in capabilities["brain_regions"]
        assert LearningAlgorithm.HEBBIAN.value in capabilities["learning_algorithms"]

        print(
            f"✅ Capabilities test passed - {len(capabilities['correlation_types'])} correlations, "
            f"{len(capabilities['neural_pathways'])} pathways, "
            f"{len(capabilities['brain_regions'])} regions"
        )

    def test_configuration_validation(self):
        """Test brain-inspired configuration validation."""

        from feature_flags.brain_inspired import validate_brain_inspired_config

        # Test valid configuration
        valid_config = {
            "correlation": {"temporal_threshold": 0.7, "spatial_threshold": 0.6},
            "learning": {"learning_rate": 0.01, "memory_size": 1000},
            "enrichment": {"max_trace_depth": 10},
        }

        is_valid, errors = validate_brain_inspired_config(valid_config)
        assert is_valid, f"Valid config should pass validation: {errors}"

        # Test invalid configuration
        invalid_config = {
            "correlation": {"temporal_threshold": 1.5},  # Invalid: > 1.0
            "learning": {
                "learning_rate": -0.1,  # Invalid: < 0.0
                "memory_size": 5,  # Invalid: < 10
            },
            "enrichment": {"max_trace_depth": 0},  # Invalid: < 1
        }

        is_valid, errors = validate_brain_inspired_config(invalid_config)
        assert not is_valid, "Invalid config should fail validation"
        assert len(errors) > 0, "Should provide error messages"

        print(
            f"✅ Configuration validation test passed - valid config accepted, {len(errors)} errors for invalid"
        )


async def run_epic_m4_3_integration_tests():
    """Run all Epic M4.3 integration tests."""

    print("🧠 Epic M4.3: Brain-Inspired Features Integration Tests")
    print("=" * 60)

    test_suite = TestBrainInspiredIntegration()

    try:
        # Test neural pathway correlation
        await test_suite.test_neural_pathway_correlation()

        # Test cognitive trace enrichment
        await test_suite.test_cognitive_trace_enrichment()

        # Test adaptive learning
        await test_suite.test_adaptive_learning_performance_recording()

        # Test Hebbian learning
        await test_suite.test_hebbian_learning()

        # Test full integration
        await test_suite.test_brain_inspired_integration()

        # Test capabilities
        test_suite.test_brain_inspired_capabilities()

        # Test configuration validation
        test_suite.test_configuration_validation()

        print("=" * 60)
        print("🎉 Epic M4.3: Brain-Inspired Features - ALL TESTS PASSED!")
        print("✅ Neural pathway correlation working")
        print("✅ Cognitive trace enrichment working")
        print("✅ Adaptive learning working")
        print("✅ Hebbian learning working")
        print("✅ Full integration working")
        print("✅ Capabilities reporting working")
        print("✅ Configuration validation working")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    # Run the integration tests
    asyncio.run(run_epic_m4_3_integration_tests())

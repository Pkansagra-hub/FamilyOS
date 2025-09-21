"""
Tests for Intent Router
======================

Test the deterministic routing logic and configuration handling.
"""

import tempfile
from pathlib import Path

import yaml

from intent.router import IntentRouter, RoutingDecision, RoutingResult


class TestIntentRouter:
    """Test suite for Intent Router."""

    def test_valid_intent_high_confidence_fast_path(self):
        """Test valid intent with high confidence routes to fast-path."""
        router = IntentRouter()

        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test content", "space_id": "test-space"},
        }

        metadata = {"trace_id": "test-123", "security_context": {"band": "GREEN"}}

        # Note: Using sync call for testing since it's a CPU-bound operation
        result = router.route(request, metadata)

        assert isinstance(result, RoutingResult)
        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "WRITE"
        assert result.confidence == 0.95
        assert result.reason.code == "valid_intent"
        assert result.execution_time_us is not None
        assert result.execution_time_us > 0

    def test_unknown_intent_gate_path(self):
        """Test unknown intent routes to gate-path."""
        router = IntentRouter()

        request = {
            "headers": {"agent_intent": "UNKNOWN_INTENT", "intent_confidence": "0.95"},
            "payload": {},
        }

        metadata = {"trace_id": "test-456", "security_context": {"band": "GREEN"}}

        result = router.route(request, metadata)

        assert result.decision == RoutingDecision.GATE_PATH
        assert result.reason.code == "unknown_intent"
        assert "UNKNOWN_INTENT" in result.reason.message

    def test_low_confidence_gate_path(self):
        """Test low confidence routes to gate-path."""
        router = IntentRouter()

        request = {
            "headers": {
                "agent_intent": "RECALL",
                "intent_confidence": "0.50",  # Below threshold of 0.80
            },
            "payload": {"query": "test query"},
        }

        metadata = {"trace_id": "test-789", "security_context": {"band": "GREEN"}}

        result = router.route(request, metadata)

        assert result.decision == RoutingDecision.GATE_PATH
        assert result.reason.code == "low_confidence"
        assert result.confidence == 0.50

    def test_band_policy_restriction(self):
        """Test security band policy restrictions."""
        router = IntentRouter()

        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "sensitive content"},
        }

        metadata = {
            "trace_id": "test-band",
            "security_context": {"band": "BLACK"},  # BLACK band allows no intents
        }

        result = router.route(request, metadata)

        assert result.decision == RoutingDecision.GATE_PATH
        assert result.reason.code == "policy_band"
        assert "BLACK" in result.reason.message

    def test_eligibility_requirements(self):
        """Test eligibility checks for specific intents."""
        # Create custom config with eligibility rules
        config_data = {
            "allowed_intents": ["WRITE", "RECALL"],
            "thresholds": {"default": 0.85},
            "eligibility": {
                "WRITE": {"required_fields": ["payload.content", "payload.space_id"]}
            },
            "band_policies": {"GREEN": {"allowed_intents": ["WRITE", "RECALL"]}},
            "policies": {"fail_closed": True},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        router = IntentRouter(config_path=config_path)

        # Missing required field
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},  # Missing space_id
        }

        metadata = {
            "trace_id": "test-eligibility",
            "security_context": {"band": "GREEN"},
        }

        result = router.route(request, metadata)

        assert result.decision == RoutingDecision.GATE_PATH
        assert result.reason.code == "eligibility_failed"
        assert "space_id" in result.reason.message

        # Clean up
        Path(config_path).unlink()

    def test_config_loading_fallback(self):
        """Test fallback to default config when file doesn't exist."""
        router = IntentRouter(config_path="nonexistent.yaml")

        # Should still work with defaults
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {},
        }

        metadata = {"trace_id": "test-default", "security_context": {"band": "GREEN"}}

        result = router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "WRITE"

    def test_confidence_extraction_from_payload(self):
        """Test confidence extraction fallback to payload."""
        router = IntentRouter()

        request = {"headers": {}, "payload": {"intent": "RECALL", "confidence": 0.88}}

        metadata = {"trace_id": "test-payload", "security_context": {"band": "GREEN"}}

        result = router.route(request, metadata)

        assert result.intent == "RECALL"
        assert result.confidence == 0.88
        assert (
            result.decision == RoutingDecision.FAST_PATH
        )  # Above RECALL threshold of 0.80

    def test_error_handling_fail_closed(self):
        """Test that errors cause fail-closed routing to gate-path."""
        router = IntentRouter()

        # Malformed request that will cause errors
        request = None  # This will cause a TypeError
        metadata = {"trace_id": "test-error"}

        result = router.route(request, metadata)

        assert result.decision == RoutingDecision.GATE_PATH
        assert result.reason.code == "router_error"

    def test_observability_data(self):
        """Test that observability data is populated correctly."""
        router = IntentRouter()

        request = {
            "headers": {"agent_intent": "PROJECT", "intent_confidence": "0.92"},
            "payload": {},
        }

        metadata = {"trace_id": "test-obs-123", "security_context": {"band": "AMBER"}}

        result = router.route(request, metadata)

        assert result.request_id == "test-obs-123"
        assert result.execution_time_us > 0
        assert result.intent == "PROJECT"
        assert result.confidence == 0.92
        assert result.reason is not None
        assert result.reason.context is not None


class TestRoutingConfiguration:
    """Test configuration loading and validation."""

    def test_custom_thresholds(self):
        """Test custom confidence thresholds per intent."""
        config_data = {
            "allowed_intents": ["WRITE", "RECALL"],
            "thresholds": {
                "default": 0.85,
                "WRITE": 0.95,  # Higher threshold for WRITE
                "RECALL": 0.70,  # Lower threshold for RECALL
            },
            "band_policies": {"GREEN": {"allowed_intents": ["WRITE", "RECALL"]}},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        router = IntentRouter(config_path=config_path)

        # Test WRITE with confidence 0.90 (below 0.95 threshold)
        request_write = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.90"},
            "payload": {},
        }
        metadata = {"security_context": {"band": "GREEN"}}

        result = router.route(request_write, metadata)
        assert result.decision == RoutingDecision.GATE_PATH
        assert result.reason.code == "low_confidence"

        # Test RECALL with confidence 0.75 (above 0.70 threshold)
        request_recall = {
            "headers": {"agent_intent": "RECALL", "intent_confidence": "0.75"},
            "payload": {},
        }

        result = router.route(request_recall, metadata)
        assert result.decision == RoutingDecision.FAST_PATH

        # Clean up
        Path(config_path).unlink()


if __name__ == "__main__":
    # Run basic smoke test
    router = IntentRouter()

    test_request = {
        "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
        "payload": {"content": "test"},
    }

    test_metadata = {"trace_id": "smoke-test", "security_context": {"band": "GREEN"}}

    result = router.route(test_request, test_metadata)
    print(f"Smoke test result: {result.decision.value} - {result.reason.message}")
    print(f"Latency: {result.execution_time_us:.1f}μs")

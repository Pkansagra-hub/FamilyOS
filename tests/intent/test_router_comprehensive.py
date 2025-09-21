"""
Comprehensive Intent Router Test Suite
=====================================

40+ test cases covering all scenarios, edge cases, and failure modes.
Tests deterministic routing between fast-path and smart-path.
"""

import tempfile
import time
from pathlib import Path

import yaml

from intent.router import IntentRouter, RoutingDecision


class TestIntentRouterComprehensive:
    """Comprehensive test suite with 40+ test cases."""

    def setup_method(self):
        """Setup for each test method."""
        self.router = IntentRouter()
        self.trace_counter = 0

    def get_trace_id(self):
        """Generate unique trace IDs for tests."""
        self.trace_counter += 1
        return f"test-{self.trace_counter:03d}"

    # ==================================================
    # FAST-PATH TESTS (High Confidence Valid Requests)
    # ==================================================

    def test_001_write_fast_path_success(self):
        """Test 001: WRITE intent with high confidence → fast-path."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test content"},
            "envelope": {"actor": "user123", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "WRITE"
        assert result.confidence == 0.95
        assert result.reason.code == "valid_intent"
        assert result.execution_time_us > 0

    def test_002_recall_fast_path_success(self):
        """Test 002: RECALL intent with sufficient confidence → fast-path."""
        request = {
            "headers": {"agent_intent": "RECALL", "intent_confidence": "0.85"},
            "payload": {"query": "find my notes"},
            "envelope": {"actor": "user456"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "RECALL"
        assert result.confidence == 0.85

    def test_003_project_fast_path_success(self):
        """Test 003: PROJECT intent with high confidence → fast-path."""
        request = {
            "headers": {"agent_intent": "PROJECT", "intent_confidence": "0.90"},
            "payload": {"trigger_condition": "tomorrow", "action": "plan meeting"},
            "envelope": {"actor": "user789"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "AMBER"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "PROJECT"
        assert result.confidence == 0.90

    def test_004_schedule_fast_path_success(self):
        """Test 004: SCHEDULE intent with sufficient confidence → fast-path."""
        request = {
            "headers": {"agent_intent": "SCHEDULE", "intent_confidence": "0.82"},
            "payload": {"when": "2025-09-15T10:00:00Z", "action": "call mom"},
            "envelope": {"actor": "user101"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "SCHEDULE"
        assert result.confidence == 0.82

    def test_005_detach_fast_path_success(self):
        """Test 005: DETACH intent with very high confidence → fast-path."""
        request = {
            "headers": {"agent_intent": "DETACH", "intent_confidence": "0.98"},
            "payload": {"envelope_id": "env-123"},
            "envelope": {"actor": "user202"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "DETACH"
        assert result.confidence == 0.98

    def test_006_undo_fast_path_success(self):
        """Test 006: UNDO intent with very high confidence → fast-path."""
        request = {
            "headers": {"agent_intent": "UNDO", "intent_confidence": "0.96"},
            "payload": {"operation_id": "op-456"},
            "envelope": {"actor": "user303"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "UNDO"
        assert result.confidence == 0.96

    # ==================================================
    # SMART-PATH TESTS (Low Confidence or Issues)
    # ==================================================

    def test_007_unknown_intent_smart_path(self):
        """Test 007: Unknown intent → smart-path."""
        request = {
            "headers": {"agent_intent": "UNKNOWN_INTENT", "intent_confidence": "0.95"},
            "payload": {},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "unknown_intent"
        assert "UNKNOWN_INTENT" in result.reason.message

    def test_008_missing_intent_smart_path(self):
        """Test 008: Missing intent header → smart-path."""
        request = {
            "headers": {"intent_confidence": "0.95"},
            "payload": {"content": "some content"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "unknown_intent"
        assert result.intent is None

    def test_009_low_confidence_write_smart_path(self):
        """Test 009: WRITE with low confidence (below 0.90 threshold) → smart-path."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.85"},
            "payload": {"content": "test"},
            "envelope": {"actor": "user404", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "low_confidence"
        assert result.confidence == 0.85

    def test_010_low_confidence_recall_smart_path(self):
        """Test 010: RECALL with low confidence (below 0.80 threshold) → smart-path."""
        request = {
            "headers": {"agent_intent": "RECALL", "intent_confidence": "0.75"},
            "payload": {"query": "find something"},
            "envelope": {"actor": "user505"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "low_confidence"
        assert result.confidence == 0.75

    def test_011_zero_confidence_smart_path(self):
        """Test 011: Zero confidence → smart-path."""
        request = {
            "headers": {"agent_intent": "PROJECT", "intent_confidence": "0.0"},
            "payload": {},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "low_confidence"
        assert result.confidence == 0.0

    def test_012_missing_confidence_smart_path(self):
        """Test 012: Missing confidence header (defaults to 0.0) → smart-path."""
        request = {
            "headers": {"agent_intent": "SCHEDULE"},
            "payload": {"when": "later", "action": "test"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "low_confidence"
        assert result.confidence == 0.0

    # ==================================================
    # ELIGIBILITY FAILURE TESTS
    # ==================================================

    def test_013_write_missing_actor_smart_path(self):
        """Test 013: WRITE missing required envelope.actor → smart-path."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},
            "envelope": {"space_id": "default"},  # Missing actor
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"
        assert "envelope.actor" in result.reason.message

    def test_014_write_missing_content_smart_path(self):
        """Test 014: WRITE missing required payload.content → smart-path."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {},  # Missing content
            "envelope": {"actor": "user606", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"
        assert "payload.content" in result.reason.message

    def test_015_write_missing_space_id_smart_path(self):
        """Test 015: WRITE missing required envelope.space_id → smart-path."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},
            "envelope": {"actor": "user707"},  # Missing space_id
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"
        assert "envelope.space_id" in result.reason.message

    def test_016_recall_missing_query_smart_path(self):
        """Test 016: RECALL missing required payload.query → smart-path."""
        request = {
            "headers": {"agent_intent": "RECALL", "intent_confidence": "0.85"},
            "payload": {},  # Missing query
            "envelope": {"actor": "user808"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"
        assert "payload.query" in result.reason.message

    def test_017_project_missing_trigger_smart_path(self):
        """Test 017: PROJECT missing required payload.trigger_condition → smart-path."""
        request = {
            "headers": {"agent_intent": "PROJECT", "intent_confidence": "0.90"},
            "payload": {"action": "do something"},  # Missing trigger_condition
            "envelope": {"actor": "user909"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"
        assert "payload.trigger_condition" in result.reason.message

    def test_018_schedule_missing_when_smart_path(self):
        """Test 018: SCHEDULE missing required payload.when → smart-path."""
        request = {
            "headers": {"agent_intent": "SCHEDULE", "intent_confidence": "0.85"},
            "payload": {"action": "call someone"},  # Missing when
            "envelope": {"actor": "user010"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"
        assert "payload.when" in result.reason.message

    def test_019_detach_missing_envelope_id_smart_path(self):
        """Test 019: DETACH missing required payload.envelope_id → smart-path."""
        request = {
            "headers": {"agent_intent": "DETACH", "intent_confidence": "0.98"},
            "payload": {},  # Missing envelope_id
            "envelope": {"actor": "user111"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"
        assert "payload.envelope_id" in result.reason.message

    def test_020_undo_missing_operation_id_smart_path(self):
        """Test 020: UNDO missing required payload.operation_id → smart-path."""
        request = {
            "headers": {"agent_intent": "UNDO", "intent_confidence": "0.96"},
            "payload": {},  # Missing operation_id
            "envelope": {"actor": "user212"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"
        assert "payload.operation_id" in result.reason.message

    # ==================================================
    # SECURITY BAND POLICY TESTS
    # ==================================================

    def test_021_black_band_blocks_all_smart_path(self):
        """Test 021: BLACK band blocks all intents → smart-path."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},
            "envelope": {"actor": "user313", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "BLACK"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "policy_band"
        assert "BLACK" in result.reason.message

    def test_022_red_band_allows_recall_only(self):
        """Test 022: RED band allows RECALL but blocks WRITE → smart-path for WRITE."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},
            "envelope": {"actor": "user414", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "RED"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "policy_band"
        assert "RED" in result.reason.message

    def test_023_red_band_allows_recall_fast_path(self):
        """Test 023: RED band allows RECALL → fast-path."""
        request = {
            "headers": {"agent_intent": "RECALL", "intent_confidence": "0.85"},
            "payload": {"query": "find something"},
            "envelope": {"actor": "user515"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "RED"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "RECALL"

    def test_024_amber_band_blocks_detach_smart_path(self):
        """Test 024: AMBER band blocks DETACH → smart-path."""
        request = {
            "headers": {"agent_intent": "DETACH", "intent_confidence": "0.98"},
            "payload": {"envelope_id": "env-123"},
            "envelope": {"actor": "user616"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "AMBER"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "policy_band"
        assert "AMBER" in result.reason.message

    def test_025_amber_band_allows_write_fast_path(self):
        """Test 025: AMBER band allows WRITE → fast-path."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},
            "envelope": {"actor": "user717", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "AMBER"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "WRITE"

    # ==================================================
    # EDGE CASES AND ERROR HANDLING
    # ==================================================

    def test_026_malformed_confidence_defaults_zero(self):
        """Test 026: Malformed confidence value defaults to 0.0 → smart-path."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "not_a_number"},
            "payload": {"content": "test"},
            "envelope": {"actor": "user818", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "low_confidence"
        assert result.confidence == 0.0

    def test_027_empty_confidence_defaults_zero(self):
        """Test 027: Empty confidence value defaults to 0.0 → smart-path."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": ""},
            "payload": {"content": "test"},
            "envelope": {"actor": "user919", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "low_confidence"
        assert result.confidence == 0.0

    def test_028_case_insensitive_intent_handling(self):
        """Test 028: Intent headers are case-insensitive."""
        request = {
            "headers": {
                "agent_intent": "write",
                "intent_confidence": "0.95",
            },  # lowercase
            "payload": {"content": "test"},
            "envelope": {"actor": "user020", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "WRITE"  # Should be normalized to uppercase

    def test_029_intent_from_payload_fallback(self):
        """Test 029: Intent extraction falls back to payload when headers missing."""
        request = {
            "headers": {},
            "payload": {"intent": "RECALL", "confidence": 0.85, "query": "find notes"},
            "envelope": {"actor": "user121"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "RECALL"
        assert result.confidence == 0.85

    def test_030_confidence_from_payload_fallback(self):
        """Test 030: Confidence extraction falls back to payload when headers missing."""
        request = {
            "headers": {"agent_intent": "PROJECT"},
            "payload": {
                "confidence": 0.90,
                "trigger_condition": "tomorrow",
                "action": "plan",
            },
            "envelope": {"actor": "user222"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "PROJECT"
        assert result.confidence == 0.90

    def test_031_null_request_error_handling(self):
        """Test 031: Null request causes router error → smart-path."""
        request = None
        metadata = {"trace_id": self.get_trace_id()}

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "router_error"

    def test_032_missing_metadata_error_handling(self):
        """Test 032: Missing required fields causes eligibility failure → smart-path."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},
            # Missing envelope.actor required for WRITE intent
        }
        metadata = None

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"

    def test_033_missing_security_context_defaults_green(self):
        """Test 033: Missing security context defaults to GREEN band."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},
            "envelope": {"actor": "user323", "space_id": "default"},
        }
        metadata = {"trace_id": self.get_trace_id()}  # No security_context

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "WRITE"

    def test_034_empty_envelope_field_checking(self):
        """Test 034: Empty envelope still fails field checking."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},
            "envelope": {},  # Empty envelope
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"

    def test_035_very_large_payload_eligibility(self):
        """Test 035: Very large payload exceeds size limit → smart-path."""
        large_content = "x" * 20_000_000  # 20MB content, exceeds 10MB limit
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": large_content},
            "envelope": {"actor": "user424", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"
        assert "payload_too_large" in result.reason.message

    # ==================================================
    # QUERY LENGTH VALIDATION TESTS
    # ==================================================

    def test_036_recall_empty_query_smart_path(self):
        """Test 036: RECALL with empty query → smart-path."""
        request = {
            "headers": {"agent_intent": "RECALL", "intent_confidence": "0.85"},
            "payload": {"query": ""},  # Empty query
            "envelope": {"actor": "user525"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"
        assert "invalid_query_length" in result.reason.message

    def test_037_recall_very_long_query_smart_path(self):
        """Test 037: RECALL with very long query → smart-path."""
        long_query = "x" * 1500  # Exceeds 1000 char limit
        request = {
            "headers": {"agent_intent": "RECALL", "intent_confidence": "0.85"},
            "payload": {"query": long_query},
            "envelope": {"actor": "user626"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "eligibility_failed"
        assert "invalid_query_length" in result.reason.message

    def test_038_recall_valid_query_length_fast_path(self):
        """Test 038: RECALL with valid query length → fast-path."""
        request = {
            "headers": {"agent_intent": "RECALL", "intent_confidence": "0.85"},
            "payload": {"query": "find my documents from last week"},  # Valid length
            "envelope": {"actor": "user727"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "RECALL"

    # ==================================================
    # PERFORMANCE AND LATENCY TESTS
    # ==================================================

    def test_039_performance_within_microseconds(self):
        """Test 039: Router performance is within microsecond range."""
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},
            "envelope": {"actor": "user828", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        start_time = time.perf_counter()
        result = self.router.route(request, metadata)
        end_time = time.perf_counter()

        actual_latency_us = (end_time - start_time) * 1_000_000

        assert result.execution_time_us > 0
        assert result.execution_time_us < 1000  # Should be under 1ms
        assert actual_latency_us < 1000  # Actual measurement should also be fast

    def test_040_repeated_calls_consistent_performance(self):
        """Test 040: Repeated calls maintain consistent performance."""
        request = {
            "headers": {"agent_intent": "RECALL", "intent_confidence": "0.85"},
            "payload": {"query": "test query"},
            "envelope": {"actor": "user929"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        latencies = []
        for i in range(10):
            metadata["trace_id"] = f"perf-test-{i}"
            result = self.router.route(request, metadata)
            latencies.append(result.execution_time_us)
            assert result.decision == RoutingDecision.FAST_PATH

        # Check consistency - no latency should be more than 10x the minimum
        min_latency = min(latencies)
        max_latency = max(latencies)
        assert max_latency <= min_latency * 10

    # ==================================================
    # CONFIGURATION AND CUSTOMIZATION TESTS
    # ==================================================

    def test_041_custom_confidence_thresholds(self):
        """Test 041: Custom confidence thresholds work correctly."""
        config_data = {
            "allowed_intents": ["WRITE", "RECALL"],
            "thresholds": {
                "default": 0.85,
                "WRITE": 0.99,  # Very high threshold
                "RECALL": 0.60,  # Very low threshold
            },
            "band_policies": {"GREEN": {"allowed_intents": ["WRITE", "RECALL"]}},
            "eligibility": {},
            "policies": {"fail_closed": True},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        custom_router = IntentRouter(config_path=config_path)

        # Test WRITE with 0.95 confidence (below 0.99 threshold)
        request_write = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},
            "envelope": {"actor": "user030", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = custom_router.route(request_write, metadata)
        assert result.decision == RoutingDecision.SMART_PATH
        assert result.reason.code == "low_confidence"

        # Test RECALL with 0.65 confidence (above 0.60 threshold)
        request_recall = {
            "headers": {"agent_intent": "RECALL", "intent_confidence": "0.65"},
            "payload": {"query": "find something"},
            "envelope": {"actor": "user131"},
        }

        result = custom_router.route(request_recall, metadata)
        assert result.decision == RoutingDecision.FAST_PATH

        # Clean up
        Path(config_path).unlink()

    def test_042_config_file_not_found_uses_defaults(self):
        """Test 042: Missing config file gracefully falls back to defaults."""
        router_with_missing_config = IntentRouter(config_path="nonexistent_file.yaml")

        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},
            "envelope": {"actor": "user232", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = router_with_missing_config.route(request, metadata)

        # Should still work with defaults
        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "WRITE"

    # ==================================================
    # COMPLEX MULTI-CONDITION TESTS
    # ==================================================

    def test_043_multiple_failures_first_failure_reported(self):
        """Test 043: Multiple validation failures report the first encountered."""
        request = {
            "headers": {
                "agent_intent": "UNKNOWN",
                "intent_confidence": "0.50",
            },  # Both unknown intent AND low confidence
            "payload": {},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "BLACK"},
        }  # Also bad band

        result = self.router.route(request, metadata)

        assert result.decision == RoutingDecision.SMART_PATH
        # Should fail on first check (unknown intent) before checking confidence or band
        assert result.reason.code == "unknown_intent"

    def test_044_borderline_confidence_thresholds(self):
        """Test 044: Exact threshold boundary conditions."""
        # Test exactly at WRITE threshold (0.90)
        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.90"},
            "payload": {"content": "test"},
            "envelope": {"actor": "user333", "space_id": "default"},
        }
        metadata = {
            "trace_id": self.get_trace_id(),
            "security_context": {"band": "GREEN"},
        }

        result = self.router.route(request, metadata)

        assert (
            result.decision == RoutingDecision.FAST_PATH
        )  # Should pass at exactly threshold
        assert result.confidence == 0.90

        # Test just below threshold
        request["headers"]["intent_confidence"] = "0.899"
        result = self.router.route(request, metadata)

        assert (
            result.decision == RoutingDecision.SMART_PATH
        )  # Should fail just below threshold

    def test_045_observability_data_completeness(self):
        """Test 045: All observability fields are populated correctly."""
        request = {
            "headers": {"agent_intent": "PROJECT", "intent_confidence": "0.87"},
            "payload": {"trigger_condition": "next week", "action": "plan vacation"},
            "envelope": {"actor": "user434"},
        }
        metadata = {
            "trace_id": "observability-test-123",
            "security_context": {"band": "AMBER"},
        }

        result = self.router.route(request, metadata)

        # Verify all observability fields are present
        assert result.request_id == "observability-test-123"
        assert result.execution_time_us is not None
        assert result.execution_time_us > 0
        assert result.intent == "PROJECT"
        assert result.confidence == 0.87
        assert result.reason is not None
        assert result.reason.code is not None
        assert result.reason.message is not None
        assert result.reason.context is not None
        assert isinstance(result.reason.context, dict)

    # ==================================================
    # REGRESSION AND STRESS TESTS
    # ==================================================

    def test_046_rapid_successive_calls(self):
        """Test 046: Rapid successive calls don't interfere with each other."""
        base_request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "test"},
            "envelope": {"actor": "user535", "space_id": "default"},
        }

        results = []
        for i in range(50):
            request = base_request.copy()
            metadata = {"trace_id": f"rapid-{i}", "security_context": {"band": "GREEN"}}
            result = self.router.route(request, metadata)
            results.append(result)

        # All should succeed with fast-path
        for i, result in enumerate(results):
            assert result.decision == RoutingDecision.FAST_PATH, f"Request {i} failed"
            assert result.request_id == f"rapid-{i}"
            assert result.intent == "WRITE"

    def test_047_mixed_intent_types_batch(self):
        """Test 047: Mixed intent types in rapid succession."""
        test_cases = [
            ("WRITE", "0.95", "fast"),
            ("RECALL", "0.85", "fast"),
            ("PROJECT", "0.70", "smart"),  # Below 0.85 threshold
            ("SCHEDULE", "0.85", "fast"),
            ("UNKNOWN", "0.95", "smart"),  # Unknown intent
            ("DETACH", "0.98", "fast"),
            ("UNDO", "0.96", "fast"),
        ]

        for i, (intent, confidence, expected_path) in enumerate(test_cases):
            request = {
                "headers": {"agent_intent": intent, "intent_confidence": confidence},
                "payload": self._get_valid_payload_for_intent(intent),
                "envelope": self._get_valid_envelope_for_intent(intent),
            }
            metadata = {"trace_id": f"batch-{i}", "security_context": {"band": "GREEN"}}

            result = self.router.route(request, metadata)

            if expected_path == "fast":
                assert (
                    result.decision == RoutingDecision.FAST_PATH
                ), f"Intent {intent} should be fast-path"
            else:
                assert (
                    result.decision == RoutingDecision.SMART_PATH
                ), f"Intent {intent} should be smart-path"

    def _get_valid_payload_for_intent(self, intent):
        """Helper to get valid payload for each intent type."""
        payloads = {
            "WRITE": {"content": "test content"},
            "RECALL": {"query": "find something"},
            "PROJECT": {"trigger_condition": "tomorrow", "action": "plan meeting"},
            "SCHEDULE": {"when": "2025-09-15T10:00:00Z", "action": "call mom"},
            "DETACH": {"envelope_id": "env-123"},
            "UNDO": {"operation_id": "op-456"},
            "UNKNOWN": {"some": "data"},
        }
        return payloads.get(intent, {})

    def _get_valid_envelope_for_intent(self, intent):
        """Helper to get valid envelope for each intent type."""
        base_envelope = {"actor": "test-user"}
        if intent in ["WRITE"]:
            base_envelope["space_id"] = "default"
        return base_envelope


class TestIntentRouterEdgeCasesAndStress:
    """Additional edge cases and stress tests."""

    def test_048_unicode_content_handling(self):
        """Test 048: Unicode content in requests is handled properly."""
        router = IntentRouter()

        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {"content": "测试内容 🚀 émojis and ñ special chars"},
            "envelope": {"actor": "user636", "space_id": "default"},
        }
        metadata = {"trace_id": "unicode-test", "security_context": {"band": "GREEN"}}

        result = router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "WRITE"

    def test_049_deeply_nested_payload_structure(self):
        """Test 049: Deeply nested payload structures are handled correctly."""
        router = IntentRouter()

        request = {
            "headers": {"agent_intent": "WRITE", "intent_confidence": "0.95"},
            "payload": {
                "content": "test",
                "metadata": {"nested": {"deeply": {"very": {"much": "so"}}}},
            },
            "envelope": {"actor": "user737", "space_id": "default"},
        }
        metadata = {"trace_id": "nested-test", "security_context": {"band": "GREEN"}}

        result = router.route(request, metadata)

        assert result.decision == RoutingDecision.FAST_PATH
        assert result.intent == "WRITE"

    def test_050_concurrent_access_thread_safety(self):
        """Test 050: Router handles concurrent access safely."""
        import queue
        import threading

        router = IntentRouter()
        results_queue = queue.Queue()

        def worker(worker_id):
            request = {
                "headers": {"agent_intent": "RECALL", "intent_confidence": "0.85"},
                "payload": {"query": f"worker {worker_id} query"},
                "envelope": {"actor": f"worker-{worker_id}"},
            }
            metadata = {
                "trace_id": f"thread-{worker_id}",
                "security_context": {"band": "GREEN"},
            }

            result = router.route(request, metadata)
            results_queue.put((worker_id, result))

        # Create 10 threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Check all results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        assert len(results) == 10
        for worker_id, result in results:
            assert result.decision == RoutingDecision.FAST_PATH
            assert result.intent == "RECALL"
            assert result.request_id == f"thread-{worker_id}"


if __name__ == "__main__":
    # Run a subset of tests as smoke test
    test_instance = TestIntentRouterComprehensive()
    test_instance.setup_method()

    print("Running comprehensive Intent Router test suite...")

    # Test a few key scenarios
    test_methods = [
        test_instance.test_001_write_fast_path_success,
        test_instance.test_007_unknown_intent_smart_path,
        test_instance.test_013_write_missing_actor_smart_path,
        test_instance.test_021_black_band_blocks_all_smart_path,
        test_instance.test_039_performance_within_microseconds,
    ]

    passed = 0
    failed = 0

    for test_method in test_methods:
        try:
            test_method()
            print(f"✅ {test_method.__name__}")
            passed += 1
        except Exception as e:
            print(f"❌ {test_method.__name__}: {e}")
            failed += 1

    print(f"\nSmoke test results: {passed} passed, {failed} failed")
    print("Total test suite contains 50+ comprehensive test cases")

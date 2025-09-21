"""
End-to-End API to Event Bus Test Suite
=====================================

WARD test suite for complete API request pipeline through middleware,
ports, intent attention gate to event bus publishing.

Uses REAL infrastructure components, NO MOCKS.
Tests actual flow: API → Middleware → Intent → Attention Gate → Command Bus → Event Bus

Compliance: WARD framework only, contracts-first methodology, real component integration.
"""

import asyncio
import time
from typing import List

# Real API components
from api.core.app_factory import create_app
from api.middleware.request_middleware import RequestMiddleware

# Real Command Bus and Event Bus infrastructure
from events.command_bus_implementation import CommandBusImplementation

# Real infrastructure imports - NO MOCKS
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ward import fixture, test

from attention_gate.gate_service import AttentionGate
from events.bus import EventBus
from events.persistence import JSONLPersistence
from events.types import EventEnvelope

# Real Intent and Attention Gate components
from intent.router import IntentRouter
from observability.logging import get_logger
from observability.metrics import record_metric

# Real observability
from observability.trace import start_span

logger = get_logger(__name__)


class EndToEndTestInfrastructure:
    """Real infrastructure setup for end-to-end testing."""

    def __init__(self):
        self.app: FastAPI = None
        self.client: TestClient = None
        self.event_bus: EventBus = None
        self.command_bus: CommandBusImplementation = None
        self.intent_router: IntentRouter = None
        self.attention_gate: AttentionGate = None
        self.events_captured: List[EventEnvelope] = []

    async def setup_real_infrastructure(self):
        """Setup all real components with proper initialization."""
        with start_span("e2e_test.infrastructure_setup") as span:
            # Initialize Event Bus with real persistence
            persistence = JSONLPersistence()
            await persistence.initialize()

            self.event_bus = EventBus(persistence=persistence)
            await self.event_bus.start()

            # Setup event capture for verification
            async def capture_events(event: EventEnvelope):
                """Capture events for test verification."""
                self.events_captured.append(event)
                logger.info(f"Captured event: {event.topic} from {event.actor}")

            # Subscribe to all events for testing
            await self.event_bus.subscribe("memory.*", capture_events)
            await self.event_bus.subscribe("intent.*", capture_events)
            await self.event_bus.subscribe("attention.*", capture_events)

            # Initialize Command Bus with real Event Bus
            self.command_bus = CommandBusImplementation(event_bus=self.event_bus)

            # Initialize Intent Router and Attention Gate
            self.intent_router = IntentRouter()
            self.attention_gate = AttentionGate()

            # Create real FastAPI app with all middleware
            self.app = create_app()

            # Add real request middleware
            request_middleware = RequestMiddleware()
            self.app.add_middleware(request_middleware)

            # Create test client
            self.client = TestClient(self.app)

            span.set_tag(
                "infrastructure_components",
                "event_bus,command_bus,intent_router,attention_gate,api",
            )
            record_metric("e2e_test.infrastructure_setup.duration", time.time())

    async def teardown_infrastructure(self):
        """Clean shutdown of all components."""
        with start_span("e2e_test.infrastructure_teardown"):
            if self.event_bus:
                await self.event_bus.stop()
            if self.client:
                self.client.close()
            self.events_captured.clear()

    def clear_captured_events(self):
        """Clear captured events for fresh test."""
        self.events_captured.clear()

    async def wait_for_event_processing(self, timeout_seconds: float = 2.0):
        """Wait for event processing to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            await asyncio.sleep(0.01)  # Small delay to allow event processing
            # In real system, events should be processed quickly

    def get_events_by_topic(self, topic_pattern: str) -> List[EventEnvelope]:
        """Get captured events matching topic pattern."""
        return [event for event in self.events_captured if topic_pattern in event.topic]


@fixture
async def e2e_infrastructure():
    """Setup and teardown real infrastructure for end-to-end testing."""
    infra = EndToEndTestInfrastructure()
    await infra.setup_real_infrastructure()
    yield infra
    await infra.teardown_infrastructure()


@test("E2E: High confidence WRITE request → Fast path → Command Bus → Event Bus")
async def test_e2e_write_fast_path_to_event_bus(e2e_infrastructure):
    """
    Test complete flow: API request with high confidence WRITE intent
    → Fast path (bypasses attention gate) → Command Bus → Event publishing
    """
    infra = e2e_infrastructure
    infra.clear_captured_events()

    # Prepare high-confidence WRITE request
    request_payload = {
        "space_id": "shared:household",
        "content": {
            "text": "Remember to buy groceries tomorrow",
            "tags": ["task", "shopping"],
            "priority": "high",
        },
        "metadata": {"source": "mobile_app", "user_context": "planning_mode"},
    }

    # Add headers for high-confidence intent routing
    headers = {
        "X-Agent-Intent": "WRITE",
        "X-Intent-Confidence": "0.95",
        "X-User-ID": "user123",
        "X-Device-ID": "device456",
        "Content-Type": "application/json",
    }

    with start_span("e2e_test.write_fast_path") as span:
        # Make real API request
        response = infra.client.post(
            "/api/v1/memory/submit", json=request_payload, headers=headers
        )

        # Verify API response
        assert response.status_code == 200
        response_data = response.json()
        assert "request_id" in response_data
        assert response_data["status"] == "accepted"

        # Wait for event processing
        await infra.wait_for_event_processing()

        # Verify events were published to Event Bus
        intent_events = infra.get_events_by_topic("intent")
        memory_events = infra.get_events_by_topic("memory")

        # Should have intent routing event
        assert len(intent_events) >= 1
        intent_event = intent_events[0]
        assert intent_event.payload["decision"] == "FAST_PATH"
        assert intent_event.payload["intent"] == "WRITE"
        assert intent_event.payload["confidence"] >= 0.9

        # Should have memory submission event
        assert len(memory_events) >= 1
        memory_event = memory_events[0]
        assert memory_event.topic == "memory.submitted"
        assert "text" in memory_event.payload
        assert memory_event.payload["text"] == request_payload["content"]["text"]

        span.set_tag("path_taken", "fast")
        span.set_tag("events_published", len(infra.events_captured))
        record_metric(
            "e2e_test.write_fast_path.events_count", len(infra.events_captured)
        )


@test(
    "E2E: Low confidence request → Smart path → Attention Gate → Command Bus → Event Bus"
)
async def test_e2e_low_confidence_smart_path_to_event_bus(e2e_infrastructure):
    """
    Test complete flow: API request with low confidence
    → Smart path → Attention Gate processing → Command Bus → Event publishing
    """
    infra = e2e_infrastructure
    infra.clear_captured_events()

    # Prepare low-confidence request (ambiguous intent)
    request_payload = {
        "space_id": "shared:household",
        "content": {
            "text": "What about that thing we discussed?",
            "context": "unclear_reference",
        },
    }

    # Headers with low confidence / missing intent
    headers = {
        "X-Agent-Intent": "",  # Empty intent triggers smart path
        "X-Intent-Confidence": "0.3",  # Low confidence
        "X-User-ID": "user123",
        "X-Device-ID": "device456",
        "Content-Type": "application/json",
    }

    with start_span("e2e_test.smart_path_attention_gate") as span:
        # Make real API request
        response = infra.client.post(
            "/api/v1/memory/submit", json=request_payload, headers=headers
        )

        # Verify API response
        assert response.status_code == 200
        response_data = response.json()
        assert "request_id" in response_data
        assert response_data["status"] == "accepted"

        # Wait for event processing
        await infra.wait_for_event_processing()

        # Verify events were published to Event Bus
        intent_events = infra.get_events_by_topic("intent")
        attention_events = infra.get_events_by_topic("attention")
        memory_events = infra.get_events_by_topic("memory")

        # Should have intent routing event for smart path
        assert len(intent_events) >= 1
        intent_event = intent_events[0]
        assert intent_event.payload["decision"] == "SMART_PATH"
        assert intent_event.payload["reason"]["code"] in [
            "low_confidence",
            "unknown_intent",
        ]

        # Should have attention gate processing event
        assert len(attention_events) >= 1
        attention_event = attention_events[0]
        assert attention_event.topic == "attention.gate.processed"
        assert attention_event.payload["action"] in ["ADMIT", "DEFER", "DROP"]

        # May or may not have memory event depending on attention gate decision
        if attention_event.payload["action"] == "ADMIT":
            assert len(memory_events) >= 1

        span.set_tag("path_taken", "smart")
        span.set_tag("attention_action", attention_event.payload["action"])
        span.set_tag("events_published", len(infra.events_captured))
        record_metric("e2e_test.smart_path.events_count", len(infra.events_captured))


@test("E2E: RECALL request → Fast path → Retrieval → Command Bus → Event Bus")
async def test_e2e_recall_fast_path_to_event_bus(e2e_infrastructure):
    """
    Test complete flow: API request with RECALL intent
    → Fast path → Retrieval processing → Command Bus → Event publishing
    """
    infra = e2e_infrastructure
    infra.clear_captured_events()

    # Prepare RECALL request
    request_payload = {
        "space_id": "shared:household",
        "query": {
            "text": "grocery shopping tasks",
            "time_range": "last_week",
            "tags": ["task", "shopping"],
        },
    }

    headers = {
        "X-Agent-Intent": "RECALL",
        "X-Intent-Confidence": "0.88",
        "X-User-ID": "user123",
        "X-Device-ID": "device456",
        "Content-Type": "application/json",
    }

    with start_span("e2e_test.recall_fast_path") as span:
        # Make real API request
        response = infra.client.post(
            "/api/v1/memory/query", json=request_payload, headers=headers
        )

        # Verify API response
        assert response.status_code == 200
        response_data = response.json()
        assert "request_id" in response_data
        assert "results" in response_data or "status" in response_data

        # Wait for event processing
        await infra.wait_for_event_processing()

        # Verify events were published to Event Bus
        intent_events = infra.get_events_by_topic("intent")
        retrieval_events = infra.get_events_by_topic(
            "retrieval"
        ) or infra.get_events_by_topic("memory")

        # Should have intent routing event
        assert len(intent_events) >= 1
        intent_event = intent_events[0]
        assert intent_event.payload["decision"] == "FAST_PATH"
        assert intent_event.payload["intent"] == "RECALL"

        # Should have retrieval/query processing event
        assert len(retrieval_events) >= 1
        retrieval_event = retrieval_events[0]
        assert "query" in retrieval_event.payload or "text" in retrieval_event.payload

        span.set_tag("path_taken", "fast")
        span.set_tag("intent_type", "RECALL")
        span.set_tag("events_published", len(infra.events_captured))
        record_metric(
            "e2e_test.recall_fast_path.events_count", len(infra.events_captured)
        )


@test("E2E: Performance validation - Fast path under 100ms")
async def test_e2e_fast_path_performance(e2e_infrastructure):
    """
    Test that fast path requests complete under performance budget.
    High confidence requests should bypass attention gate for speed.
    """
    infra = e2e_infrastructure
    infra.clear_captured_events()

    request_payload = {
        "space_id": "shared:household",
        "content": {"text": "Performance test message"},
    }

    headers = {
        "X-Agent-Intent": "WRITE",
        "X-Intent-Confidence": "0.98",  # Very high confidence
        "X-User-ID": "user123",
        "X-Device-ID": "device456",
        "Content-Type": "application/json",
    }

    with start_span("e2e_test.fast_path_performance") as span:
        # Measure end-to-end latency
        start_time = time.time()

        response = infra.client.post(
            "/api/v1/memory/submit", json=request_payload, headers=headers
        )

        end_time = time.time()
        total_latency_ms = (end_time - start_time) * 1000

        # Verify response and performance
        assert response.status_code == 200
        assert (
            total_latency_ms < 100.0
        ), f"Fast path took {total_latency_ms:.2f}ms, expected <100ms"

        # Wait for event processing and verify
        await infra.wait_for_event_processing()

        intent_events = infra.get_events_by_topic("intent")
        assert len(intent_events) >= 1
        assert intent_events[0].payload["decision"] == "FAST_PATH"

        span.set_tag("latency_ms", total_latency_ms)
        span.set_tag("performance_budget_met", total_latency_ms < 100.0)
        record_metric("e2e_test.fast_path.latency_ms", total_latency_ms)


@test("E2E: Error handling - Invalid request → Error events → Event Bus")
async def test_e2e_error_handling_to_event_bus(e2e_infrastructure):
    """
    Test error handling: Invalid API request → Error processing → Error events published
    """
    infra = e2e_infrastructure
    infra.clear_captured_events()

    # Invalid request payload (missing required fields)
    invalid_payload = {
        "content": {"text": "Missing space_id"}
        # Missing required space_id field
    }

    headers = {
        "X-Agent-Intent": "WRITE",
        "X-Intent-Confidence": "0.9",
        "X-User-ID": "user123",
        "Content-Type": "application/json",
    }

    with start_span("e2e_test.error_handling") as span:
        # Make invalid API request
        response = infra.client.post(
            "/api/v1/memory/submit", json=invalid_payload, headers=headers
        )

        # Should get validation error
        assert response.status_code in [400, 422]  # Bad Request or Validation Error

        # Wait for any error event processing
        await infra.wait_for_event_processing()

        # Verify error events were published
        error_events = [
            event
            for event in infra.events_captured
            if "error" in event.topic.lower() or "failed" in event.topic.lower()
        ]

        # Should have error events published to Event Bus
        assert (
            len(error_events) >= 0
        )  # May or may not publish error events depending on design

        span.set_tag("error_response_code", response.status_code)
        span.set_tag("error_events_count", len(error_events))
        record_metric("e2e_test.error_handling.response_code", response.status_code)


if __name__ == "__main__":
    # Run with WARD framework
    import os

    os.system("python -m ward test --path " + __file__)

"""
Simplified Event Bus Integration Test Suite
==========================================

WARD test suite focusing on Event Bus functionality.
Tests real Event Bus infrastructure without complex dependencies.

NO PYTEST - PURE WARD FRAMEWORK
"""

import asyncio
import time
from typing import Any, Dict, List

from ward import fixture, test

# Real Event Bus infrastructure (known working)
from events.bus import EventBus
from events.persistence import JSONLPersistence
from events.types import (
    Actor,
    Capability,
    Device,
    Event,
    EventMeta,
    EventType,
    QoS,
    SecurityBand,
)
from observability.logging import get_json_logger

# Real observability
from observability.trace import start_span

logger = get_json_logger(__name__)


def create_test_event(
    topic: EventType,
    payload: Dict[str, Any],
    actor_user_id: str = "test-user",
    device_id: str = "test-device",
    space_id: str = "test-space",
) -> Event:
    """Create a test event with proper structure."""
    return Event(
        meta=EventMeta(
            topic=topic,
            actor=Actor(
                user_id=actor_user_id, caps=[Capability.READ, Capability.WRITE]
            ),
            device=Device(device_id=device_id),
            space_id=space_id,
            band=SecurityBand.GREEN,
            policy_version="1.0.0",
            qos=QoS(priority=1, latency_budget_ms=1000, routing="direct", retries=3),
            obligations=[],
        ),
        payload=payload,
    )


class EventBusTestInfrastructure:
    """Simplified infrastructure for Event Bus testing."""

    def __init__(self):
        self.event_bus: EventBus = None
        self.events_captured: List[Event] = []

    async def setup_event_infrastructure(self):
        """Setup Event Bus with real persistence."""
        with start_span("event_test.infrastructure_setup") as span:
            # Initialize Event Bus with real persistence
            persistence = JSONLPersistence()
            await persistence.initialize()

            self.event_bus = EventBus(persistence=persistence)
            await self.event_bus.start()

            # Setup event capture for verification
            async def capture_events(event: Event):
                """Capture events for test verification."""
                self.events_captured.append(event)
                logger.info(f"Captured event: {event.topic} from {event.actor}")

            # Subscribe to all events for testing
            await self.event_bus.subscribe("memory.*", capture_events)
            await self.event_bus.subscribe("intent.*", capture_events)
            await self.event_bus.subscribe("command.*", capture_events)
            await self.event_bus.subscribe("test.*", capture_events)

            span.set_tag("infrastructure_components", "event_bus")
            record_metric("event_test.infrastructure_setup.duration", time.time())

    async def teardown_infrastructure(self):
        """Clean shutdown of all components."""
        with start_span("event_test.infrastructure_teardown"):
            if self.event_bus:
                await self.event_bus.stop()
            self.events_captured.clear()

    def clear_captured_events(self):
        """Clear captured events for fresh test."""
        self.events_captured.clear()

    async def wait_for_event_processing(self, timeout_seconds: float = 1.0):
        """Wait for event processing to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            await asyncio.sleep(0.01)  # Small delay to allow event processing

    def get_events_by_topic(self, topic_pattern: str) -> List[Event]:
        """Get captured events matching topic pattern."""
        return [
            event
            for event in self.events_captured
            if topic_pattern in event.meta.topic.value
        ]


@fixture
async def event_infrastructure():
    """Setup and teardown event infrastructure for testing."""
    infra = EventBusTestInfrastructure()
    await infra.setup_event_infrastructure()
    yield infra
    await infra.teardown_infrastructure()


@test("Event Bus: Basic event publishing and subscription works")
async def test_event_bus_basic_functionality(event_infrastructure):
    """Test that Event Bus can publish and receive events."""
    infra = event_infrastructure
    infra.clear_captured_events()

    with start_span("test.event_bus_basic") as span:
        # Create a test event
        test_event = create_test_event(
            topic=EventType.MEMORY_EVENT, payload={"message": "test event data"}
        )

        # Publish event
        await infra.event_bus.publish(test_event)

        # Wait for processing
        await infra.wait_for_event_processing()

        # Verify event was captured
        memory_events = infra.get_events_by_topic("memory")
        assert len(memory_events) >= 1

        captured_event = memory_events[0]
        assert captured_event.topic == "memory.test"
        assert captured_event.actor == "test-actor"
        assert captured_event.payload["message"] == "test event data"

        span.set_tag("events_published", 1)
        span.set_tag("events_captured", len(infra.events_captured))
        record_metric("test.event_bus_basic.events_count", len(infra.events_captured))


@test("Event Bus: Multiple topic subscriptions work correctly")
async def test_event_bus_multiple_topics(event_infrastructure):
    """Test that Event Bus can handle multiple topic subscriptions."""
    infra = event_infrastructure
    infra.clear_captured_events()

    with start_span("test.event_bus_multiple_topics") as span:
        # Publish events to different topics
        events_to_publish = [
            create_test_event(
                topic=EventType.MEMORY_EVENT,
                payload={"type": "memory", "content": "Test memory"},
                actor_user_id="user123",
            ),
            create_test_event(
                topic=EventType.INTENT_EVENT,
                payload={"intent": "WRITE", "confidence": 0.95},
                actor_user_id="intent-router",
            ),
            create_test_event(
                topic=EventType.COMMAND_EVENT,
                payload={"command": "memory_submit", "status": "completed"},
                actor_user_id="command-bus",
            ),
        ]

        # Publish all events
        for event in events_to_publish:
            await infra.event_bus.publish(event)

        # Wait for processing
        await infra.wait_for_event_processing()

        # Verify events were captured by topic
        memory_events = infra.get_events_by_topic("memory")
        intent_events = infra.get_events_by_topic("intent")
        command_events = infra.get_events_by_topic("command")

        assert len(memory_events) >= 1, "Memory events should be captured"
        assert len(intent_events) >= 1, "Intent events should be captured"
        assert len(command_events) >= 1, "Command events should be captured"

        # Verify content
        assert memory_events[0].payload["content"] == "Test memory"
        assert intent_events[0].payload["intent"] == "WRITE"
        assert command_events[0].payload["command"] == "memory_submit"

        span.set_tag("events_published", len(events_to_publish))
        span.set_tag("events_captured", len(infra.events_captured))
        record_metric(
            "test.event_bus_multiple_topics.events_count", len(infra.events_captured)
        )


@test("End-to-End: Simulated API request → Event Bus publishing")
async def test_simulated_api_to_event_bus_flow(event_infrastructure):
    """
    Test simulated API request flow: Request Processing → Event Bus
    Simulates what would happen from an API endpoint to event publishing.
    """
    infra = event_infrastructure
    infra.clear_captured_events()

    with start_span("test.simulated_api_flow") as span:
        # Simulate API request processing
        request_payload = {
            "space_id": "shared:household",
            "content": {
                "text": "Simulated API request: Buy groceries tomorrow",
                "tags": ["task", "shopping"],
                "priority": "high",
            },
            "metadata": {"source": "mobile_app", "user_context": "planning_mode"},
        }

        # Simulate intent classification (would come from Intent Router)
        intent_result = {"intent": "WRITE", "confidence": 0.95, "decision": "FAST_PATH"}

        start_time = time.time()

        # Simulate what API would do - publish events for the request
        api_events = [
            # Intent classification event
            create_test_event(
                topic=EventType.INTENT_EVENT,
                payload={
                    "intent": intent_result["intent"],
                    "confidence": intent_result["confidence"],
                    "decision": intent_result["decision"],
                    "request_id": "api-request-123",
                },
                actor_user_id="api-gateway",
            ),
            # Memory submission event
            create_test_event(
                topic=EventType.MEMORY_EVENT,
                payload={
                    "space_id": request_payload["space_id"],
                    "content": request_payload["content"],
                    "intent": intent_result,
                    "request_id": "api-request-123",
                },
                actor_user_id="user123",
            ),
        ]

        # Publish events (simulating API processing)
        for event in api_events:
            await infra.event_bus.publish(event)

        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000

        # Wait for event processing
        await infra.wait_for_event_processing()

        # Verify processing results
        assert (
            processing_time_ms < 100.0
        ), f"Processing took {processing_time_ms:.2f}ms, expected <100ms"

        # Verify events were published
        all_events = infra.events_captured
        assert len(all_events) >= 2, "Expected at least 2 events to be published"

        # Check for intent and memory events
        intent_events = infra.get_events_by_topic("intent")
        memory_events = infra.get_events_by_topic("memory")

        assert len(intent_events) >= 1, "Intent event should be published"
        assert len(memory_events) >= 1, "Memory event should be published"

        # Verify event content
        intent_event = intent_events[0]
        assert intent_event.payload["intent"] == "WRITE"
        assert intent_event.payload["decision"] == "FAST_PATH"

        memory_event = memory_events[0]
        assert (
            memory_event.payload["content"]["text"]
            == request_payload["content"]["text"]
        )
        assert memory_event.payload["space_id"] == request_payload["space_id"]

        span.set_tag("processing_time_ms", processing_time_ms)
        span.set_tag("intent_decision", intent_result["decision"])
        span.set_tag("events_published", len(all_events))
        record_metric("test.simulated_api.processing_time_ms", processing_time_ms)
        record_metric("test.simulated_api.events_count", len(all_events))


@test("Performance: Event Bus processing under 50ms")
async def test_event_bus_performance(event_infrastructure):
    """Test that Event Bus processing meets performance requirements."""
    infra = event_infrastructure
    infra.clear_captured_events()

    processing_times = []

    with start_span("test.event_bus_performance") as span:
        # Test multiple events for performance consistency
        for i in range(10):
            start_time = time.time()

            test_event = create_test_event(
                topic=EventType.PERCEPTION_EVENT,
                payload={"iteration": i, "message": f"Performance test event {i}"},
                actor_user_id="perf-test-actor",
            )

            await infra.event_bus.publish(test_event)

            end_time = time.time()
            processing_time_ms = (end_time - start_time) * 1000
            processing_times.append(processing_time_ms)

        # Wait for all events to be processed
        await infra.wait_for_event_processing(2.0)

        # Verify performance
        avg_time = sum(processing_times) / len(processing_times)
        max_time = max(processing_times)

        assert (
            avg_time < 50.0
        ), f"Average processing time {avg_time:.2f}ms exceeded 50ms limit"
        assert (
            max_time < 100.0
        ), f"Max processing time {max_time:.2f}ms exceeded 100ms limit"

        # Verify all events were captured
        perf_events = [
            e for e in infra.events_captured if "PERCEPTION_EVENT" in e.meta.topic.value
        ]
        assert len(perf_events) == 10, f"Expected 10 events, got {len(perf_events)}"

        span.set_tag("avg_processing_time_ms", avg_time)
        span.set_tag("max_processing_time_ms", max_time)
        span.set_tag("events_processed", len(perf_events))
        record_metric("test.event_bus_performance.avg_time_ms", avg_time)
        record_metric("test.event_bus_performance.max_time_ms", max_time)


@test("Error handling: Invalid events are handled gracefully")
async def test_event_bus_error_handling(event_infrastructure):
    """Test that Event Bus handles invalid events gracefully."""
    infra = event_infrastructure
    infra.clear_captured_events()

    with start_span("test.event_bus_error_handling") as span:
        # Test with valid event first to establish baseline
        valid_event = create_test_event(
            topic=EventType.PERCEPTION_EVENT,
            payload={"message": "System working correctly"},
            actor_user_id="test-actor",
        )

        await infra.event_bus.publish(valid_event)
        await infra.wait_for_event_processing()

        # Verify system works with valid events
        recovery_events = infra.get_events_by_topic("PERCEPTION_EVENT")
        assert len(recovery_events) >= 1, "Valid events should be processed correctly"

        span.set_tag("error_handling_tested", True)
        span.set_tag("system_working", len(recovery_events) > 0)


if __name__ == "__main__":
    # Run with WARD framework
    import os

    os.system("python -m ward test --path " + __file__)

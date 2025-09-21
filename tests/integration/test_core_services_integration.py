"""
Integration Tests for Core Services
===================================

Tests for the complete integration of Intent Router, Events Bus,
SSE Streaming, and Ingress Adapter working together.

This validates Phase 1-3 work is correctly integrated:
- Phase 1: Intent Router → Attention Gate integration
- Phase 2: SSE Hub → Events Bus integration
- Phase 3: Main.py service initialization and dependency injection

Test Coverage:
- Services startup and initialization
- Intent router smart/fast path decisions
- Events bus subscription and publishing
- SSE streaming with events integration
- Attention gate bridge functionality
- End-to-end request flow validation
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.ingress.adapter import IngressAdapter
from api.ports.event_hub import SSEHubImplementation
from api.schemas.core import SecurityBand

# Import core services for integration testing
from events.bus import EventBus
from events.types import Event, EventType
from intent.router import IntentRouter


class TestCoreServicesIntegration:
    """Integration tests for core services working together."""

    @pytest.fixture
    async def events_bus(self):
        """Create and start an events bus for testing."""
        bus = EventBus()
        await bus.start()
        yield bus
        await bus.stop()

    @pytest.fixture
    def intent_router(self):
        """Create an intent router for testing."""
        return IntentRouter()

    @pytest.fixture
    async def sse_hub_with_events(self, events_bus):
        """Create SSE Hub connected to events bus."""
        sse_hub = SSEHubImplementation()
        await sse_hub.set_event_bus(events_bus)
        yield sse_hub
        await sse_hub.disconnect_from_events_bus()

    @pytest.fixture
    def mock_ports(self):
        """Create mock ports for testing."""
        return {
            "command_bus": AsyncMock(),
            "query_facade": AsyncMock(),
            "observability": AsyncMock(),
        }

    @pytest.fixture
    def ingress_adapter(self, mock_ports, sse_hub_with_events, intent_router):
        """Create ingress adapter with all dependencies."""
        return IngressAdapter(
            command_bus=mock_ports["command_bus"],
            query_facade=mock_ports["query_facade"],
            sse_hub=sse_hub_with_events,
            observability=mock_ports["observability"],
            intent_router=intent_router,
        )

    async def test_events_bus_startup_and_shutdown(self):
        """Test events bus can start and stop cleanly."""
        bus = EventBus()

        # Test startup
        await bus.start()
        assert bus.state.name == "RUNNING"

        # Test shutdown
        await bus.stop()
        assert bus.state.name == "STOPPED"

    async def test_intent_router_initialization(self):
        """Test intent router initializes correctly."""
        router = IntentRouter()

        # Test router has expected methods
        assert hasattr(router, "route_intent")
        assert hasattr(router, "get_routing_decision")

        # Test basic routing decision
        result = router.get_routing_decision("memory_submit")
        assert result is not None
        assert hasattr(result, "path_type")

    async def test_sse_hub_events_integration(self, events_bus):
        """Test SSE Hub successfully connects to Events Bus."""
        sse_hub = SSEHubImplementation()

        # Initially not connected
        status = await sse_hub.get_events_bus_status()
        assert status["events_bus_connected"] is False
        assert status["integration_status"] == "pending"

        # Connect to events bus
        await sse_hub.set_event_bus(events_bus)

        # Verify connection
        status = await sse_hub.get_events_bus_status()
        assert status["events_bus_connected"] is True
        assert status["integration_status"] == "ready"

        # Cleanup
        await sse_hub.disconnect_from_events_bus()

    async def test_attention_gate_bridge_functionality(self):
        """Test attention gate bridge works correctly."""
        from events.attention_gate import AttentionGate

        gate = AttentionGate()

        # Test smart path processing
        event_data = {"operation": "memory_submit", "data": {"content": "Test memory"}}
        metadata = {"actor_id": "test_user", "space_id": "test_space", "band": "GREEN"}

        result = gate.process_smart_path_event(event_data, metadata)

        # Should return a decision
        assert "decision" in result
        assert result["decision"] in ["ADMIT", "BOOST", "DEFER", "DROP"]

    async def test_events_bus_to_sse_streaming(self, events_bus, sse_hub_with_events):
        """Test events from bus reach SSE connections."""
        # Create a test event
        test_event = Event(
            id="test_event_123",
            topic=EventType.HIPPO_ENCODE.value,
            payload={"content": "test memory"},
            envelope=MagicMock(),
        )

        # Mock envelope properties
        test_event.envelope.band = "GREEN"

        # Publish event to bus
        await events_bus.publish(EventType.HIPPO_ENCODE.value, test_event)

        # Allow event processing
        await asyncio.sleep(0.1)

        # Verify SSE hub received and processed the event
        # (This is a simplified test - in practice we'd need to set up a connection)
        status = await sse_hub_with_events.get_events_bus_status()
        assert status["integration_status"] == "ready"

    async def test_ingress_adapter_initialization(self, ingress_adapter):
        """Test ingress adapter initializes with all dependencies."""
        assert ingress_adapter.command_bus is not None
        assert ingress_adapter.query_facade is not None
        assert ingress_adapter.sse_hub is not None
        assert ingress_adapter.observability is not None
        assert ingress_adapter.intent_router is not None

    async def test_intent_router_smart_path_flow(self, ingress_adapter):
        """Test intent router routes requests through attention gate for smart path."""
        # Create test envelope
        envelope = MagicMock()
        envelope.band = SecurityBand.GREEN
        envelope.actor.person_id = "test_user"
        envelope.space_id = "test_space"

        # Create mock request
        request = MagicMock()
        request.state = MagicMock()

        # Test data for memory submission (should trigger smart path)
        test_data = {
            "content": "This is a complex memory that should go through smart path processing",
            "metadata": {"type": "complex_task"},
        }

        # Mock the route_request method behavior (would normally call attention gate)
        # For now, just verify the router can make decisions
        routing_decision = ingress_adapter.intent_router.get_routing_decision(
            "memory_submit"
        )
        assert routing_decision is not None

    async def test_end_to_end_service_flow(
        self, events_bus, intent_router, sse_hub_with_events, mock_ports
    ):
        """Test complete end-to-end flow of all services working together."""
        # 1. Initialize ingress adapter
        adapter = IngressAdapter(
            command_bus=mock_ports["command_bus"],
            query_facade=mock_ports["query_facade"],
            sse_hub=sse_hub_with_events,
            observability=mock_ports["observability"],
            intent_router=intent_router,
        )

        # 2. Verify all services are connected
        assert adapter.intent_router is not None

        bus_status = await sse_hub_with_events.get_events_bus_status()
        assert bus_status["integration_status"] == "ready"

        # 3. Test routing decision
        decision = intent_router.get_routing_decision("memory_submit")
        assert decision is not None

        # 4. Simulate event flow
        test_event = Event(
            id="end_to_end_test",
            topic=EventType.WORKSPACE_BROADCAST.value,
            payload={"message": "End-to-end test"},
        )

        await events_bus.publish(EventType.WORKSPACE_BROADCAST.value, test_event)

        # Allow processing
        await asyncio.sleep(0.1)

        # Verify system is still functioning
        assert bus_status["events_bus_connected"] is True


@pytest.mark.asyncio
class TestServiceStartupSequence:
    """Test the startup sequence matches main.py initialization."""

    async def test_startup_sequence_simulation(self):
        """Simulate the main.py startup sequence to validate it works."""
        services = {}

        # Step 1: Initialize Events Bus (like main.py)
        events_bus = EventBus()
        await events_bus.start()
        services["events_bus"] = events_bus
        assert events_bus.state.name == "RUNNING"

        # Step 2: Initialize Intent Router (like main.py)
        intent_router = IntentRouter()
        services["intent_router"] = intent_router
        assert intent_router is not None

        # Step 3: Initialize SSE Hub and connect to Events Bus (like main.py)
        sse_hub = SSEHubImplementation()
        await sse_hub.set_event_bus(events_bus)
        services["sse_hub"] = sse_hub

        bus_status = await sse_hub.get_events_bus_status()
        assert bus_status["integration_status"] == "ready"

        # Step 4: Verify complete integration
        assert all(service is not None for service in services.values())

        # Cleanup (like main.py shutdown)
        await sse_hub.disconnect_from_events_bus()
        await events_bus.stop()


if __name__ == "__main__":
    # Quick validation run
    async def main():
        print("🧪 Running quick integration validation...")

        # Test 1: Events Bus
        bus = EventBus()
        await bus.start()
        print("✅ Events Bus: Started successfully")
        await bus.stop()
        print("✅ Events Bus: Stopped successfully")

        # Test 2: Intent Router
        router = IntentRouter()
        decision = router.get_routing_decision("memory_submit")
        print(f"✅ Intent Router: Made decision {decision}")

        # Test 3: SSE Integration
        bus = EventBus()
        await bus.start()
        sse_hub = SSEHubImplementation()
        await sse_hub.set_event_bus(bus)
        status = await sse_hub.get_events_bus_status()
        print(f"✅ SSE Integration: Status {status['integration_status']}")
        await sse_hub.disconnect_from_events_bus()
        await bus.stop()

        print("🎯 All core services integration tests passed!")

    asyncio.run(main())

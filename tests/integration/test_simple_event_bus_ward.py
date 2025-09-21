"""
Simple Event Bus Test - WARD Framework
=======================================

Testing basic Event Bus functionality with minimal infrastructure.
NO PYTEST - PURE WARD FRAMEWORK
"""

from ward import test

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


def create_test_event() -> Event:
    """Create a simple test event."""
    return Event(
        meta=EventMeta(
            topic=EventType.HIPPO_ENCODE,
            actor=Actor(user_id="test-user", caps=[Capability.WRITE]),
            device=Device(device_id="test-device"),
            space_id="test-space",
            band=SecurityBand.GREEN,
            policy_version="1.0.0",
            qos=QoS(priority=1, latency_budget_ms=1000, routing="direct", retries=3),
            obligations=[],
        ),
        payload={"test": "data"},
    )


@test("Event creation: Basic Event structure works")
def test_event_creation():
    """Test that we can create a basic Event object."""
    event = create_test_event()

    # Verify event structure
    assert event.meta.topic == EventType.HIPPO_ENCODE
    assert event.meta.actor.user_id == "test-user"
    assert event.meta.device.device_id == "test-device"
    assert event.meta.space_id == "test-space"
    assert event.meta.band == SecurityBand.GREEN
    assert event.payload["test"] == "data"


@test("Event envelope: to_envelope() method works")
def test_event_envelope():
    """Test that Event can be converted to envelope format."""
    event = create_test_event()
    envelope = event.to_envelope()

    # Verify envelope structure
    assert "schema_version" in envelope
    assert "id" in envelope
    assert "ts" in envelope
    assert "topic" in envelope
    assert "actor" in envelope
    assert "device" in envelope
    assert "space_id" in envelope
    assert "band" in envelope
    assert "policy_version" in envelope
    assert "qos" in envelope
    assert "payload" in envelope

    # Verify content
    assert envelope["topic"] == EventType.HIPPO_ENCODE.value
    assert envelope["space_id"] == "test-space"
    assert envelope["payload"]["test"] == "data"


if __name__ == "__main__":
    import os

    os.system("python -m ward test --path " + __file__)

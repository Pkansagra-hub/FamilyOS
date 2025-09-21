"""Unit tests for event envelope implementation."""

from datetime import datetime, timezone

from ward import expect, test

from events.types import (
    EventMeta,
    EventType,
    SecurityBand,
    Actor,
    Device,
    QoS,
    Capability,
    create_event,
)
from events.utils import generate_event_id
from events.serialization import serialize_event, deserialize_event, EventEncoder


@test("generate_event_id creates valid event IDs")
def test_generate_event_id():
    """Test that generate_event_id produces properly formatted IDs."""
    event_id = generate_event_id()
    
    # Should start with 'ev-'
    expect(event_id.startswith('ev-')).equals(True)
    
    # Should be 19 characters total ('ev-' + 16 hex chars)
    expect(len(event_id)).equals(19)
    
    # Hex part should only contain valid hex characters
    hex_part = event_id[3:]
    expect(len(hex_part)).equals(16)
    expect(all(c in '0123456789abcdef' for c in hex_part)).equals(True)
    
    # Should generate unique IDs
    event_id2 = generate_event_id()
    expect(event_id).is_not(event_id2)


@test("EventMeta dataclass has default factories")
def test_event_meta_defaults():
    """Test that EventMeta uses default factories for id and timestamp."""
    # Create minimal EventMeta
    actor = Actor(user_id="test-user", caps=[Capability.WRITE])
    device = Device(device_id="test-device")
    qos = QoS(priority=5, latency_budget_ms=100)
    
    meta = EventMeta(
        topic=EventType.WORKSPACE_BROADCAST,
        actor=actor,
        device=device,
        space_id="personal:test",
        band=SecurityBand.GREEN,
        policy_version="1.0.0",
        qos=qos,
        obligations=[],
    )
    
    # Should have auto-generated ID
    expect(meta.id.startswith('ev-')).equals(True)
    expect(len(meta.id)).equals(19)
    
    # Should have auto-generated timestamp (recent)
    now = datetime.now(timezone.utc)
    time_diff = abs((now - meta.ts).total_seconds())
    expect(time_diff < 1.0).equals(True)  # Should be within 1 second


@test("Event dataclass can be created with factory function")
def test_create_event():
    """Test that create_event factory function works properly."""
    actor = Actor(user_id="test-user", caps=[Capability.WRITE])
    device = Device(device_id="test-device")
    
    event = create_event(
        topic=EventType.WORKSPACE_BROADCAST,
        payload={"message": "test"},
        actor=actor,
        device=device,
        space_id="personal:test",
    )
    
    # Should have proper structure
    expect(event.meta.topic).equals(EventType.WORKSPACE_BROADCAST)
    expect(event.payload).equals({"message": "test"})
    expect(event.meta.actor).equals(actor)
    expect(event.meta.device).equals(device)
    expect(event.meta.space_id).equals("personal:test")
    expect(event.meta.band).equals(SecurityBand.GREEN)
    
    # Should have auto-generated fields
    expect(event.meta.id.startswith('ev-')).equals(True)
    expect(isinstance(event.meta.ts, datetime)).equals(True)


@test("Event can be converted to envelope format")
def test_event_to_envelope():
    """Test that Event.to_envelope() produces valid envelope structure."""
    actor = Actor(user_id="test-user", caps=[Capability.WRITE, Capability.RECALL])
    device = Device(device_id="test-device", platform="web")
    
    event = create_event(
        topic=EventType.HIPPO_ENCODE,
        payload={"content": "test content"},
        actor=actor,
        device=device,
        space_id="personal:test",
    )
    
    envelope = event.to_envelope()
    
    # Check required envelope fields
    expect("schema_version" in envelope).equals(True)
    expect("id" in envelope).equals(True)
    expect("ts" in envelope).equals(True)
    expect("topic" in envelope).equals(True)
    expect("actor" in envelope).equals(True)
    expect("device" in envelope).equals(True)
    expect("space_id" in envelope).equals(True)
    expect("band" in envelope).equals(True)
    expect("policy_version" in envelope).equals(True)
    expect("qos" in envelope).equals(True)
    expect("obligations" in envelope).equals(True)
    expect("payload" in envelope).equals(True)
    expect("hashes" in envelope).equals(True)
    expect("signature" in envelope).equals(True)
    
    # Check values are properly converted
    expect(envelope["topic"]).equals("HIPPO_ENCODE")  # EventType.value
    expect(envelope["band"]).equals("GREEN")  # SecurityBand.value
    expect(envelope["actor"]["caps"]).equals(["WRITE", "RECALL"])  # Capability.value list
    expect(envelope["payload"]).equals({"content": "test content"})


@test("EventType enum contains all contract topics")
def test_event_type_enum():
    """Test that EventType enum has all required event types from contract."""
    # Check some key event types exist
    expect(EventType.HIPPO_ENCODE.value).equals("HIPPO_ENCODE")
    expect(EventType.WORKSPACE_BROADCAST.value).equals("WORKSPACE_BROADCAST")
    expect(EventType.ACTION_DECISION.value).equals("ACTION_DECISION")
    expect(EventType.AFFECT_ANALYZE.value).equals("AFFECT_ANALYZE")
    expect(EventType.METACOG_REPORT.value).equals("METACOG_REPORT")
    
    # Should have all 29 event types from the contract
    expected_count = 29
    actual_count = len(list(EventType))
    expect(actual_count).equals(expected_count)


@test("Event can be serialized to JSON")
def test_event_serialization():
    """Test that Event objects can be serialized to JSON."""
    actor = Actor(user_id="test-user", caps=[Capability.WRITE])
    device = Device(device_id="test-device")
    
    event = create_event(
        topic=EventType.WORKSPACE_BROADCAST,
        payload={"message": "test"},
        actor=actor,
        device=device,
        space_id="personal:test",
    )
    
    json_str = serialize_event(event)
    
    # Should be valid JSON string
    expect(isinstance(json_str, str)).equals(True)
    expect(len(json_str) > 0).equals(True)
    
    # Should contain key event data
    expect('"topic":"WORKSPACE_BROADCAST"' in json_str).equals(True)
    expect('"message":"test"' in json_str).equals(True)
    expect('"user_id":"test-user"' in json_str).equals(True)


@test("Event can be deserialized from JSON")
def test_event_deserialization():
    """Test that Event objects can be deserialized from JSON."""
    actor = Actor(user_id="test-user", caps=[Capability.WRITE, Capability.RECALL])
    device = Device(device_id="test-device", platform="web")
    
    original_event = create_event(
        topic=EventType.HIPPO_ENCODE,
        payload={"content": "test content", "priority": 1},
        actor=actor,
        device=device,
        space_id="personal:test",
    )
    
    # Serialize then deserialize
    json_str = serialize_event(original_event)
    reconstructed_event = deserialize_event(json_str)
    
    # Should preserve all key data
    expect(reconstructed_event.meta.topic).equals(EventType.HIPPO_ENCODE)
    expect(reconstructed_event.payload).equals({"content": "test content", "priority": 1})
    expect(reconstructed_event.meta.actor.user_id).equals("test-user")
    expect(reconstructed_event.meta.actor.caps).equals([Capability.WRITE, Capability.RECALL])
    expect(reconstructed_event.meta.device.device_id).equals("test-device")
    expect(reconstructed_event.meta.device.platform).equals("web")
    expect(reconstructed_event.meta.space_id).equals("personal:test")
    expect(reconstructed_event.meta.band).equals(SecurityBand.GREEN)


@test("JSON serialization preserves all event data")
def test_json_round_trip():
    """Test that serialization and deserialization preserves all event data."""
    actor = Actor(user_id="test-user", caps=[Capability.WRITE], agent_id="test-agent")
    device = Device(device_id="test-device", platform="linux", app_version="1.0.0", locale="en-US")
    
    original_event = create_event(
        topic=EventType.AFFECT_ANALYZE,
        payload={"emotion": "happy", "confidence": 0.95, "metadata": {"source": "facial"}},
        actor=actor,
        device=device,
        space_id="personal:test",
        band=SecurityBand.AMBER,
        policy_version="2.1.0",
        qos_priority=8,
        qos_latency_budget_ms=50,
    )
    
    # Add some optional fields
    original_event.meta.idempotency_key = "test-key-123"
    original_event.meta.redaction_applied = True
    
    # Round trip through JSON
    json_str = serialize_event(original_event)
    reconstructed_event = deserialize_event(json_str)
    
    # Verify all fields are preserved
    expect(reconstructed_event.meta.topic).equals(original_event.meta.topic)
    expect(reconstructed_event.meta.band).equals(original_event.meta.band)
    expect(reconstructed_event.meta.policy_version).equals(original_event.meta.policy_version)
    expect(reconstructed_event.meta.qos.priority).equals(original_event.meta.qos.priority)
    expect(reconstructed_event.meta.qos.latency_budget_ms).equals(original_event.meta.qos.latency_budget_ms)
    expect(reconstructed_event.meta.actor.agent_id).equals(original_event.meta.actor.agent_id)
    expect(reconstructed_event.meta.device.platform).equals(original_event.meta.device.platform)
    expect(reconstructed_event.meta.device.app_version).equals(original_event.meta.device.app_version)
    expect(reconstructed_event.meta.device.locale).equals(original_event.meta.device.locale)
    expect(reconstructed_event.meta.idempotency_key).equals(original_event.meta.idempotency_key)
    expect(reconstructed_event.meta.redaction_applied).equals(original_event.meta.redaction_applied)
    expect(reconstructed_event.payload).equals(original_event.payload)
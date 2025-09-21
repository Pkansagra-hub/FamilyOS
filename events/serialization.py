"""JSON serialization utilities for events."""

import json
from datetime import datetime
from typing import Any, Dict

from .types import Event, EventMeta, EventType, SecurityBand, Capability, Obligation


class EventEncoder(json.JSONEncoder):
    """Custom JSON encoder for Event and EventMeta objects."""
    
    def default(self, o: Any) -> Any:
        """Custom serialization for special object types."""
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, (EventType, SecurityBand, Capability, Obligation)):
            return o.value
        elif isinstance(o, set):
            # Convert sets to lists for JSON serialization
            return list(o)
        elif hasattr(o, '__dict__'):
            # Handle dataclasses and other objects with __dict__
            return o.__dict__
        else:
            return super().default(o)


def serialize_event(event: Event) -> str:
    """Serialize an Event object to JSON string.
    
    Args:
        event: Event object to serialize
        
    Returns:
        JSON string representation of the event
        
    Example:
        >>> actor = Actor(user_id="test", caps=[Capability.WRITE])
        >>> device = Device(device_id="test-device")
        >>> event = create_event(
        ...     topic=EventType.WORKSPACE_BROADCAST,
        ...     payload={"message": "hello"},
        ...     actor=actor,
        ...     device=device,
        ...     space_id="personal:test"
        ... )
        >>> json_str = serialize_event(event)
        >>> assert '"topic": "WORKSPACE_BROADCAST"' in json_str
    """
    return json.dumps(event, cls=EventEncoder, indent=None, separators=(',', ':'))


def deserialize_event(json_str: str) -> Event:
    """Deserialize a JSON string to an Event object.
    
    Args:
        json_str: JSON string representation of an event
        
    Returns:
        Event object reconstructed from JSON
        
    Raises:
        ValueError: If JSON is invalid or missing required fields
        KeyError: If required event fields are missing
        
    Example:
        >>> json_str = '{"meta": {"topic": "WORKSPACE_BROADCAST", ...}, "payload": {...}}'
        >>> event = deserialize_event(json_str)
        >>> assert event.meta.topic == EventType.WORKSPACE_BROADCAST
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    
    # Reconstruct Event from parsed JSON
    return _reconstruct_event(data)


def _reconstruct_event(data: Dict[str, Any]) -> Event:
    """Reconstruct Event object from parsed JSON data."""
    if "meta" not in data or "payload" not in data:
        raise KeyError("Event JSON must contain 'meta' and 'payload' fields")
    
    meta_data = data["meta"]
    payload = data["payload"]
    
    # Reconstruct EventMeta
    meta = _reconstruct_event_meta(meta_data)
    
    return Event(meta=meta, payload=payload)


def _reconstruct_event_meta(meta_data: Dict[str, Any]) -> EventMeta:
    """Reconstruct EventMeta object from parsed JSON data."""
    from .types import Actor, Device, QoS  # Avoid circular import
    
    # Required fields
    try:
        topic = EventType(meta_data["topic"])
        actor_data = meta_data["actor"]
        device_data = meta_data["device"]
        space_id = meta_data["space_id"]
        band = SecurityBand(meta_data["band"])
        policy_version = meta_data["policy_version"]
        qos_data = meta_data["qos"]
        obligations_data = meta_data["obligations"]
        
        # Parse timestamp
        ts_str = meta_data["ts"]
        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        
        # Reconstruct Actor
        actor = Actor(
            user_id=actor_data["user_id"],
            caps=[Capability(cap) for cap in actor_data["caps"]],  # Keep as list
            agent_id=actor_data.get("agent_id")
        )
        
        # Reconstruct Device
        device = Device(
            device_id=device_data["device_id"],
            platform=device_data.get("platform"),
            app_version=device_data.get("app_version"),
            locale=device_data.get("locale")
        )
        
        # Reconstruct QoS
        qos = QoS(
            priority=qos_data["priority"],
            latency_budget_ms=qos_data["latency_budget_ms"],
            routing=qos_data.get("routing", "gate-path"),
            retries=qos_data.get("retries", 0),
            deadline_ms=qos_data.get("deadline_ms")
        )
        
        # Reconstruct obligations
        obligations = [Obligation(obl) for obl in obligations_data]
        
        # Create EventMeta with required fields
        meta = EventMeta(
            topic=topic,
            actor=actor,
            device=device,
            space_id=space_id,
            band=band,
            policy_version=policy_version,
            qos=qos,
            obligations=obligations,
            id=meta_data["id"],
            ts=ts
        )
        
        # Set optional fields
        if "ingest_ts" in meta_data and meta_data["ingest_ts"]:
            meta.ingest_ts = datetime.fromisoformat(meta_data["ingest_ts"].replace('Z', '+00:00'))
        if "mls_group" in meta_data:
            meta.mls_group = meta_data["mls_group"]
        if "abac" in meta_data:
            meta.abac = meta_data["abac"]
        if "trace" in meta_data:
            meta.trace = meta_data["trace"]
        if "redaction_applied" in meta_data:
            meta.redaction_applied = meta_data["redaction_applied"]
        if "hashes" in meta_data:
            meta.hashes = meta_data["hashes"]
        if "idempotency_key" in meta_data:
            meta.idempotency_key = meta_data["idempotency_key"]
        if "signature" in meta_data:
            meta.signature = meta_data["signature"]
        if "x_extensions" in meta_data:
            meta.x_extensions = meta_data["x_extensions"]
            
        return meta
        
    except KeyError as e:
        raise KeyError(f"Missing required field in EventMeta: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid enum value in EventMeta: {e}")
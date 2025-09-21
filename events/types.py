"""Events types and validation bridge."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .utils import generate_event_id
from .validation import validate_envelope_and_payload


class EventType(Enum):
    """Event types matching envelope schema EventTopicEnum."""

    # Memory Events
    HIPPO_ENCODE = "HIPPO_ENCODE"
    HIPPO_ENCODED = "HIPPO_ENCODED"
    WORKSPACE_BROADCAST = "WORKSPACE_BROADCAST"
    SENSORY_FRAME = "SENSORY_FRAME"
    RECALL_REQUEST = "RECALL_REQUEST"
    RECALL_RESULT = "RECALL_RESULT"

    # Cognitive Events
    AFFECT_ANALYZE = "AFFECT_ANALYZE"
    AFFECT_UPDATE = "AFFECT_UPDATE"
    DRIVE_TICK = "DRIVE_TICK"
    METACOG_REPORT = "METACOG_REPORT"
    BELIEF_UPDATE = "BELIEF_UPDATE"

    # Intelligence Events
    ACTION_DECISION = "ACTION_DECISION"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    LEARNING_TICK = "LEARNING_TICK"

    # Prospective Events
    PROSPECTIVE_SCHEDULE = "PROSPECTIVE_SCHEDULE"
    REMIND_TICK = "REMIND_TICK"
    PROSPECTIVE_REMIND_TICK = "PROSPECTIVE_REMIND_TICK"

    # System Events
    DSAR_EXPORT = "DSAR_EXPORT"
    REINDEX_REQUEST = "REINDEX_REQUEST"
    ML_RUN_EVENT = "ML_RUN_EVENT"
    WORKFLOW_UPDATE = "WORKFLOW_UPDATE"
    PII_MINIMIZED = "PII_MINIMIZED"
    TOMBSTONE_APPLIED = "TOMBSTONE_APPLIED"
    TOMBSTONE_PROPAGATE = "TOMBSTONE_PROPAGATE"
    SAFETY_ALERT = "SAFETY_ALERT"
    JOB_STATUS_CHANGED = "JOB_STATUS_CHANGED"
    MEMORY_RECEIPT_CREATED = "MEMORY_RECEIPT_CREATED"
    INTEGRATION_THING_CHANGED = "INTEGRATION_THING_CHANGED"
    PRESENCE_DEVICE_CHANGED = "PRESENCE_DEVICE_CHANGED"
    SAFETY_BAND_CHANGED = "SAFETY_BAND_CHANGED"


class SecurityBand(Enum):
    """Security band levels matching envelope schema."""

    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    BLACK = "BLACK"


class Capability(Enum):
    """Actor capabilities."""

    WRITE = "WRITE"
    RECALL = "RECALL"
    PROJECT = "PROJECT"
    SCHEDULE = "SCHEDULE"


class Obligation(Enum):
    """Policy obligations."""

    REDACT_PII = "REDACT_PII"
    AUDIT_ACCESS = "AUDIT_ACCESS"
    TOMBSTONE_ON_DELETE = "TOMBSTONE_ON_DELETE"
    SYNC_REQUIRED = "SYNC_REQUIRED"


@dataclass
class Actor:
    """Event actor matching envelope schema."""

    user_id: str
    caps: List[Capability]
    agent_id: Optional[str] = None


@dataclass
class Device:
    """Event device matching envelope schema."""

    device_id: str
    platform: Optional[str] = None
    app_version: Optional[str] = None
    locale: Optional[str] = None


@dataclass
class QoS:
    """Quality of Service parameters."""

    priority: int
    latency_budget_ms: int
    routing: str = "gate-path"
    retries: int = 0
    deadline_ms: Optional[int] = None


@dataclass
class EventMeta:
    """Event metadata matching envelope schema."""

    topic: EventType
    actor: Actor
    device: Device
    space_id: str
    band: SecurityBand
    policy_version: str
    qos: QoS
    obligations: List[Obligation]

    # Fields with default factories
    id: str = field(default_factory=generate_event_id)
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Optional fields
    ingest_ts: Optional[datetime] = None
    mls_group: Optional[str] = None
    abac: Optional[Dict[str, Any]] = None
    trace: Optional[Dict[str, Any]] = None
    redaction_applied: bool = False
    hashes: Optional[Dict[str, str]] = None
    idempotency_key: Optional[str] = None
    signature: Optional[Dict[str, str]] = None
    x_extensions: Optional[Dict[str, Any]] = None


@dataclass
class Event:
    """Complete event with metadata and payload."""

    meta: EventMeta
    payload: Dict[str, Any]

    def to_envelope(self) -> Dict[str, Any]:
        """Convert to envelope format for validation."""
        envelope = {
            "schema_version": "1.3.0",
            "id": self.meta.id,
            "ts": self.meta.ts.isoformat(),
            "topic": self.meta.topic.value,  # Use .value for EventType enum
            "actor": {
                "user_id": self.meta.actor.user_id,
                "caps": [c.value for c in self.meta.actor.caps],
            },
            "device": {"device_id": self.meta.device.device_id},
            "space_id": self.meta.space_id,
            "band": self.meta.band.value,
            "policy_version": self.meta.policy_version,
            "qos": {
                "priority": self.meta.qos.priority,
                "latency_budget_ms": self.meta.qos.latency_budget_ms,
                "routing": self.meta.qos.routing,
                "retries": self.meta.qos.retries,
            },
            "obligations": [o.value for o in self.meta.obligations],
            "redaction_applied": self.meta.redaction_applied,
            "hashes": self.meta.hashes or {"payload_sha256": "0" * 64},
            "payload": self.payload,
            "signature": self.meta.signature
            or {"alg": "ed25519", "key_id": "stub-key", "signature": "stub-sig"},
        }

        # Add optional fields
        if self.meta.actor.agent_id:
            envelope["actor"]["agent_id"] = self.meta.actor.agent_id
        if self.meta.device.platform:
            envelope["device"]["platform"] = self.meta.device.platform
        if self.meta.device.app_version:
            envelope["device"]["app_version"] = self.meta.device.app_version
        if self.meta.device.locale:
            envelope["device"]["locale"] = self.meta.device.locale
        if self.meta.ingest_ts:
            envelope["ingest_ts"] = self.meta.ingest_ts.isoformat()
        if self.meta.mls_group:
            envelope["mls_group"] = self.meta.mls_group
        if self.meta.abac:
            envelope["abac"] = self.meta.abac
        if self.meta.trace:
            envelope["trace"] = self.meta.trace
        if self.meta.idempotency_key:
            envelope["idempotency_key"] = self.meta.idempotency_key
        if self.meta.x_extensions:
            envelope["x_extensions"] = self.meta.x_extensions
        if self.meta.qos.deadline_ms:
            envelope["qos"]["deadline_ms"] = self.meta.qos.deadline_ms

        return envelope

    def validate(self) -> None:
        """Validate event against envelope schema."""
        envelope = self.to_envelope()
        validate_envelope_and_payload(envelope)

    @classmethod
    def from_envelope(cls, envelope: Dict[str, Any]) -> "Event":
        """Create Event from envelope format."""
        # Parse actor
        actor_data = envelope["actor"]
        actor = Actor(
            user_id=actor_data["user_id"],
            caps=[Capability(c) for c in actor_data["caps"]],
            agent_id=actor_data.get("agent_id"),
        )

        # Parse device
        device_data = envelope["device"]
        device = Device(
            device_id=device_data["device_id"],
            platform=device_data.get("platform"),
            app_version=device_data.get("app_version"),
            locale=device_data.get("locale"),
        )

        # Parse QoS
        qos_data = envelope["qos"]
        qos = QoS(
            priority=qos_data["priority"],
            latency_budget_ms=qos_data["latency_budget_ms"],
            routing=qos_data.get("routing", "gate-path"),
            retries=qos_data.get("retries", 0),
            deadline_ms=qos_data.get("deadline_ms"),
        )

        # Parse timestamps
        ts = datetime.fromisoformat(envelope["ts"].replace("Z", "+00:00"))
        ingest_ts = None
        if "ingest_ts" in envelope:
            ingest_ts = datetime.fromisoformat(
                envelope["ingest_ts"].replace("Z", "+00:00")
            )

        # Create EventMeta
        meta = EventMeta(
            id=envelope["id"],
            ts=ts,
            topic=EventType(envelope["topic"]),
            actor=actor,
            device=device,
            space_id=envelope["space_id"],
            band=SecurityBand(envelope["band"]),
            policy_version=envelope["policy_version"],
            qos=qos,
            obligations=[Obligation(o) for o in envelope.get("obligations", [])],
            ingest_ts=ingest_ts,
            mls_group=envelope.get("mls_group"),
            abac=envelope.get("abac"),
            trace=envelope.get("trace"),
            redaction_applied=envelope.get("redaction_applied", False),
            hashes=envelope.get("hashes"),
            idempotency_key=envelope.get("idempotency_key"),
            signature=envelope.get("signature"),
            x_extensions=envelope.get("x_extensions"),
        )

        return cls(meta=meta, payload=envelope["payload"])


def create_event(
    topic: EventType,
    payload: Dict[str, Any],
    actor: Actor,
    device: Device,
    space_id: str,
    band: SecurityBand = SecurityBand.GREEN,
    policy_version: str = "1.0.0",
    qos_priority: int = 5,
    qos_latency_budget_ms: int = 100,
) -> Event:
    """Factory function to create a valid event."""
    return Event(
        meta=EventMeta(
            topic=topic,
            actor=actor,
            device=device,
            space_id=space_id,
            band=band,
            policy_version=policy_version,
            qos=QoS(priority=qos_priority, latency_budget_ms=qos_latency_budget_ms),
            obligations=[],
        ),
        payload=payload,
    )

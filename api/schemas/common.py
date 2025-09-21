"""
Common schemas derived from contracts/api/openapi.v1.yaml and contracts/events/envelope.schema.json
100% contract compliant - DO NOT MODIFY without updating contracts first
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Enums from OpenAPI contract
Band = Literal["GREEN", "AMBER", "RED", "BLACK"]
Capability = Literal["WRITE", "RECALL", "PROJECT", "SCHEDULE"]
AuthMethod = Literal["mtls", "jwt", "api_key"]
TrustLevel = Literal["green", "amber", "red", "black"]
Platform = Literal["ios", "android", "macos", "windows", "linux", "web", "edge"]
Role = Literal["parent", "child", "guest", "system", "service"]
Obligation = Literal[
    "REDACT_PII", "AUDIT_ACCESS", "TOMBSTONE_ON_DELETE", "SYNC_REQUIRED"
]


class Actor(BaseModel):
    """Actor schema from contracts/events/envelope.schema.json"""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    agent_id: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9._:-]{3,64}$")
    caps: List[Capability] = Field(min_length=1)


class Device(BaseModel):
    """Device schema from contracts/events/envelope.schema.json"""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{3,64}$")
    platform: Optional[Platform] = None
    app_version: Optional[str] = Field(
        None, pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-.]+)?$"
    )
    locale: Optional[str] = Field(None, pattern=r"^[A-Za-z]{2}(-[A-Za-z]{2})?$")


class ABAC(BaseModel):
    """ABAC context from contracts/events/envelope.schema.json"""

    model_config = ConfigDict(extra="forbid")

    role: Optional[Role] = None
    trust: Optional[TrustLevel] = None
    geo_precision: Optional[Literal["city", "region"]] = None


class QoS(BaseModel):
    """QoS schema from contracts/events/envelope.schema.json"""

    model_config = ConfigDict(extra="forbid")

    routing: Literal["fast-path", "gate-path"] = "gate-path"
    priority: int = Field(ge=1, le=10)
    latency_budget_ms: int = Field(ge=1, le=1000)
    retries: Optional[int] = Field(None, ge=0, le=3)
    deadline_ms: Optional[int] = Field(None, ge=1)


class Trace(BaseModel):
    """Trace schema from contracts/events/envelope.schema.json"""

    model_config = ConfigDict(extra="forbid")

    trace_id: Optional[str] = Field(None, pattern=r"^[a-f0-9]{32}$")
    span_id: Optional[str] = Field(None, pattern=r"^[a-f0-9]{16}$")
    parent_span_id: Optional[str] = Field(None, pattern=r"^[a-f0-9]{16}$")
    sampled: bool = True


class Hashes(BaseModel):
    """Hashes schema from contracts/events/envelope.schema.json"""

    model_config = ConfigDict(extra="forbid")

    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    envelope_sha256: Optional[str] = Field(None, pattern=r"^[a-f0-9]{64}$")
    prev_event_id: Optional[Union[UUID, str]] = None  # UUID or ULID
    merkle_root: Optional[str] = Field(None, pattern=r"^[a-f0-9]{64}$")


class Signature(BaseModel):
    """Signature schema from contracts/events/envelope.schema.json"""

    model_config = ConfigDict(extra="forbid")

    alg: Literal["ed25519", "ecdsa_p256"]
    key_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{8,128}$")
    public_key: Optional[str] = Field(None, description="base64 encoded")
    signature: str = Field(description="base64 encoded")


class Envelope(BaseModel):
    """
    Canonical Event Envelope from contracts/events/envelope.schema.json
    Used for all internal events - strict validation at bus ingress
    """

    model_config = ConfigDict(extra="forbid")

    # Required core fields
    schema_version: str = Field(
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
    )
    id: Union[UUID, str]  # UUID or ULID
    ts: datetime
    topic: str  # Event topic enum or name@semver
    actor: Actor
    device: Device
    space_id: str = Field(
        pattern=r"^(personal|selective|shared|extended|interfamily):[A-Za-z0-9_\-\.]+$"
    )
    band: Band
    policy_version: str = Field(
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?$"
    )
    qos: QoS
    hashes: Hashes
    payload: Dict[str, Any]
    signature: Signature

    # Optional fields
    ingest_ts: Optional[datetime] = None
    abac: Optional[ABAC] = None
    mls_group: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9._:-]{3,64}$")
    trace: Optional[Trace] = None
    obligations: List[Obligation] = Field(default_factory=list)
    redaction_applied: Optional[bool] = None
    idempotency_key: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9._:-]{8,64}$")
    x_extensions: Optional[Dict[str, Any]] = None


class SecurityContext(BaseModel):
    """SecurityContext schema from contracts/api/openapi.v1.yaml"""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    device_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{3,64}$")
    authenticated: bool
    auth_method: Optional[AuthMethod] = None
    capabilities: Optional[List[Capability]] = None
    mls_group: Optional[str] = Field(None, pattern=r"^[A-Za-z0-9._:-]{3,64}$")
    trust_level: Optional[TrustLevel] = None


class Problem(BaseModel):
    """RFC 7807 Problem Details schema from contracts/api/openapi.v1.yaml"""

    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int = Field(ge=100, le=599)
    detail: Optional[str] = None
    instance: Optional[str] = None
    traceId: Optional[str] = Field(None, pattern=r"^[a-f0-9]{32}$")

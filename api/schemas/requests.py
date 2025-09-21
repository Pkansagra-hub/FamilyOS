"""
Request schema models for MemoryOS API - Contract Compliant.

Contains all request body schemas matching OpenAPI contract exactly.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .core import SecurityContext


class QoSRequest(BaseModel):
    """QoS parameters for requests - Contract Compliant."""

    model_config = ConfigDict(extra="forbid")

    priority: Optional[int] = Field(None, ge=1, le=10, description="Request priority")
    latency_budget_ms: Optional[int] = Field(
        None, ge=1, le=1000, description="Latency budget in milliseconds"
    )
    retries: Optional[int] = Field(None, ge=0, le=3, description="Number of retries")


class SubmitRequest(BaseModel):
    """Request schema for memory submission - Contract Compliant."""

    model_config = ConfigDict(
        extra="forbid",  # additionalProperties: false from contract
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "space_id": "personal:work",
                "text": "Important meeting notes from today",
                "attachments": ["https://example.com/doc1.pdf"],
                "payload": {"source": "meeting", "participants": ["alice", "bob"]},
                "idempotency_key": "submit_20240910_001",
                "qos": {"priority": 5, "latency_budget_ms": 80},
            }
        },
    )

    # Required field from contract
    space_id: str = Field(..., description="Target memory space with namespace")

    # Optional fields from contract
    text: Optional[str] = Field(None, description="Text content to store")
    attachments: Optional[List[str]] = Field(
        None, description="Array of attachment URIs"
    )
    payload: Optional[Dict[str, Any]] = Field(
        None, description="Structured payload object"
    )
    idempotency_key: Optional[str] = Field(
        None, pattern=r"^[A-Za-z0-9._:-]{8,64}$", description="Idempotency key"
    )
    qos: Optional[QoSRequest] = Field(None, description="Quality of service parameters")

    @field_validator("space_id")
    @classmethod
    def validate_space_id(cls, v: str) -> str:
        """Validate space_id matches contract pattern."""
        import re

        if not re.match(r"^(personal|selective|shared|extended|interfamily):", v):
            raise ValueError(
                "space_id must start with personal:, selective:, shared:, extended:, or interfamily:"
            )

        _, context = v.split(":", 1)
        if not context:
            raise ValueError("space_id must have context after namespace")
        return v.strip()

    @field_validator("attachments")
    @classmethod
    def validate_attachments(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate attachment URIs."""
        if v is None:
            return v

        import re

        uri_pattern = re.compile(r"^https?://[^\s]+$")
        for attachment in v:
            if not uri_pattern.match(attachment):
                raise ValueError(f"Invalid URI format: {attachment}")
        return v


class RecallRequest(BaseModel):
    """Request schema for memory recall - Contract Compliant."""

    model_config = ConfigDict(
        extra="forbid",  # additionalProperties: false from contract
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "query": "meeting notes about project planning",
                "space_id": "personal:work",
                "k": 10,
                "filters": {
                    "after": "2024-01-01T00:00:00Z",
                    "topics": ["meeting"],
                    "bands": ["GREEN", "AMBER"],
                },
                "return_trace": False,
                "qos": {"latency_budget_ms": 120, "priority": 5},
            }
        },
    )

    # Required field from contract
    query: str = Field(..., min_length=1, description="Search query for memory recall")

    # Optional fields from contract
    space_id: Optional[str] = Field(None, description="Memory space to search in")
    k: Optional[int] = Field(10, ge=1, le=200, description="Maximum number of results")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    return_trace: Optional[bool] = Field(False, description="Return trace information")
    qos: Optional[QoSRequest] = Field(None, description="Quality of service parameters")

    @field_validator("space_id")
    @classmethod
    def validate_space_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate space_id matches contract pattern."""
        if v is None:
            return v

        import re

        if not re.match(r"^(personal|selective|shared|extended|interfamily):", v):
            raise ValueError(
                "space_id must start with personal:, selective:, shared:, extended:, or interfamily:"
            )
        return v.strip()

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate filters match contract schema."""
        if v is None:
            return v

        allowed_keys = {"after", "before", "topics", "bands"}
        for key in v.keys():
            if key not in allowed_keys:
                raise ValueError(
                    f"Filter key '{key}' not allowed. Must be one of: {allowed_keys}"
                )

        # Validate bands if present
        if "bands" in v:
            valid_bands = {"GREEN", "AMBER", "RED", "BLACK"}
            for band in v["bands"]:
                if band not in valid_bands:
                    raise ValueError(
                        f"Invalid band '{band}'. Must be one of: {valid_bands}"
                    )

        return v


class ProjectRequest(BaseModel):
    """Request schema for sharing projection - Contract Compliant."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {"source_id": "mem_12345", "target_space_id": "shared:household"}
        },
    )

    # Required fields from contract
    source_id: str = Field(..., description="Source memory identifier")
    target_space_id: str = Field(..., description="Target space for projection")

    @field_validator("target_space_id")
    @classmethod
    def validate_target_space_id(cls, v: str) -> str:
        """Validate target_space_id matches contract pattern."""
        import re

        if not re.match(r"^(personal|selective|shared|extended|interfamily):", v):
            raise ValueError(
                "target_space_id must start with personal:, selective:, shared:, extended:, or interfamily:"
            )
        return v.strip()

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "source_space": "personal:work",
                "target_space": "shared:team",
                "sync_type": "incremental",
                "security_context": {"user_id": "user123", "session_id": "sess456"},
            }
        },
    )

    source_space: str = Field(..., description="Source memory space", min_length=1)
    target_space: str = Field(..., description="Target memory space", min_length=1)
    sync_type: str = Field(default="incremental", description="Type of synchronization")
    security_context: SecurityContext = Field(
        ..., description="Security context for sync"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Sync filters"
    )
    dry_run: Optional[bool] = Field(
        default=False, description="Perform dry run without actual sync"
    )

    @field_validator("source_space", "target_space")
    @classmethod
    def validate_spaces(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("Space must be in format 'namespace:context'")
        return v.strip()

    @field_validator("sync_type")
    @classmethod
    def validate_sync_type(cls, v: str) -> str:
        allowed_types = ["full", "incremental", "selective"]
        if v not in allowed_types:
            raise ValueError(f"sync_type must be one of: {', '.join(allowed_types)}")
        return v


class RegisterRequest(BaseModel):
    """Service registration request."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "service_name": "my-memory-service",
                "endpoints": ["submit", "recall"],
                "callback_url": "https://my-service.local/callback",
                "metadata": {"version": "1.0.0"},
            }
        },
    )

    service_name: str = Field(
        ..., min_length=1, max_length=255, description="Service name"
    )
    endpoints: List[str] = Field(..., min_length=1, description="Supported endpoints")
    callback_url: Optional[str] = Field(
        None, description="Callback URL for notifications"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Service metadata")


class UnregisterRequest(BaseModel):
    """Service unregistration request."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {"registration_id": "reg_123456", "reason": "Service shutdown"}
        },
    )

    registration_id: str = Field(..., description="Registration identifier")
    reason: Optional[str] = Field(None, description="Unregistration reason")


class SyncRequest(BaseModel):
    """Synchronization request."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "source": "local",
                "target": "remote",
                "conflict_resolution": "merge",
                "filters": {"space_id": "personal:work"},
            }
        },
    )

    source: str = Field(..., description="Source location")
    target: str = Field(..., description="Target location")
    conflict_resolution: Optional[str] = Field(
        "merge", description="Conflict resolution strategy"
    )
    filters: Optional[Dict[str, Any]] = Field(None, description="Sync filters")

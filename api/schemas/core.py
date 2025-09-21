"""
Core Pydantic models for MemoryOS.

Contains fundamental data structures used across the API.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SecurityBand(str, Enum):
    """Security classification levels for memory access control."""

    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    BLACK = "BLACK"


class TrustLevel(str, Enum):
    """Trust levels from contract - lowercase as per OpenAPI spec."""

    GREEN = "green"
    AMBER = "amber"
    RED = "red"
    BLACK = "black"


class AuthMethod(str, Enum):
    """Authentication methods from contract."""

    MTLS = "mtls"
    JWT = "jwt"
    API_KEY = "api_key"


class Capability(str, Enum):
    """System capabilities from contract - exact match to OpenAPI spec."""

    WRITE = "WRITE"
    RECALL = "RECALL"
    PROJECT = "PROJECT"
    SCHEDULE = "SCHEDULE"


class SecurityContext(BaseModel):
    """Security context for memory operations - Contract Compliant."""

    model_config = ConfigDict(
        extra="forbid",  # additionalProperties: false from contract
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "device_id": "dad_iphone_12pro",
                "authenticated": True,
                "auth_method": "mtls",
                "capabilities": ["WRITE", "RECALL"],
                "mls_group": "family_household",
                "trust_level": "green",
            }
        },
    )

    # Required fields from contract
    user_id: str = Field(..., description="UUID format user identifier")
    device_id: str = Field(
        ..., pattern=r"^[A-Za-z0-9._:-]{3,64}$", description="Device identifier"
    )
    authenticated: bool = Field(..., description="Authentication status")

    # Optional fields from contract
    auth_method: Optional[AuthMethod] = Field(None, description="Authentication method")
    capabilities: Optional[List[Capability]] = Field(
        None, description="Available capabilities"
    )
    mls_group: Optional[str] = Field(
        None, pattern=r"^[A-Za-z0-9._:-]{3,64}$", description="MLS group identifier"
    )
    trust_level: Optional[TrustLevel] = Field(None, description="Trust level")

    @field_validator("user_id")
    @classmethod
    def validate_user_id_uuid(cls, v: str) -> str:
        """Validate user_id is UUID format as per contract."""
        try:
            # Validate UUID format
            from uuid import UUID

            UUID(v)
            return v
        except ValueError:
            raise ValueError("user_id must be valid UUID format")

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v: str) -> str:
        """Validate device ID format and content"""
        if not v or len(v) < 3 or len(v) > 64:
            raise ValueError("device_id must be 3-64 characters")

        # Additional validation for device naming conventions
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("device_id cannot start or end with hyphen")

        return v

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(
        cls, v: Optional[List[Capability]]
    ) -> Optional[List[Capability]]:
        """Validate capabilities list for duplicates."""
        if v is None:
            return v

        # Remove duplicates while preserving order
        seen = set()
        unique_caps = []
        for cap in v:
            if cap not in seen:
                seen.add(cap)
                unique_caps.append(cap)

        return unique_caps


class MemoryItem(BaseModel):
    """Core memory item structure."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "content": "Important meeting notes from today",
                "space": "personal:work",
                "metadata": {"source": "meeting", "participants": ["alice", "bob"]},
                "tags": ["meeting", "work", "important"],
                "importance": 0.8,
            }
        },
    )

    id: Optional[str] = Field(None, description="Unique memory identifier")
    content: str = Field(
        ..., description="Memory content", min_length=1, max_length=1000000
    )
    space: str = Field(..., description="Memory space identifier", min_length=1)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Memory metadata"
    )
    security_context: SecurityContext = Field(
        ..., description="Security context for this memory"
    )
    tags: List[str] = Field(default_factory=list, description="Memory tags")
    importance: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Memory importance score"
    )

    @field_validator("space")
    @classmethod
    def validate_space(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("Memory space must be in format 'namespace:context'")
        return v.strip()


class SpacePolicy(BaseModel):
    """Policy configuration for memory spaces."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "space": "personal:work",
                "retention_days": 365,
                "max_size_mb": 1024,
                "encryption_required": True,
                "access_controls": {"read": ["user123"], "write": ["user123"]},
                "security_band": "AMBER",
            }
        },
    )

    space: str = Field(..., description="Memory space identifier", min_length=1)
    retention_days: Optional[int] = Field(
        None, ge=1, description="Retention period in days"
    )
    max_size_mb: Optional[int] = Field(
        None, ge=1, description="Maximum space size in MB"
    )
    encryption_required: bool = Field(
        default=False, description="Whether encryption is required"
    )
    access_controls: Dict[str, List[str]] = Field(
        default_factory=dict, description="Access control rules"
    )
    security_band: SecurityBand = Field(
        default=SecurityBand.GREEN, description="Required security band"
    )

    @field_validator("space")
    @classmethod
    def validate_space(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("Space must be in format 'namespace:context'")
        return v.strip()


class UserProfile(BaseModel):
    """User profile information."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "user_id": "user123",
                "display_name": "Alice Smith",
                "email": "alice@example.com",
                "preferences": {"theme": "dark", "notifications": True},
            }
        },
    )

    user_id: str = Field(..., description="Unique user identifier", min_length=1)
    display_name: str = Field(
        ..., description="User display name", min_length=1, max_length=100
    )
    email: Optional[str] = Field(None, description="User email address")
    preferences: Dict[str, Any] = Field(
        default_factory=dict, description="User preferences"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Profile creation time",
    )
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")


class MemorySpace(BaseModel):
    """Memory space configuration."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "space": "personal:work",
                "display_name": "Work Memories",
                "description": "Personal work-related memories and notes",
                "owner_id": "user123",
            }
        },
    )

    space: str = Field(..., description="Space identifier", min_length=1)
    display_name: str = Field(
        ..., description="Human-readable space name", min_length=1
    )
    description: Optional[str] = Field(None, description="Space description")
    owner_id: str = Field(..., description="Space owner user ID", min_length=1)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    policy: SpacePolicy = Field(..., description="Space policy configuration")

    @field_validator("space")
    @classmethod
    def validate_space(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("Space must be in format 'namespace:context'")
        return v.strip()


class ActivityLog(BaseModel):
    """Activity log entry."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user123",
                "action": "memory_submit",
                "resource": "memory456",
                "metadata": {"space": "personal:work", "size_bytes": 1024},
                "success": True,
            }
        }
    )

    id: Optional[str] = Field(None, description="Log entry ID")
    user_id: str = Field(..., description="User who performed the action", min_length=1)
    action: str = Field(..., description="Action performed", min_length=1)
    resource: Optional[str] = Field(None, description="Resource affected")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Action timestamp",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional action metadata"
    )
    success: bool = Field(default=True, description="Whether action was successful")


class ActionCapability(BaseModel):
    """Action capability definition."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "memory_recall",
                "description": "Ability to recall memories from the system",
                "required_trust_level": "MEDIUM",
                "required_capabilities": ["READ"],
                "parameters": {"max_results": 100},
            }
        }
    )

    name: str = Field(..., description="Capability name", min_length=1)
    description: str = Field(..., description="Capability description", min_length=1)
    required_trust_level: TrustLevel = Field(
        ..., description="Minimum required trust level"
    )
    required_capabilities: List[Capability] = Field(
        default_factory=list, description="Required system capabilities"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Capability parameters"
    )


class Envelope(BaseModel):
    """
    Standard envelope for API operations.
    Simplified envelope for internal use - full event envelope is in events/envelope.schema.json
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    envelope_id: str = Field(..., description="Unique envelope identifier")
    operation: str = Field(..., description="Operation being performed")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Operation timestamp",
    )
    trace_id: Optional[str] = Field(None, description="Tracing identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    space_id: Optional[str] = Field(None, description="Memory space identifier")
    security_band: SecurityBand = Field(
        default=SecurityBand.GREEN, description="Security classification"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

"""
Event schema models for MemoryOS.

Contains schemas for event messages and envelopes.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .core import SecurityBand


class Envelope(BaseModel):
    """Event envelope for message transport."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "evt_123456",
                "event_type": "memory.submitted",
                "source": "memoryos.api",
                "timestamp": "2025-09-09T12:00:00Z",
                "data": {"memory_id": "mem_123", "space": "personal:work"},
                "security_band": "GREEN",
            }
        }
    )

    id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event type identifier")
    source: str = Field(..., description="Event source identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp",
    )
    data: Dict[str, Any] = Field(..., description="Event payload data")
    version: str = Field(default="1.0", description="Event schema version")
    security_band: SecurityBand = Field(
        default=SecurityBand.GREEN, description="Security classification"
    )
    correlation_id: Optional[str] = Field(
        None, description="Correlation identifier for tracing"
    )
    causation_id: Optional[str] = Field(
        None, description="Causation identifier for event sourcing"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional event metadata"
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if not v or "." not in v:
            raise ValueError("Event type must be in format 'domain.action'")
        return v.lower()

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if not v or "." not in v:
            raise ValueError("Event source must be in format 'service.component'")
        return v.lower()


class MemoryEvent(BaseModel):
    """Base memory-related event data."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "memory_id": "mem_123456",
                "user_id": "user123",
                "space": "personal:work",
                "action": "submitted",
            }
        }
    )

    memory_id: str = Field(..., description="Memory identifier")
    user_id: str = Field(..., description="User who triggered the event")
    space: str = Field(..., description="Memory space")
    action: str = Field(..., description="Action performed")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Action timestamp",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional event metadata"
    )


class MemorySubmittedEvent(MemoryEvent):
    """Event for memory submission."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "memory_id": "mem_123456",
                "user_id": "user123",
                "space": "personal:work",
                "action": "submitted",
                "content_size": 1024,
                "tags": ["meeting", "important"],
            }
        }
    )

    action: str = Field(default="submitted", description="Action performed")
    content_size: int = Field(..., ge=0, description="Size of memory content in bytes")
    tags: Optional[List[str]] = Field(default_factory=list, description="Memory tags")
    importance: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Memory importance score"
    )


class MemoryRecalledEvent(MemoryEvent):
    """Event for memory recall."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "memory_id": "mem_123456",
                "user_id": "user123",
                "space": "personal:work",
                "action": "recalled",
                "query": "meeting notes",
                "relevance_score": 0.95,
            }
        }
    )

    action: str = Field(default="recalled", description="Action performed")
    query: str = Field(..., description="Search query used")
    relevance_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Relevance score"
    )
    results_count: Optional[int] = Field(
        None, ge=0, description="Number of results returned"
    )


class PolicyEvent(BaseModel):
    """Policy decision event data."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "decision_id": "dec_123456",
                "user_id": "user123",
                "resource": "/api/v1/memories/submit",
                "action": "POST",
                "decision": "PERMIT",
                "reason": "User has sufficient privileges",
            }
        }
    )

    decision_id: str = Field(..., description="Policy decision identifier")
    user_id: str = Field(..., description="User requesting access")
    resource: str = Field(..., description="Resource being accessed")
    action: str = Field(..., description="Action being performed")
    decision: str = Field(..., description="Policy decision")
    reason: str = Field(..., description="Decision reason")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Decision timestamp",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional decision metadata"
    )

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        allowed_decisions = ["PERMIT", "DENY", "INDETERMINATE", "NOT_APPLICABLE"]
        if v not in allowed_decisions:
            raise ValueError(f"Decision must be one of: {', '.join(allowed_decisions)}")
        return v


class SecurityEvent(BaseModel):
    """Security-related event data."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "sec_123456",
                "event_type": "AUTHENTICATION_SUCCESS",
                "user_id": "user123",
                "resource": "/api/v1/memories",
                "severity": "INFO",
                "ip_address": "192.168.1.100",
            }
        }
    )

    event_id: str = Field(..., description="Security event identifier")
    event_type: str = Field(..., description="Type of security event")
    user_id: Optional[str] = Field(None, description="User involved in the event")
    session_id: Optional[str] = Field(None, description="Session identifier")
    resource: str = Field(..., description="Resource accessed")
    severity: str = Field(..., description="Event severity level")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional security metadata"
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        allowed_types = [
            "AUTHENTICATION_SUCCESS",
            "AUTHENTICATION_FAILURE",
            "AUTHORIZATION_SUCCESS",
            "AUTHORIZATION_FAILURE",
            "ACCESS_GRANTED",
            "ACCESS_DENIED",
            "DATA_ACCESS",
            "DATA_MODIFICATION",
            "DATA_DELETION",
            "SYSTEM_EVENT",
            "SECURITY_VIOLATION",
        ]
        if v not in allowed_types:
            raise ValueError(f"Event type must be one of: {', '.join(allowed_types)}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        allowed_severities = ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]
        if v not in allowed_severities:
            raise ValueError(
                f"Severity must be one of: {', '.join(allowed_severities)}"
            )
        return v.upper()


class SyncEvent(BaseModel):
    """Synchronization event data."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sync_id": "sync_123456",
                "source_space": "personal:work",
                "target_space": "shared:team",
                "sync_type": "incremental",
                "status": "completed",
                "memories_synced": 25,
            }
        }
    )

    sync_id: str = Field(..., description="Synchronization identifier")
    source_space: str = Field(..., description="Source memory space")
    target_space: str = Field(..., description="Target memory space")
    sync_type: str = Field(..., description="Type of synchronization")
    status: str = Field(..., description="Synchronization status")
    memories_synced: int = Field(
        ..., ge=0, description="Number of memories synchronized"
    )
    duration_ms: Optional[int] = Field(
        None, ge=0, description="Synchronization duration"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional sync metadata"
    )

    @field_validator("sync_type")
    @classmethod
    def validate_sync_type(cls, v: str) -> str:
        allowed_types = ["full", "incremental", "selective"]
        if v not in allowed_types:
            raise ValueError(f"Sync type must be one of: {', '.join(allowed_types)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed_statuses = [
            "started",
            "in_progress",
            "completed",
            "failed",
            "cancelled",
        ]
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v

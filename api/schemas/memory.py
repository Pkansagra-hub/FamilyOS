"""
Memory-specific API schema models for MemoryOS - Based on MMD Architecture Diagram.

Contains memory operation schemas for API endpoints as defined in the architecture.
These are the API-level schemas used by memory handlers and routers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Import core schemas for compatibility
from .core import MemoryItem, MemorySpace, SecurityContext


class RecallQuery(BaseModel):
    """Query schema for memory recall operations - API Level Schema."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "query": "project planning meeting",
                "space_id": "personal:work",
                "k": 10,
                "filters": {
                    "time_range": {
                        "start": "2024-09-01T00:00:00Z",
                        "end": "2024-09-10T23:59:59Z",
                    },
                    "bands": ["GREEN", "AMBER"],
                },
                "options": {"include_embeddings": False, "include_metadata": True},
            }
        },
    )

    # Core query parameters
    query: str = Field(..., min_length=1, description="Search query text")
    space_id: str = Field(..., description="Memory space to search")
    k: int = Field(default=10, ge=1, le=100, description="Number of results to return")

    # Optional filtering
    filters: Optional[Dict[str, Any]] = Field(None, description="Query filters")
    options: Optional[Dict[str, Any]] = Field(None, description="Query options")

    # Context
    context: Optional[Dict[str, Any]] = Field(None, description="Query context")

    @field_validator("space_id")
    @classmethod
    def validate_space_id(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("space_id must be in format 'namespace:context'")
        return v.strip()


class MemoryEnvelope(BaseModel):
    """Memory operation envelope for tracking and routing - API Level Schema."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "envelope_id": "env_20240910_001",
                "operation": "submit",
                "space_id": "personal:work",
                "timestamp": "2024-09-10T12:00:00Z",
                "security_context": {
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "device_id": "123e4567-e89b-12d3-a456-426614174001",
                    "authenticated": True,
                    "auth_method": "jwt",
                    "capabilities": ["WRITE"],
                    "trust_level": "green",
                },
                "qos": {"priority": "normal", "timeout_ms": 5000},
                "payload": {
                    "text": "Meeting notes from project planning",
                    "metadata": {"source": "voice_memo"},
                },
            }
        },
    )

    # Required envelope fields
    envelope_id: str = Field(..., description="Unique envelope identifier")
    operation: str = Field(..., description="Memory operation type")
    space_id: str = Field(..., description="Target memory space")
    timestamp: datetime = Field(..., description="Operation timestamp")
    security_context: SecurityContext = Field(..., description="Security context")

    # Optional envelope fields
    qos: Optional[Dict[str, Any]] = Field(
        None, description="Quality of service parameters"
    )
    payload: Optional[Dict[str, Any]] = Field(None, description="Operation payload")
    trace_id: Optional[str] = Field(None, description="Distributed tracing ID")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: str) -> str:
        allowed_ops = ["submit", "recall", "project", "refer", "detach", "undo"]
        if v not in allowed_ops:
            raise ValueError(f"operation must be one of: {', '.join(allowed_ops)}")
        return v


class MemoryResult(BaseModel):
    """Memory operation result item - API Level Schema."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "mem_123456",
                "score": 0.95,
                "content": "Meeting notes from project planning session",
                "space_id": "personal:work",
                "timestamp": "2024-09-10T12:00:00Z",
                "metadata": {
                    "source": "voice_memo",
                    "duration_seconds": 1800,
                    "participants": ["alice", "bob"],
                },
                "security_band": "GREEN",
            }
        },
    )

    # Core result fields
    id: str = Field(..., description="Memory item identifier")
    score: float = Field(..., ge=0, le=1, description="Relevance score")
    content: str = Field(..., description="Memory content")
    space_id: str = Field(..., description="Memory space")
    timestamp: datetime = Field(..., description="Memory timestamp")

    # Optional result fields
    metadata: Optional[Dict[str, Any]] = Field(None, description="Memory metadata")
    security_band: Optional[str] = Field(None, description="Security classification")
    snippet: Optional[str] = Field(None, description="Content snippet")
    links: Optional[List[str]] = Field(None, description="Related memory IDs")


class MemoryBatch(BaseModel):
    """Batch memory operation schema - API Level Schema."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "batch_id": "batch_20240910_001",
                "operation": "submit",
                "space_id": "personal:work",
                "items": [
                    {"text": "First memory item", "metadata": {"source": "email"}},
                    {"text": "Second memory item", "metadata": {"source": "document"}},
                ],
                "options": {"async_processing": True, "duplicate_detection": True},
            }
        },
    )

    # Required batch fields
    batch_id: str = Field(..., description="Batch identifier")
    operation: str = Field(..., description="Batch operation type")
    space_id: str = Field(..., description="Target memory space")
    items: List[Dict[str, Any]] = Field(..., min_length=1, description="Batch items")

    # Optional batch fields
    options: Optional[Dict[str, Any]] = Field(
        None, description="Batch processing options"
    )
    priority: Optional[str] = Field("normal", description="Processing priority")


class MemoryProjection(BaseModel):
    """Memory projection schema for prospective operations - API Level Schema."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "projection_id": "proj_20240910_001",
                "query": "What would happen if we changed the pricing model?",
                "space_id": "personal:work",
                "horizon": "30d",
                "confidence_threshold": 0.7,
                "context": {"domain": "business_planning", "scope": "pricing_strategy"},
            }
        },
    )

    # Required projection fields
    projection_id: str = Field(..., description="Projection identifier")
    query: str = Field(..., min_length=1, description="Projection query")
    space_id: str = Field(..., description="Memory space for projection")

    # Optional projection fields
    horizon: Optional[str] = Field("7d", description="Projection time horizon")
    confidence_threshold: Optional[float] = Field(
        0.5, ge=0, le=1, description="Minimum confidence"
    )
    context: Optional[Dict[str, Any]] = Field(None, description="Projection context")
    constraints: Optional[List[str]] = Field(None, description="Projection constraints")


class MemoryReference(BaseModel):
    """Memory reference schema for linking operations - API Level Schema."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "reference_id": "ref_20240910_001",
                "source_id": "mem_123456",
                "target_id": "mem_789012",
                "relationship": "relates_to",
                "strength": 0.8,
                "metadata": {
                    "created_by": "link_detection_algo",
                    "evidence": ["semantic_similarity", "temporal_proximity"],
                },
            }
        },
    )

    # Required reference fields
    reference_id: str = Field(..., description="Reference identifier")
    source_id: str = Field(..., description="Source memory ID")
    target_id: str = Field(..., description="Target memory ID")
    relationship: str = Field(..., description="Relationship type")

    # Optional reference fields
    strength: Optional[float] = Field(
        None, ge=0, le=1, description="Relationship strength"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Reference metadata")
    created_at: Optional[datetime] = Field(None, description="Reference creation time")


# Re-export core schemas for convenience
__all__ = [
    # Core schemas (re-exported)
    "MemoryItem",
    "MemorySpace",
    # API-level memory schemas (as per MMD diagram)
    "RecallQuery",
    "MemoryEnvelope",
    "MemoryResult",
    "MemoryBatch",
    "MemoryProjection",
    "MemoryReference",
]

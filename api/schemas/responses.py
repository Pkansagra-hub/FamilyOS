"""
Response schema models for MemoryOS API - Contract Compliant.

Contains all response schemas matching OpenAPI contract exactly.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SubmitAccepted(BaseModel):
    """Submit accepted response - Contract Compliant."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "status": "accepted",
                "envelope_id": "env_20240910_001",
                "receipt_url": "https://api.familyos.local/v1/receipts/env_20240910_001",
            }
        },
    )

    # Required fields from contract
    status: str = Field(
        ..., pattern="^accepted$", description="Submission status - must be 'accepted'"
    )
    envelope_id: str = Field(..., description="Unique envelope identifier")

    # Optional fields from contract
    receipt_url: Optional[str] = Field(None, description="URI to receipt endpoint")


class WriteReceipt(BaseModel):
    """Write receipt response - Contract Compliant."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "envelope_id": "env_20240910_001",
                "committed": True,
                "stores": [
                    {"name": "episodic", "ts": "2024-09-10T12:00:00Z"},
                    {"name": "semantic", "ts": "2024-09-10T12:00:01Z"},
                ],
            }
        },
    )

    # Required fields from contract
    envelope_id: str = Field(..., description="Envelope identifier")
    committed: bool = Field(..., description="Whether write was committed")
    stores: List[Dict[str, Any]] = Field(..., description="Store commitment details")


class RecallItem(BaseModel):
    """Individual recall result item - Contract Compliant."""

    model_config = ConfigDict(extra="forbid")

    # Required fields from contract
    id: str = Field(..., description="Memory item identifier")
    score: float = Field(..., ge=0, description="Relevance score")

    # Optional fields from contract
    topic: Optional[str] = Field(None, description="Memory topic")
    band: Optional[str] = Field(
        None, pattern="^(GREEN|AMBER|RED|BLACK)$", description="Security band"
    )
    snippet: Optional[str] = Field(None, description="Content snippet")
    space_id: Optional[str] = Field(None, description="Memory space identifier")
    payload: Optional[Dict[str, Any]] = Field(None, description="Full memory payload")


class TraceInfo(BaseModel):
    """Trace information for recall response - Contract Compliant."""

    model_config = ConfigDict(extra="forbid")

    features: Optional[List[str]] = Field(None, description="Feature extraction info")
    fusion: Optional[Dict[str, Any]] = Field(
        None, description="Fusion algorithm details"
    )
    ranker: Optional[Dict[str, Any]] = Field(
        None, description="Ranking algorithm details"
    )


class RecallResponse(BaseModel):
    """Recall response - Contract Compliant."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "mem_123456",
                        "score": 0.95,
                        "topic": "meeting",
                        "band": "GREEN",
                        "snippet": "Project planning discussion...",
                        "space_id": "personal:work",
                        "payload": {"content": "Full meeting notes"},
                    }
                ],
                "trace": {
                    "features": ["semantic", "temporal"],
                    "fusion": {"algorithm": "weighted"},
                    "ranker": {"model": "bert-v2"},
                },
            }
        },
    )

    # Required field from contract
    items: List[RecallItem] = Field(..., description="Recall result items")

    # Optional field from contract
    trace: Optional[TraceInfo] = Field(None, description="Trace information")


class ProjectAccepted(BaseModel):
    """Project accepted response - Contract Compliant."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {"link_group_id": "link_grp_001", "status": "accepted"}
        },
    )

    # Required fields from contract
    link_group_id: str = Field(..., description="Link group identifier")
    status: str = Field(..., pattern="^accepted$", description="Project status")


class ReferResponse(BaseModel):
    """Refer response - Contract Compliant."""

    model_config = ConfigDict(extra="forbid")

    resolved: Optional[bool] = Field(None, description="Whether reference was resolved")
    payload: Optional[Dict[str, Any]] = Field(None, description="Referenced content")


class ErrorResponse(BaseModel):
    """Standard error response - Contract Compliant."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "type": "https://example.com/errors/validation",
                "title": "Validation Error",
                "status": 400,
                "detail": "space_id must match required pattern",
                "instance": "/v1/tools/memory/submit",
                "traceId": "abc123def456",
            }
        },
    )

    type: Optional[str] = Field(None, description="Error type URI")
    title: Optional[str] = Field(None, description="Error title")
    status: Optional[int] = Field(None, ge=100, le=599, description="HTTP status code")
    detail: Optional[str] = Field(None, description="Error detail")
    instance: Optional[str] = Field(None, description="Error instance URI")
    traceId: Optional[str] = Field(
        None, pattern="^[a-f0-9]{32}$", description="Trace identifier"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2024-09-10T12:00:00Z",
                "version": "1.0.0",
                "uptime_seconds": 3600,
                "dependencies": {"database": "healthy", "security_module": "healthy"},
            }
        }
    )

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    uptime_seconds: int = Field(..., ge=0, description="Uptime in seconds")
    dependencies: Optional[Dict[str, str]] = Field(
        None, description="Dependency health status"
    )


class JobStatus(BaseModel):
    """Generic job status response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "job_123456",
                "status": "completed",
                "progress": 100,
                "created_at": "2024-09-10T12:00:00Z",
                "completed_at": "2024-09-10T12:05:00Z",
                "result": {"processed_items": 1500},
            }
        }
    )

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status")
    progress: Optional[int] = Field(
        None, ge=0, le=100, description="Progress percentage"
    )
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    result: Optional[Dict[str, Any]] = Field(None, description="Job result data")
    error: Optional[str] = Field(None, description="Error message if failed")


class BatchResponse(BaseModel):
    """Batch operation response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_items": 100,
                "successful": 95,
                "failed": 5,
                "batch_id": "batch_123456",
                "errors": [
                    {"item_id": "item_001", "error": "validation failed"},
                    {"item_id": "item_002", "error": "insufficient permissions"},
                ],
            }
        }
    )

    total_items: int = Field(..., ge=0, description="Total items in batch")
    successful: int = Field(..., ge=0, description="Successfully processed items")
    failed: int = Field(..., ge=0, description="Failed items")
    batch_id: str = Field(..., description="Batch identifier")
    errors: Optional[List[Dict[str, str]]] = Field(
        None, description="Error details for failed items"
    )


class RegisterResponse(BaseModel):
    """Service registration response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "registration_id": "reg_123456",
                "service_name": "my-memory-service",
                "status": "registered",
                "endpoints": ["submit", "recall"],
                "metadata": {"version": "1.0.0"},
            }
        }
    )

    registration_id: str = Field(..., description="Registration identifier")
    service_name: str = Field(..., description="Registered service name")
    status: str = Field(..., description="Registration status")
    endpoints: List[str] = Field(..., description="Available endpoints")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Service metadata")


class UnregisterResponse(BaseModel):
    """Service unregistration response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "registration_id": "reg_123456",
                "status": "unregistered",
                "timestamp": "2024-09-10T12:00:00Z",
            }
        }
    )

    registration_id: str = Field(..., description="Registration identifier")
    status: str = Field(..., description="Unregistration status")
    timestamp: datetime = Field(..., description="Unregistration timestamp")


class SyncResponse(BaseModel):
    """Synchronization response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sync_id": "sync_123456",
                "status": "completed",
                "items_synced": 150,
                "conflicts_resolved": 2,
                "timestamp": "2024-09-10T12:00:00Z",
            }
        }
    )

    sync_id: str = Field(..., description="Synchronization identifier")
    status: str = Field(..., description="Sync status")
    items_synced: int = Field(..., ge=0, description="Number of items synchronized")
    conflicts_resolved: Optional[int] = Field(
        None, ge=0, description="Conflicts resolved"
    )
    timestamp: datetime = Field(..., description="Sync completion timestamp")


class JobAccepted(BaseModel):
    """Job accepted response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "job_123456",
                "status": "accepted",
                "estimated_duration_seconds": 300,
                "status_url": "/v1/jobs/job_123456/status",
            }
        }
    )

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., pattern="^accepted$", description="Job status")
    estimated_duration_seconds: Optional[int] = Field(
        None, ge=0, description="Estimated duration"
    )
    status_url: Optional[str] = Field(None, description="Status check URL")


class Receipt(BaseModel):
    """Generic receipt response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "receipt_id": "receipt_123456",
                "operation": "submit",
                "timestamp": "2024-09-10T12:00:00Z",
                "details": {"envelope_id": "env_20240910_001"},
            }
        }
    )

    receipt_id: str = Field(..., description="Receipt identifier")
    operation: str = Field(..., description="Operation performed")
    timestamp: datetime = Field(..., description="Operation timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Operation details")


class StandardResponse(BaseModel):
    """Standard API response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "timestamp": "2024-09-10T12:00:00Z",
            }
        }
    )

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(..., description="Response timestamp")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")


# Legacy aliases for backward compatibility during migration
SubmitResponse = SubmitAccepted
ProjectResponse = ProjectAccepted

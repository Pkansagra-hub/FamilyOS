"""
Security-related schema models for MemoryOS API.

Contains schemas for security, policy, and authorization.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .core import Capability, SecurityBand, TrustLevel


class PolicyDecisionResponse(BaseModel):
    """Response schema for policy decision requests."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "decision": "PERMIT",
                "reason": "User has sufficient privileges",
                "obligations": ["log_access", "encrypt_response"],
                "advice": ["consider_rate_limiting"],
                "decision_id": "dec_123456",
            }
        }
    )

    decision: str = Field(
        ..., description="Policy decision (PERMIT/DENY/INDETERMINATE)"
    )
    reason: str = Field(..., description="Human-readable reason for the decision")
    obligations: Optional[List[str]] = Field(
        default_factory=list, description="Required obligations"
    )
    advice: Optional[List[str]] = Field(
        default_factory=list, description="Advisory actions"
    )
    decision_id: str = Field(..., description="Unique decision identifier")
    timestamp: datetime = Field(..., description="Decision timestamp")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Decision context"
    )

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        allowed_decisions = ["PERMIT", "DENY", "INDETERMINATE", "NOT_APPLICABLE"]
        if v not in allowed_decisions:
            raise ValueError(f"Decision must be one of: {', '.join(allowed_decisions)}")
        return v


class Problem(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "https://memoryos.ai/problems/validation-error",
                "title": "Validation Error",
                "status": 400,
                "detail": "The provided memory space format is invalid",
                "instance": "/api/v1/memories/submit",
            }
        }
    )

    type: str = Field(
        default="about:blank",
        description="URI reference that identifies the problem type",
    )
    title: str = Field(..., description="Short, human-readable summary of the problem")
    status: int = Field(..., ge=100, le=599, description="HTTP status code")
    detail: Optional[str] = Field(
        None, description="Human-readable explanation specific to this occurrence"
    )
    instance: Optional[str] = Field(
        None, description="URI reference that identifies the specific occurrence"
    )

    # Additional custom fields
    errors: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Detailed error information"
    )
    request_id: Optional[str] = Field(
        None, description="Request identifier for tracking"
    )
    timestamp: Optional[datetime] = Field(None, description="Error timestamp")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v != "about:blank" and not (
            v.startswith("http://") or v.startswith("https://")
        ):
            raise ValueError("Type must be 'about:blank' or a valid URI")
        return v


class AuthenticationChallenge(BaseModel):
    """Authentication challenge response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "challenge_type": "bearer_token",
                "realm": "memoryos",
                "challenge_data": {"nonce": "abc123", "algorithm": "HS256"},
                "expires_in": 300,
            }
        }
    )

    challenge_type: str = Field(..., description="Type of authentication challenge")
    realm: str = Field(..., description="Authentication realm")
    challenge_data: Dict[str, Any] = Field(..., description="Challenge-specific data")
    expires_in: int = Field(
        ..., ge=1, description="Challenge expiration time in seconds"
    )
    challenge_id: Optional[str] = Field(None, description="Unique challenge identifier")

    @field_validator("challenge_type")
    @classmethod
    def validate_challenge_type(cls, v: str) -> str:
        allowed_types = ["bearer_token", "basic", "digest", "oauth2", "api_key"]
        if v not in allowed_types:
            raise ValueError(
                f"Challenge type must be one of: {', '.join(allowed_types)}"
            )
        return v


class AccessToken(BaseModel):
    """Access token response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "read write",
                "refresh_token": "refresh_abc123",
            }
        }
    )

    access_token: str = Field(..., description="The access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., ge=1, description="Token expiration time in seconds")
    scope: Optional[str] = Field(None, description="Token scope")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    issued_at: Optional[datetime] = Field(None, description="Token issuance timestamp")


class SecurityAuditLog(BaseModel):
    """Security audit log entry."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "audit_123456",
                "event_type": "AUTHENTICATION_SUCCESS",
                "user_id": "user123",
                "resource": "/api/v1/memories/submit",
                "action": "POST",
                "result": "SUCCESS",
                "security_band": "GREEN",
            }
        }
    )

    event_id: str = Field(..., description="Unique audit event identifier")
    event_type: str = Field(..., description="Type of security event")
    user_id: Optional[str] = Field(None, description="User involved in the event")
    session_id: Optional[str] = Field(None, description="Session identifier")
    resource: str = Field(..., description="Resource accessed")
    action: str = Field(..., description="Action performed")
    result: str = Field(..., description="Event result")
    timestamp: datetime = Field(..., description="Event timestamp")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    security_band: SecurityBand = Field(
        ..., description="Security classification of the event"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional audit metadata"
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

    @field_validator("result")
    @classmethod
    def validate_result(cls, v: str) -> str:
        allowed_results = ["SUCCESS", "FAILURE", "BLOCKED", "WARNING"]
        if v not in allowed_results:
            raise ValueError(f"Result must be one of: {', '.join(allowed_results)}")
        return v


class PermissionScope(BaseModel):
    """Permission scope definition."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scope_name": "memory:read",
                "description": "Read access to memory data",
                "required_capabilities": ["READ"],
                "required_trust_level": "MEDIUM",
                "restrictions": {"space_pattern": "personal:*"},
            }
        }
    )

    scope_name: str = Field(..., description="Unique scope identifier")
    description: str = Field(..., description="Human-readable scope description")
    required_capabilities: List[Capability] = Field(
        ..., description="Required system capabilities"
    )
    required_trust_level: TrustLevel = Field(
        ..., description="Minimum required trust level"
    )
    restrictions: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional access restrictions"
    )
    expires_at: Optional[datetime] = Field(None, description="Scope expiration time")

    @field_validator("scope_name")
    @classmethod
    def validate_scope_name(cls, v: str) -> str:
        if not v or ":" not in v:
            raise ValueError("Scope name must be in format 'resource:action'")
        return v.lower()


class RoleDefinition(BaseModel):
    """Role definition with permissions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role_name": "memory_user",
                "description": "Standard memory system user",
                "permissions": ["memory:read", "memory:write"],
                "default_trust_level": "MEDIUM",
                "max_security_band": "AMBER",
            }
        }
    )

    role_name: str = Field(..., description="Unique role identifier")
    description: str = Field(..., description="Human-readable role description")
    permissions: List[str] = Field(..., description="Granted permission scopes")
    default_trust_level: TrustLevel = Field(
        default=TrustLevel.AMBER, description="Default trust level for this role"
    )
    max_security_band: SecurityBand = Field(
        default=SecurityBand.GREEN, description="Maximum security band accessible"
    )
    is_system_role: bool = Field(
        default=False, description="Whether this is a system-defined role"
    )
    created_at: Optional[datetime] = Field(None, description="Role creation timestamp")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional role metadata"
    )

    @field_validator("role_name")
    @classmethod
    def validate_role_name(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Role name must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v.lower()

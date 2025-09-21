"""
Schema validation middleware for automatic request/response validation.

This middleware enforces the Pydantic schemas defined in api.schemas for all API endpoints.
"""

import json
from typing import Any, Awaitable, Callable, Dict, Optional, Type

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic schema validation of requests and responses.

    Features:
    - Validates request bodies against Pydantic schemas
    - Validates response bodies against Pydantic schemas
    - Returns RFC 7807 Problem Details for validation errors
    - Integrates with FastAPI's automatic OpenAPI generation
    """

    def __init__(
        self, app: ASGIApp, schema_registry: Optional[Dict[str, Type[BaseModel]]] = None
    ):
        super().__init__(app)
        self.schema_registry = schema_registry or {}

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request through validation pipeline"""

        # Validate request if applicable
        try:
            await self._validate_request(request)
        except ValidationError as e:
            return await self._create_validation_error_response(request, e, "request")
        except Exception as e:
            return await self._create_server_error_response(request, e)

        # Process request
        response = await call_next(request)

        # Validate response if applicable
        try:
            response = await self._validate_response(request, response)
        except ValidationError as e:
            return await self._create_validation_error_response(request, e, "response")
        except Exception as e:
            return await self._create_server_error_response(request, e)

        return response

    async def _validate_request(self, request: Request) -> None:
        """Validate request body against appropriate schema"""

        # Skip validation for GET requests and other methods without body
        if request.method in ("GET", "HEAD", "DELETE"):
            return

        # Get request schema based on endpoint
        schema_class = self._get_request_schema(request)
        if not schema_class:
            return

        # Read and validate request body
        body = await request.body()
        if not body:
            return

        try:
            body_data = json.loads(body)
            validated_data = schema_class(**body_data)

            # Store validated data for use in endpoint handlers
            request.state.validated_body = validated_data

        except json.JSONDecodeError:
            # Create a simple validation error for JSON decode issues
            raise ValidationError.from_exception_data(
                title="Invalid JSON", line_errors=[]
            )

    async def _validate_response(
        self, request: Request, response: Response
    ) -> Response:
        """Validate response body against appropriate schema"""

        # Only validate JSON responses
        if not self._is_json_response(response):
            return response

        # Get response schema based on endpoint and status code
        schema_class = self._get_response_schema(request, response.status_code)
        if not schema_class:
            return response

        # Read response body - handle different response types
        if hasattr(response, "body"):
            body = response.body
        else:
            # For streaming responses, we'll skip validation for now
            return response

        if not body:
            return response

        try:
            if isinstance(body, bytes):
                body_data = json.loads(body.decode("utf-8"))
            else:
                body_data = json.loads(body)

            validated_data = schema_class(**body_data)

            # Create new response with validated data
            validated_json = validated_data.model_dump(by_alias=True, exclude_none=True)
            return JSONResponse(
                content=validated_json,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

        except (json.JSONDecodeError, UnicodeDecodeError):
            # Return original response if JSON parsing fails
            return response

    def _get_request_schema(self, request: Request) -> Optional[Type[BaseModel]]:
        """Get appropriate request schema for endpoint"""

        # Map endpoint patterns to schema classes (updated for architecture diagram)
        endpoint_schemas = {
            # Memory management endpoints (Agents Plane)
            ("POST", "/v1/tools/memory/submit"): "SubmitRequest",
            ("POST", "/v1/tools/memory/recall"): "RecallRequest",
            ("POST", "/v1/tools/memory/project"): "ProjectRequest",
            (
                "POST",
                "/v1/tools/memory/refer",
            ): "ProjectRequest",  # Reuse ProjectRequest
            ("POST", "/v1/tools/memory/undo"): "ProjectRequest",  # Reuse ProjectRequest
            # App Plane endpoints
            ("POST", "/v1/events/ack"): "EventAckRequest",  # TODO: Define this schema
            # Control Plane endpoints
            (
                "POST",
                "/v1/tools/memory/detach",
            ): "ProjectRequest",  # Reuse ProjectRequest
            (
                "POST",
                "/v1/privacy/dsar/requests",
            ): "DsarRequest",  # TODO: Define this schema
            (
                "POST",
                "/v1/privacy/dsar/requests/{job_id}/cancel",
            ): "CancelRequest",  # TODO: Define
            (
                "POST",
                "/v1/security/mls/groups/{group_id}/join",
            ): "MlsJoinRequest",  # TODO: Define
            ("POST", "/v1/security/keys/rotate"): "KeyRotateRequest",  # TODO: Define
            (
                "POST",
                "/v1/security/ratchet/advance",
            ): "RatchetAdvanceRequest",  # TODO: Define
            ("POST", "/v1/admin/index/rebuild"): "IndexRebuildRequest",  # TODO: Define
            (
                "POST",
                "/v1/admin/index/rebuild/{job_id}/cancel",
            ): "CancelRequest",  # TODO: Define
            ("POST", "/v1/rbac/bindings"): "RoleBindingRequest",  # TODO: Define
            ("POST", "/v1/sync/peers"): "SyncRequest",
            (
                "POST",
                "/v1/connectors/{id}/authorize",
            ): "AuthorizeRequest",  # TODO: Define
            (
                "POST",
                "/v1/things/{thing_id}/commands",
            ): "ThingCommandRequest",  # TODO: Define
            (
                "POST",
                "/v1/integrations/webhooks/{connector_id}",
            ): "WebhookRequest",  # TODO: Define
        }

        key = (request.method, request.url.path)
        schema_name = endpoint_schemas.get(key)

        if schema_name and schema_name in self.schema_registry:
            return self.schema_registry[schema_name]

        return None

    def _get_response_schema(
        self, request: Request, status_code: int
    ) -> Optional[Type[BaseModel]]:
        """Get appropriate response schema for endpoint and status code"""

        # Map endpoint patterns and status codes to response schemas (updated for architecture)
        response_schemas = {
            # Memory management responses (Agents Plane)
            ("POST", "/v1/tools/memory/submit", 200): "SubmitResponse",
            ("POST", "/v1/tools/memory/recall", 200): "RecallResponse",
            ("POST", "/v1/tools/memory/project", 200): "ProjectResponse",
            ("POST", "/v1/tools/memory/refer", 200): "ProjectResponse",
            ("POST", "/v1/tools/memory/undo", 200): "ProjectResponse",
            # App Plane responses
            (
                "GET",
                "/v1/receipts/{envelope_id}",
                200,
            ): "ReceiptResponse",  # TODO: Define
            ("GET", "/v1/events/stream", 200): "EventStreamResponse",  # TODO: Define
            ("POST", "/v1/events/ack", 200): "EventAckResponse",  # TODO: Define
            ("GET", "/v1/flags", 200): "FlagsResponse",  # TODO: Define
            ("GET", "/v1/things", 200): "ThingsListResponse",  # TODO: Define
            ("GET", "/v1/things/{thing_id}", 200): "ThingResponse",  # TODO: Define
            # Control Plane responses
            ("POST", "/v1/tools/memory/detach", 200): "ProjectResponse",
            (
                "POST",
                "/v1/privacy/dsar/requests",
                202,
            ): "JobAcceptedResponse",  # TODO: Define
            (
                "GET",
                "/v1/privacy/dsar/requests/{job_id}",
                200,
            ): "JobStatusResponse",  # TODO: Define
            (
                "POST",
                "/v1/security/mls/groups/{group_id}/join",
                200,
            ): "MlsJoinResponse",  # TODO: Define
            (
                "POST",
                "/v1/security/keys/rotate",
                200,
            ): "KeyRotateResponse",  # TODO: Define
            (
                "POST",
                "/v1/security/ratchet/advance",
                200,
            ): "RatchetResponse",  # TODO: Define
            ("POST", "/v1/admin/index/rebuild", 202): "JobAcceptedResponse",
            ("GET", "/v1/admin/index/rebuild/{job_id}", 200): "JobStatusResponse",
            ("GET", "/v1/registry/tools", 200): "ToolsListResponse",  # TODO: Define
            ("GET", "/v1/registry/prompts", 200): "PromptsListResponse",  # TODO: Define
            ("GET", "/v1/rbac/roles", 200): "RolesListResponse",  # TODO: Define
            ("POST", "/v1/rbac/bindings", 200): "RoleBindingResponse",  # TODO: Define
            ("POST", "/v1/sync/peers", 200): "SyncResponse",
            ("GET", "/v1/sync/status", 200): "SyncStatusResponse",  # TODO: Define
            ("GET", "/v1/connectors", 200): "ConnectorsListResponse",  # TODO: Define
            (
                "POST",
                "/v1/connectors/{id}/authorize",
                200,
            ): "AuthorizeResponse",  # TODO: Define
            (
                "POST",
                "/v1/things/{thing_id}/commands",
                200,
            ): "ThingCommandResponse",  # TODO: Define
            (
                "POST",
                "/v1/integrations/webhooks/{connector_id}",
                200,
            ): "WebhookResponse",  # TODO: Define
        }

        # Try exact match first
        key = (request.method, request.url.path, status_code)
        schema_name = response_schemas.get(key)

        # Try wildcard match for dynamic paths
        if not schema_name:
            for (method, pattern, code), name in response_schemas.items():
                if (
                    method == request.method
                    and code == status_code
                    and pattern.endswith("*")
                    and request.url.path.startswith(pattern[:-1])
                ):
                    schema_name = name
                    break

        # Default error responses
        if not schema_name and 400 <= status_code < 600:
            schema_name = "Problem"

        if schema_name and schema_name in self.schema_registry:
            return self.schema_registry[schema_name]

        return None

    def _is_json_response(self, response: Response) -> bool:
        """Check if response is JSON content type"""
        content_type = response.headers.get("content-type", "")
        return (
            "application/json" in content_type
            or "application/problem+json" in content_type
        )

    async def _create_validation_error_response(
        self, request: Request, error: ValidationError, error_type: str
    ) -> JSONResponse:
        """Create RFC 7807 Problem Details response for validation errors"""

        # Extract trace ID from request headers
        trace_id = request.headers.get("x-trace-id")

        # Create basic problem details dict
        problem_dict: Dict[str, Any] = {
            "type": "https://memoryos.dev/problems/validation-error",
            "title": f"Schema Validation Error ({error_type})",
            "status": 400,
            "detail": f"The {error_type} does not conform to the expected schema",
            "instance": str(request.url),
        }

        if trace_id:
            problem_dict["traceId"] = trace_id

        # Add validation error details
        problem_dict["errors"] = error.errors()

        return JSONResponse(
            content=problem_dict,
            status_code=400,
            headers={"content-type": "application/problem+json"},
        )

    async def _create_server_error_response(
        self, request: Request, error: Exception
    ) -> JSONResponse:
        """Create RFC 7807 Problem Details response for server errors"""

        # Extract trace ID from request headers
        trace_id = request.headers.get("x-trace-id")

        # Create basic problem details dict
        problem_dict: Dict[str, Any] = {
            "type": "https://memoryos.dev/problems/server-error",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred during request processing",
            "instance": str(request.url),
        }

        if trace_id:
            problem_dict["traceId"] = trace_id

        return JSONResponse(
            content=problem_dict,
            status_code=500,
            headers={"content-type": "application/problem+json"},
        )


def create_validation_middleware(
    app: ASGIApp, schema_registry: Optional[Dict[str, Type[BaseModel]]] = None
) -> ValidationMiddleware:
    """
    Factory function to create validation middleware with schema registry.

    Args:
        app: ASGI application instance
        schema_registry: Dictionary mapping schema names to Pydantic model classes

    Returns:
        Configured ValidationMiddleware instance
    """

    if schema_registry is None:
        # Import all schemas from the new modular schemas package
        from ..schemas import (  # Request schemas; Response schemas; Security schemas; Event schemas; Core schemas
            AccessToken,
            ActionCapability,
            ActivityLog,
            AuthenticationChallenge,
            BatchResponse,
            Envelope,
            ErrorResponse,
            HealthResponse,
            MemoryEvent,
            MemoryItem,
            MemoryRecalledEvent,
            MemorySpace,
            MemorySubmittedEvent,
            PermissionScope,
            PolicyDecisionResponse,
            PolicyEvent,
            Problem,
            ProjectRequest,
            ProjectResponse,
            RecallRequest,
            RecallResponse,
            RegisterRequest,
            RegisterResponse,
            RoleDefinition,
            SecurityAuditLog,
            SecurityContext,
            SecurityEvent,
            SpacePolicy,
            SubmitRequest,
            SubmitResponse,
            SyncEvent,
            SyncRequest,
            SyncResponse,
            UnregisterRequest,
            UnregisterResponse,
            UserProfile,
        )

        schema_registry = {
            # Request schemas
            "SubmitRequest": SubmitRequest,
            "RecallRequest": RecallRequest,
            "ProjectRequest": ProjectRequest,
            "RegisterRequest": RegisterRequest,
            "UnregisterRequest": UnregisterRequest,
            "SyncRequest": SyncRequest,
            # Response schemas
            "SubmitResponse": SubmitResponse,
            "RecallResponse": RecallResponse,
            "ProjectResponse": ProjectResponse,
            "RegisterResponse": RegisterResponse,
            "UnregisterResponse": UnregisterResponse,
            "SyncResponse": SyncResponse,
            "HealthResponse": HealthResponse,
            "ErrorResponse": ErrorResponse,
            "BatchResponse": BatchResponse,
            # Security schemas
            "PolicyDecisionResponse": PolicyDecisionResponse,
            "Problem": Problem,
            "AuthenticationChallenge": AuthenticationChallenge,
            "AccessToken": AccessToken,
            "SecurityAuditLog": SecurityAuditLog,
            "PermissionScope": PermissionScope,
            "RoleDefinition": RoleDefinition,
            # Event schemas
            "Envelope": Envelope,
            "MemoryEvent": MemoryEvent,
            "MemorySubmittedEvent": MemorySubmittedEvent,
            "MemoryRecalledEvent": MemoryRecalledEvent,
            "PolicyEvent": PolicyEvent,
            "SecurityEvent": SecurityEvent,
            "SyncEvent": SyncEvent,
            # Core schemas
            "SecurityContext": SecurityContext,
            "MemoryItem": MemoryItem,
            "SpacePolicy": SpacePolicy,
            "UserProfile": UserProfile,
            "MemorySpace": MemorySpace,
            "ActivityLog": ActivityLog,
            "ActionCapability": ActionCapability,
        }

    return ValidationMiddleware(app, schema_registry)


# Dependency injection helper for FastAPI
async def get_validated_body(request: Request) -> BaseModel:
    """
    FastAPI dependency to get validated request body.

    Usage:
        @app.post("/v1/tools/memory/submit")
        async def submit_memory(
            body: SubmitRequest = Depends(get_validated_body)
        ):
            # body is already validated SubmitRequest instance
            pass
    """
    if hasattr(request.state, "validated_body"):
        return request.state.validated_body
    else:
        raise HTTPException(
            status_code=422, detail="Request body validation failed or not available"
        )

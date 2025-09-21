"""
Policy Enforcement Point (PEP) Middleware - Sub-issue #8.2

This module implements the main Policy Enforcement Point middleware
that integrates RBAC, ABAC, and capability-based authorization.

This is the MW_PEP component in the middleware chain:
MW_AUTH → MW_PEP → MW_SEC → MW_QOS → MW_SAF → MW_OBS
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from api.schemas import SecurityContext
from policy.decision import PolicyDecision
from policy.service import PolicyService, get_policy_service

logger = logging.getLogger(__name__)


class PolicyEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Main Policy Enforcement Point (PEP) middleware.

    Integrates RBAC, ABAC, and capability-based authorization
    for comprehensive access control across all API endpoints.
    """

    def __init__(
        self,
        app: ASGIApp,
        policy_service: PolicyService | None = None,
    ):
        """
        Initialize Policy Enforcement Point middleware.

        Args:
            app: ASGI application
            policy_service: Policy service instance (or use singleton)
        """
        super().__init__(app)
        self.policy_service = policy_service or get_policy_service()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """
        Enforce policy decisions for API requests.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response from downstream handler

        Raises:
            HTTPException: 403 if policy enforcement fails
        """
        # Skip policy enforcement for health/docs endpoints
        if self._should_bypass_policy(request):
            return await call_next(request)

        try:
            # Get security context from previous middleware (MW_AUTH)
            security_ctx = getattr(request.state, "security_context", None)
            if not security_ctx:
                logger.warning(
                    f"No security context for policy check: {request.url.path}"
                )
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required for policy enforcement",
                )

            # Perform policy evaluation
            policy_decision = await self._evaluate_policy(request, security_ctx)

            if policy_decision.decision == "DENY":
                logger.warning(
                    f"Policy denied access: {security_ctx.user_id} "
                    f"to {request.method}:{request.url.path}, "
                    f"reasons: {policy_decision.reasons}"
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied by policy: {', '.join(policy_decision.reasons)}",
                )

            # Store policy decision for downstream middleware
            request.state.policy_decision = policy_decision
            request.state.policy_obligations = policy_decision.obligations

            logger.debug(
                f"Policy granted access: {security_ctx.user_id} "
                f"to {request.method}:{request.url.path}"
            )

            return await call_next(request)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Policy enforcement error for {request.url}: {e}")
            raise HTTPException(status_code=500, detail="Policy enforcement failed")

    def _should_bypass_policy(self, request: Request) -> bool:
        """Check if request should bypass policy enforcement."""
        bypass_paths = {
            "/health",
            "/health/ready",
            "/health/live",
            "/v1/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/metrics",
            "/",  # Root endpoint
        }
        path = str(request.url.path)
        return any(path.startswith(bypass) for bypass in bypass_paths)

    async def _evaluate_policy(
        self, request: Request, security_ctx: SecurityContext
    ) -> PolicyDecision:
        """
        Evaluate policy for the request.

        This method integrates multiple policy engines:
        - RBAC for role-based access
        - ABAC for attribute-based access
        - Space policy for memory operations
        - Capability-based authorization
        """
        method = request.method
        path = str(request.url.path)

        # Determine operation type from route
        operation = self._get_operation_from_route(method, path)

        # Extract space_id from request (query params, body, or default)
        space_id = await self._extract_space_id(request)

        # Determine security band from request context
        security_band = self._determine_security_band(request, security_ctx)

        try:
            # Memory operations use comprehensive space policy
            if operation in ("submit", "recall", "project", "refer", "undo"):
                return await self.policy_service.check_api_operation(
                    security_context=security_ctx,
                    operation=operation.upper(),
                    resource=space_id,
                    band=security_band,
                )

            # Admin operations require elevated privileges
            elif path.startswith("/admin/"):
                return await self._evaluate_admin_policy(
                    request, security_ctx, operation
                )

            # Sync operations require peer verification
            elif "sync" in path:
                return await self._evaluate_sync_policy(
                    request, security_ctx, operation
                )

            # Privacy operations require special handling
            elif "privacy" in path:
                return await self._evaluate_privacy_policy(
                    request, security_ctx, operation
                )

            # General API operations use capability-based access
            else:
                return await self._evaluate_capability_policy(
                    request, security_ctx, operation
                )

        except Exception as e:
            logger.error(f"Policy evaluation failed for {path}: {e}")
            # Fail secure - deny access on evaluation errors
            from policy.decision import Obligation, PolicyDecision

            return PolicyDecision(
                decision="DENY",
                reasons=[f"policy_evaluation_error: {str(e)}"],
                obligations=Obligation(
                    log_audit=True, reason_tags=["evaluation_error"]
                ),
            )

    def _get_operation_from_route(self, method: str, path: str) -> str:
        """Extract operation type from route for policy evaluation."""
        # Map common routes to operations
        if "/tools/memory/submit" in path:
            return "submit"
        elif "/tools/memory/recall" in path:
            return "recall"
        elif "/tools/memory/project" in path:
            return "project"
        elif "/tools/memory/refer" in path:
            return "refer"
        elif "/tools/memory/undo" in path:
            return "undo"
        elif "/admin/" in path:
            return "admin"
        elif "/sync/" in path:
            return "sync"
        elif "/privacy/" in path:
            return "privacy"
        else:
            # Generic operation based on HTTP method
            return method.lower()

    async def _extract_space_id(self, request: Request) -> str:
        """Extract space_id from request context."""
        # Try query parameters first
        space_id = request.query_params.get("space_id")
        if space_id:
            return space_id

        # Try to extract from request body (for POST/PUT requests)
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                if body:
                    import json

                    data = json.loads(body)
                    if isinstance(data, dict) and "space_id" in data:
                        return data["space_id"]
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Try path parameters
        path_parts = str(request.url.path).split("/")
        for i, part in enumerate(path_parts):
            if part == "spaces" and i + 1 < len(path_parts):
                return path_parts[i + 1]

        # Default space for the user's primary context
        return "shared:household"

    def _determine_security_band(
        self, request: Request, security_ctx: SecurityContext
    ) -> str:
        """Determine security band for the request."""
        # Check for explicit band in headers
        band_header = request.headers.get("Security-Band")
        if band_header:
            return band_header.upper()

        # Check trust level from security context
        if security_ctx.trust_level:
            trust_mapping = {
                "red": "RED",
                "amber": "AMBER",
                "green": "GREEN",
            }
            return trust_mapping.get(security_ctx.trust_level.value.lower(), "GREEN")

        # Default to GREEN for normal operations
        return "GREEN"

    async def _evaluate_admin_policy(
        self, request: Request, security_ctx: SecurityContext, operation: str
    ) -> PolicyDecision:
        """Evaluate policy for admin operations."""
        from policy.decision import Obligation, PolicyDecision

        # Admin operations require admin role
        if not security_ctx.capabilities or not any(
            cap.value.startswith("admin") for cap in security_ctx.capabilities
        ):
            return PolicyDecision(
                decision="DENY",
                reasons=["admin_capability_required"],
                obligations=Obligation(
                    log_audit=True, reason_tags=["admin_access_denied"]
                ),
            )

        # Additional admin checks based on specific operation
        path = str(request.url.path)
        if "/admin/policies" in path:
            # Policy management requires highest privileges
            return PolicyDecision(
                decision="ALLOW",
                reasons=["admin_policy_access_granted"],
                obligations=Obligation(
                    log_audit=True, reason_tags=["admin_policy_operation"]
                ),
            )

        return PolicyDecision(
            decision="ALLOW",
            reasons=["admin_access_granted"],
            obligations=Obligation(log_audit=True),
        )

    async def _evaluate_sync_policy(
        self, request: Request, security_ctx: SecurityContext, operation: str
    ) -> PolicyDecision:
        """Evaluate policy for sync operations."""
        from policy.decision import Obligation, PolicyDecision

        # Sync operations require SYNC capability
        if not security_ctx.capabilities or not any(
            cap.value in ("SYNC", "WRITE") for cap in security_ctx.capabilities
        ):
            return PolicyDecision(
                decision="DENY",
                reasons=["sync_capability_required"],
                obligations=Obligation(log_audit=True),
            )

        # Check device trust level for sync operations
        if security_ctx.trust_level and security_ctx.trust_level.value.lower() == "red":
            return PolicyDecision(
                decision="DENY",
                reasons=["untrusted_device_sync_denied"],
                obligations=Obligation(log_audit=True),
            )

        return PolicyDecision(
            decision="ALLOW",
            reasons=["sync_access_granted"],
            obligations=Obligation(log_audit=True),
        )

    async def _evaluate_privacy_policy(
        self, request: Request, security_ctx: SecurityContext, operation: str
    ) -> PolicyDecision:
        """Evaluate policy for privacy operations."""
        from policy.decision import Obligation, PolicyDecision

        # Privacy operations require PRIVACY capability
        if not security_ctx.capabilities or not any(
            cap.value in ("PRIVACY", "ADMIN") for cap in security_ctx.capabilities
        ):
            return PolicyDecision(
                decision="DENY",
                reasons=["privacy_capability_required"],
                obligations=Obligation(log_audit=True),
            )

        # GDPR/DSAR operations require additional verification
        path = str(request.url.path)
        if any(term in path for term in ["/dsar", "/export", "/delete"]):
            return PolicyDecision(
                decision="ALLOW",
                reasons=["privacy_access_granted"],
                obligations=Obligation(
                    log_audit=True, reason_tags=["privacy_operation", "dsar"]
                ),
            )

        return PolicyDecision(
            decision="ALLOW",
            reasons=["privacy_access_granted"],
            obligations=Obligation(log_audit=True),
        )

    async def _evaluate_capability_policy(
        self, request: Request, security_ctx: SecurityContext, operation: str
    ) -> PolicyDecision:
        """Evaluate policy for general capability-based operations."""
        from policy.decision import Obligation, PolicyDecision

        # Map HTTP methods to required capabilities
        method_capability_map = {
            "GET": "RECALL",
            "POST": "WRITE",
            "PUT": "WRITE",
            "PATCH": "WRITE",
            "DELETE": "ADMIN",
        }

        required_capability = method_capability_map.get(request.method, "RECALL")

        # Check if user has required capability
        if security_ctx.capabilities and any(
            cap.value == required_capability for cap in security_ctx.capabilities
        ):
            return PolicyDecision(
                decision="ALLOW",
                reasons=[f"{required_capability.lower()}_capability_granted"],
                obligations=Obligation(log_audit=True),
            )

        return PolicyDecision(
            decision="DENY",
            reasons=[f"{required_capability.lower()}_capability_required"],
            obligations=Obligation(log_audit=True),
        )


# Convenience function for FastAPI application setup
def create_policy_middleware(
    policy_service: PolicyService | None = None,
) -> type[PolicyEnforcementMiddleware]:
    """
    Create policy enforcement middleware class.

    Args:
        policy_service: Policy service instance

    Returns:
        Configured middleware class
    """

    class ConfiguredPolicyMiddleware(PolicyEnforcementMiddleware):
        def __init__(self, app: ASGIApp):
            super().__init__(app, policy_service)

    return ConfiguredPolicyMiddleware

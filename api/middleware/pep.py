"""
MW_PEP - Policy Enforcement Point Implementation - Issue #20.1

This module implements the complete Policy Enforcement Point (PEP) middleware
that serves as the central authorization component in the middleware chain.

Middleware Chain Position: MW_AUTH → MW_PEP → MW_SEC → MW_QOS → MW_SAF → MW_OBS

Features:
- RBAC (Role-Based Access Control)
- ABAC (Attribute-Based Access Control)
- Capability-based authorization
- Cross-space access control
- Performance optimization with caching
- Comprehensive audit logging
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from api.schemas import SecurityContext
from policy.decision import PolicyDecision
from policy.service import PolicyService, get_policy_service

logger = logging.getLogger(__name__)


class PolicyEnforcementPoint(BaseHTTPMiddleware):
    """
    Complete Policy Enforcement Point (PEP) middleware implementation.

    This is the MW_PEP component that provides comprehensive authorization
    for all API requests using RBAC, ABAC, and capability-based controls.
    """

    def __init__(
        self,
        app: ASGIApp,
        policy_service: Optional[PolicyService] = None,
        cache_ttl: int = 300,  # 5 minutes default cache
        enable_performance_logging: bool = True,
    ):
        """
        Initialize Policy Enforcement Point.

        Args:
            app: ASGI application
            policy_service: Policy service instance (uses singleton if None)
            cache_ttl: Policy decision cache TTL in seconds
            enable_performance_logging: Enable detailed performance metrics
        """
        super().__init__(app)
        self.policy_service = policy_service or get_policy_service()
        self.cache_ttl = cache_ttl
        self.enable_performance_logging = enable_performance_logging
        self._decision_cache: dict[str, tuple[PolicyDecision, float]] = {}

        logger.info("MW_PEP initialized with caching enabled (TTL: %ds)", cache_ttl)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Main PEP dispatch logic with comprehensive authorization.

        Flow:
        1. Extract SecurityContext from request
        2. Determine required operation and resource
        3. Check policy decision (with caching)
        4. Log authorization result
        5. Proceed or deny request

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response

        Raises:
            HTTPException: On authorization failure
        """
        start_time = time.time() if self.enable_performance_logging else 0

        try:
            # Step 1: Extract SecurityContext
            security_context = self._extract_security_context(request)
            if not security_context:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing or invalid security context",
                )

            # Step 2: Determine operation and resource
            operation = self._determine_operation(request)
            resource = self._extract_resource(request)

            # Step 3: Check authorization with caching
            decision = await self._check_authorization(
                security_context, operation, resource, request
            )

            if decision.decision != "ALLOW":
                self._log_authorization_failure(
                    security_context, operation, resource, decision
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: {'; '.join(decision.reasons)}",
                )

            # Step 4: Log successful authorization
            self._log_authorization_success(
                security_context, operation, resource, decision
            )

            # Step 5: Add decision context to request for downstream middleware
            request.state.policy_decision = decision
            request.state.security_context = security_context

            # Continue to next middleware
            response = await call_next(request)

            # Log performance metrics
            if self.enable_performance_logging:
                duration = time.time() - start_time
                logger.debug("MW_PEP processed request in %.3fms", duration * 1000)

            return response

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error("MW_PEP unexpected error: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal authorization error",
            )

    def _extract_security_context(self, request: Request) -> Optional[SecurityContext]:
        """
        Extract SecurityContext from request state.

        SecurityContext should be set by MW_AUTH middleware.

        Args:
            request: HTTP request

        Returns:
            SecurityContext if available, None otherwise
        """
        return getattr(request.state, "security_context", None)

    def _determine_operation(self, request: Request) -> str:
        """
        Determine the operation type from HTTP method and path.

        Maps HTTP operations to policy operations:
        - GET /v1/memories/* → memory.read
        - POST /v1/tools/memory/submit → memory.write
        - POST /v1/tools/memory/recall → memory.recall
        - GET /v1/admin/* → admin.read
        - POST /v1/admin/* → admin.write

        Args:
            request: HTTP request

        Returns:
            Operation string for policy evaluation
        """
        method = request.method.upper()
        path = request.url.path

        # Admin operations
        if path.startswith("/v1/admin/"):
            return f"admin.{method.lower()}"

        # Memory operations
        if path.startswith("/v1/tools/memory/"):
            if "submit" in path:
                return "memory.write"
            elif "recall" in path:
                return "memory.recall"
            elif "project" in path:
                return "memory.project"
            elif "refer" in path:
                return "memory.refer"

        if path.startswith("/v1/memories/"):
            return "memory.read"

        # Sync operations
        if path.startswith("/v1/sync/"):
            return f"sync.{method.lower()}"

        # Events operations (SSE)
        if path.startswith("/v1/events/"):
            return "events.stream"

        # Privacy operations
        if path.startswith("/v1/privacy/"):
            return f"privacy.{method.lower()}"

        # Default operation based on method
        return f"api.{method.lower()}"

    def _extract_resource(self, request: Request) -> Optional[str]:
        """
        Extract resource identifier from request path and query parameters.

        For space-scoped operations, extract the space/namespace.
        For user-scoped operations, extract user identifiers.

        Args:
            request: HTTP request

        Returns:
            Resource identifier for policy evaluation
        """
        path = request.url.path
        query_params = request.query_params

        # Extract space from query parameters
        if "space" in query_params:
            return query_params["space"]

        # Extract space from path segments
        path_segments = path.strip("/").split("/")

        # Look for space indicators in path
        for i, segment in enumerate(path_segments):
            if segment in ["space", "namespace", "group"]:
                if i + 1 < len(path_segments):
                    return path_segments[i + 1]

        # For admin operations, resource is the admin domain
        if path.startswith("/v1/admin/"):
            return path.split("/")[-1] if len(path.split("/")) > 3 else "system"

        # Default to the API path as resource
        return path

    async def _check_authorization(
        self,
        context: SecurityContext,
        operation: str,
        resource: Optional[str],
        request: Request,
    ) -> PolicyDecision:
        """
        Check authorization with caching and comprehensive policy evaluation.

        Uses caching to optimize repeated authorization checks.

        Args:
            context: Security context
            operation: Operation to authorize
            resource: Resource being accessed
            request: HTTP request for additional context

        Returns:
            Policy decision result
        """
        # Create cache key
        cache_key = self._create_cache_key(context, operation, resource)

        # Check cache first
        cached_decision = self._get_cached_decision(cache_key)
        if cached_decision:
            logger.debug("MW_PEP cache hit for operation: %s", operation)
            return cached_decision

        # Evaluate policy
        try:
            decision = await self.policy_service.check_api_operation(
                security_context=context,
                operation=operation,
                resource=resource or request.url.path,
                band="GREEN",  # Default band, could be determined from request
                tags=None,
            )

            # Cache the decision
            self._cache_decision(cache_key, decision)

            return decision

        except Exception as e:
            logger.error("Policy evaluation failed: %s", e, exc_info=True)
            # Fail secure - deny by default
            from policy.decision import Obligation

            return PolicyDecision(
                decision="DENY",
                reasons=[f"Policy evaluation error: {str(e)}"],
                obligations=Obligation(),
            )

    def _create_cache_key(
        self, context: SecurityContext, operation: str, resource: Optional[str]
    ) -> str:
        """
        Create cache key for policy decision.

        Args:
            context: Security context
            operation: Operation
            resource: Resource

        Returns:
            Cache key string
        """
        context_key = f"{context.user_id}:{context.mls_group}:{context.trust_level}"
        caps_key = ":".join(sorted(cap.value for cap in context.capabilities or []))
        return f"{context_key}:{operation}:{resource or 'none'}:{caps_key}"

    def _get_cached_decision(self, cache_key: str) -> Optional[PolicyDecision]:
        """
        Get cached policy decision if still valid.

        Args:
            cache_key: Cache key

        Returns:
            Cached decision if valid, None otherwise
        """
        if cache_key in self._decision_cache:
            decision, timestamp = self._decision_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return decision
            else:
                # Remove expired entry
                del self._decision_cache[cache_key]
        return None

    def _cache_decision(self, cache_key: str, decision: PolicyDecision) -> None:
        """
        Cache policy decision with timestamp.

        Args:
            cache_key: Cache key
            decision: Policy decision to cache
        """
        self._decision_cache[cache_key] = (decision, time.time())

        # Simple cache cleanup - remove oldest entries if cache gets too large
        if len(self._decision_cache) > 1000:
            # Remove oldest 200 entries
            sorted_items = sorted(
                self._decision_cache.items(), key=lambda x: x[1][1]  # Sort by timestamp
            )
            for key, _ in sorted_items[:200]:
                del self._decision_cache[key]

    def _log_authorization_success(
        self,
        context: SecurityContext,
        operation: str,
        resource: Optional[str],
        decision: PolicyDecision,
    ) -> None:
        """
        Log successful authorization for audit trail.

        Args:
            context: Security context
            operation: Operation authorized
            resource: Resource accessed
            decision: Policy decision
        """
        logger.info(
            "MW_PEP ALLOW: user=%s operation=%s resource=%s reason=%s",
            context.user_id,
            operation,
            resource or "none",
            "; ".join(decision.reasons) if decision.reasons else "policy_allowed",
        )

    def _log_authorization_failure(
        self,
        context: SecurityContext,
        operation: str,
        resource: Optional[str],
        decision: PolicyDecision,
    ) -> None:
        """
        Log authorization failure for security monitoring.

        Args:
            context: Security context
            operation: Operation denied
            resource: Resource access attempted
            decision: Policy decision
        """
        logger.warning(
            "MW_PEP DENY: user=%s operation=%s resource=%s reason=%s",
            context.user_id,
            operation,
            resource or "none",
            "; ".join(decision.reasons) if decision.reasons else "policy_denied",
        )

    async def clear_cache(self) -> None:
        """Clear the policy decision cache."""
        self._decision_cache.clear()
        logger.info("MW_PEP cache cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "cache_size": len(self._decision_cache),
            "cache_ttl": self.cache_ttl,
            "performance_logging": self.enable_performance_logging,
        }


# Backward compatibility alias
PolicyEnforcementMiddleware = PolicyEnforcementPoint

__all__ = [
    "PolicyEnforcementPoint",
    "PolicyEnforcementMiddleware",  # Backward compatibility
]

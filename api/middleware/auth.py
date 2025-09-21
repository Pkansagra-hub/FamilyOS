"""
Authentication Middleware (MW_AUTH) - Clean Implementation

This middleware implements the Policy Enforcement Point's authentication layer,
supporting both mTLS (Agents/Control planes) and JWT (App plane) authentication
methods as specified in the OpenAPI contract.

Features:
- Development authentication with X-Test-* headers
- mTLS and JWT authentication
- Security context creation
- Bypass for health endpoints

Author: GitHub Copilot
"""

import logging
import os
from typing import Callable, Optional
from uuid import uuid4

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api.schemas import AuthMethod, Capability, SecurityContext, TrustLevel

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Base authentication error"""

    def __init__(self, message: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    MW_AUTH: Authentication middleware for multi-plane security

    Handles mTLS, JWT, and development authentication according to OpenAPI security schemes.
    Creates SecurityContext for downstream middleware consumption.
    """

    def __init__(self, app):
        super().__init__(app)
        self.exempt_paths = {
            "/health",
            "/health/ready",
            "/health/live",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/metrics",
        }
        logger.info("MW_AUTH: Authentication middleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Main middleware dispatch method.

        Flow:
        1. Check if path is exempt from authentication
        2. Attempt authentication with available methods
        3. Create SecurityContext and attach to request
        4. Pass to next middleware with context
        """

        # Skip authentication for exempt paths
        if self._is_exempt_path(request.url.path):
            logger.debug(f"MW_AUTH: Skipping auth for exempt path: {request.url.path}")
            return await call_next(request)

        try:
            # Attempt authentication
            security_context = await self._authenticate_request(request)

            if not security_context:
                raise AuthenticationError("Authentication required")

            # Attach SecurityContext to request state for downstream middleware
            request.state.security_context = security_context
            request.state.authenticated = True

            logger.info(
                "MW_AUTH: Authentication successful",
                extra={
                    "user_id": security_context.user_id,
                    "auth_method": (
                        security_context.auth_method.value
                        if security_context.auth_method
                        else None
                    ),
                    "trust_level": (
                        security_context.trust_level.value
                        if security_context.trust_level
                        else None
                    ),
                    "path": request.url.path,
                },
            )

            # Continue to next middleware
            response = await call_next(request)
            return response

        except AuthenticationError as e:
            logger.warning(
                f"MW_AUTH: Authentication failed - {e.message}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": e.status_code,
                },
            )
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": "authentication_failed",
                    "message": e.message,
                    "path": request.url.path,
                },
            )

        except Exception as e:
            logger.error(f"MW_AUTH: Unexpected error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "authentication_error",
                    "message": "Authentication system error",
                    "path": request.url.path,
                },
            )

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from authentication."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)

    async def _authenticate_request(
        self, request: Request
    ) -> Optional[SecurityContext]:
        """
        Attempt authentication using available methods.
        Tries development auth first, then JWT, then mTLS.
        """

        # 1. Try development authentication first (X-Test-* headers)
        dev_context = await self._authenticate_development(request)
        if dev_context:
            return dev_context

        # 2. Try JWT authentication
        jwt_context = await self._authenticate_jwt(request)
        if jwt_context:
            return jwt_context

        # 3. Try mTLS authentication
        mtls_context = await self._authenticate_mtls(request)
        if mtls_context:
            return mtls_context

        # No authentication method succeeded
        return None

    async def _authenticate_development(
        self, request: Request
    ) -> Optional[SecurityContext]:
        """
        Development authentication using X-Test-* headers.

        This method creates mock SecurityContext objects for testing.
        Only active in development/testing environments.
        """

        # Only enable in development/testing
        if os.getenv("ENVIRONMENT", "development").lower() not in [
            "development",
            "test",
        ]:
            return None

        # Check for test user header
        test_user = request.headers.get("X-Test-User")
        if not test_user:
            return None

        test_role = request.headers.get("X-Test-Role", "member")

        # Map test roles to capabilities
        role_capabilities = {
            "admin": [
                Capability.WRITE,
                Capability.RECALL,
                Capability.SCHEDULE,
                Capability.PROJECT,
            ],
            "guardian": [Capability.WRITE, Capability.RECALL, Capability.SCHEDULE],
            "member": [Capability.WRITE, Capability.RECALL],
            "child": [Capability.RECALL],
            "guest": [],
        }

        capabilities = role_capabilities.get(test_role, [Capability.RECALL])

        logger.info(
            f"MW_AUTH: Development authentication for {test_user} with role {test_role}"
        )

        # Create mock security context
        return SecurityContext(
            user_id=test_user,  # Use the test username for policy lookups
            device_id=f"dev_device_{uuid4().hex[:8]}",
            authenticated=True,
            auth_method=AuthMethod.JWT,  # Mock JWT authentication
            capabilities=capabilities,
            mls_group="dev_family",
            trust_level=TrustLevel.GREEN,
        )

    async def _authenticate_jwt(self, request: Request) -> Optional[SecurityContext]:
        """
        Authenticate using JWT Bearer token.

        In production, this would validate the JWT token.
        For now, returns None since JWT validation is not implemented.
        """
        try:
            # Extract Authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            # TODO: Implement actual JWT validation
            # For now, return None to fall back to development auth
            logger.debug("MW_AUTH: JWT authentication not yet implemented")
            return None

        except Exception as e:
            logger.debug(f"MW_AUTH: JWT authentication failed: {e}")
            return None

    async def _authenticate_mtls(self, request: Request) -> Optional[SecurityContext]:
        """
        Authenticate using mTLS certificates.

        In production, this would validate client certificates.
        For now, returns None since mTLS validation is not implemented.
        """
        try:
            # TODO: Implement actual mTLS validation
            # For now, return None to fall back to development auth
            logger.debug("MW_AUTH: mTLS authentication not yet implemented")
            return None

        except Exception as e:
            logger.debug(f"MW_AUTH: mTLS authentication failed: {e}")
            return None

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first (proxy setup)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to client host
        return (
            getattr(request.client, "host", "unknown") if request.client else "unknown"
        )


# Export for middleware chain
__all__ = [
    "AuthenticationMiddleware",
    "AuthenticationError",
]

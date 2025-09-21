"""
Middleware Integration Module - Sub-issue #8.2

This module provides the complete middleware chain integration
for the MemoryOS API, following the architecture:

MW_AUTH → MW_PEP → MW_SEC → MW_QOS → MW_SAF → MW_OBS

This implements the middleware chain pattern from the architecture
documentation where each middleware adds specific functionality
and passes control to the next middleware in the chain.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from policy.service import PolicyService

logger = logging.getLogger(__name__)


def setup_middleware_chain(
    app: FastAPI,
    policy_service: PolicyService | None = None,
) -> None:
    """
    Set up the complete middleware chain for MemoryOS API.

    This function adds middleware in the correct order according to
    the architecture specification. Middleware is applied in reverse
    order (last added = first executed).

    Args:
        app: FastAPI application instance
        policy_service: Policy service instance (optional)
    """

    # Import middleware classes (lazy import to avoid circular dependencies)
    from api.middleware.policy import PolicyEnforcementMiddleware

    # Import optional middleware with graceful fallbacks
    try:
        from api.middleware.auth import AuthenticationMiddleware

        auth_available = True
    except ImportError:
        logger.warning("⚠️  AuthenticationMiddleware not available")
        auth_available = False

    try:
        from api.middleware.observability import ObservabilityMiddleware

        observability_available = True
    except ImportError:
        logger.warning("⚠️  ObservabilityMiddleware not available")
        observability_available = False

    try:
        from api.middleware.memory_observability import MemoryObservabilityMiddleware

        memory_observability_available = True
    except ImportError:
        logger.warning("⚠️  MemoryObservabilityMiddleware not available")
        memory_observability_available = False

    try:
        from api.middleware.qos import QualityOfServiceMiddleware

        qos_available = True
    except ImportError:
        logger.warning("⚠️  QualityOfServiceMiddleware not available")
        qos_available = False

    try:
        from api.middleware.safety import SafetyFiltersMiddleware

        safety_available = True
    except ImportError:
        logger.warning("⚠️  SafetyFiltersMiddleware not available")
        safety_available = False

    try:
        from api.middleware.security import SecurityControlsMiddleware

        security_available = True
    except ImportError:
        logger.warning("⚠️  SecurityControlsMiddleware not available")
        security_available = False

    # Add middleware in reverse order (last added = first executed)

    # MW_OBS - Observability (metrics, tracing, logging)
    if observability_available:
        app.add_middleware(ObservabilityMiddleware)
        logger.info("✅ Added ObservabilityMiddleware (MW_OBS)")

    # MW_MEM_OBS - Memory Flow Observability (6-layer memory tracking)
    if memory_observability_available:
        app.add_middleware(MemoryObservabilityMiddleware)
        logger.info("✅ Added MemoryObservabilityMiddleware (MW_MEM_OBS)")

    # MW_SAF - Safety Filters (content safety, abuse prevention)
    if safety_available:
        app.add_middleware(SafetyFiltersMiddleware)
        logger.info("✅ Added SafetyFiltersMiddleware (MW_SAF)")

    # MW_QOS - Quality of Service (rate limiting, resource management)
    if qos_available:
        app.add_middleware(QualityOfServiceMiddleware)
        logger.info("✅ Added QualityOfServiceMiddleware (MW_QOS)")

    # MW_SEC - Security Controls (encryption, MLS, hardware validation)
    if security_available:
        app.add_middleware(SecurityControlsMiddleware)
        logger.info("✅ Added SecurityControlsMiddleware (MW_SEC)")

    # MW_PEP - Policy Enforcement Point (RBAC, ABAC, capabilities) - REQUIRED
    if policy_service:
        app.add_middleware(PolicyEnforcementMiddleware, policy_service=policy_service)
    else:
        app.add_middleware(PolicyEnforcementMiddleware)
    logger.info("✅ Added PolicyEnforcementMiddleware (MW_PEP)")

    # MW_AUTH - Authentication (JWT, mTLS, session management)
    if auth_available:
        app.add_middleware(AuthenticationMiddleware)
        logger.info("✅ Added AuthenticationMiddleware (MW_AUTH)")

    logger.info("🔗 Middleware chain setup complete")


def validate_middleware_chain(app: FastAPI) -> bool:
    """
    Validate that all required middleware is properly configured.

    Args:
        app: FastAPI application instance

    Returns:
        True if middleware chain is valid

    Raises:
        RuntimeError: If middleware chain is invalid
    """
    required_middleware = [
        "PolicyEnforcementMiddleware",  # Critical for Sub-issue #8.2
    ]

    # Get middleware classes from the app
    middleware_classes = [
        middleware.cls.__name__
        for middleware in app.user_middleware
        if hasattr(middleware.cls, "__name__")
    ]

    missing_required = []
    for required in required_middleware:
        if required not in middleware_classes:
            missing_required.append(required)

    if missing_required:
        raise RuntimeError(
            f"Missing required middleware: {', '.join(missing_required)}"
        )

    logger.info(
        f"✅ Middleware chain validation passed: {len(middleware_classes)} middleware active"
    )
    return True


class MiddlewareChainHealth:
    """Health check utilities for the middleware chain."""

    @staticmethod
    def get_middleware_status(app: FastAPI) -> dict[str, bool]:
        """Get status of all middleware in the chain."""
        status = {}

        for middleware in app.user_middleware:
            middleware_name = middleware.cls.__name__
            # Basic health check - middleware is loaded
            status[middleware_name] = True

        return status

    @staticmethod
    def get_chain_metrics(app: FastAPI) -> dict[str, any]:
        """Get performance metrics for the middleware chain."""
        return {
            "total_middleware": len(app.user_middleware),
            "middleware_list": [
                middleware.cls.__name__ for middleware in app.user_middleware
            ],
        }


# Convenience functions for specific middleware operations


def get_policy_middleware(app: FastAPI) -> BaseHTTPMiddleware | None:
    """Get the PolicyEnforcementMiddleware instance from the app."""
    for middleware in app.user_middleware:
        if middleware.cls.__name__ == "PolicyEnforcementMiddleware":
            return middleware
    return None


__all__ = [
    "setup_middleware_chain",
    "validate_middleware_chain",
    "MiddlewareChainHealth",
    "get_policy_middleware",
]

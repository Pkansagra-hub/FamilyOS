"""
Middleware chain implementation for MemoryOS API - Issue #20.1

This package implements the complete Policy Enforcement Point (PEP) chain:
MW_AUTH → MW_PEP → MW_SEC → MW_QOS → MW_SAF → MW_OBS

Complete middleware chain for production-ready API authorization and control.
"""

from fastapi import FastAPI

# Import all middleware components
from .auth import AuthenticationMiddleware
from .observability import ObservabilityMiddleware
from .pep import PolicyEnforcementPoint
from .qos import QualityOfServiceMiddleware
from .safety import SafetyFiltersMiddleware
from .security import SecurityControlsMiddleware


def setup_middleware_chain(app: FastAPI) -> None:
    """
    Setup the complete middleware chain in correct order for Issue #20.1.

    Order is critical - each middleware depends on previous ones:
    MW_AUTH → MW_PEP → MW_SEC → MW_QOS → MW_SAF → MW_OBS

    Note: FastAPI adds middleware in reverse order, so we add them backwards.
    """
    # MW_OBS - Observability (last, wraps everything)
    app.add_middleware(ObservabilityMiddleware)

    # MW_SAF - Safety Filters (safety checks and content filtering)
    app.add_middleware(SafetyFiltersMiddleware)

    # MW_QOS - Quality of Service (rate limiting, throttling)
    app.add_middleware(QualityOfServiceMiddleware)

    # MW_SEC - Security Controls (additional security headers, validation)
    app.add_middleware(SecurityControlsMiddleware)

    # MW_PEP - Policy Enforcement Point (main authorization)
    app.add_middleware(PolicyEnforcementPoint)

    # MW_AUTH - Authentication (first, everything depends on this)
    app.add_middleware(AuthenticationMiddleware)


__all__ = [
    "setup_middleware_chain",
    "AuthenticationMiddleware",
    "PolicyEnforcementPoint",
    "SecurityControlsMiddleware",
    "QualityOfServiceMiddleware",
    "SafetyFiltersMiddleware",
    "ObservabilityMiddleware",
]

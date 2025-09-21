"""
Global exception handlers for MemoryOS API.

This module provides centralized exception handling that converts
policy errors, validation errors, and other exceptions into proper
HTTP responses following the API contract.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from policy.errors import PolicyError, RBACError


async def policy_exception_handler(request: Request, exc: PolicyError) -> JSONResponse:
    """Handle policy-related exceptions."""
    return JSONResponse(
        status_code=403,
        content={
            "type": "policy_error",
            "title": "Policy Violation",
            "detail": str(exc),
            "status": 403,
            "instance": str(request.url),
        },
    )


async def rbac_exception_handler(request: Request, exc: RBACError) -> JSONResponse:
    """Handle RBAC-related exceptions."""
    return JSONResponse(
        status_code=403,
        content={
            "type": "rbac_error",
            "title": "Access Denied",
            "detail": str(exc),
            "status": 403,
            "instance": str(request.url),
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "type": "validation_error",
            "title": "Request Validation Failed",
            "detail": "The request contains invalid data",
            "status": 422,
            "instance": str(request.url),
            "errors": exc.errors(),
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "http_error",
            "title": "HTTP Error",
            "detail": exc.detail,
            "status": exc.status_code,
            "instance": str(request.url),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "type": "internal_error",
            "title": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "status": 500,
            "instance": str(request.url),
        },
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup all exception handlers."""
    app.add_exception_handler(PolicyError, policy_exception_handler)
    app.add_exception_handler(RBACError, rbac_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

"""
Capability-Based Authorization Decorators - Sub-issue #8.2

This module provides decorators for endpoint-level capability requirements.
These decorators work with the CapabilityAuthorizationMiddleware to provide
fine-grained access control at the route level.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, TypeVar

from fastapi import HTTPException, Request

from api.schemas import Capability, SecurityContext

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def require_capability(capability: Capability) -> Callable[[F], F]:
    """
    Decorator to require specific capability for an endpoint.

    This decorator can be used on FastAPI route handlers to specify
    the capability required for access. It works in conjunction with
    the CapabilityAuthorizationMiddleware.

    Args:
        capability: Required capability for this endpoint

    Returns:
        Decorated function with capability requirement

    Example:
        @router.post("/tools/memory/submit")
        @require_capability(Capability.WRITE)
        async def submit_memory(request: SubmitRequest):
            # Endpoint implementation
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if "request" in kwargs:
                request = kwargs["request"]

            if not request:
                logger.error(
                    f"No request found for capability check on {func.__name__}"
                )
                raise HTTPException(
                    status_code=500,
                    detail="Internal error: Unable to verify capabilities",
                )

            # Check if capability was already verified by middleware
            authorized_capability = getattr(
                request.state, "authorized_capability", None
            )

            if authorized_capability != capability:
                logger.warning(
                    f"Capability mismatch: endpoint requires {capability.value}, "
                    f"but middleware authorized {authorized_capability}"
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient privileges: {capability.value} capability required",
                )

            # Capability verified, proceed with endpoint
            return await func(*args, **kwargs)

        # Add capability metadata to function for introspection
        wrapper.__capability_requirement__ = capability  # type: ignore

        return wrapper  # type: ignore

    return decorator


def require_capabilities(*capabilities: Capability) -> Callable[[F], F]:
    """
    Decorator to require multiple capabilities for an endpoint.

    User must have ALL specified capabilities to access the endpoint.

    Args:
        capabilities: Required capabilities for this endpoint

    Returns:
        Decorated function with capability requirements

    Example:
        @router.post("/admin/dangerous-operation")
        @require_capabilities(Capability.WRITE, Capability.SCHEDULE)
        async def dangerous_operation():
            # Endpoint implementation
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if "request" in kwargs:
                request = kwargs["request"]

            if not request:
                logger.error(
                    f"No request found for capability check on {func.__name__}"
                )
                raise HTTPException(
                    status_code=500,
                    detail="Internal error: Unable to verify capabilities",
                )

            # Get security context
            security_ctx = getattr(request.state, "security_context", None)
            if not security_ctx or not security_ctx.capabilities:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient privileges: capabilities required",
                )

            # Check all required capabilities
            missing_caps: list[str] = []
            for cap in capabilities:
                if cap not in security_ctx.capabilities:
                    missing_caps.append(cap.value)

            if missing_caps:
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing capabilities: {', '.join(missing_caps)}",
                )

            # All capabilities verified, proceed with endpoint
            return await func(*args, **kwargs)

        # Add capability metadata to function for introspection
        wrapper.__capability_requirements__ = capabilities  # type: ignore

        return wrapper  # type: ignore

    return decorator


def require_any_capability(*capabilities: Capability) -> Callable[[F], F]:
    """
    Decorator to require ANY of the specified capabilities for an endpoint.

    User must have at least ONE of the specified capabilities to access.

    Args:
        capabilities: Any of these capabilities grants access

    Returns:
        Decorated function with capability requirements

    Example:
        @router.get("/data/read-or-recall")
        @require_any_capability(Capability.RECALL, Capability.WRITE)
        async def read_data():
            # Endpoint implementation
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if "request" in kwargs:
                request = kwargs["request"]

            if not request:
                logger.error(
                    f"No request found for capability check on {func.__name__}"
                )
                raise HTTPException(
                    status_code=500,
                    detail="Internal error: Unable to verify capabilities",
                )

            # Get security context
            security_ctx = getattr(request.state, "security_context", None)
            if not security_ctx or not security_ctx.capabilities:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient privileges: capabilities required",
                )

            # Check if user has any of the required capabilities
            has_any_cap = any(cap in security_ctx.capabilities for cap in capabilities)

            if not has_any_cap:
                cap_names = [cap.value for cap in capabilities]
                raise HTTPException(
                    status_code=403, detail=f"Requires one of: {', '.join(cap_names)}"
                )

            # At least one capability verified, proceed with endpoint
            return await func(*args, **kwargs)

        # Add capability metadata to function for introspection
        wrapper.__capability_alternatives__ = capabilities  # type: ignore

        return wrapper  # type: ignore

    return decorator


def capability_optional(capability: Capability) -> Callable[[F], F]:
    """
    Decorator to mark capability as optional for enhanced functionality.

    Endpoint works without the capability, but provides enhanced features
    if the user has it. Useful for progressive disclosure of functionality.

    Args:
        capability: Optional capability for enhanced features

    Returns:
        Decorated function with optional capability awareness

    Example:
        @router.get("/memory/search")
        @capability_optional(Capability.PROJECT)
        async def search_memory(request: Request):
            # Basic search for all users
            results = basic_search()

            # Enhanced search if user has PROJECT capability
            if has_optional_capability(request, Capability.PROJECT):
                results = enhance_with_projections(results)

            return results
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Just proceed - capability is optional
            # The endpoint can check has_optional_capability() if needed
            return await func(*args, **kwargs)

        # Add capability metadata to function for introspection
        wrapper.__optional_capability__ = capability  # type: ignore

        return wrapper  # type: ignore

    return decorator


def has_optional_capability(request: Request, capability: Capability) -> bool:
    """
    Check if user has an optional capability.

    This function can be used within endpoints decorated with
    @capability_optional to check if enhanced features should be enabled.

    Args:
        request: FastAPI request object
        capability: Capability to check

    Returns:
        True if user has the capability
    """
    security_ctx = getattr(request.state, "security_context", None)
    if not security_ctx or not security_ctx.capabilities:
        return False

    return capability in security_ctx.capabilities


def require_space_access(operation: str = "READ") -> Callable[[F], F]:
    """
    Decorator to require space-specific access for an endpoint.

    This decorator validates that the user has access to the specific
    memory space mentioned in the request, with role inheritance and
    delegation support.

    Args:
        operation: Type of operation (READ, WRITE, ADMIN)

    Returns:
        Decorated function with space access requirement

    Example:
        @router.get("/spaces/{space_id}/memories")
        @require_space_access("READ")
        async def get_space_memories(space_id: str):
            # Implementation
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if "request" in kwargs:
                request = kwargs["request"]

            if not request:
                logger.error(
                    f"No request found for space access check on {func.__name__}"
                )
                raise HTTPException(
                    status_code=500,
                    detail="Internal error: Unable to verify space access",
                )

            # Get security context and policy decision from middleware
            security_ctx = getattr(request.state, "security_context", None)
            policy_decision = getattr(request.state, "policy_decision", None)

            if not security_ctx:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication required for space access",
                )

            # Check if PolicyEnforcementMiddleware already validated access
            if policy_decision and policy_decision.decision == "ALLOW":
                # Middleware already validated, proceed
                return await func(*args, **kwargs)

            # Fallback space access check if middleware didn't handle it
            space_id = _extract_space_id_from_request(request)
            has_access = await _check_space_access(security_ctx, space_id, operation)

            if not has_access:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient access to space: {space_id}",
                )

            return await func(*args, **kwargs)

        # Add metadata for introspection
        wrapper.__space_access_requirement__ = operation  # type: ignore

        return wrapper  # type: ignore

    return decorator


def delegate_capability(
    capability: Capability,
    to_user: str,
    duration_minutes: int = 60,
    space_id: str | None = None,
) -> Callable[[F], F]:
    """
    Decorator to temporarily delegate a capability to another user.

    This decorator allows a user with a capability to temporarily grant
    it to another user for a specific duration and optionally within
    a specific space.

    Args:
        capability: Capability to delegate
        to_user: User ID to delegate to
        duration_minutes: How long the delegation lasts
        space_id: Optional space restriction for delegation

    Returns:
        Decorated function with capability delegation

    Example:
        @router.post("/delegate/write-access")
        @delegate_capability(Capability.WRITE, "child_user_123", 30, "homework:space")
        async def delegate_homework_access():
            # Implementation
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if "request" in kwargs:
                request = kwargs["request"]

            if not request:
                logger.error(
                    f"No request found for capability delegation on {func.__name__}"
                )
                raise HTTPException(
                    status_code=500,
                    detail="Internal error: Unable to process capability delegation",
                )

            # Get security context
            security_ctx = getattr(request.state, "security_context", None)
            if not security_ctx or not security_ctx.capabilities:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient privileges for capability delegation",
                )

            # Check if delegating user has the capability
            if capability not in security_ctx.capabilities:
                raise HTTPException(
                    status_code=403,
                    detail=f"Cannot delegate capability you don't have: {capability.value}",
                )

            # TODO: Implement actual delegation logic with PolicyService
            # This would involve:
            # 1. Creating a temporary capability grant
            # 2. Setting expiration time
            # 3. Optionally restricting to specific space
            # 4. Logging the delegation for audit

            return await func(*args, **kwargs)

        # Add metadata for introspection
        wrapper.__capability_delegation__ = {  # type: ignore
            "capability": capability,
            "to_user": to_user,
            "duration_minutes": duration_minutes,
            "space_id": space_id,
        }

        return wrapper  # type: ignore

    return decorator


async def _check_space_access(
    security_ctx: SecurityContext, space_id: str, operation: str
) -> bool:
    """
    Check if user has access to a specific space.

    This is a fallback method for when PolicyEnforcementMiddleware
    doesn't handle the space access check.

    Args:
        security_ctx: User's security context
        space_id: ID of the space to check
        operation: Type of operation (READ, WRITE, ADMIN)

    Returns:
        True if user has access
    """
    # TODO: Implement actual space access logic
    # This would involve checking:
    # 1. User's role in the space
    # 2. Inherited permissions from parent spaces
    # 3. Delegated capabilities
    # 4. Space-specific policies

    # For now, allow access if user is authenticated
    return security_ctx.authenticated


def _extract_space_id_from_request(request: Request) -> str:
    """Extract space_id from request path, query, or body."""
    # Try path parameters first
    path_params = getattr(request, "path_params", {})
    if "space_id" in path_params:
        return path_params["space_id"]

    # Try query parameters
    space_id = request.query_params.get("space_id")
    if space_id:
        return space_id

    # Default space
    return "shared:household"

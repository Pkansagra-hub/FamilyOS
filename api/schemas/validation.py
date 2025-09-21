"""
Validation utilities for MemoryOS schemas.

Contains reusable validation functions and business logic validation.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .core import MemoryItem, SecurityContext, SpacePolicy


def validate_memory_content(content: str) -> bool:
    """
    Validate memory content for safety and compliance.

    Args:
        content: Memory content to validate

    Returns:
        True if content is valid

    Raises:
        ValueError: If content is invalid
    """
    if not content or len(content.strip()) == 0:
        raise ValueError("Memory content cannot be empty")

    if len(content) > 1000000:  # 1MB limit
        raise ValueError("Memory content too large (max 1MB)")

    # Check for potentially sensitive patterns
    sensitive_patterns = [
        r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit card numbers
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email addresses (for privacy)
    ]

    for pattern in sensitive_patterns:
        if re.search(pattern, content):
            # Don't raise error, but could log warning
            pass

    return True


def validate_security_context(
    context: SecurityContext, required_capabilities: Optional[List[str]] = None
) -> bool:
    """
    Validate security context for a given operation.

    Args:
        context: Security context to validate
        required_capabilities: Required capabilities for the operation

    Returns:
        True if context is valid

    Raises:
        ValueError: If context is invalid
    """
    if not context.user_id or len(context.user_id.strip()) == 0:
        raise ValueError("Security context must have a valid user_id")

    if not context.session_id or len(context.session_id.strip()) == 0:
        raise ValueError("Security context must have a valid session_id")

    if required_capabilities:
        context_caps = [cap.value for cap in context.capabilities]
        missing_caps = [cap for cap in required_capabilities if cap not in context_caps]
        if missing_caps:
            raise ValueError(
                f"Missing required capabilities: {', '.join(missing_caps)}"
            )

    return True


def validate_space_policy(policy: SpacePolicy) -> bool:
    """
    Validate space policy configuration.

    Args:
        policy: Space policy to validate

    Returns:
        True if policy is valid

    Raises:
        ValueError: If policy is invalid
    """
    if not policy.space or ":" not in policy.space:
        raise ValueError(
            "Space policy must specify a valid space in format 'namespace:context'"
        )

    namespace, context = policy.space.split(":", 1)
    if not namespace or not context:
        raise ValueError("Both namespace and context are required in space identifier")

    # Validate retention policy
    if policy.retention_days and policy.retention_days < 1:
        raise ValueError("Retention period must be at least 1 day")

    # Validate size limits
    if policy.max_size_mb and policy.max_size_mb < 1:
        raise ValueError("Maximum size must be at least 1 MB")

    # Validate access controls
    if policy.access_controls:
        valid_permissions = ["read", "write", "delete", "admin"]
        for permission, users in policy.access_controls.items():
            if permission not in valid_permissions:
                raise ValueError(
                    f"Invalid permission '{permission}'. Must be one of: {', '.join(valid_permissions)}"
                )
            if not isinstance(users, list):
                raise ValueError(f"Users for permission '{permission}' must be a list")

    return True


def validate_temporal_bounds(
    start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
) -> bool:
    """
    Validate temporal bounds for queries and operations.

    Args:
        start_time: Start time boundary
        end_time: End time boundary

    Returns:
        True if bounds are valid

    Raises:
        ValueError: If bounds are invalid
    """
    now = datetime.now(timezone.utc)

    if start_time and start_time > now:
        raise ValueError("Start time cannot be in the future")

    if end_time and end_time > now:
        raise ValueError("End time cannot be in the future")

    if start_time and end_time and start_time >= end_time:
        raise ValueError("Start time must be before end time")

    # Check for reasonable time ranges (not more than 10 years ago)
    max_past = datetime.now(timezone.utc).replace(year=datetime.now().year - 10)

    if start_time and start_time < max_past:
        raise ValueError("Start time cannot be more than 10 years ago")

    if end_time and end_time < max_past:
        raise ValueError("End time cannot be more than 10 years ago")

    return True


def validate_space_identifier(space: str) -> bool:
    """
    Validate memory space identifier format and constraints.

    Args:
        space: Space identifier to validate

    Returns:
        True if space is valid

    Raises:
        ValueError: If space is invalid
    """
    if not space or len(space.strip()) == 0:
        raise ValueError("Space identifier cannot be empty")

    space = space.strip()

    if ":" not in space:
        raise ValueError("Space identifier must be in format 'namespace:context'")

    parts = space.split(":")
    if len(parts) != 2:
        raise ValueError("Space identifier must have exactly one colon separator")

    namespace, context = parts

    if not namespace or len(namespace.strip()) == 0:
        raise ValueError("Namespace cannot be empty")

    if not context or len(context.strip()) == 0:
        raise ValueError("Context cannot be empty")

    # Validate character constraints
    valid_chars = re.compile(r"^[a-zA-Z0-9_-]+$")

    if not valid_chars.match(namespace):
        raise ValueError(
            "Namespace must contain only alphanumeric characters, hyphens, and underscores"
        )

    if not valid_chars.match(context):
        raise ValueError(
            "Context must contain only alphanumeric characters, hyphens, and underscores"
        )

    # Length constraints
    if len(namespace) > 50:
        raise ValueError("Namespace must be 50 characters or less")

    if len(context) > 50:
        raise ValueError("Context must be 50 characters or less")

    return True


def validate_query_parameters(
    query: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Validate query parameters for memory recall operations.

    Args:
        query: Search query string
        limit: Result limit
        offset: Result offset
        filters: Additional filters

    Returns:
        True if parameters are valid

    Raises:
        ValueError: If parameters are invalid
    """
    if not query or len(query.strip()) == 0:
        raise ValueError("Query cannot be empty")

    if len(query) > 1000:
        raise ValueError("Query too long (max 1000 characters)")

    if limit is not None:
        if limit < 1:
            raise ValueError("Limit must be at least 1")
        if limit > 100:
            raise ValueError("Limit cannot exceed 100")

    if offset is not None:
        if offset < 0:
            raise ValueError("Offset cannot be negative")
        if offset > 10000:
            raise ValueError("Offset cannot exceed 10000")

    if filters:
        # Validate common filter types
        if "importance_min" in filters:
            importance = filters["importance_min"]
            if (
                not isinstance(importance, (int, float))
                or importance < 0
                or importance > 1
            ):
                raise ValueError("importance_min must be a number between 0 and 1")

        if "importance_max" in filters:
            importance = filters["importance_max"]
            if (
                not isinstance(importance, (int, float))
                or importance < 0
                or importance > 1
            ):
                raise ValueError("importance_max must be a number between 0 and 1")

        if "tags" in filters:
            tags = filters["tags"]
            if not isinstance(tags, list):
                raise ValueError("tags filter must be a list")
            if len(tags) > 20:
                raise ValueError("Maximum 20 tags allowed in filter")

    return True


def validate_memory_item(memory: MemoryItem) -> bool:
    """
    Comprehensive validation of a memory item.

    Args:
        memory: Memory item to validate

    Returns:
        True if memory is valid

    Raises:
        ValueError: If memory is invalid
    """
    # Validate content
    validate_memory_content(memory.content)

    # Validate space
    validate_space_identifier(memory.space)

    # Validate security context
    validate_security_context(memory.security_context)

    # Validate importance score
    if memory.importance < 0 or memory.importance > 1:
        raise ValueError("Importance score must be between 0 and 1")

    # Validate tags
    if memory.tags:
        if len(memory.tags) > 50:
            raise ValueError("Maximum 50 tags allowed")
        for tag in memory.tags:
            if not tag or len(tag.strip()) == 0:
                raise ValueError("Tags cannot be empty")
            if len(tag) > 50:
                raise ValueError("Tag length cannot exceed 50 characters")

    return True

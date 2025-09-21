"""Storage Core Exceptions - Exception classes for storage operations"""

from typing import Any, Dict, Optional

from policy.errors import PolicyError


class PolicyViolation(PolicyError):
    """Raised when policy band restrictions are violated."""

    def __init__(
        self,
        message: str,
        band: Optional[str] = None,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.band = band
        self.operation = operation
        self.context = context or {}
        self.code = "POLICY_VIOLATION"

    def __str__(self):
        base_msg = super().__str__()
        if self.band and self.operation:
            return f"{base_msg} (band={self.band}, operation={self.operation})"
        return base_msg


class StorageException(Exception):
    """Base exception for storage operations."""

    pass


class ConnectionException(StorageException):
    """Raised when database connection fails."""

    pass


class ValidationException(StorageException):
    """Raised when data validation fails."""

    pass


class TransactionException(StorageException):
    """Raised when transaction operations fail."""

    pass

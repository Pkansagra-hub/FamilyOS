from __future__ import annotations

class PolicyError(Exception):
    """Base class for policy-related exceptions."""
    code = "POLICY_ERROR"

class StorageError(PolicyError):
    """Raised when storage operations fail."""
    code = "STORAGE_ERROR"

class RBACError(PolicyError):
    """Raised for RBAC-related issues."""
    code = "RBAC_ERROR"

class ConsentError(PolicyError):
    """Raised for consent layer failures."""
    code = "CONSENT_ERROR"

"""Policy violation exception for band enforcement."""

from storage.core.exceptions import PolicyViolation

# Re-export for backward compatibility
__all__ = ["PolicyViolation"]

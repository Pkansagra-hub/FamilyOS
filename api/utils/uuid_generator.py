"""
UUID generation utilities for FamilyOS.

Provides secure and consistent UUID generation for various system components
including user IDs, device IDs, and other entity identifiers.
"""

import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


class UUIDGenerator:
    """Utility class for generating various types of UUIDs."""

    @staticmethod
    def generate_user_id() -> str:
        """
        Generate a secure UUID for user identification.

        Uses UUID4 for secure random UUIDs.

        Returns:
            str: UUID as string
        """
        return str(uuid4())

    @staticmethod
    def generate_device_id(prefix: Optional[str] = None) -> str:
        """
        Generate a device ID with optional prefix.

        Args:
            prefix: Optional prefix for the device ID (e.g., 'mobile', 'desktop')

        Returns:
            str: Device ID in format 'prefix_UUID' or just UUID
        """
        device_uuid = str(uuid4())
        if prefix:
            # Ensure prefix is safe for device_id pattern
            safe_prefix = "".join(c for c in prefix if c.isalnum() or c in "._-")[:8]
            return f"{safe_prefix}_{device_uuid}"
        return device_uuid

    @staticmethod
    def generate_session_id() -> str:
        """
        Generate a session ID for API sessions.

        Returns:
            str: Session UUID
        """
        return str(uuid4())

    @staticmethod
    def generate_request_id() -> str:
        """
        Generate a request ID for API request tracing.

        Returns:
            str: Request UUID
        """
        return str(uuid4())

    @staticmethod
    def generate_space_id(space_type: str = "personal") -> str:
        """
        Generate a space ID with type prefix.

        Args:
            space_type: Type of space (personal, shared, family, etc.)

        Returns:
            str: Space ID with type prefix
        """
        space_uuid = str(uuid4())
        safe_type = "".join(c for c in space_type if c.isalnum() or c in "._-")[:10]
        return f"{safe_type}:{space_uuid}"

    @staticmethod
    def generate_event_id() -> str:
        """
        Generate an event ID for the event bus.

        Returns:
            str: Event UUID
        """
        return str(uuid4())

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate a secure random token (not a UUID).

        Args:
            length: Length of the token in bytes

        Returns:
            str: Hex-encoded secure token
        """
        return secrets.token_hex(length)

    @staticmethod
    def is_valid_uuid(uuid_string: str) -> bool:
        """
        Validate if a string is a valid UUID.

        Args:
            uuid_string: String to validate

        Returns:
            bool: True if valid UUID, False otherwise
        """
        try:
            UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def normalize_uuid(uuid_string: str) -> str:
        """
        Normalize a UUID string to standard format.

        Args:
            uuid_string: UUID string to normalize

        Returns:
            str: Normalized UUID string

        Raises:
            ValueError: If the input is not a valid UUID
        """
        return str(UUID(uuid_string))

    @staticmethod
    def generate_username_to_uuid_mapping(username: str) -> str:
        """
        Generate a deterministic UUID from a username.

        This is useful for development mode where we want consistent
        UUIDs for the same username across restarts.

        Args:
            username: Username to convert

        Returns:
            str: UUID derived from username
        """
        # Use a namespace UUID for username mapping
        from uuid import NAMESPACE_OID, uuid5

        # Create a deterministic UUID based on username
        return str(uuid5(NAMESPACE_OID, username))


# Convenience functions for common use cases
def new_user_id() -> str:
    """Generate a new user ID."""
    return UUIDGenerator.generate_user_id()


def new_device_id(prefix: Optional[str] = None) -> str:
    """Generate a new device ID."""
    return UUIDGenerator.generate_device_id(prefix)


def new_session_id() -> str:
    """Generate a new session ID."""
    return UUIDGenerator.generate_session_id()


def new_request_id() -> str:
    """Generate a new request ID."""
    return UUIDGenerator.generate_request_id()


def new_space_id(space_type: str = "personal") -> str:
    """Generate a new space ID."""
    return UUIDGenerator.generate_space_id(space_type)


def new_event_id() -> str:
    """Generate a new event ID."""
    return UUIDGenerator.generate_event_id()


def username_to_uuid(username: str) -> str:
    """Convert username to deterministic UUID."""
    return UUIDGenerator.generate_username_to_uuid_mapping(username)


def is_uuid(value: str) -> bool:
    """Check if string is a valid UUID."""
    return UUIDGenerator.is_valid_uuid(value)


# Example usage for development mode
def create_dev_user_context(
    username: str, device_name: str = "dev_device"
) -> dict[str, str]:
    """
    Create a development user context with consistent UUIDs.

    This is useful for development mode where we want predictable
    user IDs for testing and policy configuration.

    Args:
        username: Username for the user
        device_name: Name of the device

    Returns:
        dict: User context with UUIDs
    """
    return {
        "user_id": username_to_uuid(username),
        "username": username,
        "device_id": new_device_id(device_name),
        "session_id": new_session_id(),
        "space_id": new_space_id("personal"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    # Demo the UUID generator
    print("=== FamilyOS UUID Generator Demo ===")
    print(f"User ID: {new_user_id()}")
    print(f"Device ID: {new_device_id('laptop')}")
    print(f"Session ID: {new_session_id()}")
    print(f"Space ID: {new_space_id('family')}")
    print(f"Event ID: {new_event_id()}")
    print(f"Username to UUID: {username_to_uuid('john_doe')}")
    print(f"Dev context: {create_dev_user_context('alice', 'mobile')}")

"""
API Key utilities for FamilyOS authentication.

Provides API key generation, validation, and management for service-to-service authentication.
"""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..utils.uuid_generator import new_session_id


class APIKeyManager:
    """Manages API key creation, validation, and rotation for FamilyOS."""

    def __init__(self, secret_salt: str = "familyos-api-salt"):
        """
        Initialize API key manager.

        Args:
            secret_salt: Salt for hashing API keys
        """
        self.secret_salt = secret_salt
        self.key_prefix = "fos_"  # FamilyOS prefix
        self.key_length = 32  # Length of random part

    def generate_api_key(
        self,
        user_id: str,
        service_name: str,
        capabilities: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, str]:
        """
        Generate a new API key with metadata.

        Args:
            user_id: User identifier
            service_name: Name of the service using the key
            capabilities: List of capabilities granted to this key
            expires_at: Optional expiration datetime

        Returns:
            dict: API key information
        """
        # Generate random key
        random_part = secrets.token_urlsafe(self.key_length)
        api_key = f"{self.key_prefix}{random_part}"

        # Generate key ID for storage/lookup
        key_id = new_session_id()

        # Create hash for secure storage
        key_hash = self._hash_api_key(api_key)

        # Generate metadata
        created_at = datetime.now(timezone.utc)

        return {
            "key_id": key_id,
            "api_key": api_key,
            "key_hash": key_hash,
            "user_id": user_id,
            "service_name": service_name,
            "capabilities": capabilities or ["RECALL"],
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "active": True,
        }

    def _hash_api_key(self, api_key: str) -> str:
        """
        Create a secure hash of the API key for storage.

        Args:
            api_key: Raw API key

        Returns:
            str: SHA256 hash of the key
        """
        combined = f"{api_key}{self.secret_salt}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def validate_api_key_format(self, api_key: str) -> bool:
        """
        Validate API key format without checking against storage.

        Args:
            api_key: API key to validate

        Returns:
            bool: True if format is valid
        """
        if not api_key or not isinstance(api_key, str):
            return False

        if not api_key.startswith(self.key_prefix):
            return False

        # Check length (prefix + base64 encoded random bytes)
        expected_length = len(self.key_prefix) + ((self.key_length * 4) // 3)
        if len(api_key) < expected_length - 2:  # Allow for base64 padding variation
            return False

        return True

    def extract_key_info(self, api_key: str) -> Dict[str, str]:
        """
        Extract information that can be determined from the key itself.

        Args:
            api_key: API key to analyze

        Returns:
            dict: Key information
        """
        return {
            "key_hash": (
                self._hash_api_key(api_key)
                if self.validate_api_key_format(api_key)
                else None
            ),
            "prefix": self.key_prefix,
            "format_valid": self.validate_api_key_format(api_key),
            "key_type": "api_key",
        }


class DevAPIKeyHelper:
    """Helper for creating development/demo API keys."""

    def __init__(self):
        """Initialize with development settings."""
        self.api_manager = APIKeyManager("dev-salt-change-in-production")
        self.dev_keys: Dict[str, Dict[str, str]] = {}

    def create_dev_service_key(
        self,
        service_name: str,
        user_id: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Create development API key for a service.

        Args:
            service_name: Name of the service
            user_id: Optional user ID (defaults to service name)
            capabilities: List of capabilities

        Returns:
            dict: API key information
        """
        from ..utils.uuid_generator import username_to_uuid

        if not user_id:
            user_id = username_to_uuid(f"service_{service_name}")

        key_info = self.api_manager.generate_api_key(
            user_id=user_id,
            service_name=service_name,
            capabilities=capabilities or ["WRITE", "RECALL"],
        )

        # Store for development lookup
        self.dev_keys[key_info["api_key"]] = key_info

        return key_info

    def validate_dev_key(self, api_key: str) -> Optional[Dict[str, str]]:
        """
        Validate development API key.

        Args:
            api_key: API key to validate

        Returns:
            dict: Key information if valid, None otherwise
        """
        if not self.api_manager.validate_api_key_format(api_key):
            return None

        # In development, just return stored key info
        return self.dev_keys.get(api_key)

    def create_standard_dev_keys(self) -> Dict[str, Dict[str, str]]:
        """
        Create standard development API keys for common services.

        Returns:
            dict: Mapping of service names to key information
        """
        services = [
            ("admin_service", ["WRITE", "RECALL", "PROJECT", "SCHEDULE"]),
            ("read_service", ["RECALL"]),
            ("write_service", ["WRITE", "RECALL"]),
            ("scheduler_service", ["SCHEDULE", "WRITE", "RECALL"]),
            ("test_service", ["WRITE", "RECALL"]),
        ]

        keys = {}
        for service_name, capabilities in services:
            key_info = self.create_dev_service_key(
                service_name, capabilities=capabilities
            )
            keys[service_name] = key_info

        return keys


class SecurityTokenValidator:
    """Validates different types of security tokens (JWT, API key, etc.)."""

    def __init__(self):
        """Initialize token validator."""
        self.jwt_helper = None  # Lazy load to avoid circular imports
        self.api_helper = DevAPIKeyHelper()

    def identify_token_type(self, token: str) -> str:
        """
        Identify the type of security token.

        Args:
            token: Token to identify

        Returns:
            str: Token type ('jwt', 'api_key', 'unknown')
        """
        if not token:
            return "unknown"

        # Check for JWT format (3 base64 parts separated by dots)
        if token.count(".") == 2:
            parts = token.split(".")
            if all(len(part) > 0 for part in parts):
                return "jwt"

        # Check for API key format
        if self.api_helper.api_manager.validate_api_key_format(token):
            return "api_key"

        return "unknown"

    def validate_token(
        self, token: str, token_type: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Validate a security token.

        Args:
            token: Token to validate
            token_type: Optional token type hint

        Returns:
            dict: Token information if valid, None otherwise
        """
        if not token_type:
            token_type = self.identify_token_type(token)

        if token_type == "api_key":
            return self.api_helper.validate_dev_key(token)
        elif token_type == "jwt":
            # Lazy load JWT helper to avoid circular imports
            if not self.jwt_helper:
                try:
                    from .jwt_utils import DevJWTHelper

                    self.jwt_helper = DevJWTHelper()
                except ImportError:
                    return None

            try:
                decoded = self.jwt_helper.jwt_manager.validate_token(token)
                return {
                    "user_id": decoded.get("user_id"),
                    "username": decoded.get("username"),
                    "device_id": decoded.get("device_id"),
                    "capabilities": decoded.get("capabilities", []),
                    "trust_level": decoded.get("trust_level", "amber"),
                    "token_type": "jwt",
                }
            except Exception:
                return None

        return None


# Convenience functions
def create_dev_api_keys() -> Dict[str, Dict[str, str]]:
    """Create standard development API keys."""
    helper = DevAPIKeyHelper()
    return helper.create_standard_dev_keys()


def validate_security_token(token: str) -> Optional[Dict[str, str]]:
    """Validate any type of security token."""
    validator = SecurityTokenValidator()
    return validator.validate_token(token)


def identify_token_type(token: str) -> str:
    """Identify the type of security token."""
    validator = SecurityTokenValidator()
    return validator.identify_token_type(token)


if __name__ == "__main__":
    # Demo API key creation
    print("=== FamilyOS API Key Demo ===")

    helper = DevAPIKeyHelper()

    # Create development keys
    dev_keys = helper.create_standard_dev_keys()

    print("Created development API keys:")
    for service, key_info in dev_keys.items():
        print(f"  {service}: {key_info['api_key'][:20]}...")
        print(f"    Capabilities: {key_info['capabilities']}")

    # Test validation
    test_key = dev_keys["admin_service"]["api_key"]
    validated = helper.validate_dev_key(test_key)

    if validated:
        print("\nValidation successful for admin service key")
        print(f"  User ID: {validated['user_id']}")
        print(f"  Service: {validated['service_name']}")

    # Test token identification
    print("\nToken type identification:")
    print(f"  API Key: {identify_token_type(test_key)}")
    print(f"  Invalid: {identify_token_type('invalid_token')}")

"""
API utilities package.

Provides common utilities for the FamilyOS API layer including UUID generation,
JWT tokens, mTLS certificates, and API key management.
"""

from .uuid_generator import (
    UUIDGenerator,
    create_dev_user_context,
    is_uuid,
    new_device_id,
    new_event_id,
    new_request_id,
    new_session_id,
    new_space_id,
    new_user_id,
    username_to_uuid,
)

# Security utilities - with conditional imports
try:
    from .jwt_utils import (
        DevJWTHelper,
        JWTTokenManager,
        create_dev_jwt_tokens,
        decode_jwt_unsafe,
        validate_jwt_token,
    )

    HAS_JWT = True
except ImportError:
    HAS_JWT = False

try:
    from .mtls_utils import (
        DevMTLSHelper,
        MTLSCertificateManager,
        create_dev_client_cert,
        setup_dev_mtls,
    )

    HAS_MTLS = True
except ImportError:
    HAS_MTLS = False

from .api_key_utils import (
    APIKeyManager,
    DevAPIKeyHelper,
    SecurityTokenValidator,
    create_dev_api_keys,
    identify_token_type,
    validate_security_token,
)

__all__ = [
    # UUID utilities
    "UUIDGenerator",
    "new_user_id",
    "new_device_id",
    "new_session_id",
    "new_request_id",
    "new_space_id",
    "new_event_id",
    "username_to_uuid",
    "is_uuid",
    "create_dev_user_context",
    # Security utilities
    "APIKeyManager",
    "DevAPIKeyHelper",
    "SecurityTokenValidator",
    "create_dev_api_keys",
    "validate_security_token",
    "identify_token_type",
    # Feature flags
    "HAS_JWT",
    "HAS_MTLS",
]

# Conditional exports for JWT
if HAS_JWT:
    __all__.extend(
        [
            "JWTTokenManager",
            "DevJWTHelper",
            "create_dev_jwt_tokens",
            "validate_jwt_token",
            "decode_jwt_unsafe",
        ]
    )

# Conditional exports for mTLS
if HAS_MTLS:
    __all__.extend(
        [
            "MTLSCertificateManager",
            "DevMTLSHelper",
            "setup_dev_mtls",
            "create_dev_client_cert",
        ]
    )

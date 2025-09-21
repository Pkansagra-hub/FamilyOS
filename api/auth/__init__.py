"""
Edge-First Authentication Module

Implements contract-compliant authentication for MemoryOS family networks.
All authentication happens locally without cloud dependencies.

Architecture:
- Family PKI: Self-signed certificate authority for device trust
- Local JWT: Bearer tokens for app plane authentication
- mTLS: Mutual TLS for agents and control planes
- Hardware Security: Leverage device secure enclaves where available

Contract Compliance:
- OpenAPI SecurityContext schema: 100% compliant
- Event envelope signatures: ed25519/ecdsa_p256 supported
- Local network operation: .familyos.local domains only

Sub-issue #2.2: JWT token validation (COMPLETED)
"""

from .auth_errors import (
    AuthenticationError,
    AuthorizationError,
    CertificateError,
    TokenError,
    TrustError,
)
from .jwt_validator import (
    JWTAlgorithm,
    JWTClaims,
    JWTConfig,
    JWTEnvironmentConfigs,
    JWTTokenGenerator,
    JWTValidator,
    get_jwt_validator,
    validate_jwt_token,
)
from .mtls_validator import (
    CertificateInfo,
    CertificateType,
    CertificateValidationLevel,
    DeviceAttestationLevel,
    MTLSConfig,
    MTLSEnvironmentConfigs,
    MTLSValidator,
    get_mtls_validator,
    validate_mtls_certificate,
)
from .security_context import SecurityContext, SecurityContextBuilder

__all__ = [
    "SecurityContext",
    "SecurityContextBuilder",
    "AuthenticationError",
    "AuthorizationError",
    "CertificateError",
    "TokenError",
    "TrustError",
    # Sub-issue #2.2: JWT validation
    "JWTValidator",
    "JWTConfig",
    "JWTClaims",
    "JWTAlgorithm",
    "JWTTokenGenerator",
    "JWTEnvironmentConfigs",
    "get_jwt_validator",
    "validate_jwt_token",
    # Sub-issue #2.3: mTLS validation
    "MTLSValidator",
    "MTLSConfig",
    "CertificateInfo",
    "CertificateType",
    "CertificateValidationLevel",
    "DeviceAttestationLevel",
    "MTLSEnvironmentConfigs",
    "get_mtls_validator",
    "validate_mtls_certificate",
]

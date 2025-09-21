"""
Enhanced Authentication Module

Provides edge-first authentication capabilities that extend the existing
SecurityContext with business logic and policy integration.

This module transforms the OpenAPI-compliant SecurityContext into a
fully functional authentication system for family networks.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from policy.rbac import RbacEngine

from .schemas import AuthMethod, Capability, TrustLevel
from .schemas import SecurityContext as BaseSecurityContext


class EnhancedSecurityContext:
    """
    Enhanced SecurityContext with business logic and policy integration.

    Wraps the Pydantic SecurityContext with authentication factory methods
    and authorization helpers for edge-first family authentication.
    """

    def __init__(self, base_context: BaseSecurityContext):
        """Initialize with base SecurityContext from schemas."""
        self.base = base_context
        self.created_at = datetime.now(timezone.utc)
        self.session_metadata: Dict[str, Any] = {}

    @property
    def user_id(self) -> UUID:
        """Get user ID."""
        return self.base.user_id

    @property
    def device_id(self) -> str:
        """Get device ID."""
        return self.base.device_id

    @property
    def authenticated(self) -> bool:
        """Get authentication status."""
        return self.base.authenticated

    @property
    def capabilities(self) -> Optional[List[str]]:
        """Get capabilities list as strings."""
        if self.base.capabilities:
            return [cap.value for cap in self.base.capabilities]
        return None

    @property
    def trust_level(self) -> Optional[str]:
        """Get trust level."""
        return self.base.trust_level.value if self.base.trust_level else None

    @classmethod
    def from_jwt_claims(
        cls, claims: Dict[str, Any], rbac_engine: Optional[RbacEngine] = None
    ) -> "EnhancedSecurityContext":
        """
        Create EnhancedSecurityContext from JWT claims.

        Args:
            claims: JWT token claims
            rbac_engine: Optional RBAC engine for capability resolution

        Returns:
            EnhancedSecurityContext with JWT authentication
        """
        # Extract contract-compliant fields
        user_id = UUID(claims["sub"])
        device_id = claims["device"]
        capabilities_str = claims.get("caps", [])

        # Convert string capabilities to enum
        capabilities = []
        for cap_str in capabilities_str:
            try:
                capabilities.append(Capability(cap_str))
            except ValueError:
                # Skip invalid capabilities
                pass

        # Resolve capabilities via RBAC if engine provided
        if rbac_engine and "space" in claims:
            space_caps = rbac_engine.list_caps(str(user_id), claims["space"])
            # Convert RBAC caps to enums and merge (intersection for security)
            rbac_cap_enums = []
            for cap_str in space_caps:
                try:
                    rbac_cap_enums.append(Capability(cap_str))
                except ValueError:
                    pass
            capabilities = list(set(capabilities) & set(rbac_cap_enums))

        # Create base SecurityContext using schemas
        base_context = BaseSecurityContext(
            user_id=user_id,
            device_id=device_id,
            authenticated=True,
            auth_method=AuthMethod.JWT,
            capabilities=capabilities if capabilities else None,
            mls_group=claims.get("mls_group"),
            trust_level=TrustLevel(claims.get("trust", "green")),
        )

        # Create enhanced context
        enhanced = cls(base_context)
        enhanced.session_metadata = {
            "jwt_session_id": claims.get("session_id"),
            "token_issued_at": claims.get("iat"),
            "token_expires_at": claims.get("exp"),
        }

        return enhanced

    @classmethod
    def from_certificate_info(
        cls, cert_info: Dict[str, Any], rbac_engine: Optional[RbacEngine] = None
    ) -> "EnhancedSecurityContext":
        """
        Create EnhancedSecurityContext from certificate information.

        Args:
            cert_info: Extracted certificate information
            rbac_engine: Optional RBAC engine for capability resolution

        Returns:
            EnhancedSecurityContext with mTLS authentication
        """
        # Extract contract-compliant fields
        user_id = UUID(cert_info["user_id"])
        device_id = cert_info["device_id"]
        capabilities_str = cert_info.get("capabilities", [])

        # Convert string capabilities to enum
        capabilities = []
        for cap_str in capabilities_str:
            try:
                capabilities.append(Capability(cap_str))
            except ValueError:
                pass

        # Get capabilities from RBAC if available
        if rbac_engine and cert_info.get("default_space"):
            rbac_caps = rbac_engine.list_caps(str(user_id), cert_info["default_space"])
            # Convert and merge capabilities
            rbac_cap_enums = []
            for cap_str in rbac_caps:
                try:
                    rbac_cap_enums.append(Capability(cap_str))
                except ValueError:
                    pass
            capabilities = list(set(capabilities) | set(rbac_cap_enums))

        # Create base SecurityContext
        base_context = BaseSecurityContext(
            user_id=user_id,
            device_id=device_id,
            authenticated=True,
            auth_method=AuthMethod.MTLS,
            capabilities=capabilities if capabilities else None,
            mls_group=cert_info.get("mls_group"),
            trust_level=TrustLevel(cert_info.get("trust_level", "green")),
        )

        # Create enhanced context
        enhanced = cls(base_context)
        enhanced.session_metadata = {
            "cert_subject": cert_info.get("subject"),
            "cert_serial": cert_info.get("serial"),
            "cert_valid_until": cert_info.get("not_after"),
        }

        return enhanced

    async def has_capability(
        self, capability: str, space_id: str, rbac_engine: Optional[RbacEngine] = None
    ) -> bool:
        """
        Check if context has specific capability in space.

        Args:
            capability: Required capability (e.g., "WRITE", "RECALL")
            space_id: Target space ID
            rbac_engine: Optional RBAC engine for dynamic lookup

        Returns:
            True if capability is granted
        """
        # Check cached capabilities first
        if self.capabilities and capability in self.capabilities:
            return True

        # Dynamic RBAC lookup if engine provided
        if rbac_engine:
            return rbac_engine.has_cap(str(self.user_id), space_id, capability)

        return False

    async def get_effective_permissions(
        self, space_id: str, rbac_engine: Optional[RbacEngine] = None
    ) -> Set[str]:
        """
        Get all effective permissions for context in space.

        Args:
            space_id: Target space ID
            rbac_engine: Optional RBAC engine for dynamic lookup

        Returns:
            Set of all granted capabilities
        """
        permissions = set(self.capabilities or [])

        # Add RBAC permissions if engine provided
        if rbac_engine:
            rbac_permissions = rbac_engine.list_caps(str(self.user_id), space_id)
            permissions.update(rbac_permissions)

        return permissions

    def to_audit_record(self) -> Dict[str, Any]:
        """Convert to audit record for logging."""
        return {
            "user_id": str(self.user_id),
            "device_id": self.device_id,
            "auth_method": (
                self.base.auth_method.value if self.base.auth_method else None
            ),
            "capabilities": self.capabilities,
            "trust_level": self.trust_level,
            "authenticated": self.authenticated,
            "created_at": self.created_at.isoformat(),
            "session_metadata": self.session_metadata,
        }

    def to_base_context(self) -> BaseSecurityContext:
        """Get the underlying base SecurityContext."""
        return self.base


# Backward compatibility alias
SecurityContext = EnhancedSecurityContext

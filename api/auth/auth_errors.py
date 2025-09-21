"""
Authentication and Authorization Error Classes

Edge-first authentication error hierarchy with detailed error context
for debugging and security monitoring.
"""

from typing import Any, Dict, Optional


class AuthenticationError(Exception):
    """Base class for authentication failures"""

    def __init__(
        self,
        message: str,
        error_code: str = "AUTH_FAILED",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and API responses"""
        return {"error": self.error_code, "message": str(self), "details": self.details}


class AuthorizationError(AuthenticationError):
    """Authorization failure - authenticated but insufficient permissions"""

    def __init__(
        self,
        message: str,
        required_capability: Optional[str] = None,
        space_id: Optional[str] = None,
        **kwargs: Any
    ):
        super().__init__(message, error_code="AUTHORIZATION_FAILED", **kwargs)
        self.required_capability = required_capability
        self.space_id = space_id
        if required_capability:
            self.details["required_capability"] = required_capability
        if space_id:
            self.details["space_id"] = space_id


class CertificateError(AuthenticationError):
    """Certificate validation failure"""

    def __init__(
        self,
        message: str,
        cert_subject: Optional[str] = None,
        validation_stage: Optional[str] = None,
        **kwargs: Any
    ):
        super().__init__(message, error_code="CERTIFICATE_INVALID", **kwargs)
        self.cert_subject = cert_subject
        self.validation_stage = validation_stage
        if cert_subject:
            self.details["cert_subject"] = cert_subject
        if validation_stage:
            self.details["validation_stage"] = validation_stage


class TokenError(AuthenticationError):
    """JWT token validation failure"""

    def __init__(
        self,
        message: str,
        token_type: str = "jwt",
        validation_failure: Optional[str] = None,
        **kwargs: Any
    ):
        super().__init__(message, error_code="TOKEN_INVALID", **kwargs)
        self.token_type = token_type
        self.validation_failure = validation_failure
        if validation_failure:
            self.details["validation_failure"] = validation_failure


class TrustError(AuthenticationError):
    """Device or network trust validation failure"""

    def __init__(
        self,
        message: str,
        device_id: Optional[str] = None,
        trust_level: Optional[str] = None,
        **kwargs: Any
    ):
        super().__init__(message, error_code="TRUST_VIOLATION", **kwargs)
        self.device_id = device_id
        self.trust_level = trust_level
        if device_id:
            self.details["device_id"] = device_id
        if trust_level:
            self.details["trust_level"] = trust_level


class FamilyNetworkError(AuthenticationError):
    """Family network access or membership error"""

    def __init__(
        self, message: str, network_address: Optional[str] = None, **kwargs: Any
    ):
        super().__init__(message, error_code="FAMILY_NETWORK_ERROR", **kwargs)
        self.network_address = network_address
        if network_address:
            self.details["network_address"] = network_address


class HardwareSecurityError(AuthenticationError):
    """Hardware security module or device attestation error"""

    def __init__(
        self,
        message: str,
        hardware_type: Optional[str] = None,
        attestation_failure: Optional[str] = None,
        **kwargs: Any
    ):
        super().__init__(message, error_code="HARDWARE_SECURITY_ERROR", **kwargs)
        self.hardware_type = hardware_type
        self.attestation_failure = attestation_failure
        if hardware_type:
            self.details["hardware_type"] = hardware_type
        if attestation_failure:
            self.details["attestation_failure"] = attestation_failure

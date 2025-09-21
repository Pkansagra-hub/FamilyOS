"""
mTLS Certificate Validation for MemoryOS API
Sub-issue #2.3: Implement mTLS certificate validation (2 days)

This module provides mTLS certificate validation for Agents and Control planes:
- Agents Plane: mTLS authentication for AI agents and automated systems
- Control Plane: mTLS + RBAC for administrative operations
- Device Attestation: Hardware-backed certificate validation
- Certificate Chain Validation: X.509 certificate hierarchy verification
- Integration with SecurityContext for unified authentication
"""

import base64
import hashlib
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.x509.oid import ExtensionOID
from fastapi import HTTPException, Request, status
from pydantic import BaseModel, Field

from ..schemas.core import AuthMethod, Capability, SecurityContext, TrustLevel


class CertificateType(str, Enum):
    """Certificate types supported by MemoryOS"""

    DEVICE = "device"  # Device identity certificates
    AGENT = "agent"  # AI agent certificates
    ADMIN = "admin"  # Administrative certificates
    HSM = "hsm"  # Hardware Security Module certificates
    FAMILY_CA = "family_ca"  # Family Certificate Authority


class CertificateValidationLevel(str, Enum):
    """Certificate validation strictness levels"""

    STRICT = "strict"  # Full chain validation, all checks
    STANDARD = "standard"  # Standard validation, some flexibility
    DEVELOPMENT = "development"  # Relaxed for development/testing


class DeviceAttestationLevel(str, Enum):
    """Device attestation levels based on certificate properties"""

    HARDWARE_BACKED = "hardware_backed"  # Hardware security module
    SOFTWARE_VERIFIED = "software_verified"  # Software-based verification
    SELF_SIGNED = "self_signed"  # Self-signed certificates
    UNKNOWN = "unknown"  # Unknown attestation


class CertificateInfo(BaseModel):
    """Parsed certificate information"""

    subject: Dict[str, str] = Field(description="Certificate subject fields")
    issuer: Dict[str, str] = Field(description="Certificate issuer fields")
    serial_number: str = Field(description="Certificate serial number")
    not_before: datetime = Field(description="Certificate validity start")
    not_after: datetime = Field(description="Certificate validity end")
    signature_algorithm: str = Field(description="Signature algorithm")
    public_key_algorithm: str = Field(description="Public key algorithm")
    public_key_size: int = Field(description="Public key size in bits")
    fingerprint_sha256: str = Field(description="SHA256 fingerprint")

    # MemoryOS specific fields
    device_id: Optional[str] = Field(
        None, description="Device identifier from certificate"
    )
    certificate_type: CertificateType = Field(
        description="Certificate type classification"
    )
    attestation_level: DeviceAttestationLevel = Field(
        description="Device attestation level"
    )
    capabilities: List[Capability] = Field(
        default_factory=list, description="Granted capabilities"
    )
    trust_level: TrustLevel = Field(description="Determined trust level")

    # Extension information
    key_usage: List[str] = Field(
        default_factory=list, description="Key usage extensions"
    )
    extended_key_usage: List[str] = Field(
        default_factory=list, description="Extended key usage"
    )
    subject_alt_names: List[str] = Field(
        default_factory=list, description="Subject alternative names"
    )


class MTLSConfig(BaseModel):
    """mTLS validation configuration"""

    # Validation settings
    validation_level: CertificateValidationLevel = CertificateValidationLevel.STANDARD
    verify_chain: bool = True
    verify_hostname: bool = True
    verify_expiration: bool = True
    allow_self_signed: bool = False

    # Certificate Authority settings
    ca_cert_path: Optional[Path] = None
    ca_cert_data: Optional[str] = None  # PEM format CA certificate
    family_ca_fingerprints: List[str] = Field(
        default_factory=list, description="Trusted family CA fingerprints"
    )

    # Device attestation settings
    require_device_attestation: bool = True
    min_attestation_level: DeviceAttestationLevel = (
        DeviceAttestationLevel.SOFTWARE_VERIFIED
    )
    trusted_device_fingerprints: Dict[str, str] = Field(
        default_factory=dict, description="device_id -> fingerprint"
    )

    # Security policies
    min_key_size_rsa: int = 2048
    min_key_size_ec: int = 256
    allowed_signature_algorithms: List[str] = Field(
        default_factory=lambda: [
            "sha256WithRSAEncryption",
            "ecdsa-with-SHA256",
            "ed25519",
        ]
    )

    # Certificate type policies
    certificate_type_capabilities: Dict[CertificateType, List[Capability]] = Field(
        default_factory=lambda: {
            CertificateType.DEVICE: [Capability.WRITE, Capability.RECALL],
            CertificateType.AGENT: [
                Capability.WRITE,
                Capability.RECALL,
                Capability.PROJECT,
            ],
            CertificateType.ADMIN: [
                Capability.WRITE,
                Capability.RECALL,
                Capability.PROJECT,
                Capability.SCHEDULE,
            ],
            CertificateType.HSM: [
                Capability.WRITE,
                Capability.RECALL,
                Capability.PROJECT,
                Capability.SCHEDULE,
            ],
            CertificateType.FAMILY_CA: [],
        }
    )

    # Trust level determination
    trust_level_rules: Dict[DeviceAttestationLevel, TrustLevel] = Field(
        default_factory=lambda: {
            DeviceAttestationLevel.HARDWARE_BACKED: TrustLevel.GREEN,
            DeviceAttestationLevel.SOFTWARE_VERIFIED: TrustLevel.AMBER,
            DeviceAttestationLevel.SELF_SIGNED: TrustLevel.RED,
            DeviceAttestationLevel.UNKNOWN: TrustLevel.BLACK,
        }
    )


class MTLSValidator:
    """mTLS certificate validator with SecurityContext integration"""

    def __init__(self, config: MTLSConfig):
        self.config = config
        self._ca_cert: Optional[x509.Certificate] = None
        self._load_ca_certificate()

    def _load_ca_certificate(self) -> None:
        """Load Certificate Authority certificate"""
        try:
            if self.config.ca_cert_path and self.config.ca_cert_path.exists():
                with open(self.config.ca_cert_path, "rb") as f:
                    pem_data = f.read()
                self._ca_cert = x509.load_pem_x509_certificate(pem_data)
            elif self.config.ca_cert_data:
                pem_data = self.config.ca_cert_data.encode()
                self._ca_cert = x509.load_pem_x509_certificate(pem_data)
        except Exception as e:
            if self.config.validation_level == CertificateValidationLevel.STRICT:
                raise ValueError(f"Failed to load CA certificate: {e}")

    async def validate_certificate_chain(self, request: Request) -> SecurityContext:
        """
        Validate mTLS certificate chain from FastAPI request

        Args:
            request: FastAPI request with client certificate

        Returns:
            SecurityContext: Validated security context

        Raises:
            HTTPException: On validation failure
        """
        try:
            # Extract client certificate from request
            client_cert = await self._extract_client_certificate(request)

            # Parse and validate certificate
            cert_info = await self._parse_certificate(client_cert)

            # Validate certificate chain
            if self.config.verify_chain:
                await self._validate_chain(client_cert)

            # Validate certificate properties
            await self._validate_certificate_properties(cert_info)

            # Convert to SecurityContext
            security_context = await self._certificate_to_security_context(cert_info)

            # Additional validation
            await self._validate_security_context(security_context, cert_info)

            return security_context

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Certificate validation error: {str(e)}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"mTLS authentication failed: {str(e)}",
            )

    async def _extract_client_certificate(self, request: Request) -> x509.Certificate:
        """Extract client certificate from ASGI scope"""

        # Try to get certificate from ASGI scope (for production)
        scope = request.scope
        if "client" in scope and scope["client"] and len(scope["client"]) > 2:
            # ASGI scope should contain certificate in client[2] for mTLS
            cert_der = scope["client"][2] if len(scope["client"]) > 2 else None
            if cert_der:
                return x509.load_der_x509_certificate(cert_der)

        # Try to get from headers (for development/testing)
        cert_header = request.headers.get("X-Client-Cert")
        if cert_header:
            try:
                # Assume PEM format in header
                cert_pem = base64.b64decode(cert_header)
                return x509.load_pem_x509_certificate(cert_pem)
            except Exception:
                # Try direct PEM
                return x509.load_pem_x509_certificate(cert_header.encode())

        # Check for admin HSM certificate header
        hsm_cert = request.headers.get("X-Admin-Cert")
        if hsm_cert:
            try:
                cert_pem = base64.b64decode(hsm_cert)
                return x509.load_pem_x509_certificate(cert_pem)
            except Exception:
                return x509.load_pem_x509_certificate(hsm_cert.encode())

        raise ValueError("No client certificate found in request")

    async def _parse_certificate(self, cert: x509.Certificate) -> CertificateInfo:
        """Parse X.509 certificate into structured information"""

        # Extract subject and issuer
        subject = {attr.oid._name: attr.value for attr in cert.subject}
        issuer = {attr.oid._name: attr.value for attr in cert.issuer}

        # Calculate fingerprint
        fingerprint = hashlib.sha256(
            cert.public_bytes(serialization.Encoding.DER)
        ).hexdigest()

        # Determine public key information
        public_key = cert.public_key()
        if isinstance(public_key, rsa.RSAPublicKey):
            pub_alg = "RSA"
            pub_size = public_key.key_size
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            pub_alg = "ECDSA"
            pub_size = public_key.curve.key_size
        elif isinstance(public_key, ed25519.Ed25519PublicKey):
            pub_alg = "Ed25519"
            pub_size = 256
        else:
            pub_alg = "Unknown"
            pub_size = 0

        # Extract extensions
        key_usage = []
        extended_key_usage = []
        subject_alt_names = []

        try:
            ku = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE).value
            if ku.digital_signature:
                key_usage.append("digital_signature")
            if ku.key_cert_sign:
                key_usage.append("key_cert_sign")
            if ku.crl_sign:
                key_usage.append("crl_sign")
        except x509.ExtensionNotFound:
            pass

        try:
            eku = cert.extensions.get_extension_for_oid(
                ExtensionOID.EXTENDED_KEY_USAGE
            ).value
            extended_key_usage = [usage._name for usage in eku]
        except x509.ExtensionNotFound:
            pass

        try:
            san = cert.extensions.get_extension_for_oid(
                ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            ).value
            subject_alt_names = [name.value for name in san]
        except x509.ExtensionNotFound:
            pass

        # Determine certificate type and device ID
        device_id = await self._extract_device_id(cert, subject, subject_alt_names)
        cert_type = await self._classify_certificate_type(
            cert, subject, extended_key_usage
        )
        attestation_level = await self._determine_attestation_level(cert, cert_type)

        # Determine capabilities and trust level
        capabilities = self.config.certificate_type_capabilities.get(cert_type, [])
        trust_level = self.config.trust_level_rules.get(
            attestation_level, TrustLevel.BLACK
        )

        return CertificateInfo(
            subject=subject,
            issuer=issuer,
            serial_number=str(cert.serial_number),
            not_before=cert.not_valid_before.replace(tzinfo=timezone.utc),
            not_after=cert.not_valid_after.replace(tzinfo=timezone.utc),
            signature_algorithm=cert.signature_algorithm_oid._name,
            public_key_algorithm=pub_alg,
            public_key_size=pub_size,
            fingerprint_sha256=fingerprint,
            device_id=device_id,
            certificate_type=cert_type,
            attestation_level=attestation_level,
            capabilities=capabilities,
            trust_level=trust_level,
            key_usage=key_usage,
            extended_key_usage=extended_key_usage,
            subject_alt_names=subject_alt_names,
        )

    async def _extract_device_id(
        self, cert: x509.Certificate, subject: Dict[str, str], san: List[str]
    ) -> Optional[str]:
        """Extract device ID from certificate"""

        # Try Common Name first
        device_id = subject.get("commonName")
        if device_id and self._is_valid_device_id(device_id):
            return device_id

        # Try Subject Alternative Names
        for name in san:
            if self._is_valid_device_id(name):
                return name

        # Try Organization Unit
        ou = subject.get("organizationalUnitName")
        if ou and self._is_valid_device_id(ou):
            return ou

        return None

    def _is_valid_device_id(self, device_id: str) -> bool:
        """Validate device ID format"""
        import re

        return bool(re.match(r"^[A-Za-z0-9._:-]{3,64}$", device_id))

    async def _classify_certificate_type(
        self, cert: x509.Certificate, subject: Dict[str, str], eku: List[str]
    ) -> CertificateType:
        """Classify certificate type based on properties"""

        # Check for HSM indicators
        if "hsm" in subject.get("organizationalUnitName", "").lower():
            return CertificateType.HSM

        # Check for admin indicators
        if (
            "admin" in subject.get("commonName", "").lower()
            or "administrator" in subject.get("title", "").lower()
        ):
            return CertificateType.ADMIN

        # Check for agent indicators
        if "agent" in subject.get("commonName", "").lower() or "clientAuth" in eku:
            return CertificateType.AGENT

        # Check for CA indicators
        if "CA" in subject.get(
            "commonName", ""
        ) or "Certificate Authority" in subject.get("organizationName", ""):
            return CertificateType.FAMILY_CA

        # Default to device
        return CertificateType.DEVICE

    async def _determine_attestation_level(
        self, cert: x509.Certificate, cert_type: CertificateType
    ) -> DeviceAttestationLevel:
        """Determine device attestation level"""

        # HSM certificates are hardware-backed
        if cert_type == CertificateType.HSM:
            return DeviceAttestationLevel.HARDWARE_BACKED

        # Check if certificate is self-signed
        if cert.issuer == cert.subject:
            return DeviceAttestationLevel.SELF_SIGNED

        # Check if issued by known family CA
        if self._ca_cert and cert.issuer == self._ca_cert.subject:
            return DeviceAttestationLevel.SOFTWARE_VERIFIED

        # Check fingerprint against trusted devices
        fingerprint = hashlib.sha256(
            cert.public_bytes(serialization.Encoding.DER)
        ).hexdigest()
        if fingerprint in self.config.family_ca_fingerprints:
            return DeviceAttestationLevel.HARDWARE_BACKED

        return DeviceAttestationLevel.UNKNOWN

    async def _validate_chain(self, cert: x509.Certificate) -> None:
        """Validate certificate chain"""

        if not self._ca_cert:
            if self.config.validation_level == CertificateValidationLevel.STRICT:
                raise ValueError("No CA certificate available for chain validation")
            return

        # Verify certificate was signed by CA
        try:
            self._ca_cert.public_key().verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                cert.signature_algorithm_oid._name,
            )
        except Exception as e:
            raise ValueError(f"Certificate chain validation failed: {e}")

    async def _validate_certificate_properties(
        self, cert_info: CertificateInfo
    ) -> None:
        """Validate certificate properties against policies"""

        # Check expiration
        if self.config.verify_expiration:
            now = datetime.now(timezone.utc)
            if now < cert_info.not_before:
                raise ValueError("Certificate not yet valid")
            if now > cert_info.not_after:
                raise ValueError("Certificate has expired")

        # Check key size
        if (
            cert_info.public_key_algorithm == "RSA"
            and cert_info.public_key_size < self.config.min_key_size_rsa
        ):
            raise ValueError(
                f"RSA key size {cert_info.public_key_size} below minimum {self.config.min_key_size_rsa}"
            )

        if (
            cert_info.public_key_algorithm == "ECDSA"
            and cert_info.public_key_size < self.config.min_key_size_ec
        ):
            raise ValueError(
                f"EC key size {cert_info.public_key_size} below minimum {self.config.min_key_size_ec}"
            )

        # Check signature algorithm
        if (
            cert_info.signature_algorithm
            not in self.config.allowed_signature_algorithms
        ):
            raise ValueError(
                f"Signature algorithm {cert_info.signature_algorithm} not allowed"
            )

        # Check attestation level
        if cert_info.attestation_level.value < self.config.min_attestation_level.value:
            raise ValueError(
                f"Attestation level {cert_info.attestation_level} below minimum {self.config.min_attestation_level}"
            )

        # Check device ID if required
        if self.config.require_device_attestation and not cert_info.device_id:
            raise ValueError("Device ID required but not found in certificate")

    async def _certificate_to_security_context(
        self, cert_info: CertificateInfo
    ) -> SecurityContext:
        """Convert certificate info to SecurityContext"""

        # Generate user_id from certificate subject
        user_id = cert_info.subject.get("commonName", cert_info.device_id or "unknown")

        # Use device_id or fallback to subject CN
        device_id = cert_info.device_id or cert_info.subject.get(
            "commonName", "unknown_device"
        )

        # Determine MLS group from certificate
        mls_group = cert_info.subject.get("organizationName", "family_default")

        return SecurityContext(
            user_id=user_id,
            device_id=device_id,
            authenticated=True,
            auth_method=AuthMethod.MTLS,
            capabilities=cert_info.capabilities,
            trust_level=cert_info.trust_level,
            mls_group=mls_group,
        )

    async def _validate_security_context(
        self, context: SecurityContext, cert_info: CertificateInfo
    ) -> None:
        """Additional SecurityContext validation"""

        # Validate device fingerprint if configured
        if (
            cert_info.device_id
            and cert_info.device_id in self.config.trusted_device_fingerprints
        ):
            expected_fingerprint = self.config.trusted_device_fingerprints[
                cert_info.device_id
            ]
            if expected_fingerprint != cert_info.fingerprint_sha256:
                raise ValueError(
                    f"Device fingerprint mismatch for {cert_info.device_id}"
                )

        # Validate trust level consistency
        if context.trust_level == TrustLevel.BLACK and context.capabilities:
            raise ValueError("BLACK trust level devices cannot have capabilities")


class MTLSEnvironmentConfigs:
    """Pre-configured mTLS settings for different environments"""

    @staticmethod
    def development() -> MTLSConfig:
        """Development configuration with relaxed security"""
        return MTLSConfig(
            validation_level=CertificateValidationLevel.DEVELOPMENT,
            verify_chain=False,
            verify_hostname=False,
            verify_expiration=False,
            allow_self_signed=True,
            require_device_attestation=False,
            min_attestation_level=DeviceAttestationLevel.SELF_SIGNED,
        )

    @staticmethod
    def production() -> MTLSConfig:
        """Production configuration with strict security"""
        return MTLSConfig(
            validation_level=CertificateValidationLevel.STRICT,
            verify_chain=True,
            verify_hostname=True,
            verify_expiration=True,
            allow_self_signed=False,
            require_device_attestation=True,
            min_attestation_level=DeviceAttestationLevel.SOFTWARE_VERIFIED,
        )


# Dependency injection helpers for FastAPI
def get_mtls_validator() -> MTLSValidator:
    """FastAPI dependency to get mTLS validator"""
    # In production, this would load config from environment/settings
    config = MTLSEnvironmentConfigs.development()
    return MTLSValidator(config)


async def validate_mtls_certificate(
    request: Request, validator: Optional[MTLSValidator] = None
) -> SecurityContext:
    """FastAPI dependency for mTLS certificate validation"""
    if not validator:
        validator = get_mtls_validator()

    return await validator.validate_certificate_chain(request)

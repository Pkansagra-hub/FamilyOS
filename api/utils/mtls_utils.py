"""
mTLS (Mutual TLS) utilities for FamilyOS secure authentication.

Provides certificate generation, validation, and mTLS client authentication helpers.
"""

import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

from ..utils.uuid_generator import new_device_id


class MTLSCertificateManager:
    """Manages mTLS certificates for FamilyOS authentication."""

    def __init__(
        self, ca_cert_path: Optional[str] = None, ca_key_path: Optional[str] = None
    ):
        """
        Initialize mTLS certificate manager.

        Args:
            ca_cert_path: Path to CA certificate file
            ca_key_path: Path to CA private key file
        """
        if not HAS_CRYPTOGRAPHY:
            raise ImportError(
                "cryptography library not available. Install with: pip install cryptography"
            )

        self.ca_cert_path = ca_cert_path
        self.ca_key_path = ca_key_path
        self.default_validity_days = 365

    def generate_ca_certificate(
        self,
        common_name: str = "FamilyOS CA",
        organization: str = "FamilyOS",
        validity_days: int = 3650,
    ) -> Tuple[bytes, bytes]:
        """
        Generate a Certificate Authority (CA) certificate and private key.

        Args:
            common_name: CA common name
            organization: Organization name
            validity_days: Certificate validity in days

        Returns:
            tuple: (cert_pem, private_key_pem)
        """
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=validity_days))
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName("localhost"),
                        x509.DNSName("familyos.local"),
                        x509.IPAddress(socket.inet_aton("127.0.0.1")),
                    ]
                ),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    key_agreement=False,
                    key_encipherment=False,
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    content_commitment=False,
                    data_encipherment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(private_key, hashes.SHA256())
        )

        # Serialize to PEM format
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        return cert_pem, key_pem

    def generate_client_certificate(
        self,
        user_id: str,
        device_id: str,
        ca_cert_pem: bytes,
        ca_key_pem: bytes,
        validity_days: Optional[int] = None,
    ) -> Tuple[bytes, bytes]:
        """
        Generate a client certificate signed by the CA.

        Args:
            user_id: User identifier
            device_id: Device identifier
            ca_cert_pem: CA certificate in PEM format
            ca_key_pem: CA private key in PEM format
            validity_days: Certificate validity in days

        Returns:
            tuple: (client_cert_pem, client_key_pem)
        """
        validity_days = validity_days or self.default_validity_days

        # Load CA certificate and key
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem)
        ca_key = serialization.load_pem_private_key(ca_key_pem, password=None)

        # Generate client private key
        client_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create client certificate
        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FamilyOS Client"),
                x509.NameAttribute(
                    NameOID.ORGANIZATIONAL_UNIT_NAME, f"Device:{device_id}"
                ),
                x509.NameAttribute(NameOID.COMMON_NAME, f"user:{user_id}"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(client_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=validity_days))
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName(f"user-{user_id}.familyos.local"),
                        x509.DNSName(f"device-{device_id}.familyos.local"),
                    ]
                ),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    key_agreement=False,
                    key_encipherment=True,
                    digital_signature=True,
                    key_cert_sign=False,
                    crl_sign=False,
                    content_commitment=False,
                    data_encipherment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage(
                    [
                        x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                    ]
                ),
                critical=True,
            )
            .sign(ca_key, hashes.SHA256())
        )

        # Serialize to PEM format
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = client_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        return cert_pem, key_pem

    def validate_client_certificate(
        self, client_cert_pem: bytes, ca_cert_pem: bytes
    ) -> Dict[str, str]:
        """
        Validate a client certificate against the CA.

        Args:
            client_cert_pem: Client certificate in PEM format
            ca_cert_pem: CA certificate in PEM format

        Returns:
            dict: Certificate information if valid

        Raises:
            ValueError: If certificate is invalid
        """
        try:
            client_cert = x509.load_pem_x509_certificate(client_cert_pem)
            ca_cert = x509.load_pem_x509_certificate(ca_cert_pem)

            # Verify signature
            ca_public_key = ca_cert.public_key()
            ca_public_key.verify(
                client_cert.signature,
                client_cert.tbs_certificate_bytes,
                client_cert.signature_algorithm_oid._name.value,
            )

            # Check validity period
            now = datetime.now(timezone.utc)
            if now < client_cert.not_valid_before or now > client_cert.not_valid_after:
                raise ValueError("Certificate is not within valid time period")

            # Extract user information
            subject = client_cert.subject
            user_id = None
            device_id = None

            for attribute in subject:
                if attribute.oid == NameOID.COMMON_NAME:
                    cn = attribute.value
                    if cn.startswith("user:"):
                        user_id = cn[5:]  # Remove "user:" prefix
                elif attribute.oid == NameOID.ORGANIZATIONAL_UNIT_NAME:
                    ou = attribute.value
                    if ou.startswith("Device:"):
                        device_id = ou[7:]  # Remove "Device:" prefix

            return {
                "user_id": user_id or "unknown",
                "device_id": device_id or "unknown",
                "serial_number": str(client_cert.serial_number),
                "not_valid_before": client_cert.not_valid_before.isoformat(),
                "not_valid_after": client_cert.not_valid_after.isoformat(),
                "issuer": client_cert.issuer.rfc4514_string(),
                "subject": client_cert.subject.rfc4514_string(),
            }

        except Exception as e:
            raise ValueError(f"Certificate validation failed: {str(e)}")


class DevMTLSHelper:
    """Helper for creating development/demo mTLS certificates."""

    def __init__(self, base_dir: str = "./dev_certs"):
        """Initialize with development certificate directory."""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.cert_manager = MTLSCertificateManager()

        # File paths
        self.ca_cert_path = self.base_dir / "ca.crt"
        self.ca_key_path = self.base_dir / "ca.key"

    def setup_dev_ca(self, force_recreate: bool = False) -> None:
        """
        Set up development CA certificate.

        Args:
            force_recreate: Force recreation of existing CA
        """
        if not HAS_CRYPTOGRAPHY:
            raise ImportError("cryptography library not available")

        if (
            not force_recreate
            and self.ca_cert_path.exists()
            and self.ca_key_path.exists()
        ):
            print(f"CA certificates already exist at {self.base_dir}")
            return

        print("Generating development CA certificate...")
        ca_cert_pem, ca_key_pem = self.cert_manager.generate_ca_certificate(
            common_name="FamilyOS Dev CA", organization="FamilyOS Development"
        )

        # Save CA certificate and key
        self.ca_cert_path.write_bytes(ca_cert_pem)
        self.ca_key_path.write_bytes(ca_key_pem)

        print(f"CA certificate saved to: {self.ca_cert_path}")
        print(f"CA private key saved to: {self.ca_key_path}")

    def create_client_cert(
        self, username: str, device_name: str = "dev_device"
    ) -> Dict[str, str]:
        """
        Create a client certificate for development.

        Args:
            username: Username for the certificate
            device_name: Device name

        Returns:
            dict: Certificate information and file paths
        """
        if not HAS_CRYPTOGRAPHY:
            raise ImportError("cryptography library not available")

        # Ensure CA exists
        self.setup_dev_ca()

        from ..utils.uuid_generator import username_to_uuid

        user_id = username_to_uuid(username)
        device_id = new_device_id(device_name)

        # Load CA certificate and key
        ca_cert_pem = self.ca_cert_path.read_bytes()
        ca_key_pem = self.ca_key_path.read_bytes()

        # Generate client certificate
        client_cert_pem, client_key_pem = self.cert_manager.generate_client_certificate(
            user_id=user_id,
            device_id=device_id,
            ca_cert_pem=ca_cert_pem,
            ca_key_pem=ca_key_pem,
        )

        # Save client certificate and key
        client_cert_path = self.base_dir / f"{username}.crt"
        client_key_path = self.base_dir / f"{username}.key"

        client_cert_path.write_bytes(client_cert_pem)
        client_key_path.write_bytes(client_key_pem)

        print(f"Client certificate for {username} saved to: {client_cert_path}")
        print(f"Client private key saved to: {client_key_path}")

        return {
            "username": username,
            "user_id": user_id,
            "device_id": device_id,
            "cert_path": str(client_cert_path),
            "key_path": str(client_key_path),
            "ca_cert_path": str(self.ca_cert_path),
        }

    def validate_client_cert(self, username: str) -> Dict[str, str]:
        """
        Validate a client certificate.

        Args:
            username: Username whose certificate to validate

        Returns:
            dict: Validation results
        """
        if not HAS_CRYPTOGRAPHY:
            raise ImportError("cryptography library not available")

        client_cert_path = self.base_dir / f"{username}.crt"

        if not client_cert_path.exists():
            raise FileNotFoundError(f"Client certificate not found: {client_cert_path}")

        ca_cert_pem = self.ca_cert_path.read_bytes()
        client_cert_pem = client_cert_path.read_bytes()

        return self.cert_manager.validate_client_certificate(
            client_cert_pem, ca_cert_pem
        )


# Convenience functions
def setup_dev_mtls(base_dir: str = "./dev_certs") -> DevMTLSHelper:
    """Set up development mTLS environment."""
    helper = DevMTLSHelper(base_dir)
    helper.setup_dev_ca()
    return helper


def create_dev_client_cert(
    username: str, base_dir: str = "./dev_certs"
) -> Dict[str, str]:
    """Create development client certificate."""
    helper = DevMTLSHelper(base_dir)
    return helper.create_client_cert(username)


if __name__ == "__main__":
    # Demo mTLS certificate creation
    if HAS_CRYPTOGRAPHY:
        print("=== FamilyOS mTLS Demo ===")

        helper = DevMTLSHelper("./demo_certs")

        # Set up CA
        helper.setup_dev_ca()

        # Create client certificates
        admin_cert = helper.create_client_cert("admin", "laptop")
        user_cert = helper.create_client_cert("john_doe", "mobile")

        print(f"Admin cert created: {admin_cert['cert_path']}")
        print(f"User cert created: {user_cert['cert_path']}")

        # Validate certificates
        try:
            admin_info = helper.validate_client_cert("admin")
            print(f"Admin cert validation: {admin_info['user_id']}")
        except Exception as e:
            print(f"Admin cert validation failed: {e}")

    else:
        print(
            "cryptography library not available. Install with: pip install cryptography"
        )

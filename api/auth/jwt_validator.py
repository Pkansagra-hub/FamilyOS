"""
JWT Token Validation for MemoryOS API
Sub-issue #2.2: Implement JWT token validation (2 days)

This module provides JWT token validation for both Agents and App planes:
- Agent Plane: mTLS + JWT authentication (agents.familyos.local)
- App Plane: Bearer JWT authentication (app.familyos.local)
- Contract-compliant with OpenAPI security schemes
- Integration with SecurityContext for unified authentication
"""

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from ..schemas.core import AuthMethod, Capability, SecurityContext, TrustLevel


class JWTAlgorithm(str, Enum):
    """Supported JWT signing algorithms"""

    RS256 = "RS256"  # RSA with SHA-256 (preferred for production)
    ES256 = "ES256"  # ECDSA with SHA-256 (preferred for performance)
    HS256 = "HS256"  # HMAC with SHA-256 (for development/testing only)


class JWTClaims(BaseModel):
    """Standard and custom JWT claims for MemoryOS"""

    # Standard JWT claims (RFC 7519)
    iss: str = Field(description="Issuer - MemoryOS identity provider")
    sub: str = Field(description="Subject - User ID (UUID format)")
    aud: str = Field(description="Audience - API plane (agents/app/control)")
    exp: int = Field(description="Expiration time (Unix timestamp)")
    nbf: int = Field(description="Not before time (Unix timestamp)")
    iat: int = Field(description="Issued at time (Unix timestamp)")
    jti: str = Field(description="JWT ID (unique identifier)")

    # MemoryOS custom claims
    device_id: str = Field(description="Device identifier")
    capabilities: List[Capability] = Field(description="Granted capabilities")
    trust_level: TrustLevel = Field(description="Trust assessment level")
    space_id: Optional[str] = Field(None, description="Default space context")
    mls_group: Optional[str] = Field(None, description="MLS group membership")
    auth_method: AuthMethod = Field(AuthMethod.JWT, description="Authentication method")

    @field_validator("sub")
    @classmethod
    def validate_user_id_format(cls, v: str) -> str:
        """Validate user_id is proper UUID format"""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("sub (user_id) must be valid UUID format")

    @field_validator("device_id")
    @classmethod
    def validate_device_id_format(cls, v: str) -> str:
        """Validate device_id matches contract pattern"""
        import re

        if not re.match(r"^[A-Za-z0-9._:-]{3,64}$", v):
            raise ValueError(
                "device_id must be 3-64 chars, alphanumeric with ._:- allowed"
            )
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("device_id cannot start or end with hyphen")
        return v

    @field_validator("aud")
    @classmethod
    def validate_audience(cls, v: str) -> str:
        """Validate audience matches supported API planes"""
        valid_audiences = [
            "agents.familyos.local",
            "app.familyos.local",
            "control.familyos.local",
            "*.familyos.local",  # Wildcard for development
        ]
        if v not in valid_audiences:
            raise ValueError(f"Invalid audience. Must be one of: {valid_audiences}")
        return v


class JWTConfig(BaseModel):
    """JWT validation configuration"""

    # Signing configuration
    algorithm: JWTAlgorithm = JWTAlgorithm.RS256
    public_key: Optional[str] = None
    secret_key: Optional[str] = None  # Only for HS256 development

    # Validation settings
    verify_signature: bool = True
    verify_exp: bool = True
    verify_nbf: bool = True
    verify_iss: bool = True
    verify_aud: bool = True

    # Clock skew tolerance
    leeway: int = 30  # seconds

    # Token lifetime limits
    max_token_age: int = 3600  # 1 hour default
    min_token_age: int = 0  # immediate validity

    # Issuer validation
    valid_issuers: List[str] = Field(
        default_factory=lambda: [
            "memoryos.familyos.local",
            "auth.familyos.local",
            "localhost",  # Development only
        ]
    )

    # Required capabilities by plane
    plane_required_capabilities: Dict[str, List[Capability]] = Field(
        default_factory=lambda: {
            "agents.familyos.local": [Capability.WRITE, Capability.RECALL],
            "app.familyos.local": [Capability.RECALL],
            "control.familyos.local": [
                Capability.WRITE,
                Capability.RECALL,
                Capability.PROJECT,
                Capability.SCHEDULE,
            ],
        }
    )


class JWTValidator:
    """JWT token validator with SecurityContext integration"""

    def __init__(self, config: JWTConfig):
        self.config = config
        self.bearer_scheme = HTTPBearer(auto_error=False)

    async def validate_token(
        self, credentials: HTTPAuthorizationCredentials
    ) -> SecurityContext:
        """
        Validate JWT token and return SecurityContext

        Args:
            credentials: HTTP Bearer credentials from FastAPI

        Returns:
            SecurityContext: Validated security context

        Raises:
            HTTPException: On validation failure
        """
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing JWT token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials

        try:
            # Decode and validate JWT
            claims = await self._decode_jwt(token)

            # Convert to SecurityContext
            security_context = await self._claims_to_security_context(claims)

            # Additional validation
            await self._validate_security_context(security_context)

            return security_context

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="JWT token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid JWT token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"JWT validation error: {str(e)}",
            )

    async def _decode_jwt(self, token: str) -> JWTClaims:
        """Decode and validate JWT token structure"""

        # Get signing key
        if self.config.algorithm == JWTAlgorithm.HS256:
            key = self.config.secret_key
            if not key:
                raise ValueError("HS256 requires secret_key in configuration")
        else:
            key = self.config.public_key
            if not key:
                raise ValueError(
                    f"{self.config.algorithm} requires public_key in configuration"
                )

        # Decode JWT with validation
        payload = jwt.decode(
            token,
            key=key,
            algorithms=[self.config.algorithm.value],
            options={
                "verify_signature": self.config.verify_signature,
                "verify_exp": self.config.verify_exp,
                "verify_nbf": self.config.verify_nbf,
                "verify_iss": self.config.verify_iss,
                "verify_aud": self.config.verify_aud,
            },
            leeway=self.config.leeway,
            issuer=self.config.valid_issuers if self.config.verify_iss else None,
        )

        # Validate claims structure
        try:
            claims = JWTClaims(**payload)
        except Exception as e:
            raise ValueError(f"Invalid JWT claims structure: {str(e)}")

        # Additional time-based validation
        current_time = int(time.time())

        # Check token age
        token_age = current_time - claims.iat
        if token_age > self.config.max_token_age:
            raise jwt.InvalidTokenError(
                f"Token too old: {token_age}s > {self.config.max_token_age}s"
            )

        if token_age < self.config.min_token_age:
            raise jwt.InvalidTokenError(
                f"Token too new: {token_age}s < {self.config.min_token_age}s"
            )

        return claims

    async def _claims_to_security_context(self, claims: JWTClaims) -> SecurityContext:
        """Convert JWT claims to SecurityContext"""

        return SecurityContext(
            user_id=claims.sub,
            device_id=claims.device_id,
            authenticated=True,
            auth_method=AuthMethod.JWT,
            capabilities=claims.capabilities,
            trust_level=claims.trust_level,
            mls_group=claims.mls_group,
        )

    async def _validate_security_context(self, context: SecurityContext) -> None:
        """Additional SecurityContext validation"""

        # Validate trust level consistency
        if context.trust_level == TrustLevel.BLACK and context.capabilities:
            raise ValueError("BLACK trust level cannot have capabilities")

        # Validate capabilities for audience (plane-specific requirements)
        # This would be enhanced with actual plane detection from request context

        # Validate device consistency (if mTLS is also present)
        # This would be enhanced with actual certificate validation

        pass  # Additional validation as needed


class JWTTokenGenerator:
    """JWT token generator for testing and development"""

    def __init__(self, config: JWTConfig):
        self.config = config

    async def generate_token(
        self,
        user_id: str,
        device_id: str,
        audience: str,
        capabilities: List[Capability],
        trust_level: TrustLevel = TrustLevel.GREEN,
        expires_in: int = 3600,
        **kwargs: Any,
    ) -> str:
        """Generate JWT token for testing/development"""

        current_time = int(time.time())

        claims: Dict[str, Any] = {
            "iss": self.config.valid_issuers[0],
            "sub": user_id,
            "aud": audience,
            "exp": current_time + expires_in,
            "nbf": current_time,
            "iat": current_time,
            "jti": str(uuid.uuid4()),
            "device_id": device_id,
            "capabilities": [cap.value for cap in capabilities],
            "trust_level": trust_level.value,
            "auth_method": AuthMethod.JWT.value,
            **kwargs,
        }

        # Get signing key
        key = self.config.secret_key or "dev-secret-key"

        token = jwt.encode(claims, key, algorithm=JWTAlgorithm.HS256.value)
        return token


# Default configurations for different environments
class JWTEnvironmentConfigs:
    """Pre-configured JWT settings for different environments"""

    @staticmethod
    def development() -> JWTConfig:
        """Development configuration with relaxed security"""
        return JWTConfig(
            algorithm=JWTAlgorithm.HS256,
            secret_key="dev-secret-key-for-testing-only",
            verify_signature=True,
            verify_exp=True,
            verify_nbf=False,  # Relaxed for dev
            verify_iss=False,  # Relaxed for dev
            verify_aud=False,  # Relaxed for dev
            leeway=60,  # More tolerance
            max_token_age=7200,  # 2 hours for dev
            valid_issuers=["localhost", "dev.familyos.local"],
        )

    @staticmethod
    def production() -> JWTConfig:
        """Production configuration with strict security"""
        return JWTConfig(
            algorithm=JWTAlgorithm.RS256,
            verify_signature=True,
            verify_exp=True,
            verify_nbf=True,
            verify_iss=True,
            verify_aud=True,
            leeway=30,
            max_token_age=3600,  # 1 hour
            valid_issuers=["auth.familyos.local", "memoryos.familyos.local"],
        )


# Dependency injection helpers for FastAPI
def get_jwt_validator() -> JWTValidator:
    """FastAPI dependency to get JWT validator"""
    # In production, this would load config from environment/settings
    config = JWTEnvironmentConfigs.development()
    return JWTValidator(config)


async def validate_jwt_token(
    credentials: Optional[HTTPAuthorizationCredentials] = None,
    validator: Optional[JWTValidator] = None,
) -> SecurityContext:
    """FastAPI dependency for JWT token validation"""
    if not validator:
        validator = get_jwt_validator()

    if not credentials:
        # This handles the case where HTTPBearer(auto_error=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await validator.validate_token(credentials)

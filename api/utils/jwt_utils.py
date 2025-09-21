"""
JWT Token utilities for FamilyOS authentication.

Provides JWT token generation, validation, and management for secure API authentication.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    import jwt

    HAS_JWT = True
except ImportError:
    HAS_JWT = False

from ..utils.uuid_generator import new_session_id


class JWTTokenManager:
    """Manages JWT token creation, validation, and refresh for FamilyOS."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """
        Initialize JWT token manager.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT signing algorithm (default: HS256)
        """
        if not HAS_JWT:
            raise ImportError(
                "PyJWT library not available. Install with: pip install PyJWT"
            )

        self.secret_key = secret_key
        self.algorithm = algorithm
        self.default_expiry = timedelta(hours=24)  # 24 hour default
        self.refresh_expiry = timedelta(days=7)  # 7 day refresh token

    def create_access_token(
        self,
        user_id: str,
        username: Optional[str] = None,
        device_id: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        trust_level: str = "green",
        space_access: Optional[List[str]] = None,
        custom_claims: Optional[Dict[str, Any]] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create an access token with user claims.

        Args:
            user_id: User identifier
            username: Optional username
            device_id: Device identifier
            capabilities: List of user capabilities
            trust_level: Security trust level
            space_access: List of accessible spaces
            custom_claims: Additional custom claims
            expires_delta: Custom expiration time

        Returns:
            str: Signed JWT token
        """
        now = datetime.now(timezone.utc)
        expires = now + (expires_delta or self.default_expiry)

        # Standard JWT claims
        payload = {
            "iss": "familyos-api",  # Issuer
            "sub": user_id,  # Subject (user ID)
            "aud": "familyos-clients",  # Audience
            "iat": int(now.timestamp()),  # Issued at
            "exp": int(expires.timestamp()),  # Expiration
            "jti": new_session_id(),  # JWT ID
        }

        # FamilyOS specific claims
        familyos_claims = {
            "user_id": user_id,
            "device_id": device_id,
            "trust_level": trust_level,
            "token_type": "access",
        }

        if username:
            familyos_claims["username"] = username
        if capabilities:
            familyos_claims["capabilities"] = capabilities
        if space_access:
            familyos_claims["space_access"] = space_access
        if custom_claims:
            familyos_claims.update(custom_claims)

        payload.update(familyos_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str, device_id: str) -> str:
        """
        Create a refresh token for token renewal.

        Args:
            user_id: User identifier
            device_id: Device identifier

        Returns:
            str: Signed refresh JWT token
        """
        now = datetime.now(timezone.utc)
        expires = now + self.refresh_expiry

        payload = {
            "iss": "familyos-api",
            "sub": user_id,
            "aud": "familyos-clients",
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "jti": new_session_id(),
            "user_id": user_id,
            "device_id": device_id,
            "token_type": "refresh",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate and decode a JWT token.

        Args:
            token: JWT token to validate

        Returns:
            dict: Decoded token payload

        Raises:
            jwt.InvalidTokenError: If token is invalid
            jwt.ExpiredSignatureError: If token is expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="familyos-clients",
                issuer="familyos-api",
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise jwt.ExpiredSignatureError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Create a new access token from a refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            str: New access token

        Raises:
            jwt.InvalidTokenError: If refresh token is invalid
        """
        payload = self.validate_token(refresh_token)

        if payload.get("token_type") != "refresh":
            raise jwt.InvalidTokenError("Token is not a refresh token")

        # Create new access token with same user info
        return self.create_access_token(
            user_id=payload["user_id"], device_id=payload["device_id"]
        )

    def decode_token_unsafe(self, token: str) -> Dict[str, Any]:
        """
        Decode token without validation (for debugging).

        Args:
            token: JWT token to decode

        Returns:
            dict: Decoded token payload
        """
        return jwt.decode(token, options={"verify_signature": False})

    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired without full validation.

        Args:
            token: JWT token to check

        Returns:
            bool: True if expired
        """
        try:
            payload = self.decode_token_unsafe(token)
            exp = payload.get("exp")
            if exp:
                return datetime.now(timezone.utc).timestamp() > exp
            return False
        except Exception:
            return True


class DevJWTHelper:
    """Helper for creating development/demo JWT tokens."""

    def __init__(self, secret_key: str = "dev-secret-key-change-in-production"):
        """Initialize with development secret key."""
        self.jwt_manager = JWTTokenManager(secret_key)

    def create_dev_user_token(
        self,
        username: str,
        capabilities: Optional[List[str]] = None,
        trust_level: str = "green",
    ) -> Dict[str, str]:
        """
        Create development tokens for a user.

        Args:
            username: Username for the token
            capabilities: User capabilities
            trust_level: Security trust level

        Returns:
            dict: Access and refresh tokens
        """
        from ..utils.uuid_generator import new_device_id, username_to_uuid

        user_id = username_to_uuid(username)
        device_id = new_device_id("dev")

        access_token = self.jwt_manager.create_access_token(
            user_id=user_id,
            username=username,
            device_id=device_id,
            capabilities=capabilities or ["WRITE", "RECALL"],
            trust_level=trust_level,
            space_access=[f"personal:{user_id}", "shared:family"],
        )

        refresh_token = self.jwt_manager.create_refresh_token(user_id, device_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "user_id": user_id,
            "username": username,
            "device_id": device_id,
        }

    def create_admin_token(self) -> Dict[str, str]:
        """Create admin token with all capabilities."""
        return self.create_dev_user_token(
            username="admin",
            capabilities=["WRITE", "RECALL", "PROJECT", "SCHEDULE"],
            trust_level="green",
        )

    def create_guest_token(self) -> Dict[str, str]:
        """Create guest token with limited capabilities."""
        return self.create_dev_user_token(
            username="guest", capabilities=["RECALL"], trust_level="amber"
        )


# Convenience functions for common use cases
def create_dev_jwt_tokens(username: str = "dev_user") -> Dict[str, str]:
    """Create development JWT tokens for testing."""
    helper = DevJWTHelper()
    return helper.create_dev_user_token(username)


def validate_jwt_token(
    token: str, secret_key: str = "dev-secret-key-change-in-production"
) -> Dict[str, Any]:
    """Validate a JWT token with development secret."""
    manager = JWTTokenManager(secret_key)
    return manager.validate_token(token)


def decode_jwt_unsafe(token: str) -> Dict[str, Any]:
    """Decode JWT token without validation (debugging)."""
    if not HAS_JWT:
        raise ImportError("PyJWT library not available")
    return jwt.decode(token, options={"verify_signature": False})


if __name__ == "__main__":
    # Demo JWT token creation
    if HAS_JWT:
        print("=== FamilyOS JWT Token Demo ===")

        helper = DevJWTHelper()

        # Create tokens for different users
        admin_tokens = helper.create_admin_token()
        user_tokens = helper.create_dev_user_token("john_doe")
        guest_tokens = helper.create_guest_token()

        print(f"Admin Access Token: {admin_tokens['access_token'][:50]}...")
        print(f"User Access Token: {user_tokens['access_token'][:50]}...")
        print(f"Guest Access Token: {guest_tokens['access_token'][:50]}...")

        # Validate a token
        try:
            decoded = helper.jwt_manager.validate_token(user_tokens["access_token"])
            print(f"Token validation successful for user: {decoded.get('username')}")
        except Exception as e:
            print(f"Token validation failed: {e}")
    else:
        print("PyJWT not available. Install with: pip install PyJWT")

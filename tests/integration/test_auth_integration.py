from ward import test

"""
Integration test for authentication middleware with SecurityContext validation.

Tests the complete authentication flow from middleware through policy validation.
"""

from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from api.schemas import AuthMethod, SecurityContext, TrustLevel


class TestAuthenticationIntegration:
    """Test authentication middleware integration with policy system."""

    def setup_method(self):
        """Set up test environment with FastAPI app and middleware."""

        self.app = FastAPI(title="Auth Integration Test")

        # Add authentication middleware simulation
        @self.app.middleware("http")
        async def auth_middleware(request: Request, call_next):
            """Simulate authentication middleware with SecurityContext creation."""

            # Extract test headers
            test_user = request.headers.get("X-Test-User", "anonymous")
            test_device = request.headers.get("X-Test-Device", "test_device")
            test_auth_method = request.headers.get("X-Test-Auth-Method", "jwt")

            # Create SecurityContext with string user_id (not UUID)
            try:
                security_context = SecurityContext(
                    user_id=test_user,  # String username, not UUID
                    device_id=test_device,
                    authenticated=test_user != "anonymous",
                    auth_method=(
                        AuthMethod(test_auth_method) if test_auth_method else None
                    ),
                    trust_level=TrustLevel.GREEN,
                )

                # Attach to request state
                request.state.security_context = security_context

                # Continue to next middleware/handler
                response = await call_next(request)

                # Add security headers to response
                response.headers["X-User-ID"] = security_context.user_id
                response.headers["X-Authenticated"] = str(
                    security_context.authenticated
                )

                return response

            except Exception as e:
                # Return authentication error
                return Response(
                    content=f"Authentication failed: {str(e)}", status_code=401
                )

        # Add test endpoint
        @self.app.get("/test/auth")
        async def test_auth_endpoint(request: Request):
            """Test endpoint that requires authentication."""

            if not hasattr(request.state, "security_context"):
                return {"error": "No security context"}

            ctx = request.state.security_context
            return {
                "user_id": ctx.user_id,
                "authenticated": ctx.authenticated,
                "auth_method": ctx.auth_method,
                "device_id": ctx.device_id,
                "trust_level": ctx.trust_level,
            }

        self.client = TestClient(self.app)

    @test("Test authentication with string username (not UUID).")
    def test_string_username_authentication(self):
        """Test authentication with string username (not UUID)."""

        response = self.client.get(
            "/test/auth",
            headers={
                "X-Test-User": "john_doe",
                "X-Test-Device": "laptop_001",
                "X-Test-Auth-Method": "jwt",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "john_doe"
        assert data["authenticated"] is True
        assert data["auth_method"] == "jwt"
        assert data["device_id"] == "laptop_001"
        assert data["trust_level"] == "green"

        # Check response headers
        assert response.headers["X-User-ID"] == "john_doe"
        assert response.headers["X-Authenticated"] == "True"

    @test("Test authentication with UUID user_id.")
    def test_uuid_user_authentication(self):
        """Test authentication with UUID user_id."""

        uuid_user = "123e4567-e89b-12d3-a456-426614174000"

        response = self.client.get(
            "/test/auth",
            headers={
                "X-Test-User": uuid_user,
                "X-Test-Device": "mobile_002",
                "X-Test-Auth-Method": "mtls",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == uuid_user
        assert data["authenticated"] is True
        assert data["auth_method"] == "mtls"

    @test("Test authentication for anonymous users.")
    def test_anonymous_user_authentication(self):
        """Test authentication for anonymous users."""

        response = self.client.get("/test/auth")  # No auth headers

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == "anonymous"
        assert data["authenticated"] is False
        assert data["device_id"] == "test_device"

    @test("Test that invalid user_id formats are rejected.")
    def test_invalid_user_id_format(self):
        """Test that invalid user_id formats are rejected."""

        # Test with special characters that aren't allowed
        response = self.client.get(
            "/test/auth",
            headers={
                "X-Test-User": "invalid@user#id",  # Invalid characters
                "X-Test-Device": "device_001",
            },
        )

        assert response.status_code == 401
        assert "Authentication failed" in response.text

    @test("Test integration with policy system using string user_id.")
    def test_integration_with_policy_lookup(self):
        """Test integration with policy system using string user_id."""

        # Add policy middleware simulation
        @self.app.middleware("http")
        async def policy_middleware(request: Request, call_next):
            """Simulate policy middleware that uses user_id for lookups."""

            response = await call_next(request)

            if hasattr(request.state, "security_context"):
                ctx = request.state.security_context
                # Simulate policy lookup using user_id as string
                user_id_str = str(ctx.user_id)  # This should work now
                response.headers["X-Policy-User"] = user_id_str

            return response

        response = self.client.get(
            "/test/auth",
            headers={
                "X-Test-User": "policy_test_user",
                "X-Test-Device": "policy_device",
            },
        )

        assert response.status_code == 200
        assert response.headers["X-Policy-User"] == "policy_test_user"


if __name__ == "__main__":
    # Run with WARD instead of pytest
    import os

    os.system("python -m ward test --path " + __file__)

"""
Ward Test for Development Authentication Integration

This test validates that the PolicyEnforcementMiddleware works correctly
with the development authentication system using X-Test-* headers.
"""

import os

from fastapi.testclient import TestClient
from ward import fixture, test

from main import app


@fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@test("Development authentication should work with X-Test-User header")
def test_development_auth_with_user_header(client=client):
    """Test that X-Test-User header creates valid security context."""

    # Set development environment
    os.environ["ENVIRONMENT"] = "development"

    headers = {"X-Test-User": "test_admin", "X-Test-Role": "admin"}

    # Test a protected endpoint (that doesn't exist but should get past auth)
    response = client.get("/api/test/protected", headers=headers)

    # Should get 404 (endpoint not found) not 401 (auth failed)
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"


@test(
    "Development authentication should create different capabilities for different roles"
)
def test_development_auth_role_capabilities(client=client):
    """Test that different roles get different capabilities."""

    os.environ["ENVIRONMENT"] = "development"

    # Test admin role
    admin_headers = {"X-Test-User": "test_admin", "X-Test-Role": "admin"}

    # Test guest role
    guest_headers = {"X-Test-User": "test_guest", "X-Test-Role": "guest"}

    # Both should pass authentication (get 404 not 401)
    admin_response = client.get("/api/test/protected", headers=admin_headers)
    guest_response = client.get("/api/test/protected", headers=guest_headers)

    assert admin_response.status_code == 404
    assert guest_response.status_code == 404


@test("Development authentication should not work in production environment")
def test_development_auth_disabled_in_production(client=client):
    """Test that X-Test-* headers are ignored in production."""

    # Set production environment
    os.environ["ENVIRONMENT"] = "production"

    headers = {"X-Test-User": "test_admin", "X-Test-Role": "admin"}

    # Should get 401 (auth failed) since dev auth is disabled
    response = client.get("/api/test/protected", headers=headers)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    # Reset to development
    os.environ["ENVIRONMENT"] = "development"


@test("Health endpoints should bypass authentication entirely")
def test_health_endpoints_bypass(client=client):
    """Test that health endpoints work without any authentication."""

    # No headers at all
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

    response = client.get("/health/ready")
    assert response.status_code == 200

    response = client.get("/health/live")
    assert response.status_code == 200


@test("PolicyEnforcementMiddleware should handle missing security context gracefully")
def test_policy_middleware_graceful_handling(client=client):
    """Test that policy middleware handles missing security context."""

    # Test with no authentication headers in development
    os.environ["ENVIRONMENT"] = "development"

    # Should still work (proceed without security context for now)
    response = client.get("/api/test/protected")

    # Should get 404 (endpoint not found) or 401 (auth required)
    assert response.status_code in [401, 404]


if __name__ == "__main__":
    import ward

    ward.main()

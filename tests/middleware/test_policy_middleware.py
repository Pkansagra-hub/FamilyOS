"""
PolicyEnforcementMiddleware Tests - Sub-issue #8.2

Ward-based tests for PolicyEnforcementMiddleware implementation.
Tests capability-based authorization, policy enforcement, and middleware chain integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from ward import expect, fixture, test

from api.middleware.middleware_integration import setup_middleware_chain
from api.middleware.policy import PolicyEnforcementMiddleware
from api.schemas import AuthMethod, Capability, SecurityContext, TrustLevel
from main import app
from policy.decision import PolicyDecision
from policy.service import initialize_policy_service


@fixture
async def policy_service():
    """Initialize policy service for testing."""
    return initialize_policy_service()


@fixture
def mock_security_context():
    """Create a mock security context for testing."""
    from datetime import datetime, timezone
    from uuid import uuid4

    return SecurityContext(
        user_id=f"test_user_{uuid4().hex[:8]}",
        device_id=f"test_device_{uuid4().hex[:8]}",
        authenticated=True,
        auth_method=AuthMethod.JWT,
        capabilities=[Capability.WRITE, Capability.RECALL],
        mls_group="test_family",
        trust_level=TrustLevel.GREEN,
        created_at=datetime.now(timezone.utc),
        session_id=f"test_session_{uuid4().hex[:8]}",
        network_address="127.0.0.1",
    )


@fixture
def test_app():
    """Create a test FastAPI app with middleware."""
    app = FastAPI()

    # Add a test route
    @app.get("/test/protected")
    async def protected_route():
        return {"message": "success"}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


@test("PolicyEnforcementMiddleware initializes correctly")
async def test_middleware_init(policy_service):
    """Test that PolicyEnforcementMiddleware initializes with policy service."""
    middleware = PolicyEnforcementMiddleware(None, policy_service)

    expect(middleware.policy_service).equals(policy_service)
    expect(middleware).is_not(None)


@test("Health endpoints bypass policy enforcement")
async def test_health_bypass():
    """Test that health endpoints bypass policy enforcement."""
    client = TestClient(app)

    response = client.get("/health")
    expect(response.status_code).equals(200)
    expect(response.json()).contains("status")


@test("Unauthenticated requests are handled gracefully")
async def test_unauthenticated_request(test_app, policy_service):
    """Test handling of requests without security context."""
    middleware = PolicyEnforcementMiddleware(None, policy_service)
    test_app.add_middleware(type(middleware), policy_service=policy_service)

    client = TestClient(test_app)

    # This should proceed without authentication for development
    response = client.get("/test/protected")
    # Expecting 404 since the route exists but no real endpoint implementation
    expect(response.status_code).is_in([200, 404])


@test("Authenticated requests with sufficient capabilities succeed")
async def test_authorized_request(test_app, policy_service, mock_security_context):
    """Test that requests with proper capabilities are allowed."""
    middleware = PolicyEnforcementMiddleware(None, policy_service)

    # Mock the policy evaluation to return success
    with patch.object(middleware, "_evaluate_policy") as mock_eval:
        mock_eval.return_value = PolicyDecision(
            allowed=True, reason="User has required capabilities", obligations=[]
        )

        # Mock request with security context

        mock_request = MagicMock()
        mock_request.url.path = "/test/protected"
        mock_request.method = "GET"
        mock_request.state.security_context = mock_security_context

        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        # Call the middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        expect(mock_eval.called).is_(True)
        expect(mock_call_next.called).is_(True)


@test("Requests with insufficient capabilities are denied")
async def test_unauthorized_request(test_app, policy_service, mock_security_context):
    """Test that requests without proper capabilities are denied."""
    middleware = PolicyEnforcementMiddleware(None, policy_service)

    # Mock the policy evaluation to return denial
    with patch.object(middleware, "_evaluate_policy") as mock_eval:
        mock_eval.return_value = PolicyDecision(
            allowed=False, reason="Insufficient capabilities", obligations=[]
        )

        # Mock request with security context
        mock_request = MagicMock()
        mock_request.url.path = "/test/admin"
        mock_request.method = "POST"
        mock_request.state.security_context = mock_security_context

        mock_call_next = AsyncMock()

        # Call the middleware - should raise HTTPException
        from fastapi import HTTPException

        try:
            await middleware.dispatch(mock_request, mock_call_next)
            expect(False).is_(True)  # Should not reach here
        except HTTPException as e:
            expect(e.status_code).equals(403)
            expect(mock_call_next.called).is_(False)


@test("Policy obligations are applied correctly")
async def test_policy_obligations(test_app, policy_service, mock_security_context):
    """Test that policy obligations are properly applied."""
    middleware = PolicyEnforcementMiddleware(None, policy_service)

    # Mock the policy evaluation to return success with obligations
    from policy.decision import Obligation, ObligationType

    test_obligation = Obligation(
        type=ObligationType.AUDIT,
        details={"action": "memory_access", "resource": "test"},
    )

    with patch.object(middleware, "_evaluate_policy") as mock_eval, patch.object(
        middleware, "_apply_obligations"
    ) as mock_apply:

        mock_eval.return_value = PolicyDecision(
            allowed=True,
            reason="Allowed with audit requirement",
            obligations=[test_obligation],
        )

        mock_request = MagicMock()
        mock_request.url.path = "/test/memory"
        mock_request.method = "GET"
        mock_request.state.security_context = mock_security_context

        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        await middleware.dispatch(mock_request, mock_call_next)

        expect(mock_apply.called).is_(True)
        # Check that the obligation was passed to apply method
        args, kwargs = mock_apply.call_args
        expect(args[1]).contains(test_obligation)


@test("Middleware chain integration works correctly")
async def test_middleware_chain_integration():
    """Test that PolicyEnforcementMiddleware integrates properly with the chain."""
    test_app = FastAPI()

    # Initialize policy service
    policy_service = initialize_policy_service()

    # Setup middleware chain
    setup_middleware_chain(test_app, policy_service)

    # Check that middleware was added to the app
    expect(len(test_app.middleware_stack.middleware)).is_greater_than(0)

    # Test with client
    client = TestClient(test_app)

    # Health endpoint should work
    response = client.get("/health")
    expect(response.status_code).equals(200)


@test("Policy service error handling")
async def test_policy_service_error(test_app, policy_service, mock_security_context):
    """Test error handling when policy service fails."""
    middleware = PolicyEnforcementMiddleware(None, policy_service)

    # Mock the policy evaluation to raise an exception
    with patch.object(middleware, "_evaluate_policy") as mock_eval:
        mock_eval.side_effect = Exception("Policy service error")

        mock_request = MagicMock()
        mock_request.url.path = "/test/protected"
        mock_request.method = "GET"
        mock_request.state.security_context = mock_security_context

        mock_call_next = AsyncMock()

        # Should raise HTTPException with 500 status
        from fastapi import HTTPException

        try:
            await middleware.dispatch(mock_request, mock_call_next)
            expect(False).is_(True)  # Should not reach here
        except HTTPException as e:
            expect(e.status_code).equals(500)
            expect(e.detail).contains("Policy evaluation failed")


if __name__ == "__main__":
    import subprocess
    import sys

    # Run ward tests
    result = subprocess.run([sys.executable, "-m", "ward"], cwd=".")
    sys.exit(result.returncode)

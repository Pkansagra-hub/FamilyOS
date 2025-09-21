"""
Test SecurityContext Integration - Sub-issue #8.1

Simple test to verify PolicyService and SecurityContextBridge integration.
"""

import tempfile
from uuid import uuid4

from api.schemas import Capability, SecurityContext, TrustLevel
from policy.rbac import Binding, RoleDef
from policy.service import PolicyService


def test_security_context_integration():
    """Test basic SecurityContext to policy conversion."""
    # Create temporary storage
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize PolicyService
        service = PolicyService(storage_dir=temp_dir)

        # Set up test roles
        service.rbac.define_role(
            RoleDef("admin", ["memory.read", "memory.write", "privacy.redact"])
        )
        service.rbac.define_role(RoleDef("member", ["memory.read", "memory.write"]))
        test_user_id = str(uuid4())
        service.rbac.bind(Binding(test_user_id, "member", "shared:household"))

        # Create test SecurityContext
        security_ctx = SecurityContext(
            user_id=test_user_id,
            device_id="test_device_123",
            authenticated=True,
            auth_method=None,  # Optional field
            capabilities=[Capability.WRITE, Capability.RECALL],
            mls_group="family",
            trust_level=TrustLevel.GREEN,
        )

        # Test conversion to ABAC context
        abac_ctx = service.security_bridge.to_abac_context(security_ctx)

        # Verify conversion
        assert abac_ctx.actor.actor_id == test_user_id
        assert abac_ctx.device.device_id == "test_device_123"
        assert abac_ctx.device.trust == "green"

        print("✅ SecurityContext integration test passed!")
        print(f"   Actor ID: {abac_ctx.actor.actor_id}")
        print(f"   Device ID: {abac_ctx.device.device_id}")
        print(f"   Trust Level: {abac_ctx.device.trust}")


if __name__ == "__main__":
    test_security_context_integration()

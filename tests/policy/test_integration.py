"""
Integration Tests for Policy Testing Framework - Sub-issue #8.3

Tests the complete policy testing framework including:
- PolicyTestHarness functionality
- RBAC and ABAC scenario building
- Policy decision assertions
- End-to-end policy evaluation

Uses Ward testing framework as specified.
"""

import logging

from ward import fixture, test

from policy.decision import Obligation, PolicyDecision
from policy.service import initialize_policy_service
from tests.policy.test_framework import (
    ABACScenarioBuilder,
    MockSecurityContextFactory,
    PolicyDecisionAssertions,
    PolicyTestHarness,
    RBACScenarioBuilder,
    TestRole,
)

logger = logging.getLogger(__name__)


@fixture
def policy_service():
    """Initialize policy service for testing."""
    return initialize_policy_service()


@fixture
def test_harness(policy_service=policy_service):
    """Create PolicyTestHarness fixture."""
    return PolicyTestHarness(policy_service)


@fixture
def context_factory():
    """Create MockSecurityContextFactory fixture."""
    return MockSecurityContextFactory()


@test("MockSecurityContextFactory should create valid security contexts")
def test_security_context_factory(context_factory=context_factory):
    """Test that the factory creates valid SecurityContext objects."""

    # Test admin context
    admin_context = context_factory.create_context(TestRole.ADMIN)
    assert admin_context.authenticated is True
    assert admin_context.user_id is not None
    assert admin_context.device_id is not None
    assert len(admin_context.capabilities) == 4  # WRITE, RECALL, SCHEDULE, PROJECT

    # Test guest context
    guest_context = context_factory.create_context(TestRole.GUEST)
    assert guest_context.authenticated is True
    assert len(guest_context.capabilities) == 0  # No capabilities for guest


@test("MockSecurityContextFactory should create batch contexts")
def test_batch_context_creation(context_factory=context_factory):
    """Test batch creation of security contexts."""

    roles = [TestRole.ADMIN, TestRole.MEMBER, TestRole.GUEST]
    contexts = context_factory.create_batch_contexts(roles)

    assert len(contexts) == 3
    assert TestRole.ADMIN in contexts
    assert TestRole.MEMBER in contexts
    assert TestRole.GUEST in contexts

    # Verify different capabilities per role
    assert len(contexts[TestRole.ADMIN].capabilities) > len(
        contexts[TestRole.MEMBER].capabilities
    )
    assert len(contexts[TestRole.MEMBER].capabilities) > len(
        contexts[TestRole.GUEST].capabilities
    )


@test("MockSecurityContextFactory should create cross-group contexts")
def test_cross_group_contexts(context_factory=context_factory):
    """Test creation of contexts across different MLS groups."""

    groups = ["family_a", "family_b", "family_c"]
    contexts = context_factory.create_cross_group_contexts(TestRole.MEMBER, groups)

    assert len(contexts) == 3
    for group in groups:
        assert group in contexts
        assert contexts[group].mls_group == group


@test("RBACScenarioBuilder should build memory access scenarios")
def test_rbac_memory_scenarios(context_factory=context_factory):
    """Test RBAC scenario building for memory access."""

    builder = RBACScenarioBuilder(context_factory)
    scenarios = builder.build_memory_access_scenarios()

    # Should have scenarios for all roles and operations
    expected_scenarios = [
        "memory_write_admin",
        "memory_write_member",
        "memory_write_guest",
        "memory_recall_admin",
        "memory_recall_member",
        "memory_recall_guest",
        "admin_access_admin",
        "admin_access_member",
        "admin_access_guest",
    ]

    for scenario in expected_scenarios:
        assert scenario in scenarios

    # Verify admin has write access
    admin_write = scenarios["memory_write_admin"]
    assert admin_write[2] is True  # Expected result should be True

    # Verify guest doesn't have write access
    guest_write = scenarios["memory_write_guest"]
    assert guest_write[2] is False  # Expected result should be False


@test("RBACScenarioBuilder should build capability scenarios")
def test_rbac_capability_scenarios(context_factory=context_factory):
    """Test RBAC scenario building for capabilities."""

    builder = RBACScenarioBuilder(context_factory)
    scenarios = builder.build_capability_scenarios()

    # Should have capability scenarios for different roles
    assert "capability_write_admin" in scenarios
    assert "capability_recall_child" in scenarios
    assert "capability_schedule_guest" in scenarios

    # Verify admin has write capability
    admin_write = scenarios["capability_write_admin"]
    assert admin_write[2] is True

    # Verify guest doesn't have schedule capability
    guest_schedule = scenarios["capability_schedule_guest"]
    assert guest_schedule[2] is False


@test("ABACScenarioBuilder should build cross-space scenarios")
def test_abac_cross_space_scenarios(context_factory=context_factory):
    """Test ABAC scenario building for cross-space access."""

    builder = ABACScenarioBuilder(context_factory)
    scenarios = builder.build_cross_space_scenarios()

    # Should have cross-space scenarios
    assert "same_group_access" in scenarios
    assert "cross_group_access" in scenarios
    assert "admin_cross_group" in scenarios

    # Verify same group access is allowed
    same_group = scenarios["same_group_access"]
    assert same_group[3] is True  # Expected result

    # Verify cross group access is denied
    cross_group = scenarios["cross_group_access"]
    assert cross_group[3] is False  # Expected result


@test("ABACScenarioBuilder should build trust level scenarios")
def test_abac_trust_level_scenarios(context_factory=context_factory):
    """Test ABAC scenario building for trust levels."""

    builder = ABACScenarioBuilder(context_factory)
    scenarios = builder.build_trust_level_scenarios()

    # Should have trust level scenarios
    assert "trust_green_admin" in scenarios
    assert "trust_amber_child" in scenarios
    assert "trust_red_guest" in scenarios

    # Verify admin can access GREEN level
    admin_green = scenarios["trust_green_admin"]
    assert admin_green[2] is True

    # Verify no one can access RED level by default
    guest_red = scenarios["trust_red_guest"]
    assert guest_red[2] is False


@test("PolicyDecisionAssertions should validate policy decisions")
def test_policy_decision_assertions():
    """Test the policy decision assertion helpers."""

    assertions = PolicyDecisionAssertions()

    # Test allowed decision
    allowed_decision = PolicyDecision(
        decision="ALLOW", reasons=["Access granted"], obligations=Obligation()
    )

    # Should not raise exception
    assertions.assert_allowed(allowed_decision)

    # Test denied decision
    denied_decision = PolicyDecision(
        decision="DENY", reasons=["Missing capability: WRITE"], obligations=Obligation()
    )

    # Should not raise exception
    assertions.assert_denied(denied_decision)

    # Test reason contains
    assertions.assert_reason_contains(denied_decision, "capability")
    assertions.assert_reason_contains(denied_decision, "WRITE")


@test("PolicyTestHarness should run RBAC test suite")
async def test_harness_rbac_suite(test_harness=test_harness):
    """Test that the PolicyTestHarness can run RBAC tests."""

    results = await test_harness.run_rbac_test_suite()

    # Should have test results
    assert len(results) > 0

    # Should have some passing tests
    passed_tests = sum(results.values())
    assert passed_tests > 0

    # Log results for debugging
    logger.info(f"RBAC test results: {passed_tests}/{len(results)} passed")


@test("PolicyTestHarness should run ABAC test suite")
async def test_harness_abac_suite(test_harness=test_harness):
    """Test that the PolicyTestHarness can run ABAC tests."""

    results = await test_harness.run_abac_test_suite()

    # Should have test results
    assert len(results) > 0

    # Should have some passing tests
    passed_tests = sum(results.values())
    assert passed_tests > 0

    # Log results for debugging
    logger.info(f"ABAC test results: {passed_tests}/{len(results)} passed")


@test("PolicyTestHarness should run capability test suite")
async def test_harness_capability_suite(test_harness=test_harness):
    """Test that the PolicyTestHarness can run capability tests."""

    results = await test_harness.run_capability_test_suite()

    # Should have test results
    assert len(results) > 0

    # Should have some passing tests
    passed_tests = sum(results.values())
    assert passed_tests > 0

    # Log results for debugging
    logger.info(f"Capability test results: {passed_tests}/{len(results)} passed")


@test("PolicyTestHarness should run full test suite")
async def test_harness_full_suite(test_harness=test_harness):
    """Test that the PolicyTestHarness can run the complete test suite."""

    results = await test_harness.run_full_test_suite()

    # Should have all test suites
    assert "rbac" in results
    assert "abac" in results
    assert "capabilities" in results

    # Each suite should have results
    for suite_name, suite_results in results.items():
        assert len(suite_results) > 0
        logger.info(
            f"{suite_name.upper()} suite: {sum(suite_results.values())}/{len(suite_results)} passed"
        )

    # Should have overall passing tests
    total_tests = sum(len(suite_results) for suite_results in results.values())
    total_passed = sum(
        sum(suite_results.values()) for suite_results in results.values()
    )

    assert total_passed > 0
    assert total_tests > 0

    logger.info(f"Full test suite: {total_passed}/{total_tests} passed")


@test("PolicyTestHarness should track failed tests")
async def test_harness_failure_tracking(test_harness=test_harness):
    """Test that the PolicyTestHarness tracks failed tests."""

    # Run a test suite that may have failures
    await test_harness.run_full_test_suite()

    # Should track failed tests (may be empty if all pass)
    assert isinstance(test_harness.failed_tests, list)

    # Log failed tests for debugging
    if test_harness.failed_tests:
        logger.warning(f"Failed tests: {test_harness.failed_tests}")
    else:
        logger.info("All policy tests passed!")


if __name__ == "__main__":
    import ward

    ward.main()

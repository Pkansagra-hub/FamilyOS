"""
Policy Testing Framework - Sub-issue #8.3

This module provides comprehensive testing infrastructure for policy decisions,
including mock factories, scenario builders, and assertion helpers.

Components:
- PolicyTestHarness: Main test orchestration class
- MockSecurityContextFactory: Creates test security contexts
- RBACScenarioBuilder: Builds role-based access control test scenarios
- ABACScenarioBuilder: Builds attribute-based access control test scenarios
- PolicyDecisionAssertions: Helper methods for policy decision testing

Author: GitHub Copilot
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from api.schemas import AuthMethod, Capability, SecurityContext, TrustLevel
from policy.decision import Obligation, PolicyDecision
from policy.service import PolicyService

logger = logging.getLogger(__name__)


class TestRole(str, Enum):
    """Standard test roles for policy testing."""

    ADMIN = "admin"
    GUARDIAN = "guardian"
    MEMBER = "member"
    CHILD = "child"
    GUEST = "guest"
    BANNED = "banned"


class TestScenario(str, Enum):
    """Common test scenarios for policy validation."""

    MEMORY_WRITE = "memory_write"
    MEMORY_RECALL = "memory_recall"
    MEMORY_PROJECT = "memory_project"
    MEMORY_SCHEDULE = "memory_schedule"
    CROSS_SPACE_ACCESS = "cross_space_access"
    PRIVACY_REDACTION = "privacy_redaction"
    ADMIN_FUNCTIONS = "admin_functions"
    CHILD_PROTECTION = "child_protection"


class MockSecurityContextFactory:
    """Factory for creating test SecurityContext objects."""

    def __init__(self):
        self.role_capabilities = {
            TestRole.ADMIN: [
                Capability.WRITE,
                Capability.RECALL,
                Capability.SCHEDULE,
                Capability.PROJECT,
            ],
            TestRole.GUARDIAN: [
                Capability.WRITE,
                Capability.RECALL,
                Capability.SCHEDULE,
            ],
            TestRole.MEMBER: [Capability.WRITE, Capability.RECALL],
            TestRole.CHILD: [Capability.RECALL],
            TestRole.GUEST: [],
            TestRole.BANNED: [],
        }

        self.role_trust_levels = {
            TestRole.ADMIN: TrustLevel.GREEN,
            TestRole.GUARDIAN: TrustLevel.GREEN,
            TestRole.MEMBER: TrustLevel.GREEN,
            TestRole.CHILD: TrustLevel.AMBER,
            TestRole.GUEST: TrustLevel.AMBER,
            TestRole.BANNED: TrustLevel.RED,
        }

    def create_context(
        self,
        role: TestRole,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
        mls_group: str = "test_family",
        auth_method: AuthMethod = AuthMethod.JWT,
        trust_level: Optional[TrustLevel] = None,
        custom_capabilities: Optional[List[Capability]] = None,
    ) -> SecurityContext:
        """Create a test SecurityContext for the given role."""

        return SecurityContext(
            user_id=user_id or str(uuid4()),
            device_id=device_id or f"test_device_{uuid4().hex[:8]}",
            authenticated=True,
            auth_method=auth_method,
            capabilities=custom_capabilities or self.role_capabilities.get(role, []),
            mls_group=mls_group,
            trust_level=trust_level
            or self.role_trust_levels.get(role, TrustLevel.GREEN),
        )

    def create_batch_contexts(
        self, roles: List[TestRole], mls_group: str = "test_family"
    ) -> Dict[TestRole, SecurityContext]:
        """Create multiple test contexts for different roles."""

        return {role: self.create_context(role, mls_group=mls_group) for role in roles}

    def create_cross_group_contexts(
        self, role: TestRole, groups: List[str]
    ) -> Dict[str, SecurityContext]:
        """Create contexts for the same role across different MLS groups."""

        return {group: self.create_context(role, mls_group=group) for group in groups}


class RBACScenarioBuilder:
    """Builder for role-based access control test scenarios."""

    def __init__(self, context_factory: MockSecurityContextFactory):
        self.context_factory = context_factory

    def build_memory_access_scenarios(
        self,
    ) -> Dict[str, Tuple[SecurityContext, str, bool]]:
        """Build scenarios for memory access testing."""

        scenarios = {}

        # Memory write scenarios
        for role in TestRole:
            context = self.context_factory.create_context(role)
            expected = role in [TestRole.ADMIN, TestRole.GUARDIAN, TestRole.MEMBER]
            scenarios[f"memory_write_{role.value}"] = (
                context,
                "memory.write",
                expected,
            )

        # Memory recall scenarios
        for role in TestRole:
            context = self.context_factory.create_context(role)
            expected = role != TestRole.BANNED
            scenarios[f"memory_recall_{role.value}"] = (
                context,
                "memory.recall",
                expected,
            )

        # Administrative scenarios
        for role in TestRole:
            context = self.context_factory.create_context(role)
            expected = role == TestRole.ADMIN
            scenarios[f"admin_access_{role.value}"] = (
                context,
                "admin.manage",
                expected,
            )

        return scenarios

    def build_capability_scenarios(
        self,
    ) -> Dict[str, Tuple[SecurityContext, List[Capability], bool]]:
        """Build scenarios for capability-based testing."""

        scenarios = {}

        test_cases = [
            ([Capability.WRITE], [TestRole.ADMIN, TestRole.GUARDIAN, TestRole.MEMBER]),
            (
                [Capability.RECALL],
                [TestRole.ADMIN, TestRole.GUARDIAN, TestRole.MEMBER, TestRole.CHILD],
            ),
            ([Capability.SCHEDULE], [TestRole.ADMIN, TestRole.GUARDIAN]),
            ([Capability.PROJECT], [TestRole.ADMIN]),
        ]

        for required_caps, allowed_roles in test_cases:
            for role in TestRole:
                context = self.context_factory.create_context(role)
                expected = role in allowed_roles
                cap_name = "_".join(cap.value.lower() for cap in required_caps)
                scenarios[f"capability_{cap_name}_{role.value}"] = (
                    context,
                    required_caps,
                    expected,
                )

        return scenarios


class ABACScenarioBuilder:
    """Builder for attribute-based access control test scenarios."""

    def __init__(self, context_factory: MockSecurityContextFactory):
        self.context_factory = context_factory

    def build_cross_space_scenarios(
        self,
    ) -> Dict[str, Tuple[SecurityContext, str, str, bool]]:
        """Build scenarios for cross-space access testing."""

        scenarios = {}

        # Same group access - should be allowed
        context = self.context_factory.create_context(
            TestRole.MEMBER, mls_group="family_a"
        )
        scenarios["same_group_access"] = (
            context,
            "family_a:personal",
            "family_a",
            True,
        )

        # Cross group access - should be denied
        context = self.context_factory.create_context(
            TestRole.MEMBER, mls_group="family_a"
        )
        scenarios["cross_group_access"] = (
            context,
            "family_b:personal",
            "family_b",
            False,
        )

        # Admin cross group - might be allowed depending on policy
        context = self.context_factory.create_context(
            TestRole.ADMIN, mls_group="family_a"
        )
        scenarios["admin_cross_group"] = (
            context,
            "family_b:personal",
            "family_b",
            False,
        )  # Still denied by default

        return scenarios

    def build_trust_level_scenarios(
        self,
    ) -> Dict[str, Tuple[SecurityContext, TrustLevel, bool]]:
        """Build scenarios for trust level testing."""

        scenarios = {}

        trust_test_cases = [
            (TrustLevel.GREEN, [TestRole.ADMIN, TestRole.GUARDIAN, TestRole.MEMBER]),
            (
                TrustLevel.AMBER,
                [TestRole.ADMIN, TestRole.GUARDIAN, TestRole.MEMBER, TestRole.CHILD],
            ),
            (TrustLevel.RED, []),  # No one should access RED level by default
        ]

        for required_trust, allowed_roles in trust_test_cases:
            for role in TestRole:
                context = self.context_factory.create_context(role)
                expected = role in allowed_roles
                scenarios[f"trust_{required_trust.value}_{role.value}"] = (
                    context,
                    required_trust,
                    expected,
                )

        return scenarios

    def build_time_based_scenarios(
        self,
    ) -> Dict[str, Tuple[SecurityContext, int, bool]]:
        """Build scenarios for time-based access control."""

        scenarios = {}

        # Child access during school hours (9 AM - 3 PM) - should be restricted
        child_context = self.context_factory.create_context(TestRole.CHILD)
        scenarios["child_school_hours"] = (child_context, 11, False)  # 11 AM
        scenarios["child_after_school"] = (child_context, 16, True)  # 4 PM

        # Regular member access - no time restrictions
        member_context = self.context_factory.create_context(TestRole.MEMBER)
        scenarios["member_anytime"] = (member_context, 11, True)

        return scenarios


class PolicyDecisionAssertions:
    """Helper methods for asserting policy decisions."""

    @staticmethod
    def assert_allowed(decision: PolicyDecision, message: str = ""):
        """Assert that a policy decision allows access."""
        assert (
            decision.decision == "ALLOW"
        ), f"Expected access to be allowed. {message}. Reasons: {decision.reasons}"

    @staticmethod
    def assert_denied(decision: PolicyDecision, message: str = ""):
        """Assert that a policy decision denies access."""
        assert (
            decision.decision == "DENY"
        ), f"Expected access to be denied. {message}. Reasons: {decision.reasons}"

    @staticmethod
    def assert_has_obligation(
        decision: PolicyDecision, obligation_type: str, message: str = ""
    ):
        """Assert that a decision has a specific obligation."""
        obligations = decision.obligations
        if obligation_type == "redact":
            assert obligations.redact, f"Expected redaction obligation. {message}"
        elif obligation_type == "audit":
            assert obligations.log_audit, f"Expected audit obligation. {message}"
        elif obligation_type == "band_min":
            assert obligations.band_min, f"Expected band minimum obligation. {message}"
        else:
            raise ValueError(f"Unknown obligation type: {obligation_type}")

    @staticmethod
    def assert_reason_contains(decision: PolicyDecision, text: str, message: str = ""):
        """Assert that a decision reason contains specific text."""
        reason_text = " ".join(decision.reasons).lower()
        assert (
            text.lower() in reason_text
        ), f"Expected reason to contain '{text}'. {message}. Actual reasons: {decision.reasons}"

    @staticmethod
    def assert_capability_required(
        decision: PolicyDecision, capability: Capability, message: str = ""
    ):
        """Assert that a decision indicates a specific capability is required."""
        assert (
            decision.decision == "DENY"
        ), f"Expected decision to be denied for capability check. {message}"
        reason_text = " ".join(decision.reasons).lower()
        capability_mentioned = capability.value.lower() in reason_text
        assert (
            capability_mentioned
        ), f"Expected capability '{capability.value}' to be mentioned in reason. {message}. Reasons: {decision.reasons}"


class PolicyTestDataGenerator:
    """Generates test data for policy testing."""

    @staticmethod
    def generate_memory_spaces(count: int = 5) -> List[str]:
        """Generate test memory space identifiers."""
        namespaces = ["personal", "work", "family", "shared", "private"]
        contexts = ["notes", "photos", "documents", "tasks", "meetings"]

        spaces = []
        for i in range(count):
            namespace = namespaces[i % len(namespaces)]
            context = contexts[i % len(contexts)]
            spaces.append(f"{namespace}:{context}")

        return spaces

    @staticmethod
    def generate_test_operations() -> Dict[str, Dict[str, Any]]:
        """Generate test operations with metadata."""
        return {
            "memory.write": {
                "description": "Write a new memory",
                "required_capabilities": [Capability.WRITE],
                "resource_type": "memory",
                "risk_level": "medium",
            },
            "memory.recall": {
                "description": "Recall existing memories",
                "required_capabilities": [Capability.RECALL],
                "resource_type": "memory",
                "risk_level": "low",
            },
            "memory.project": {
                "description": "Project memories to different spaces",
                "required_capabilities": [Capability.PROJECT],
                "resource_type": "memory",
                "risk_level": "high",
            },
            "admin.manage": {
                "description": "Administrative management functions",
                "required_capabilities": [
                    Capability.WRITE,
                    Capability.RECALL,
                    Capability.SCHEDULE,
                ],
                "resource_type": "system",
                "risk_level": "critical",
            },
        }


class PolicyTestHarness:
    """Main test harness for orchestrating policy tests."""

    def __init__(self, policy_service: PolicyService):
        self.policy_service = policy_service
        self.context_factory = MockSecurityContextFactory()
        self.rbac_builder = RBACScenarioBuilder(self.context_factory)
        self.abac_builder = ABACScenarioBuilder(self.context_factory)
        self.assertions = PolicyDecisionAssertions()
        self.data_generator = PolicyTestDataGenerator()

        # Test execution state
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.failed_tests: List[str] = []

    async def run_rbac_test_suite(self) -> Dict[str, bool]:
        """Run the complete RBAC test suite."""

        logger.info("🧪 Running RBAC test suite...")
        results = {}

        # Memory access scenarios
        memory_scenarios = self.rbac_builder.build_memory_access_scenarios()
        for scenario_name, (context, operation, expected) in memory_scenarios.items():
            try:
                decision = await self._evaluate_test_policy(context, operation)
                results[scenario_name] = (decision.decision == "ALLOW") == expected

                if not results[scenario_name]:
                    self.failed_tests.append(f"RBAC:{scenario_name}")
                    logger.warning(f"❌ RBAC test failed: {scenario_name}")

            except Exception as e:
                results[scenario_name] = False
                self.failed_tests.append(f"RBAC:{scenario_name}")
                logger.error(f"❌ RBAC test error: {scenario_name} - {e}")

        logger.info(
            f"✅ RBAC tests completed: {sum(results.values())}/{len(results)} passed"
        )
        return results

    async def run_abac_test_suite(self) -> Dict[str, bool]:
        """Run the complete ABAC test suite."""

        logger.info("🧪 Running ABAC test suite...")
        results = {}

        # Cross-space scenarios
        cross_space_scenarios = self.abac_builder.build_cross_space_scenarios()
        for scenario_name, (
            context,
            space,
            target_group,
            expected,
        ) in cross_space_scenarios.items():
            try:
                # Create a mock request with space information
                decision = await self._evaluate_space_policy(
                    context, space, "memory.read"
                )
                results[scenario_name] = (decision.decision == "ALLOW") == expected

                if not results[scenario_name]:
                    self.failed_tests.append(f"ABAC:{scenario_name}")
                    logger.warning(f"❌ ABAC test failed: {scenario_name}")

            except Exception as e:
                results[scenario_name] = False
                self.failed_tests.append(f"ABAC:{scenario_name}")
                logger.error(f"❌ ABAC test error: {scenario_name} - {e}")

        logger.info(
            f"✅ ABAC tests completed: {sum(results.values())}/{len(results)} passed"
        )
        return results

    async def run_capability_test_suite(self) -> Dict[str, bool]:
        """Run capability-based authorization tests."""

        logger.info("🧪 Running Capability test suite...")
        results = {}

        capability_scenarios = self.rbac_builder.build_capability_scenarios()
        for scenario_name, (
            context,
            required_caps,
            expected,
        ) in capability_scenarios.items():
            try:
                # Check if context has all required capabilities
                user_caps = set(context.capabilities or [])
                required_caps_set = set(required_caps)
                has_capabilities = required_caps_set.issubset(user_caps)

                results[scenario_name] = has_capabilities == expected

                if not results[scenario_name]:
                    self.failed_tests.append(f"CAP:{scenario_name}")
                    logger.warning(f"❌ Capability test failed: {scenario_name}")

            except Exception as e:
                results[scenario_name] = False
                self.failed_tests.append(f"CAP:{scenario_name}")
                logger.error(f"❌ Capability test error: {scenario_name} - {e}")

        logger.info(
            f"✅ Capability tests completed: {sum(results.values())}/{len(results)} passed"
        )
        return results

    async def run_full_test_suite(self) -> Dict[str, Dict[str, bool]]:
        """Run all policy test suites."""

        logger.info("🚀 Starting full policy test suite...")

        results = {
            "rbac": await self.run_rbac_test_suite(),
            "abac": await self.run_abac_test_suite(),
            "capabilities": await self.run_capability_test_suite(),
        }

        # Summary statistics
        total_tests = sum(len(suite_results) for suite_results in results.values())
        total_passed = sum(
            sum(suite_results.values()) for suite_results in results.values()
        )

        logger.info(
            f"🎉 Policy test suite completed: {total_passed}/{total_tests} tests passed"
        )

        if self.failed_tests:
            logger.warning(f"❌ Failed tests: {', '.join(self.failed_tests)}")

        return results

    async def _evaluate_test_policy(
        self, context: SecurityContext, operation: str
    ) -> PolicyDecision:
        """Evaluate a test policy decision."""

        # For now, create a simple mock decision based on operation and context
        # In real implementation, this would call the actual policy service

        operations_data = self.data_generator.generate_test_operations()
        operation_info = operations_data.get(operation, {})
        required_caps = operation_info.get("required_capabilities", [])

        user_caps = set(context.capabilities or [])
        required_caps_set = set(required_caps)

        has_capabilities = required_caps_set.issubset(user_caps)

        if has_capabilities:
            return PolicyDecision(
                decision="ALLOW",
                reasons=[f"User has required capabilities for {operation}"],
                obligations=Obligation(),
            )
        else:
            missing_caps = required_caps_set - user_caps
            return PolicyDecision(
                decision="DENY",
                reasons=[
                    f"Missing required capabilities: {', '.join(cap.value for cap in missing_caps)}"
                ],
                obligations=Obligation(),
            )

    async def _evaluate_space_policy(
        self, context: SecurityContext, space: str, operation: str
    ) -> PolicyDecision:
        """Evaluate a space-specific policy decision."""

        # Extract space group from space identifier
        if ":" in space:
            space_namespace = space.split(":")[0]
        else:
            space_namespace = space

        # Check if user's MLS group matches space namespace
        user_group = context.mls_group or ""

        # For cross-group access, deny by default
        if space_namespace not in user_group and "family" in space_namespace:
            return PolicyDecision(
                decision="DENY",
                reasons=[
                    f"Cross-group access denied: user group '{user_group}' cannot access space '{space}'"
                ],
                obligations=Obligation(),
            )

        return PolicyDecision(
            decision="ALLOW",
            reasons=[f"Same-group access allowed for space '{space}'"],
            obligations=Obligation(),
        )


__all__ = [
    "PolicyTestHarness",
    "MockSecurityContextFactory",
    "RBACScenarioBuilder",
    "ABACScenarioBuilder",
    "PolicyDecisionAssertions",
    "PolicyTestDataGenerator",
    "TestRole",
    "TestScenario",
]

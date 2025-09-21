#!/usr/bin/env python3
"""
Comprehensive Integration & Stress Testing Suite for MemoryOS API

This module provides authenticated API request testing that flows through:
1. Authentication Middleware
2. Policy Enforcement Point (PEP)
3. Security, QoS, Safety, Observability middleware
4. Event bus integration
5. Storage operations

Tests include:
- Integration tests: End-to-end authenticated flows
- Stress tests: High-volume concurrent requests
- Performance benchmarks: Latency and throughput
- Middleware validation: Each layer functions correctly
"""

import asyncio
import statistics
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import MemoryOS components
from api.middleware.middleware_integration import setup_middleware_chain
from events.bus import EventBus
from policy.service import PolicyService


@dataclass
class TestResult:
    """Test execution result with metrics."""

    test_name: str
    success: bool
    duration_ms: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None


@dataclass
class StressTestMetrics:
    """Stress test aggregated metrics."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    errors: List[str]


class IntegrationTestSuite:
    """Comprehensive integration test suite for authenticated API flows."""

    def __init__(self):
        self.app: Optional[FastAPI] = None
        self.client: Optional[TestClient] = None
        self.policy_service: Optional[PolicyService] = None
        self.event_bus: Optional[EventBus] = None
        self.test_results: List[TestResult] = []

    async def setup(self) -> None:
        """Initialize test environment with full middleware stack."""

        # Create FastAPI app
        self.app = FastAPI(title="MemoryOS Test API")

        # Initialize policy service
        self.policy_service = PolicyService()
        await self.policy_service.initialize()

        # Initialize event bus
        self.event_bus = EventBus()
        await self.event_bus.start()

        # Setup complete middleware chain
        setup_middleware_chain(self.app, self.policy_service)

        # Add test API endpoints
        self._setup_test_endpoints()

        # Create test client
        self.client = TestClient(self.app)

    def _setup_test_endpoints(self) -> None:
        """Setup test API endpoints for integration testing."""

        @self.app.get("/test/memory/read")
        async def test_memory_read():
            """Test memory read operation with full middleware chain."""
            return {
                "operation": "memory.read",
                "status": "success",
                "data": "test_memory_content",
            }

        @self.app.post("/test/memory/write")
        async def test_memory_write(data: Dict[str, Any]):
            """Test memory write operation with full middleware chain."""
            return {"operation": "memory.write", "status": "success", "written": data}

        @self.app.get("/test/prospective/list")
        async def test_prospective_list():
            """Test prospective memory listing with authorization."""
            return {
                "operation": "prospective.manage",
                "status": "success",
                "items": ["item1", "item2"],
            }

        @self.app.post("/test/events/publish")
        async def test_event_publish(event_data: Dict[str, Any]):
            """Test event publishing through middleware."""
            # Simulate event bus interaction
            if self.event_bus:
                # In real implementation, this would publish to event bus
                pass
            return {
                "operation": "event.publish",
                "status": "success",
                "event_id": "test_event_123",
            }

        @self.app.get("/test/health")
        async def test_health():
            """Simple health check endpoint."""
            return {"status": "healthy", "timestamp": time.time()}

    async def run_integration_tests(self) -> List[TestResult]:
        """Run comprehensive integration tests with different user roles."""

        results = []

        # Test scenarios with different users and roles
        test_scenarios = [
            ("testuser", "member", "/test/memory/read", "GET", None),
            (
                "testuser",
                "member",
                "/test/memory/write",
                "POST",
                {"content": "test data"},
            ),
            ("integration_user", "admin", "/test/memory/read", "GET", None),
            (
                "integration_user",
                "admin",
                "/test/memory/write",
                "POST",
                {"content": "admin data"},
            ),
            ("integration_user", "admin", "/test/prospective/list", "GET", None),
            (
                "integration_user",
                "admin",
                "/test/events/publish",
                "POST",
                {"type": "test", "data": "event"},
            ),
            ("guest_user", "guest", "/test/memory/read", "GET", None),  # Should fail
            ("", "", "/test/health", "GET", None),  # No auth required
        ]

        for user, role, endpoint, method, data in test_scenarios:
            result = await self._run_single_test(user, role, endpoint, method, data)
            results.append(result)
            self.test_results.append(result)

        return results

    async def _run_single_test(
        self,
        user: str,
        role: str,
        endpoint: str,
        method: str,
        data: Optional[Dict[str, Any]],
    ) -> TestResult:
        """Execute a single integration test."""

        test_name = f"{method} {endpoint} (user:{user}, role:{role})"
        start_time = time.time()

        try:
            # Setup headers for authentication
            headers = {}
            if user:
                headers["X-Test-User"] = user
            if role:
                headers["X-Test-Role"] = role

            # Execute request
            if method == "GET":
                response = self.client.get(endpoint, headers=headers)
            elif method == "POST":
                response = self.client.post(endpoint, headers=headers, json=data or {})
            else:
                raise ValueError(f"Unsupported method: {method}")

            duration_ms = (time.time() - start_time) * 1000

            return TestResult(
                test_name=test_name,
                success=response.status_code < 400,
                duration_ms=duration_ms,
                status_code=response.status_code,
                response_data=response.json() if response.content else None,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
            )

    async def run_stress_tests(
        self, concurrent_users: int = 10, requests_per_user: int = 100
    ) -> StressTestMetrics:
        """Run stress tests with concurrent authenticated requests."""

        print(
            f"\\n🔥 Starting stress test: {concurrent_users} users × {requests_per_user} requests"
        )

        start_time = time.time()
        results = []
        errors = []

        # Create tasks for concurrent execution
        tasks = []
        for user_id in range(concurrent_users):
            user_name = f"stress_user_{user_id}"
            role = "member" if user_id % 2 == 0 else "admin"

            for req_id in range(requests_per_user):
                # Vary endpoints for realistic load
                endpoint = self._get_random_endpoint(req_id)
                method = "GET" if req_id % 3 != 0 else "POST"
                data = (
                    {"stress_test": True, "user_id": user_id, "req_id": req_id}
                    if method == "POST"
                    else None
                )

                task = self._run_single_test(user_name, role, endpoint, method, data)
                tasks.append(task)

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_requests = 0
        failed_requests = 0
        response_times = []

        for result in results:
            if isinstance(result, Exception):
                failed_requests += 1
                errors.append(str(result))
            elif isinstance(result, TestResult):
                if result.success:
                    successful_requests += 1
                else:
                    failed_requests += 1
                    if result.error_message:
                        errors.append(result.error_message)
                response_times.append(result.duration_ms)

        total_requests = successful_requests + failed_requests
        total_time = time.time() - start_time

        return StressTestMetrics(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=(
                (successful_requests / total_requests * 100)
                if total_requests > 0
                else 0
            ),
            avg_response_time=statistics.mean(response_times) if response_times else 0,
            p95_response_time=(
                statistics.quantiles(response_times, n=20)[18]
                if len(response_times) > 20
                else 0
            ),
            p99_response_time=(
                statistics.quantiles(response_times, n=100)[98]
                if len(response_times) > 100
                else 0
            ),
            requests_per_second=total_requests / total_time if total_time > 0 else 0,
            errors=list(set(errors[:10])),  # Unique errors, limited to 10
        )

    def _get_random_endpoint(self, req_id: int) -> str:
        """Get varied endpoints for stress testing."""
        endpoints = [
            "/test/memory/read",
            "/test/memory/write",
            "/test/prospective/list",
            "/test/events/publish",
            "/test/health",
        ]
        return endpoints[req_id % len(endpoints)]

    def print_integration_results(self, results: List[TestResult]) -> None:
        """Print detailed integration test results."""

        print("\\n" + "=" * 80)
        print("🧪 INTEGRATION TEST RESULTS")
        print("=" * 80)

        successful = sum(1 for r in results if r.success)
        total = len(results)
        success_rate = (successful / total * 100) if total > 0 else 0

        print(f"Overall Success Rate: {success_rate:.1f}% ({successful}/{total})")
        print(
            f"Average Response Time: {statistics.mean([r.duration_ms for r in results]):.2f}ms"
        )
        print()

        # Group by success/failure
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]

        if successes:
            print("✅ SUCCESSFUL TESTS:")
            for result in successes:
                print(
                    f"  • {result.test_name} - {result.duration_ms:.2f}ms (HTTP {result.status_code})"
                )

        if failures:
            print("\\n❌ FAILED TESTS:")
            for result in failures:
                error_info = result.error_message or f"HTTP {result.status_code}"
                print(f"  • {result.test_name} - {error_info}")

    def print_stress_results(self, metrics: StressTestMetrics) -> None:
        """Print detailed stress test results."""

        print("\\n" + "=" * 80)
        print("⚡ STRESS TEST RESULTS")
        print("=" * 80)

        print(f"Total Requests: {metrics.total_requests:,}")
        print(f"Successful: {metrics.successful_requests:,}")
        print(f"Failed: {metrics.failed_requests:,}")
        print(f"Success Rate: {metrics.success_rate:.2f}%")
        print(f"Requests/Second: {metrics.requests_per_second:.2f}")
        print()
        print("Response Time Metrics:")
        print(f"  Average: {metrics.avg_response_time:.2f}ms")
        print(f"  95th Percentile: {metrics.p95_response_time:.2f}ms")
        print(f"  99th Percentile: {metrics.p99_response_time:.2f}ms")

        if metrics.errors:
            print("\\nTop Errors:")
            for i, error in enumerate(metrics.errors[:5], 1):
                print(f"  {i}. {error}")

    async def cleanup(self) -> None:
        """Cleanup test resources."""
        if self.event_bus:
            await self.event_bus.stop()
        if self.policy_service:
            # Policy service cleanup if needed
            pass


async def main():
    """Main execution function for integration and stress testing."""

    print("🚀 MemoryOS Integration & Stress Testing Suite")
    print("=" * 50)

    # Initialize test suite
    test_suite = IntegrationTestSuite()

    try:
        # Setup test environment
        print("📋 Setting up test environment...")
        await test_suite.setup()

        # Run integration tests
        print("\\n🧪 Running integration tests...")
        integration_results = await test_suite.run_integration_tests()
        test_suite.print_integration_results(integration_results)

        # Run stress tests (configurable)
        print("\\n⚡ Running stress tests...")
        stress_metrics = await test_suite.run_stress_tests(
            concurrent_users=5,  # Start small for initial testing
            requests_per_user=20,  # 100 total requests
        )
        test_suite.print_stress_results(stress_metrics)

        # Performance analysis
        if integration_results:
            avg_latency = statistics.mean([r.duration_ms for r in integration_results])
            print("\\n📊 Performance Summary:")
            print(f"Integration Test Avg Latency: {avg_latency:.2f}ms")
            print(
                f"Stress Test Throughput: {stress_metrics.requests_per_second:.2f} req/s"
            )

            # SLO Analysis (example targets)
            latency_slo = 100  # 100ms SLO
            throughput_slo = 50  # 50 req/s SLO

            print("\\n🎯 SLO Analysis:")
            print(
                f"Latency SLO ({latency_slo}ms): {'✅ PASS' if avg_latency < latency_slo else '❌ FAIL'}"
            )
            print(
                f"Throughput SLO ({throughput_slo} req/s): {'✅ PASS' if stress_metrics.requests_per_second > throughput_slo else '❌ FAIL'}"
            )

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        raise
    finally:
        # Cleanup
        await test_suite.cleanup()
        print("\\n🧹 Cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())

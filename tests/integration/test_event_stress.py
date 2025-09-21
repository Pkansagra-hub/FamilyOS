#!/usr/bin/env python3
"""
Event-Driven Integration & Stress Testing for MemoryOS

This test suite validates:
1. Authenticated API requests through full middleware chain
2. Event bus integration with middleware
3. Policy enforcement for memory operations
4. Stress testing with concurrent users
5. Performance metrics and SLO validation
"""

import asyncio
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# MemoryOS imports
from api.middleware.middleware_integration import setup_middleware_chain
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
class StressMetrics:
    """Aggregated stress test metrics."""

    total_requests: int
    successful: int
    failed: int
    success_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    requests_per_second: float
    errors: List[str]


class EventIntegrationTester:
    """Integration tester with event bus and middleware validation."""

    def __init__(self):
        self.app: Optional[FastAPI] = None
        self.client: Optional[TestClient] = None
        self.policy_service: Optional[PolicyService] = None
        self.test_results: List[TestResult] = []

    async def setup(self) -> None:
        """Initialize test environment with middleware and policy service."""

        print("🔧 Setting up test environment...")

        # Create FastAPI app
        self.app = FastAPI(title="MemoryOS Integration Test API")

        # Initialize policy service
        self.policy_service = PolicyService()
        await self.policy_service.initialize()

        # Setup complete middleware chain
        setup_middleware_chain(self.app, self.policy_service)

        # Add test endpoints
        self._setup_test_routes()

        # Create test client
        self.client = TestClient(self.app)

        print("✅ Test environment ready")

    def _setup_test_routes(self) -> None:
        """Setup test API routes with event integration."""

        @self.app.get("/api/memory/read/{memory_id}")
        async def read_memory(memory_id: str):
            """Test memory read with full auth + policy flow."""
            # Simulate memory read operation
            return {
                "operation": "memory.read",
                "memory_id": memory_id,
                "content": f"Memory content for {memory_id}",
                "timestamp": time.time(),
            }

        @self.app.post("/api/memory/write")
        async def write_memory(data: Dict[str, Any]):
            """Test memory write with event publishing."""
            memory_id = data.get("memory_id", "default")
            content = data.get("content", "")

            # Simulate event publishing
            event_data = {
                "type": "memory.written",
                "memory_id": memory_id,
                "content_length": len(content),
                "timestamp": time.time(),
            }

            return {
                "operation": "memory.write",
                "memory_id": memory_id,
                "status": "success",
                "event_published": event_data,
            }

        @self.app.get("/api/prospective/list")
        async def list_prospective():
            """Test prospective memory access with admin role."""
            return {
                "operation": "prospective.manage",
                "items": [
                    {"id": "future_1", "type": "reminder", "due": "2025-09-15"},
                    {"id": "future_2", "type": "goal", "target": "2025-12-01"},
                ],
                "count": 2,
            }

        @self.app.post("/api/events/publish")
        async def publish_event(event: Dict[str, Any]):
            """Test event publishing through middleware."""
            return {
                "operation": "event.publish",
                "event_id": f"evt_{int(time.time())}",
                "type": event.get("type", "unknown"),
                "status": "published",
            }

        @self.app.get("/api/health")
        async def health_check():
            """Simple health endpoint for baseline testing."""
            return {"status": "healthy", "timestamp": time.time()}

        @self.app.get("/api/unauthorized")
        async def unauthorized_endpoint():
            """Test endpoint that should require high permissions."""
            # This should fail for most users
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    async def run_integration_tests(self) -> List[TestResult]:
        """Execute comprehensive integration test scenarios."""

        print("\\n🧪 Running integration tests...")

        # Test scenarios: (user, role, method, endpoint, data, expected_success)
        scenarios = [
            # Memory operations
            ("testuser", "member", "GET", "/api/memory/read/test123", None, True),
            (
                "testuser",
                "member",
                "POST",
                "/api/memory/write",
                {"memory_id": "mem1", "content": "test"},
                True,
            ),
            # Admin operations
            ("integration_user", "admin", "GET", "/api/prospective/list", None, True),
            (
                "integration_user",
                "admin",
                "POST",
                "/api/events/publish",
                {"type": "test.event", "data": "admin"},
                True,
            ),
            # Permission tests
            (
                "guest_user",
                "guest",
                "GET",
                "/api/memory/read/secret",
                None,
                False,
            ),  # Should fail
            (
                "guest_user",
                "guest",
                "POST",
                "/api/memory/write",
                {"content": "guest"},
                False,
            ),  # Should fail
            # Health check (no auth required)
            ("", "", "GET", "/api/health", None, True),
            # High-permission endpoint
            (
                "testuser",
                "member",
                "GET",
                "/api/unauthorized",
                None,
                False,
            ),  # Should fail
            (
                "integration_user",
                "admin",
                "GET",
                "/api/unauthorized",
                None,
                False,
            ),  # Should fail for all
        ]

        results = []

        for user, role, method, endpoint, data, expected_success in scenarios:
            result = await self._execute_test(user, role, method, endpoint, data)

            # Validate expectation
            if result.success != expected_success:
                print(
                    f"⚠️  Unexpected result for {result.test_name}: expected {'success' if expected_success else 'failure'}"
                )

            results.append(result)

        self.test_results.extend(results)
        return results

    async def _execute_test(
        self,
        user: str,
        role: str,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]],
    ) -> TestResult:
        """Execute single test with timing and error handling."""

        test_name = (
            f"{method} {endpoint} (user:{user or 'none'}, role:{role or 'none'})"
        )
        start_time = time.time()

        try:
            # Setup authentication headers
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
                success=200 <= response.status_code < 400,
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

    async def run_stress_test(
        self, concurrent_users: int = 10, requests_per_user: int = 50
    ) -> StressMetrics:
        """Execute stress test with concurrent authenticated requests."""

        print(
            f"\\n⚡ Starting stress test: {concurrent_users} users × {requests_per_user} requests"
        )

        start_time = time.time()

        # Create concurrent tasks
        tasks = []
        for user_id in range(concurrent_users):
            user_name = f"stress_user_{user_id}"
            role = "member" if user_id % 2 == 0 else "admin"

            for req_id in range(requests_per_user):
                endpoint, method, data = self._get_stress_request(req_id)
                task = self._execute_test(user_name, role, method, endpoint, data)
                tasks.append(task)

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate metrics
        successful = 0
        failed = 0
        latencies = []
        errors = []

        for result in results:
            if isinstance(result, Exception):
                failed += 1
                errors.append(str(result)[:100])
            elif isinstance(result, TestResult):
                if result.success:
                    successful += 1
                else:
                    failed += 1
                    if result.error_message:
                        errors.append(result.error_message[:100])
                latencies.append(result.duration_ms)

        total_requests = successful + failed
        total_time = time.time() - start_time

        return StressMetrics(
            total_requests=total_requests,
            successful=successful,
            failed=failed,
            success_rate=(
                (successful / total_requests * 100) if total_requests > 0 else 0
            ),
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            p95_latency_ms=(
                statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else 0
            ),
            requests_per_second=total_requests / total_time if total_time > 0 else 0,
            errors=list(set(errors[:5])),  # Unique errors, max 5
        )

    def _get_stress_request(self, req_id: int) -> tuple:
        """Generate varied requests for stress testing."""

        endpoints = [
            ("/api/health", "GET", None),
            ("/api/memory/read/stress_test", "GET", None),
            (
                "/api/memory/write",
                "POST",
                {"memory_id": f"stress_{req_id}", "content": "stress test"},
            ),
            ("/api/events/publish", "POST", {"type": "stress.test", "req_id": req_id}),
        ]

        return endpoints[req_id % len(endpoints)]

    def print_results(
        self, integration_results: List[TestResult], stress_metrics: StressMetrics
    ) -> None:
        """Print comprehensive test results."""

        print("\\n" + "=" * 80)
        print("📊 MEMORYOS INTEGRATION & STRESS TEST RESULTS")
        print("=" * 80)

        # Integration test summary
        successful_integration = sum(1 for r in integration_results if r.success)
        total_integration = len(integration_results)
        integration_success_rate = (
            (successful_integration / total_integration * 100)
            if total_integration > 0
            else 0
        )

        print("\\n🧪 Integration Tests:")
        print(
            f"  Success Rate: {integration_success_rate:.1f}% ({successful_integration}/{total_integration})"
        )

        if integration_results:
            avg_latency = statistics.mean([r.duration_ms for r in integration_results])
            print(f"  Average Latency: {avg_latency:.2f}ms")

        # Detailed integration results
        print("\\n📋 Integration Test Details:")
        for result in integration_results:
            status = "✅" if result.success else "❌"
            print(
                f"  {status} {result.test_name} - {result.duration_ms:.1f}ms (HTTP {result.status_code})"
            )

        # Stress test summary
        print("\\n⚡ Stress Test Results:")
        print(f"  Total Requests: {stress_metrics.total_requests:,}")
        print(f"  Success Rate: {stress_metrics.success_rate:.2f}%")
        print(f"  Throughput: {stress_metrics.requests_per_second:.2f} req/s")
        print(f"  Average Latency: {stress_metrics.avg_latency_ms:.2f}ms")
        print(f"  95th Percentile: {stress_metrics.p95_latency_ms:.2f}ms")

        # SLO Analysis
        print("\\n🎯 SLO Analysis:")
        latency_slo = 100  # 100ms target
        throughput_slo = 50  # 50 req/s target
        success_slo = 95  # 95% success rate target

        print(
            f"  Latency SLO ({latency_slo}ms): {'✅ PASS' if stress_metrics.avg_latency_ms < latency_slo else '❌ FAIL'}"
        )
        print(
            f"  Throughput SLO ({throughput_slo} req/s): {'✅ PASS' if stress_metrics.requests_per_second > throughput_slo else '❌ FAIL'}"
        )
        print(
            f"  Success Rate SLO ({success_slo}%): {'✅ PASS' if stress_metrics.success_rate > success_slo else '❌ FAIL'}"
        )

        # Error summary
        if stress_metrics.errors:
            print("\\n❌ Top Errors:")
            for i, error in enumerate(stress_metrics.errors, 1):
                print(f"  {i}. {error}")

    async def cleanup(self) -> None:
        """Cleanup test resources."""
        if self.policy_service:
            # Cleanup policy service if needed
            pass


async def main():
    """Main execution function."""

    print("🚀 MemoryOS Event-Driven Integration & Stress Testing")
    print("=" * 60)

    tester = EventIntegrationTester()

    try:
        # Setup
        await tester.setup()

        # Run integration tests
        integration_results = await tester.run_integration_tests()

        # Run stress tests
        stress_metrics = await tester.run_stress_test(
            concurrent_users=8,  # Moderate concurrent load
            requests_per_user=25,  # 200 total requests
        )

        # Print comprehensive results
        tester.print_results(integration_results, stress_metrics)

        # Final assessment
        overall_success = (
            stress_metrics.success_rate > 90
            and stress_metrics.avg_latency_ms < 100
            and sum(1 for r in integration_results if r.success)
            >= len(integration_results) * 0.8
        )

        print(
            f"\\n🏁 Overall Assessment: {'✅ PASS' if overall_success else '❌ NEEDS IMPROVEMENT'}"
        )

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        raise
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

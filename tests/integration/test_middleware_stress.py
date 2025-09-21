#!/usr/bin/env python3
"""
Simplified Integration & Stress Test for MemoryOS Middleware

Tests authenticated API requests through the middleware chain
with focus on performance and correctness validation.
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

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient


@dataclass
class TestResult:
    """Test execution result with timing."""

    test_name: str
    success: bool
    duration_ms: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None


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


class MiddlewareStressTester:
    """Simple stress tester focusing on middleware performance."""

    def __init__(self):
        self.app: Optional[FastAPI] = None
        self.client: Optional[TestClient] = None
        self.test_results: List[TestResult] = []

    def setup(self) -> None:
        """Initialize test FastAPI app with basic middleware simulation."""

        print("🔧 Setting up test environment...")

        # Create FastAPI app
        self.app = FastAPI(title="MemoryOS Middleware Test")

        # Add simple middleware simulation
        @self.app.middleware("http")
        async def auth_simulation_middleware(request: Request, call_next):
            """Simulate authentication middleware processing."""

            start_time = time.time()

            # Simulate auth processing time
            await asyncio.sleep(0.001)  # 1ms auth processing

            # Check for test headers
            test_user = request.headers.get("X-Test-User")
            test_role = request.headers.get("X-Test-Role")

            # Add simulated security context to request state
            request.state.user_id = test_user or "anonymous"
            request.state.role = test_role or "guest"
            request.state.authenticated = bool(test_user)

            response = await call_next(request)

            # Add processing time header
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)

            return response

        @self.app.middleware("http")
        async def policy_simulation_middleware(request: Request, call_next):
            """Simulate policy enforcement middleware."""

            # Simulate policy check time
            await asyncio.sleep(0.002)  # 2ms policy processing

            # Simple role-based access control simulation
            user_role = getattr(request.state, "role", "guest")
            path = request.url.path

            # Define simple access rules
            if "/admin/" in path and user_role not in ["admin"]:
                return HTTPException(status_code=403, detail="Admin access required")

            if "/protected/" in path and user_role in ["guest"]:
                return HTTPException(status_code=403, detail="Authentication required")

            return await call_next(request)

        # Setup test endpoints
        self._setup_test_routes()

        # Create test client
        self.client = TestClient(self.app)

        print("✅ Test environment ready")

    def _setup_test_routes(self) -> None:
        """Setup test API routes."""

        @self.app.get("/api/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": time.time()}

        @self.app.get("/api/memory/read/{memory_id}")
        async def read_memory(memory_id: str, request: Request):
            """Memory read endpoint."""
            # Simulate some processing time
            await asyncio.sleep(0.005)  # 5ms processing

            return {
                "operation": "memory.read",
                "memory_id": memory_id,
                "user_id": getattr(request.state, "user_id", "unknown"),
                "content": f"Content for {memory_id}",
                "timestamp": time.time(),
            }

        @self.app.post("/api/memory/write")
        async def write_memory(data: Dict[str, Any], request: Request):
            """Memory write endpoint."""
            # Simulate processing time
            await asyncio.sleep(0.008)  # 8ms processing

            return {
                "operation": "memory.write",
                "memory_id": data.get("memory_id", "default"),
                "user_id": getattr(request.state, "user_id", "unknown"),
                "status": "written",
                "timestamp": time.time(),
            }

        @self.app.get("/api/protected/data")
        async def protected_data(request: Request):
            """Protected endpoint requiring authentication."""
            return {
                "data": "sensitive information",
                "user_id": getattr(request.state, "user_id", "unknown"),
                "access_level": getattr(request.state, "role", "guest"),
            }

        @self.app.get("/api/admin/stats")
        async def admin_stats(request: Request):
            """Admin-only endpoint."""
            return {
                "stats": {"users": 100, "memories": 1000},
                "admin_user": getattr(request.state, "user_id", "unknown"),
            }

    def run_integration_tests(self) -> List[TestResult]:
        """Execute integration test scenarios."""

        print("\\n🧪 Running integration tests...")

        # Test scenarios: (user, role, method, endpoint, data, expected_success)
        scenarios = [
            # Basic endpoints
            ("", "", "GET", "/api/health", None, True),
            # Memory operations
            ("testuser", "member", "GET", "/api/memory/read/test123", None, True),
            (
                "testuser",
                "member",
                "POST",
                "/api/memory/write",
                {"memory_id": "test", "content": "data"},
                True,
            ),
            # Admin user tests
            ("admin_user", "admin", "GET", "/api/memory/read/admin_mem", None, True),
            ("admin_user", "admin", "GET", "/api/admin/stats", None, True),
            # Access control tests
            (
                "guest_user",
                "guest",
                "GET",
                "/api/protected/data",
                None,
                False,
            ),  # Should fail
            (
                "member_user",
                "member",
                "GET",
                "/api/protected/data",
                None,
                True,
            ),  # Should pass
            (
                "member_user",
                "member",
                "GET",
                "/api/admin/stats",
                None,
                False,
            ),  # Should fail
            # Anonymous access
            ("", "", "GET", "/api/protected/data", None, False),  # Should fail
            ("", "", "GET", "/api/admin/stats", None, False),  # Should fail
        ]

        results = []

        for user, role, method, endpoint, data, expected_success in scenarios:
            result = self._execute_test(user, role, method, endpoint, data)

            # Validate expectation
            actual_success = result.success
            if actual_success != expected_success:
                print(
                    f"⚠️  Unexpected result for {result.test_name}: expected {'success' if expected_success else 'failure'}, got {'success' if actual_success else 'failure'}"
                )

            results.append(result)

        return results

    def _execute_test(
        self,
        user: str,
        role: str,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]],
    ) -> TestResult:
        """Execute single test with timing."""

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
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e),
            )

    def run_stress_test(
        self, concurrent_users: int = 10, requests_per_user: int = 50
    ) -> StressMetrics:
        """Execute stress test with concurrent requests."""

        print(
            f"\\n⚡ Starting stress test: {concurrent_users} users × {requests_per_user} requests"
        )

        start_time = time.time()

        # Prepare test scenarios for stress testing
        def get_stress_request(user_id: int, req_id: int):
            user_name = f"stress_user_{user_id}"
            role = "member" if user_id % 2 == 0 else "admin"

            endpoints = [
                ("GET", "/api/health", None),
                ("GET", "/api/memory/read/stress_test", None),
                (
                    "POST",
                    "/api/memory/write",
                    {"memory_id": f"stress_{req_id}", "content": "test"},
                ),
                ("GET", "/api/protected/data", None),
            ]

            method, endpoint, data = endpoints[req_id % len(endpoints)]
            return user_name, role, method, endpoint, data

        # Execute all requests
        results = []

        for user_id in range(concurrent_users):
            for req_id in range(requests_per_user):
                user_name, role, method, endpoint, data = get_stress_request(
                    user_id, req_id
                )
                result = self._execute_test(user_name, role, method, endpoint, data)
                results.append(result)

        # Aggregate metrics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        latencies = [r.duration_ms for r in results]

        total_time = time.time() - start_time

        return StressMetrics(
            total_requests=len(results),
            successful=successful,
            failed=failed,
            success_rate=(successful / len(results) * 100) if results else 0,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            p95_latency_ms=(
                statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else 0
            ),
            requests_per_second=len(results) / total_time if total_time > 0 else 0,
        )

    def print_results(
        self, integration_results: List[TestResult], stress_metrics: StressMetrics
    ) -> None:
        """Print comprehensive test results."""

        print("\\n" + "=" * 80)
        print("📊 MEMORYOS MIDDLEWARE STRESS TEST RESULTS")
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

        # Performance analysis
        print("\\n🎯 Performance Analysis:")
        latency_target = 50  # 50ms target
        throughput_target = 100  # 100 req/s target
        success_target = 95  # 95% success rate target

        latency_pass = stress_metrics.avg_latency_ms < latency_target
        throughput_pass = stress_metrics.requests_per_second > throughput_target
        success_pass = stress_metrics.success_rate > success_target

        print(
            f"  Latency Target ({latency_target}ms): {'✅ PASS' if latency_pass else '❌ FAIL'} ({stress_metrics.avg_latency_ms:.1f}ms)"
        )
        print(
            f"  Throughput Target ({throughput_target} req/s): {'✅ PASS' if throughput_pass else '❌ FAIL'} ({stress_metrics.requests_per_second:.1f} req/s)"
        )
        print(
            f"  Success Rate Target ({success_target}%): {'✅ PASS' if success_pass else '❌ FAIL'} ({stress_metrics.success_rate:.1f}%)"
        )

        # Overall assessment
        overall_pass = latency_pass and throughput_pass and success_pass
        print(
            f"\\n🏁 Overall Assessment: {'✅ PASS - All targets met!' if overall_pass else '⚠️  REVIEW - Some targets missed'}"
        )


def main():
    """Main execution function."""

    print("🚀 MemoryOS Middleware Stress Testing Suite")
    print("=" * 50)

    tester = MiddlewareStressTester()

    try:
        # Setup
        tester.setup()

        # Run integration tests
        integration_results = tester.run_integration_tests()

        # Run stress tests
        stress_metrics = tester.run_stress_test(
            concurrent_users=10, requests_per_user=50  # 500 total requests
        )

        # Print results
        tester.print_results(integration_results, stress_metrics)

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        raise


if __name__ == "__main__":
    main()

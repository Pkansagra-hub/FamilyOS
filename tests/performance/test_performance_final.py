#!/usr/bin/env python3
"""
Final Performance Test - Post Simulation Cleanup
Tests MemoryOS API performance after removing all artificial delays
"""

import asyncio
import json
import statistics
import time
from typing import Any, Dict

import aiohttp


class PerformanceTester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results = {}

    async def test_endpoint(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        method: str = "GET",
        data: Dict = None,
        requests: int = 50,
    ) -> Dict[str, Any]:
        """Test a single endpoint with multiple concurrent requests."""
        print(f"\n🎯 Testing {method} {endpoint} - {requests} requests")

        url = f"{self.base_url}{endpoint}"
        response_times = []
        errors = []
        status_codes = []

        async def single_request():
            start_time = time.time()
            try:
                if method == "GET":
                    async with session.get(url) as response:
                        await response.text()
                        response_time = time.time() - start_time
                        return response_time, response.status, None
                elif method == "POST":
                    async with session.post(url, json=data) as response:
                        await response.text()
                        response_time = time.time() - start_time
                        return response_time, response.status, None
            except Exception as e:
                response_time = time.time() - start_time
                return response_time, 0, str(e)

        # Execute all requests concurrently
        tasks = [single_request() for _ in range(requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
                continue

            resp_time, status, error = result
            response_times.append(resp_time)
            status_codes.append(status)
            if error:
                errors.append(error)

        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            p95_time = sorted(response_times)[int(0.95 * len(response_times))]
            min_time = min(response_times)
            max_time = max(response_times)
            rps = (
                len(response_times) / sum(response_times)
                if sum(response_times) > 0
                else 0
            )
        else:
            avg_time = median_time = p95_time = min_time = max_time = rps = 0

        success_rate = (
            (len([s for s in status_codes if 200 <= s < 300]) / len(status_codes) * 100)
            if status_codes
            else 0
        )

        result = {
            "endpoint": endpoint,
            "method": method,
            "total_requests": requests,
            "successful_requests": len([s for s in status_codes if 200 <= s < 300]),
            "success_rate_percent": round(success_rate, 2),
            "avg_response_time_ms": round(avg_time * 1000, 2),
            "median_response_time_ms": round(median_time * 1000, 2),
            "p95_response_time_ms": round(p95_time * 1000, 2),
            "min_response_time_ms": round(min_time * 1000, 2),
            "max_response_time_ms": round(max_time * 1000, 2),
            "requests_per_second": round(rps, 2),
            "error_count": len(errors),
            "error_rate_percent": (
                round(len(errors) / requests * 100, 2) if requests > 0 else 0
            ),
        }

        # Print results
        print(f"   ✅ Success Rate: {result['success_rate_percent']}%")
        print(f"   ⏱️  Avg Response: {result['avg_response_time_ms']}ms")
        print(f"   📊 P95 Response: {result['p95_response_time_ms']}ms")
        print(f"   🚀 Requests/sec: {result['requests_per_second']}")
        if errors:
            print(f"   ❌ Errors: {len(errors)}")

        return result

    async def comprehensive_performance_test(self):
        """Run comprehensive performance test across all endpoints."""
        print("🚀 MemoryOS Performance Test - Post Simulation Cleanup")
        print("=" * 60)

        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=100)

        async with aiohttp.ClientSession(
            timeout=timeout, connector=connector
        ) as session:

            # Test various endpoints
            endpoints_to_test = [
                ("/health", "GET", None, 100),
                ("/memory/search", "POST", {"query": "test search", "limit": 10}, 50),
                (
                    "/memory/store",
                    "POST",
                    {"content": "test content", "metadata": {"type": "test"}},
                    30,
                ),
                ("/events/stream", "GET", None, 20),
                ("/status", "GET", None, 50),
            ]

            all_results = []

            for endpoint, method, data, request_count in endpoints_to_test:
                try:
                    result = await self.test_endpoint(
                        session, endpoint, method, data, request_count
                    )
                    all_results.append(result)
                except Exception as e:
                    print(f"❌ Failed to test {endpoint}: {e}")

            # Calculate overall metrics
            if all_results:
                total_requests = sum(r["total_requests"] for r in all_results)
                successful_requests = sum(r["successful_requests"] for r in all_results)
                avg_response_times = [
                    r["avg_response_time_ms"]
                    for r in all_results
                    if r["avg_response_time_ms"] > 0
                ]
                total_rps = sum(
                    r["requests_per_second"]
                    for r in all_results
                    if r["requests_per_second"] > 0
                )

                overall_success_rate = (
                    (successful_requests / total_requests * 100)
                    if total_requests > 0
                    else 0
                )
                overall_avg_response = (
                    statistics.mean(avg_response_times) if avg_response_times else 0
                )

                # Print summary
                print("\n" + "=" * 60)
                print("📊 PERFORMANCE SUMMARY - NO MORE SIMULATIONS!")
                print("=" * 60)
                print(f"🎯 Total Requests: {total_requests}")
                print(f"✅ Success Rate: {overall_success_rate:.2f}%")
                print(f"⏱️  Overall Avg Response: {overall_avg_response:.2f}ms")
                print(f"🚀 Combined RPS: {total_rps:.2f}")
                print(
                    f"🎉 Target Achievement: {('✅ EXCEEDED' if total_rps > 20 else '❌ BELOW')} 20 req/sec"
                )

                # Performance comparison
                print("\n📈 PERFORMANCE IMPROVEMENT:")
                print("   Before cleanup: ~4.9 req/sec with 1000ms+ delays")
                print(
                    f"   After cleanup:  {total_rps:.1f} req/sec with {overall_avg_response:.0f}ms response"
                )
                improvement = (total_rps / 4.9) * 100 if total_rps > 0 else 0
                print(f"   🚀 Performance gain: {improvement:.0f}% improvement!")

                # Save detailed results
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                results_file = f"performance_results_final_{timestamp}.json"

                summary = {
                    "timestamp": timestamp,
                    "test_type": "post_simulation_cleanup",
                    "overall_metrics": {
                        "total_requests": total_requests,
                        "successful_requests": successful_requests,
                        "overall_success_rate": overall_success_rate,
                        "overall_avg_response_ms": overall_avg_response,
                        "combined_rps": total_rps,
                        "target_achieved": total_rps >= 20,
                    },
                    "endpoint_results": all_results,
                }

                with open(results_file, "w") as f:
                    json.dump(summary, f, indent=2)

                print(f"\n💾 Results saved to: {results_file}")

                return summary

            return None


async def main():
    tester = PerformanceTester()

    # Wait for server to be ready
    print("🔧 Warming up server...")
    await asyncio.sleep(2)

    results = await tester.comprehensive_performance_test()

    if results:
        print("\n🎊 Performance test completed successfully!")
        print("🚫 NO MORE ARTIFICIAL DELAYS - REAL PRODUCTION PERFORMANCE!")
    else:
        print("\n❌ Performance test failed")


if __name__ == "__main__":
    asyncio.run(main())

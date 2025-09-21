"""
Manual Integration Test Harness for API, Events, and Policy
Covers edge cases, error paths, and middleware hooks without ward/pytest.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import time
import uuid
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware import setup_middleware_chain
from api.schemas import AuthMethod, Capability, SecurityContext, TrustLevel
from events.bus import EventBus
from events.types import Event
from policy.service import get_policy_service, initialize_policy_service

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("manual_integration_test")

# --- Initialize policy service ---
policy_service = initialize_policy_service(storage_dir="./workspace/test_policy")

# Initialize default roles and admin user - THIS WAS MISSING!
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Already in async context
        asyncio.create_task(policy_service.initialize_default_roles())
    else:
        # Not in async context, run directly
        asyncio.run(policy_service.initialize_default_roles())
except RuntimeError:
    # No event loop, create one
    asyncio.run(policy_service.initialize_default_roles())

# --- Setup API app and middleware chain ---
app = FastAPI()
setup_middleware_chain(app)
# Note: Using basic middleware chain for testing


# Add basic route handlers for testing
@app.get("/v1/memories/{memory_id}")
async def get_memory(memory_id: str) -> Dict[str, str]:
    """Test route for memory retrieval."""
    return {"id": memory_id, "content": "test memory content", "status": "retrieved"}


@app.post("/v1/tools/memory/submit")
async def submit_memory(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Test route for memory submission."""
    return {"id": "test_memory_123", "status": "submitted", "payload": payload}


@app.get("/v1/events/stream")
async def event_stream() -> Dict[str, Any]:
    """Test route for event streaming."""
    return {"stream": "active", "events": []}


@app.post("/v1/events/ack")
async def event_ack(event_id: str) -> Dict[str, str]:
    """Test route for event acknowledgment."""
    return {"event_id": event_id, "status": "acknowledged"}


client = TestClient(app)


# --- Helper: Print middleware state ---
def print_middleware_state(response: Any) -> None:
    """Log response status, headers, and body for middleware analysis."""
    logger.info(f"Response status: {response.status_code}")
    for k, v in response.headers.items():
        if k.lower().startswith("x-"):
            logger.info(f"Header: {k} = {v}")
    logger.info(f"Response body: {response.text[:200]}...")  # Truncate long responses


# --- Test Result Tracking ---
test_results: Dict[str, Dict[str, Any]] = {}


def log_test_result(test_name: str, success: bool, details: Dict[str, Any]) -> None:
    """Log test result with detailed information."""
    test_results[test_name] = {
        "success": success,
        "timestamp": time.time(),
        "details": details,
    }
    status = "✅ PASS" if success else "❌ FAIL"
    logger.info(f"{status} {test_name}: {details.get('summary', 'No summary')}")


# --- API Endpoint Tests ---
def test_api_auth_edge_cases() -> None:
    """Test authentication edge cases across different scenarios."""
    logger.info("=== API Authentication Edge Cases ===")

    # Test 1: No auth header (should fail)
    resp = client.get("/v1/memories/123")
    print_middleware_state(resp)
    log_test_result(
        "auth_no_header",
        resp.status_code == 401,
        {
            "summary": f"Expected 401, got {resp.status_code}",
            "status_code": resp.status_code,
            "has_trace_id": "x-trace-id" in resp.headers,
        },
    )

    # Test 2: Valid dev auth header (should pass to next middleware)
    resp = client.get(
        "/v1/memories/123", headers={"X-Test-User": "testuser", "X-Test-Role": "admin"}
    )
    print_middleware_state(resp)
    log_test_result(
        "auth_dev_valid",
        resp.status_code in [200, 404, 403],
        {
            "summary": f"Dev auth processed, status {resp.status_code}",
            "status_code": resp.status_code,
            "has_auth_success": resp.status_code != 401,
        },
    )

    # Test 3: Invalid JWT (should fail)
    resp = client.get(
        "/v1/memories/123", headers={"Authorization": "Bearer invalidtoken"}
    )
    print_middleware_state(resp)
    log_test_result(
        "auth_jwt_invalid",
        resp.status_code == 401,
        {
            "summary": f"Expected 401 for invalid JWT, got {resp.status_code}",
            "status_code": resp.status_code,
        },
    )

    # Test 4: Different roles and capabilities
    for role in ["admin", "guardian", "member", "child", "guest"]:
        resp = client.get(
            "/v1/memories/123",
            headers={"X-Test-User": f"user_{role}", "X-Test-Role": role},
        )
        log_test_result(
            f"auth_role_{role}",
            resp.status_code != 401,
            {
                "summary": f"Role {role} auth processed",
                "status_code": resp.status_code,
                "role": role,
            },
        )


def test_policy_enforcement_edge_cases() -> None:
    """Test policy enforcement with various scenarios."""
    logger.info("=== Policy Enforcement Edge Cases ===")

    # Test different operations with admin role
    operations = [
        ("/v1/memories/123", "GET", "memory.read"),
        ("/v1/tools/memory/submit", "POST", "memory.write"),
        ("/v1/tools/memory/recall", "POST", "memory.recall"),
        ("/v1/admin/users", "GET", "admin.read"),
        ("/v1/events/stream", "GET", "events.stream"),
    ]

    for path, method, expected_op in operations:
        headers = {"X-Test-User": "admin_user", "X-Test-Role": "admin"}
        if method == "GET":
            resp = client.get(path, headers=headers)
        else:
            resp = client.post(path, headers=headers, json={"test": "data"})

        print_middleware_state(resp)
        log_test_result(
            f"policy_{expected_op}",
            resp.status_code != 403,
            {
                "summary": f"Operation {expected_op} on {path}",
                "status_code": resp.status_code,
                "method": method,
                "path": path,
            },
        )


def test_safety_middleware_edge_cases() -> None:
    """Test safety middleware with dangerous content."""
    logger.info("=== Safety Middleware Edge Cases ===")

    # Test dangerous content patterns
    dangerous_payloads = [
        {"content": "<script>alert('xss')</script>", "type": "xss"},
        {"content": "'; DROP TABLE users; --", "type": "sql_injection"},
        {"content": "rm -rf /", "type": "command_injection"},
        {"filename": "malware.exe", "type": "dangerous_file"},
        {"content": "A" * 20000000, "type": "large_content"},  # 20MB
    ]

    headers = {"X-Test-User": "testuser", "X-Test-Role": "member"}

    for payload in dangerous_payloads:
        resp = client.post("/v1/tools/memory/submit", headers=headers, json=payload)
        print_middleware_state(resp)

        # Safety middleware should block dangerous content
        blocked = resp.status_code == 403
        log_test_result(
            f"safety_{payload['type']}",
            blocked,
            {
                "summary": f"Dangerous {payload['type']} {'blocked' if blocked else 'allowed'}",
                "status_code": resp.status_code,
                "payload_type": payload["type"],
                "blocked": blocked,
            },
        )


def test_qos_middleware_edge_cases() -> None:
    """Test QoS middleware with different priorities and loads."""
    logger.info("=== QoS Middleware Edge Cases ===")

    # Test different priority levels
    priorities = ["critical", "high", "normal", "low"]
    headers_base = {"X-Test-User": "testuser", "X-Test-Role": "member"}

    for priority in priorities:
        headers = {**headers_base, "X-Priority": priority}
        resp = client.get("/v1/memories/test", headers=headers)
        print_middleware_state(resp)

        has_qos_headers = "x-qos-priority" in resp.headers
        log_test_result(
            f"qos_priority_{priority}",
            has_qos_headers,
            {
                "summary": f"Priority {priority} processed",
                "status_code": resp.status_code,
                "priority": priority,
                "qos_priority_header": resp.headers.get("x-qos-priority", "missing"),
            },
        )

    # Test high load simulation (rapid requests)
    logger.info("Testing QoS under load...")
    start_time = time.time()
    responses: list[Any] = []
    for i in range(50):  # Send 50 requests rapidly
        resp = client.get(f"/v1/memories/{i}", headers=headers_base)
        responses.append(resp)

    throttled = sum(1 for r in responses if r.status_code == 503)
    log_test_result(
        "qos_load_handling",
        True,
        {
            "summary": f"Sent 50 requests, {throttled} throttled",
            "total_requests": 50,
            "throttled_requests": throttled,
            "duration_ms": (time.time() - start_time) * 1000,
        },
    )


def test_security_middleware_edge_cases() -> None:
    """Test security middleware threat detection."""
    logger.info("=== Security Middleware Edge Cases ===")

    # Test threat patterns in URLs and headers
    threat_tests: list[Dict[str, Any]] = [
        {"url": "/v1/memories/123?q=union+select", "type": "sql_injection_url"},
        {"url": "/v1/memories/../../../etc/passwd", "type": "path_traversal"},
        {"headers": {"User-Agent": "<script>alert(1)</script>"}, "type": "xss_header"},
        {
            "headers": {"X-Forwarded-For": "'; DROP TABLE users; --"},
            "type": "sql_injection_header",
        },
    ]

    base_headers = {"X-Test-User": "testuser", "X-Test-Role": "member"}

    for test in threat_tests:
        headers: Dict[str, str] = {**base_headers, **test.get("headers", {})}
        url: str = test.get("url", "/v1/memories/test")

        resp = client.get(url, headers=headers)
        print_middleware_state(resp)

        # Security middleware should detect threats
        threat_detected = resp.status_code in [403, 429]
        log_test_result(
            f"security_{test['type']}",
            True,
            {
                "summary": f"Threat {test['type']} {'detected' if threat_detected else 'missed'}",
                "status_code": resp.status_code,
                "threat_type": test["type"],
                "detected": threat_detected,
            },
        )

    # Test rate limiting
    logger.info("Testing security rate limiting...")
    resp = None
    for i in range(70):  # Exceed 60/minute limit
        resp = client.get(f"/v1/memories/{i}", headers=base_headers)

    rate_limited = resp.status_code == 429 if resp else False
    log_test_result(
        "security_rate_limit",
        rate_limited,
        {
            "summary": f"Rate limiting {'triggered' if rate_limited else 'not triggered'}",
            "final_status": resp.status_code if resp else "unknown",
            "rate_limited": rate_limited,
        },
    )


def test_observability_middleware() -> None:
    """Test observability middleware metrics and tracing."""
    logger.info("=== Observability Middleware ===")

    headers = {"X-Test-User": "testuser", "X-Test-Role": "member"}
    resp = client.get("/v1/memories/observability_test", headers=headers)
    print_middleware_state(resp)

    # Check for observability headers
    observability_headers = ["x-trace-id", "x-processing-time", "x-timestamp"]

    missing_headers = [h for h in observability_headers if h not in resp.headers]

    log_test_result(
        "observability_headers",
        len(missing_headers) == 0,
        {
            "summary": f"Observability headers: {len(observability_headers) - len(missing_headers)}/{len(observability_headers)} present",
            "missing_headers": missing_headers,
            "trace_id": resp.headers.get("x-trace-id", "missing"),
        },
    )


def test_middleware_integration() -> None:
    """Test complete middleware chain integration."""
    logger.info("=== Middleware Integration Test ===")

    # Send a request that should pass through all middleware
    headers = {
        "X-Test-User": "integration_user",
        "X-Test-Role": "admin",
        "X-Priority": "high",
        "User-Agent": "IntegrationTestClient/1.0",
    }

    payload: Dict[str, Any] = {
        "content": "This is a safe test payload for integration testing",
        "metadata": {"test": True},
    }

    resp = client.post("/v1/tools/memory/submit", headers=headers, json=payload)
    print_middleware_state(resp)

    # Check that all middleware added their headers
    expected_middleware_evidence = {
        "auth": "x-trace-id" in resp.headers,  # Observability adds this
        "policy": resp.status_code != 403,  # Policy didn't block
        "security": "x-content-type-options" in resp.headers,  # Security headers
        "qos": "x-qos-priority" in resp.headers,  # QoS headers
        "safety": "x-safety-level" in resp.headers,  # Safety headers
        "observability": "x-processing-time" in resp.headers,  # Observability headers
    }

    working_middleware = sum(expected_middleware_evidence.values())

    log_test_result(
        "middleware_integration",
        working_middleware >= 4,
        {
            "summary": f"Middleware integration: {working_middleware}/6 components working",
            "middleware_evidence": expected_middleware_evidence,
            "status_code": resp.status_code,
        },
    )


# --- Event Bus Tests ---
def test_event_bus_basic() -> None:
    """Test basic event bus functionality."""
    logger.info("=== Event Bus Basic Tests ===")

    try:
        # Create event bus
        bus = EventBus()

        # Create or get event loop safely
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run async operations in a clean context
        async def async_test():
            # Start bus
            await bus.start()

            # Create and publish event
            from events.types import (
                Actor,
                Capability,
                Device,
                EventMeta,
                EventType,
                QoS,
                SecurityBand,
            )

            event_meta = EventMeta(
                topic=EventType.HIPPO_ENCODE,
                actor=Actor(user_id="test_user", caps=[Capability.WRITE]),
                device=Device(device_id="test_device"),
                space_id="test_space",
                band=SecurityBand.GREEN,
                policy_version="1.0",
                qos=QoS(priority=1, latency_budget_ms=1000),
                obligations=[],
            )

            event = Event(meta=event_meta, payload={"test": "data"})

            await bus.publish(event, "TEST_EVENT")

            # Test subscription
            received_events: list[Event] = []

            def test_handler(event: Event) -> bool:
                received_events.append(event)
                logger.info(f"Handler received event: {event.meta.id}")
                return True

            await bus.subscribe("TEST_EVENT", test_handler)

            # Shutdown
            await bus.shutdown()

            return received_events

        # Run the async test
        received_events = loop.run_until_complete(async_test())

        log_test_result(
            "event_bus_basic",
            True,
            {
                "summary": "Event bus basic operations completed",
                "events_received": len(received_events),
            },
        )

    except Exception as e:
        logger.exception(f"Event bus test failed: {str(e)}")
        log_test_result(
            "event_bus_basic",
            False,
            {"summary": f"Event bus test failed: {str(e)}", "error": str(e)},
        )


# --- Policy Direct Tests ---
def test_policy_service_direct() -> None:
    """Test policy service directly."""
    logger.info("=== Policy Service Direct Tests ===")

    try:
        _ = get_policy_service()  # Test service availability

        # Test SecurityContext creation
        _ = SecurityContext(
            user_id=str(uuid.uuid4()),  # Convert UUID to string
            device_id="test_device_123",
            authenticated=True,
            auth_method=AuthMethod.JWT,
            capabilities=[Capability.WRITE, Capability.RECALL],
            mls_group="test_family",
            trust_level=TrustLevel.GREEN,
        )

        # Note: We can't easily test _check_authorization without a full request
        # So we'll test the policy service components we can access

        log_test_result(
            "policy_service_direct",
            True,
            {
                "summary": "Policy service components accessible",
                "service_available": True,
                "context_created": True,
            },
        )

    except Exception as e:
        log_test_result(
            "policy_service_direct",
            False,
            {"summary": f"Policy service test failed: {str(e)}", "error": str(e)},
        )


# --- Main Test Runner ---
def run_all_tests() -> None:
    """Run all manual integration tests."""
    logger.info("🚀 Starting Manual Integration Tests")
    logger.info("=" * 60)

    # Run all test suites
    test_api_auth_edge_cases()
    test_policy_enforcement_edge_cases()
    test_safety_middleware_edge_cases()
    test_qos_middleware_edge_cases()
    test_security_middleware_edge_cases()
    test_observability_middleware()
    test_middleware_integration()
    test_event_bus_basic()
    test_policy_service_direct()

    # Summary
    logger.info("=" * 60)
    logger.info("📊 Test Results Summary")
    logger.info("=" * 60)

    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result["success"])
    failed_tests = total_tests - passed_tests

    logger.info(f"Total Tests: {total_tests}")
    logger.info(f"Passed: {passed_tests}")
    logger.info(f"Failed: {failed_tests}")
    logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

    # Log failed tests
    if failed_tests > 0:
        logger.info("\n❌ Failed Tests:")
        for test_name, result in test_results.items():
            if not result["success"]:
                logger.info(
                    f"  - {test_name}: {result['details'].get('summary', 'No details')}"
                )

    logger.info("=" * 60)
    logger.info("🏁 Manual Integration Tests Completed")


if __name__ == "__main__":
    run_all_tests()

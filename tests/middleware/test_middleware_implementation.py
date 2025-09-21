#!/usr/bin/env python3
"""
Detailed Middleware Implementation Test
Tests actual functionality of each middleware component.
"""

import time

import requests


def test_qos_implementation():
    """Test if QoS middleware is actually limiting requests."""
    print("🔧 Testing QoS Implementation")
    print("-" * 30)

    base_url = "http://localhost:8000"

    # Test 1: Priority headers
    headers = {"X-Priority": "critical", "X-Test-User": "test-user"}
    response = requests.get(
        f"{base_url}/api/v1/memories/search?q=test", headers=headers
    )

    qos_headers = {}
    for key, value in response.headers.items():
        if key.lower().startswith("x-qos"):
            qos_headers[key] = value

    print(f"QoS Headers: {qos_headers}")

    if qos_headers:
        print("✅ QoS middleware is adding headers - IMPLEMENTED")
    else:
        print("❌ QoS middleware not adding headers - NOT IMPLEMENTED")

    # Test 2: Timeout behavior (use a non-existent slow endpoint)
    try:
        slow_response = requests.get(
            f"{base_url}/api/v1/slow-endpoint", headers=headers, timeout=1
        )
        print(f"Slow endpoint status: {slow_response.status_code}")
    except requests.exceptions.Timeout:
        print("⏱️  Request timed out (expected)")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")


def test_auth_implementation():
    """Test authentication middleware enforcement."""
    print("\n🔐 Testing Auth Implementation")
    print("-" * 30)

    base_url = "http://localhost:8000"

    # Test 1: No auth headers
    response = requests.get(f"{base_url}/api/v1/memories/search?q=test")
    print(f"No auth - Status: {response.status_code}")

    # Test 2: With test auth
    headers = {"X-Test-User": "test-user", "X-Test-Role": "admin"}
    response = requests.get(
        f"{base_url}/api/v1/memories/search?q=test", headers=headers
    )
    print(f"With test auth - Status: {response.status_code}")

    # Test 3: Invalid auth
    headers = {"Authorization": "Bearer invalid-token"}
    response = requests.get(
        f"{base_url}/api/v1/memories/search?q=test", headers=headers
    )
    print(f"Invalid token - Status: {response.status_code}")

    if response.status_code == 401:
        print("✅ Auth middleware rejecting invalid tokens - IMPLEMENTED")
    else:
        print("⚠️  Auth middleware in dev mode (allowing requests)")


def test_safety_implementation():
    """Test safety middleware content filtering."""
    print("\n🛡️  Testing Safety Implementation")
    print("-" * 30)

    base_url = "http://localhost:8000"
    headers = {"X-Test-User": "test-user", "Content-Type": "application/json"}

    # Test dangerous content
    dangerous_payloads = [
        {"content": "DELETE FROM users; DROP TABLE memories;", "space_id": "test"},
        {"content": "<script>alert('xss')</script>", "space_id": "test"},
        {"content": "rm -rf / --no-preserve-root", "space_id": "test"},
        {"content": "SELECT * FROM passwords", "space_id": "test"},
    ]

    blocked_count = 0
    for payload in dangerous_payloads:
        try:
            response = requests.post(
                f"{base_url}/api/v1/memories", json=payload, headers=headers, timeout=5
            )
            if response.status_code == 403 and "safety" in response.text.lower():
                blocked_count += 1
                print(f"✅ Blocked dangerous content: {payload['content'][:30]}...")
            elif response.status_code >= 400:
                print(f"⚠️  Validation error (not safety): {response.status_code}")
            else:
                print(f"❌ Allowed dangerous content: {payload['content'][:30]}...")
        except Exception as e:
            print(f"Request error: {e}")

    if blocked_count > 0:
        print(
            f"✅ Safety middleware blocking {blocked_count}/{len(dangerous_payloads)} dangerous requests - IMPLEMENTED"
        )
    else:
        print("❌ Safety middleware not blocking dangerous content - NOT IMPLEMENTED")


def test_security_implementation():
    """Test security middleware threat detection."""
    print("\n🔒 Testing Security Implementation")
    print("-" * 30)

    base_url = "http://localhost:8000"
    headers = {"X-Test-User": "test-user"}

    # Test rapid requests (should trigger rate limiting)
    start_time = time.time()
    blocked_requests = 0

    for i in range(20):
        try:
            response = requests.get(
                f"{base_url}/api/v1/memories/search?q=test{i}",
                headers=headers,
                timeout=2,
            )
            if response.status_code == 429:  # Too Many Requests
                blocked_requests += 1
            elif response.status_code == 403:  # Forbidden
                blocked_requests += 1
        except:
            pass

    elapsed = time.time() - start_time
    print(f"Rapid requests: 20 requests in {elapsed:.2f}s")
    print(f"Blocked: {blocked_requests}/20")

    if blocked_requests > 0:
        print("✅ Security middleware rate limiting - IMPLEMENTED")
    else:
        print("❌ Security middleware not rate limiting - NOT IMPLEMENTED")

    # Check for security headers
    response = requests.get(
        f"{base_url}/api/v1/memories/search?q=test", headers=headers
    )
    security_headers = {}
    for key, value in response.headers.items():
        if any(
            sec in key.lower() for sec in ["security", "x-frame", "x-content", "strict"]
        ):
            security_headers[key] = value

    print(f"Security headers: {security_headers}")


def main():
    print("🧪 MemoryOS Middleware Implementation Analysis")
    print("=" * 50)

    test_qos_implementation()
    test_auth_implementation()
    test_safety_implementation()
    test_security_implementation()

    print("\n" + "=" * 50)
    print("📋 IMPLEMENTATION SUMMARY")
    print("=" * 50)
    print("Check the results above to see which middleware are:")
    print("✅ FULLY IMPLEMENTED - Enforcing rules and adding headers")
    print("⚠️  DEV MODE - Loaded but permissive for development")
    print("❌ NOT IMPLEMENTED - Not enforcing expected behavior")


if __name__ == "__main__":
    main()

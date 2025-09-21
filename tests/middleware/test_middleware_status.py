#!/usr/bin/env python3
"""
MemoryOS Middleware Status Report
Analyzes which middleware are loaded and functioning.
"""

import requests


def test_middleware_functionality():
    """Test middleware functionality with various requests."""

    base_url = "http://localhost:8000"

    print("🔍 MemoryOS Middleware Status Report")
    print("=" * 50)

    # Test 1: Health endpoint (should bypass auth)
    print("\n1️⃣  Testing Health Endpoint (Auth Bypass)")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print(f"   Headers: {dict(response.headers)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: Protected endpoint without auth
    print("\n2️⃣  Testing Protected Endpoint (No Auth)")
    try:
        response = requests.get(f"{base_url}/api/v1/memories/search?q=test", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Authentication middleware working - blocked unauth request")
        elif response.status_code == 200:
            print("   ⚠️  Authentication middleware allowing requests (dev mode?)")
            print(f"   Response length: {len(response.text)}")
        else:
            print(f"   🤔 Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: With test authentication
    print("\n3️⃣  Testing Protected Endpoint (Test Auth)")
    headers = {
        "X-Test-User": "test-user-123",
        "X-Test-Role": "user",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(
            f"{base_url}/api/v1/memories/search?q=test", headers=headers, timeout=5
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response length: {len(response.text)}")
        if "x-response-time" in response.headers:
            print(
                f"   ✅ Timing middleware working: {response.headers['x-response-time']}ms"
            )
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 4: Invalid/dangerous content (Safety middleware)
    print("\n4️⃣  Testing Safety Middleware")
    dangerous_data = {
        "content": "DELETE FROM users; DROP TABLE memories; malicious content",
        "metadata": {"type": "dangerous"},
    }
    try:
        response = requests.post(
            f"{base_url}/api/v1/memories",
            json=dangerous_data,
            headers=headers,
            timeout=5,
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 400 and "safety" in response.text.lower():
            print("   ✅ Safety middleware working - blocked dangerous content")
        elif response.status_code == 200:
            print("   ⚠️  Safety middleware might not be filtering content")
        else:
            print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 5: High load (QoS middleware)
    print("\n5️⃣  Testing QoS Middleware (Rate Limiting)")
    rapid_requests = 0
    blocked_requests = 0

    for i in range(10):
        try:
            response = requests.get(
                f"{base_url}/api/v1/memories/search?q=test{i}",
                headers=headers,
                timeout=2,
            )
            if response.status_code == 429:  # Too Many Requests
                blocked_requests += 1
            elif response.status_code == 200:
                rapid_requests += 1
        except:
            pass

    print(f"   Successful: {rapid_requests}/10")
    print(f"   Rate limited: {blocked_requests}/10")
    if blocked_requests > 0:
        print("   ✅ QoS middleware working - rate limiting active")
    else:
        print("   ⚠️  QoS middleware might not be rate limiting")

    print("\n" + "=" * 50)
    print("📊 MIDDLEWARE STATUS SUMMARY")
    print("=" * 50)

    # Test middleware chain order
    print("\n🔗 Testing Middleware Chain Order:")
    try:
        response = requests.get(
            f"{base_url}/api/v1/memories/search?q=chain_test",
            headers=headers,
            timeout=5,
        )
        headers_received = dict(response.headers)

        middleware_evidence = []
        if "x-response-time" in headers_received:
            middleware_evidence.append("✅ Timing/Observability")
        if response.status_code in [200, 401, 403]:
            middleware_evidence.append("✅ Authentication")
        if "server" in headers_received:
            middleware_evidence.append("✅ Base HTTP")

        print("   Detected middleware:")
        for evidence in middleware_evidence:
            print(f"     {evidence}")

    except Exception as e:
        print(f"   ❌ Chain test error: {e}")


if __name__ == "__main__":
    test_middleware_functionality()

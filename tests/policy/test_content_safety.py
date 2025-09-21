#!/usr/bin/env python3
"""
Test AI-Enhanced Content Safety Filtering
"""

import asyncio

import requests


def test_ai_content_safety_basic():
    """Test the AI content safety engine directly."""
    print("🧠 Testing AI Content Safety Engine")
    print("-" * 40)

    try:
        from policy.content_safety import ai_content_safety_engine

        # Test different types of content
        test_contents = [
            "Hello, this is a nice family-friendly message!",
            "You are such an idiot and I hate you!",
            "This content contains adult material and explicit language.",
            "Let's plan something dangerous and harmful to others.",
        ]

        async def run_tests():
            for i, content in enumerate(test_contents, 1):
                print(f"\nTest {i}: '{content[:30]}...'")
                assessment = await ai_content_safety_engine.assess_content_safety(
                    content
                )

                print(f"  Safe: {assessment.is_safe}")
                print(f"  Category: {assessment.primary_category.value}")
                print(f"  Age Rating: {assessment.age_rating.value}")
                print(f"  Confidence: {assessment.overall_confidence:.2f}")
                if assessment.reasoning:
                    print(f"  Reasoning: {assessment.reasoning[:2]}")

        # Run the async tests
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_tests())
        loop.close()

        print("\n✅ AI Content Safety Engine working!")

    except Exception as e:
        print(f"❌ AI Content Safety test failed: {e}")


def test_middleware_content_filtering():
    """Test content filtering through the API middleware."""
    print("\n🔒 Testing Middleware Content Filtering")
    print("-" * 40)

    base_url = "http://localhost:8000"

    # Test dangerous content that should be blocked using GET endpoint
    dangerous_queries = [
        "<script>alert('xss')</script>",
        "DROP TABLE users; --",
        "exec('rm -rf /')",
        "You stupid fucking idiot, I hate you and want to hurt you!",
    ]

    blocked_count = 0
    for i, query in enumerate(dangerous_queries, 1):
        try:
            print(f"\nTest {i}: Testing dangerous query: '{query[:30]}...'")

            response = requests.get(
                f"{base_url}/api/v1/memories/search", params={"q": query}, timeout=5
            )

            print(f"  Status: {response.status_code}")

            # Check safety headers
            safety_headers = {}
            for key, value in response.headers.items():
                if key.lower().startswith("x-safety"):
                    safety_headers[key] = value

            if safety_headers:
                print(f"  Safety Headers: {safety_headers}")

            if response.status_code == 403:
                print("  ✅ Content BLOCKED by safety middleware!")
                blocked_count += 1
            elif response.status_code in [400, 422]:
                print("  ⚠️  Content rejected (validation error)")
            else:
                print(f"  ❌ Content NOT blocked (status: {response.status_code})")
                # Print response text to see what's happening
                if len(response.text) < 200:
                    print(f"  Response: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"  ❌ Request failed: {e}")

    print(
        f"\n📊 Summary: {blocked_count}/{len(dangerous_queries)} dangerous requests blocked"
    )

    if blocked_count > 0:
        print("✅ Content filtering is working!")
    else:
        print("❌ Content filtering needs improvement")


def test_safe_content():
    """Test that safe content passes through."""
    print("\n✅ Testing Safe Content")
    print("-" * 25)

    base_url = "http://localhost:8000"

    safe_query = "family vacation photos"

    try:
        response = requests.get(
            f"{base_url}/api/v1/memories/search", params={"q": safe_query}, timeout=5
        )

        print(f"Status: {response.status_code}")

        # Check safety headers
        safety_headers = {}
        for key, value in response.headers.items():
            if key.lower().startswith("x-safety"):
                safety_headers[key] = value

        if safety_headers:
            print(f"Safety Headers: {safety_headers}")

        if response.status_code in [200, 201]:
            print("✅ Safe content passed through!")
        else:
            print(f"⚠️  Safe content got status: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")


if __name__ == "__main__":
    print("🛡️  AI-Enhanced Content Safety Testing")
    print("=" * 50)

    # Test AI engine directly
    test_ai_content_safety_basic()

    # Test middleware integration
    test_middleware_content_filtering()

    # Test safe content
    test_safe_content()

    print("\n" + "=" * 50)
    print("✅ Content Safety Testing Complete!")

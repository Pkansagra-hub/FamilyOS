#!/usr/bin/env python3
"""
Debug AI Content Safety
"""

import asyncio


async def debug_ai_assessment():
    """Debug the AI content safety assessment."""
    from policy.content_safety import ai_content_safety_engine

    # Test with clearly dangerous content
    dangerous_content = "You stupid fucking idiot, I hate you and want to kill you!"

    print(f"Testing: '{dangerous_content}'")
    assessment = await ai_content_safety_engine.assess_content_safety(dangerous_content)

    print(f"Is Safe: {assessment.is_safe}")
    print(f"Primary Category: {assessment.primary_category}")
    print(f"Confidence: {assessment.overall_confidence}")
    print(f"Category Scores: {assessment.category_scores}")
    print(f"Models Used: {assessment.models_used}")
    print(f"Reasoning: {assessment.reasoning}")

    # Test XSS
    xss_content = "<script>alert('xss attack')</script>"
    print(f"\nTesting XSS: '{xss_content}'")
    assessment2 = await ai_content_safety_engine.assess_content_safety(xss_content)

    print(f"Is Safe: {assessment2.is_safe}")
    print(f"Primary Category: {assessment2.primary_category}")
    print(f"Confidence: {assessment2.overall_confidence}")
    print(f"Category Scores: {assessment2.category_scores}")
    print(f"Reasoning: {assessment2.reasoning}")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(debug_ai_assessment())
    loop.close()

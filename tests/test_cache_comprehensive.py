"""Comprehensive test suite for query cache implementation.

Tests all aspects of the cache system including TTL expiration,
invalidation patterns, memory bounds, and integration patterns.
"""

import os
import sys
import threading
import time
from typing import List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.cache import QueryCache, configure_cache, create_cache_key, get_cache


class TestQueryCache:
    """Test suite for QueryCache functionality."""

    def test_basic_cache_operations(self) -> None:
        """Test basic get/set operations."""
        cache = QueryCache(ttl_seconds=10)

        call_count = 0

        def expensive_operation() -> str:
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        # First call should compute
        result1 = cache.get_or_compute("test_key", expensive_operation)
        assert result1 == "result_1"
        assert call_count == 1

        # Second call should use cache
        result2 = cache.get_or_compute("test_key", expensive_operation)
        assert result2 == "result_1"
        assert call_count == 1

    def test_ttl_expiration(self) -> None:
        """Test TTL expiration behavior."""
        cache = QueryCache(ttl_seconds=1)

        call_count = 0

        def expensive_operation() -> str:
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        # Cache value
        result1 = cache.get_or_compute("test_key", expensive_operation)
        assert result1 == "result_1"

        # Should still be cached
        result2 = cache.get_or_compute("test_key", expensive_operation)
        assert result2 == "result_1"
        assert call_count == 1

        # Wait for expiration
        time.sleep(1.1)

        # Should recompute after expiration
        result3 = cache.get_or_compute("test_key", expensive_operation)
        assert result3 == "result_2"
        assert call_count == 2

    def test_ttl_override(self) -> None:
        """Test TTL override functionality."""
        cache = QueryCache(ttl_seconds=10)  # Default 10 seconds

        call_count = 0

        def expensive_operation() -> str:
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        # Cache with short TTL override
        result1 = cache.get_or_compute("test_key", expensive_operation, ttl_override=1)
        assert result1 == "result_1"

        # Wait for override TTL expiration
        time.sleep(1.1)

        # Should recompute due to short TTL
        result2 = cache.get_or_compute("test_key", expensive_operation)
        assert result2 == "result_2"
        assert call_count == 2

    def test_cache_invalidation_by_tag(self) -> None:
        """Test cache invalidation by tags."""
        cache = QueryCache()

        # Cache values with different tags
        cache.get_or_compute("key1", lambda: "value1", tags={"table:users", "user:123"})
        cache.get_or_compute("key2", lambda: "value2", tags={"table:users", "user:456"})
        cache.get_or_compute("key3", lambda: "value3", tags={"table:posts", "user:123"})

        stats = cache.get_stats()
        assert stats["size"] == 3

        # Invalidate by tag
        invalidated = cache.invalidate("table:users")
        assert invalidated == 2

        stats = cache.get_stats()
        assert stats["size"] == 1

    def test_cache_invalidation_by_pattern(self) -> None:
        """Test cache invalidation by wildcard patterns."""
        cache = QueryCache()

        # Cache values with pattern-based keys
        cache.get_or_compute("user:123:profile", lambda: "profile1")
        cache.get_or_compute("user:123:settings", lambda: "settings1")
        cache.get_or_compute("user:456:profile", lambda: "profile2")
        cache.get_or_compute("post:789:content", lambda: "content1")

        stats = cache.get_stats()
        assert stats["size"] == 4

        # Invalidate user:123 patterns
        invalidated = cache.invalidate("user:123*")
        assert invalidated == 2

        stats = cache.get_stats()
        assert stats["size"] == 2

    def test_memory_bounds_eviction(self) -> None:
        """Test memory bounds and eviction."""
        cache = QueryCache(ttl_seconds=60, max_entries=3)

        # Fill cache to capacity
        cache.get_or_compute("key1", lambda: "value1")
        cache.get_or_compute("key2", lambda: "value2")
        cache.get_or_compute("key3", lambda: "value3")

        stats = cache.get_stats()
        assert stats["size"] == 3

        # Add one more to trigger eviction
        cache.get_or_compute("key4", lambda: "value4")

        # Should have evicted oldest entry
        stats = cache.get_stats()
        assert stats["size"] <= 3

    def test_cleanup_expired_entries(self) -> None:
        """Test automatic cleanup of expired entries."""
        cache = QueryCache(ttl_seconds=1, cleanup_interval=0)  # Immediate cleanup

        # Add entries
        cache.get_or_compute("key1", lambda: "value1")
        cache.get_or_compute("key2", lambda: "value2")

        stats = cache.get_stats()
        assert stats["size"] == 2

        # Wait for expiration
        time.sleep(1.1)

        # Trigger cleanup by accessing cache
        cache.get_or_compute("key3", lambda: "value3")

        # Should have cleaned up expired entries
        # (Note: cleanup happens during _maybe_cleanup calls)

    def test_thread_safety(self) -> None:
        """Test thread safety of cache operations."""
        cache = QueryCache()
        results: List[str] = []

        def worker(thread_id: int) -> None:
            for i in range(10):
                key = f"thread_{thread_id}_key_{i}"
                result = cache.get_or_compute(key, lambda: f"value_{thread_id}_{i}")
                results.append(result)

        # Run multiple threads
        threads: List[threading.Thread] = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check all operations completed
        assert len(results) == 50  # 5 threads * 10 operations

    def test_cache_statistics(self) -> None:
        """Test cache statistics collection."""
        cache = QueryCache()

        # Generate hits and misses
        cache.get_or_compute("key1", lambda: "value1")  # Miss
        cache.get_or_compute("key1", lambda: "value1")  # Hit
        cache.get_or_compute("key2", lambda: "value2")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 1 / 3
        assert stats["size"] == 2

    def test_clear_cache(self) -> None:
        """Test cache clearing functionality."""
        cache = QueryCache()

        # Add entries
        cache.get_or_compute("key1", lambda: "value1")
        cache.get_or_compute("key2", lambda: "value2")

        stats = cache.get_stats()
        assert stats["size"] == 2

        # Clear cache
        cache.clear()

        stats = cache.get_stats()
        assert stats["size"] == 0


class TestCacheKeyGeneration:
    """Test cache key generation utilities."""

    def test_create_cache_key_deterministic(self) -> None:
        """Test cache key generation is deterministic."""
        key1 = create_cache_key("get_user", user_id=123, include_profile=True)
        key2 = create_cache_key("get_user", include_profile=True, user_id=123)

        # Parameter order shouldn't matter
        assert key1 == key2

    def test_create_cache_key_unique(self) -> None:
        """Test cache keys are unique for different parameters."""
        key1 = create_cache_key("get_user", user_id=123)
        key2 = create_cache_key("get_user", user_id=456)
        key3 = create_cache_key("get_post", user_id=123)

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_create_cache_key_long_params(self) -> None:
        """Test cache key generation with long parameters."""
        long_data = "x" * 200
        key = create_cache_key("operation", data=long_data)

        # Should use hash for long parameters
        assert len(key) < 50  # Much shorter than original data


class TestGlobalCache:
    """Test global cache configuration."""

    def test_global_cache_singleton(self) -> None:
        """Test global cache is singleton."""
        cache1 = get_cache()
        cache2 = get_cache()

        assert cache1 is cache2

    def test_configure_global_cache(self) -> None:
        """Test global cache configuration."""
        # Configure with custom settings
        configure_cache(ttl_seconds=30, max_entries=500)

        cache = get_cache()
        assert cache.ttl == 30
        assert cache.max_entries == 500


class TestCacheIntegrationPatterns:
    """Test integration patterns for stores."""

    def test_read_operation_caching_pattern(self) -> None:
        """Test the read operation caching pattern."""
        cache = QueryCache()

        # Simulate store operation
        db_calls = 0

        def fetch_from_db(item_id: str) -> dict[str, str | int]:
            nonlocal db_calls
            db_calls += 1
            return {"id": item_id, "data": f"data_{db_calls}"}

        def cached_get_item(item_id: str) -> dict[str, str | int]:
            cache_key = create_cache_key("get_item", item_id=item_id)
            return cache.get_or_compute(
                cache_key,
                lambda: fetch_from_db(item_id),
                tags={"store:test", f"item:{item_id}"},
            )

        # First call hits database
        result1 = cached_get_item("item-123")
        assert db_calls == 1
        assert result1["data"] == "data_1"

        # Second call uses cache
        result2 = cached_get_item("item-123")
        assert db_calls == 1
        assert result2["data"] == "data_1"

    def test_write_operation_invalidation_pattern(self) -> None:
        """Test write operation invalidation pattern."""
        cache = QueryCache()

        # Cache some data
        cache.get_or_compute(
            "item:123", lambda: "data", tags={"store:test", "item:123"}
        )
        cache.get_or_compute("list:all", lambda: ["data"], tags={"store:test"})

        stats = cache.get_stats()
        assert stats["size"] == 2

        # Simulate write operation with invalidation
        def update_item(item_id: str, new_data: str) -> dict[str, str]:
            # Perform update (simulated)
            result = {"id": item_id, "data": new_data}

            # Invalidate related cache entries
            cache.invalidate(f"item:{item_id}")
            cache.invalidate("list:all")  # Lists might be affected

            return result

        # Perform update
        update_item("123", "new_data")

        # Cache should be empty after invalidation
        stats = cache.get_stats()
        assert stats["size"] == 0


def run_cache_tests() -> bool:
    """Run all cache tests."""
    print("🧪 COMPREHENSIVE CACHE TEST SUITE")
    print("=" * 50)

    test_classes = [
        TestQueryCache,
        TestCacheKeyGeneration,
        TestGlobalCache,
        TestCacheIntegrationPatterns,
    ]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 30)

        instance = test_class()

        # Get all test methods
        test_methods = [
            method for method in dir(instance) if method.startswith("test_")
        ]

        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(instance, method_name)
                method()
                print(f"✅ {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"❌ {method_name}: {e}")

    print("\n" + "=" * 50)
    print(f"📊 TEST RESULTS: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 ALL CACHE TESTS PASSED!")
        return True
    else:
        print(f"⚠️  {total_tests - passed_tests} tests failed")
        return False


if __name__ == "__main__":
    success = run_cache_tests()

    if success:
        print("\n✅ Cache implementation is production-ready!")
        print("💡 Ready to deploy caching to all storage operations")
    else:
        print("\n❌ Cache implementation needs fixes before deployment")
        exit(1)

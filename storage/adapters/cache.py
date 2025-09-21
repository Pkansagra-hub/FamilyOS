"""Query caching layer for storage operations.

Provides intelligent query caching with TTL expiration, invalidation patterns,
and memory management for high-performance storage operations.
"""

import hashlib
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Set, Tuple

# Use standard logging for now - can wire to observability later
logger = logging.getLogger(__name__)


class QueryCache:
    """Thread-safe query cache with TTL and invalidation support.

    Features:
    - TTL-based expiration
    - Key-based invalidation patterns
    - Memory bounds management
    - Thread-safe operations
    - Metrics collection
    """

    def __init__(
        self,
        ttl_seconds: int = 60,
        max_entries: int = 1000,
        cleanup_interval: int = 300,
    ):
        """Initialize query cache.

        Args:
            ttl_seconds: Default TTL for cache entries
            max_entries: Maximum number of cache entries
            cleanup_interval: Seconds between cleanup runs
        """
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self.cleanup_interval = cleanup_interval

        # Cache storage: key -> (value, timestamp, tags)
        self._cache: Dict[str, Tuple[Any, float, Set[str]]] = {}
        self._lock = threading.RLock()

        # Invalidation patterns
        self._invalidation_patterns: Dict[str, Set[str]] = {}

        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        # Last cleanup time
        self._last_cleanup = time.time()

        logger.info(
            "QueryCache initialized",
            extra={
                "ttl_seconds": ttl_seconds,
                "max_entries": max_entries,
                "cleanup_interval": cleanup_interval,
            },
        )

    def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl_override: Optional[int] = None,
        tags: Optional[Set[str]] = None,
    ) -> Any:
        """Get cached value or compute and cache new value.

        Args:
            key: Cache key
            compute_fn: Function to compute value if not cached
            ttl_override: Override default TTL for this entry
            tags: Tags for invalidation patterns

        Returns:
            Cached or computed value
        """
        tags = tags or set()

        # Try to get from cache first
        cached_value = self._get(key)
        if cached_value is not None:
            self._hits += 1
            # TODO: Wire to observability metrics
            # counter('familyos_storage_cache_hits_total').inc()
            return cached_value

        # Cache miss - compute value
        self._misses += 1
        # TODO: Wire to observability metrics
        # counter('familyos_storage_cache_misses_total').inc()

        # TODO: Add timing metrics
        # with histogram('familyos_storage_cache_compute_duration_seconds').time():
        result = compute_fn()

        # Cache the result
        self._put(key, result, ttl_override or self.ttl, tags)

        return result

    def invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern.

        Args:
            pattern: Invalidation pattern (e.g., "episodic_events:*")

        Returns:
            Number of entries invalidated
        """
        with self._lock:
            invalidated = 0
            keys_to_remove: set[str] = set()

            for cache_key, (_, _, tags, _) in self._cache.items():
                if self._matches_pattern(cache_key, pattern, tags):
                    keys_to_remove.add(cache_key)
                    invalidated += 1

            for key in keys_to_remove:
                del self._cache[key]

            # TODO: Wire to observability metrics
            # counter('familyos_storage_cache_invalidations_total').inc(invalidated)

            logger.debug(
                "Cache invalidation completed",
                extra={"pattern": pattern, "invalidated_count": invalidated},
            )

            return invalidated

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._invalidation_patterns.clear()

            # TODO: Wire to observability metrics
            # counter('familyos_storage_cache_clears_total').inc()

            logger.info("Cache cleared", extra={"cleared_count": count})

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests) if total_requests > 0 else 0.0

            return {
                "size": len(self._cache),
                "max_entries": self.max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "evictions": self._evictions,
                "ttl_seconds": self.ttl,
            }

    def _get(self, key: str) -> Optional[Any]:
        """Get value from cache if valid.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            self._maybe_cleanup()

            if key not in self._cache:
                return None

            value, expiration_time, _, _ = self._cache[key]

            if self._is_expired(expiration_time):
                del self._cache[key]
                return None

            return value

    def _put(self, key: str, value: Any, ttl: int, tags: Set[str]) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            tags: Tags for invalidation
        """
        with self._lock:
            self._maybe_cleanup()
            self._maybe_evict()

            timestamp = time.time()
            expiration_time = timestamp + ttl
            # Store: (value, expiration_time, tags, creation_time)
            self._cache[key] = (value, expiration_time, tags, timestamp)

            # Store invalidation patterns
            for tag in tags:
                if tag not in self._invalidation_patterns:
                    self._invalidation_patterns[tag] = set()
                self._invalidation_patterns[tag].add(key)

    def _is_expired(self, expiration_time: float) -> bool:
        """Check if expiration time has passed.

        Args:
            expiration_time: Entry expiration time

        Returns:
            True if expired
        """
        return time.time() > expiration_time

    def _matches_pattern(self, key: str, pattern: str, tags: Set[str]) -> bool:
        """Check if key matches invalidation pattern.

        Args:
            key: Cache key
            pattern: Invalidation pattern
            tags: Entry tags

        Returns:
            True if matches pattern
        """
        # Check exact tag match
        if pattern in tags:
            return True

        # Check wildcard patterns
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return key.startswith(prefix) or any(tag.startswith(prefix) for tag in tags)

        # Check exact key match
        return key == pattern

    def _maybe_cleanup(self) -> None:
        """Clean up expired entries if needed."""
        now = time.time()
        if (now - self._last_cleanup) < self.cleanup_interval:
            return

        self._last_cleanup = now
        expired_keys: list[str] = []

        for key, (_, expiration_time, _, _) in self._cache.items():
            if self._is_expired(expiration_time):
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(
                "Cache cleanup completed", extra={"expired_count": len(expired_keys)}
            )

    def _maybe_evict(self) -> None:
        """Evict oldest entries if cache is full."""
        if len(self._cache) < self.max_entries:
            return

        # Evict oldest 10% of entries
        evict_count = max(1, self.max_entries // 10)

        # Sort by creation timestamp and evict oldest
        sorted_items = sorted(
            self._cache.items(),
            key=lambda x: x[1][3],  # Sort by creation timestamp (4th element)
        )

        for i in range(evict_count):
            key = sorted_items[i][0]
            del self._cache[key]
            self._evictions += 1

        logger.debug("Cache eviction completed", extra={"evicted_count": evict_count})


def create_cache_key(operation: str, **params: Any) -> str:
    """Create deterministic cache key from operation and parameters.

    Args:
        operation: Operation name (e.g., "get_by_space")
        **params: Parameters for the operation

    Returns:
        Deterministic cache key
    """
    # Create sorted parameter string for consistency
    param_str = json.dumps(params, sort_keys=True, default=str)

    # Create hash for long parameter strings
    if len(param_str) > 100:
        param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        return f"{operation}:{param_hash}"

    return f"{operation}:{param_str}"


# Global cache instance
_global_cache: Optional[QueryCache] = None


def get_cache() -> QueryCache:
    """Get global cache instance.

    Returns:
        Global QueryCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = QueryCache()
    return _global_cache


def configure_cache(
    ttl_seconds: int = 60, max_entries: int = 1000, cleanup_interval: int = 300
) -> None:
    """Configure global cache instance.

    Args:
        ttl_seconds: Default TTL for cache entries
        max_entries: Maximum number of cache entries
        cleanup_interval: Seconds between cleanup runs
    """
    global _global_cache
    _global_cache = QueryCache(ttl_seconds, max_entries, cleanup_interval)

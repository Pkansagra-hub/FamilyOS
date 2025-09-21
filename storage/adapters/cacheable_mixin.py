"""Cacheable store mixin for adding query caching to storage operations."""

import functools
from typing import Any, Dict, Optional, Set

from .cache import QueryCache, create_cache_key, get_cache


class CacheableMixin:
    """Mixin to add caching capabilities to storage classes.

    Provides caching for read operations with automatic invalidation on writes.
    Can be mixed into any store class to add caching functionality.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache: Optional[QueryCache] = None
        self._cache_enabled = True

    def configure_cache(
        self, cache: Optional[QueryCache] = None, enabled: bool = True
    ) -> None:
        """Configure caching for this store.

        Args:
            cache: Cache instance to use, or None for global cache
            enabled: Whether caching is enabled
        """
        self._cache = cache or get_cache()
        self._cache_enabled = enabled

    def cached(
        self,
        ttl_seconds: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        key_params: Optional[list[str]] = None,
    ):
        """Decorator to cache method results.

        Args:
            ttl_seconds: Override TTL for this operation
            tags: Tags for invalidation patterns
            key_params: Specific parameters to include in cache key

        Returns:
            Decorated method with caching
        """

        def decorator(method: Callable) -> Callable:
            @functools.wraps(method)
            def wrapper(self, *args, **kwargs):
                # Skip caching if disabled or no cache configured
                if not self._cache_enabled or not self._cache:
                    return method(self, *args, **kwargs)

                # Create cache key
                operation_name = f"{self.get_store_name()}.{method.__name__}"

                # Build parameters for cache key
                cache_params = {}
                if key_params:
                    # Use specific parameters
                    for i, param_name in enumerate(key_params):
                        if i < len(args):
                            cache_params[param_name] = args[i]
                        elif param_name in kwargs:
                            cache_params[param_name] = kwargs[param_name]
                else:
                    # Use all parameters
                    if args:
                        cache_params.update(
                            {f"arg_{i}": arg for i, arg in enumerate(args)}
                        )
                    cache_params.update(kwargs)

                cache_key = create_cache_key(operation_name, **cache_params)

                # Build cache tags
                cache_tags = tags or set()
                cache_tags.add(f"store:{self.get_store_name()}")

                # Get or compute cached result
                def compute_result():
                    return method(self, *args, **kwargs)

                return self._cache.get_or_compute(
                    cache_key, compute_result, ttl_override=ttl_seconds, tags=cache_tags
                )

            return wrapper

        return decorator

    def invalidate_cache(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern.

        Args:
            pattern: Invalidation pattern

        Returns:
            Number of entries invalidated
        """
        if not self._cache:
            return 0

        return self._cache.invalidate(pattern)

    def invalidate_store_cache(self) -> int:
        """Invalidate all cache entries for this store.

        Returns:
            Number of entries invalidated
        """
        store_pattern = f"store:{self.get_store_name()}"
        return self.invalidate_cache(store_pattern)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics dictionary
        """
        if not self._cache:
            return {"cache_enabled": False}

        stats = self._cache.get_stats()
        stats["cache_enabled"] = self._cache_enabled
        stats["store_name"] = self.get_store_name()
        return stats


def cache_read_operation(
    ttl_seconds: Optional[int] = None,
    tags: Optional[Set[str]] = None,
    key_params: Optional[list[str]] = None,
):
    """Decorator for caching read operations on store methods.

    Usage:
        @cache_read_operation(ttl_seconds=300, tags={"episodic_records"})
        def get_record(self, record_id: str, space_id: str):
            # ... implementation

    Args:
        ttl_seconds: Override TTL for this operation
        tags: Tags for invalidation patterns
        key_params: Specific parameters to include in cache key
    """

    def decorator(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            # Check if instance has caching capabilities
            if not hasattr(self, "_cache_enabled") or not self._cache_enabled:
                return method(self, *args, **kwargs)

            if not hasattr(self, "_cache") or not self._cache:
                return method(self, *args, **kwargs)

            # Create cache key
            operation_name = f"{self.get_store_name()}.{method.__name__}"

            # Build parameters for cache key
            cache_params = {}
            if key_params:
                # Use specific parameters
                for i, param_name in enumerate(key_params):
                    if i < len(args):
                        cache_params[param_name] = args[i]
                    elif param_name in kwargs:
                        cache_params[param_name] = kwargs[param_name]
            else:
                # Use all parameters
                if args:
                    cache_params.update({f"arg_{i}": arg for i, arg in enumerate(args)})
                cache_params.update(kwargs)

            cache_key = create_cache_key(operation_name, **cache_params)

            # Build cache tags
            cache_tags = tags or set()
            cache_tags.add(f"store:{self.get_store_name()}")

            # Get or compute cached result
            def compute_result():
                return method(self, *args, **kwargs)

            return self._cache.get_or_compute(
                cache_key, compute_result, ttl_override=ttl_seconds, tags=cache_tags
            )

        return wrapper

    return decorator


def invalidate_on_write(patterns: Optional[list[str]] = None):
    """Decorator to invalidate cache on write operations.

    Usage:
        @invalidate_on_write(["store:episodic", "episodic_records"])
        def create_record(self, record_data):
            # ... implementation

    Args:
        patterns: Cache invalidation patterns to apply
    """

    def decorator(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            # Execute the write operation
            result = method(self, *args, **kwargs)

            # Invalidate cache if caching is enabled
            if hasattr(self, "_cache_enabled") and self._cache_enabled:
                if hasattr(self, "_cache") and self._cache:
                    invalidation_patterns = patterns or [
                        f"store:{self.get_store_name()}"
                    ]

                    for pattern in invalidation_patterns:
                        self._cache.invalidate(pattern)

            return result

        return wrapper

    return decorator

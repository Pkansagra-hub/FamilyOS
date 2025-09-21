"""Example of integrating caching into episodic store.

This demonstrates how to add caching to existing store methods.
"""

from typing import List, Optional, Set

from storage.adapters.cache import QueryCache, create_cache_key, get_cache
from storage.stores.memory.episodic_store import EpisodicRecord, EpisodicStore


class CachedEpisodicStore(EpisodicStore):
    """Episodic store with caching capabilities.

    Demonstrates integration of query caching into storage operations.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache: Optional[QueryCache] = None
        self._cache_enabled = True

    def configure_cache(
        self, cache: Optional[QueryCache] = None, enabled: bool = True
    ) -> None:
        """Configure caching for this store."""
        self._cache = cache or get_cache()
        self._cache_enabled = enabled

    def get_record(self, record_id: str, space_id: str) -> Optional[EpisodicRecord]:
        """Get episodic record by ID and space (with caching)."""
        if not self._cache_enabled or not self._cache:
            return super().get_record(record_id, space_id)

        # Create cache key
        cache_key = create_cache_key(
            "episodic.get_record", record_id=record_id, space_id=space_id
        )

        # Cache tags for invalidation
        cache_tags: Set[str] = {
            "store:episodic",
            f"episodic_record:{record_id}",
            f"space:{space_id}",
        }

        # Get or compute cached result
        def compute_result():
            return super(CachedEpisodicStore, self).get_record(record_id, space_id)

        return self._cache.get_or_compute(
            cache_key,
            compute_result,
            ttl_override=300,  # 5 minutes for individual records
            tags=cache_tags,
        )

    def list_sequences(
        self,
        space_id: str,
        limit: int = 100,
        offset: int = 0,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[dict]:
        """List episodic sequences (with caching)."""
        if not self._cache_enabled or not self._cache:
            return super().list_sequences(space_id, limit, offset, start_time, end_time)

        # Create cache key
        cache_key = create_cache_key(
            "episodic.list_sequences",
            space_id=space_id,
            limit=limit,
            offset=offset,
            start_time=start_time,
            end_time=end_time,
        )

        # Cache tags for invalidation
        cache_tags: Set[str] = {
            "store:episodic",
            f"space:{space_id}",
            "episodic_sequences",
        }

        # Get or compute cached result
        def compute_result():
            return super(CachedEpisodicStore, self).list_sequences(
                space_id, limit, offset, start_time, end_time
            )

        return self._cache.get_or_compute(
            cache_key,
            compute_result,
            ttl_override=120,  # 2 minutes for lists
            tags=cache_tags,
        )

    def create_record(self, record_data: dict) -> dict:
        """Create episodic record (with cache invalidation)."""
        # Execute the write operation
        result = super().create_record(record_data)

        # Invalidate related cache entries
        if self._cache_enabled and self._cache:
            space_id = record_data.get("space_id")
            invalidation_patterns = [
                "store:episodic",
                "episodic_sequences",
            ]

            if space_id:
                invalidation_patterns.append(f"space:{space_id}")

            for pattern in invalidation_patterns:
                self._cache.invalidate(pattern)

        return result

    def update_record(self, record_id: str, record_data: dict) -> dict:
        """Update episodic record (with cache invalidation)."""
        # Execute the write operation
        result = super().update_record(record_id, record_data)

        # Invalidate related cache entries
        if self._cache_enabled and self._cache:
            space_id = record_data.get("space_id")
            invalidation_patterns = [
                f"episodic_record:{record_id}",
                "episodic_sequences",
            ]

            if space_id:
                invalidation_patterns.append(f"space:{space_id}")

            for pattern in invalidation_patterns:
                self._cache.invalidate(pattern)

        return result

    def get_cache_stats(self) -> dict:
        """Get cache statistics for this store."""
        if not self._cache:
            return {"cache_enabled": False}

        stats = self._cache.get_stats()
        stats["cache_enabled"] = self._cache_enabled
        stats["store_name"] = self.get_store_name()
        return stats

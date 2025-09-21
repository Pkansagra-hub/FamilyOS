"""
Working Memory Hierarchical Cache System
=======================================

This module implements a multi-level cache system for working memory that mimics
CPU cache hierarchies (L1/L2/L3) but optimized for cognitive operations.

**Cache Levels:**
- L1 Cache: Ultra-fast in-memory buffer (OrderedDict) - immediate access items
- L2 Cache: Fast session-local cache (in-memory with TTL) - recently accessed items
- L3 Cache: Persistent storage (SQLite via UoW) - session recovery and patterns

**Cache Properties:**
- L1: ~10-20 items, nanosecond access, volatile
- L2: ~50-100 items, microsecond access, session-scoped
- L3: Unlimited items, millisecond access, persistent

**Neuroscience Inspiration:**
This mirrors the brain's memory hierarchy from immediate neural firing patterns
(L1) to short-term synaptic plasticity (L2) to long-term structural changes (L3).

**Research Backing:**
- Atkinson & Shiffrin (1968): Multi-store memory model
- Baddeley & Hitch (1974): Working memory with multiple components
- Cowan (2001): Focus of attention and activated memory
- Oberauer (2002): Working memory capacity limits and time-based decay
"""

import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from observability.logging import get_json_logger

# from observability.metrics import record_cache_operation  # TODO: Fix observability metrics
from .working_memory_store import WorkingMemoryItem, WorkingMemoryStore

logger = get_json_logger(__name__)


class CacheLevel(Enum):
    """Cache level enumeration."""

    L1 = "l1"  # Ultra-fast in-memory
    L2 = "l2"  # Fast session-local
    L3 = "l3"  # Persistent storage


@dataclass
class CacheMetrics:
    """Cache performance metrics."""

    hits: int = 0
    misses: int = 0
    promotions: int = 0
    demotions: int = 0
    evictions: int = 0
    total_access_time_ns: int = 0
    last_reset: float = field(default_factory=time.time)

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    @property
    def avg_access_time_ns(self) -> float:
        """Calculate average access time in nanoseconds."""
        total_ops = self.hits + self.misses
        return self.total_access_time_ns / total_ops if total_ops > 0 else 0.0

    def reset(self) -> None:
        """Reset metrics."""
        self.hits = 0
        self.misses = 0
        self.promotions = 0
        self.demotions = 0
        self.evictions = 0
        self.total_access_time_ns = 0
        self.last_reset = time.time()


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    item: WorkingMemoryItem
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    added_at: float = field(default_factory=time.time)
    promotion_score: float = 0.0
    ttl: Optional[float] = None  # Time-to-live for L2 cache

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired (L2 cache only)."""
        if self.ttl is None:
            return False
        return time.time() > (self.added_at + self.ttl)

    def calculate_promotion_score(self) -> float:
        """Calculate score for cache promotion decisions."""
        now = time.time()
        age = now - self.added_at
        recency = max(0, 1.0 - (now - self.last_accessed) / 3600)  # Decay over 1 hour
        frequency = min(1.0, self.access_count / 10.0)  # Normalize access count
        priority = self.item.priority / 5.0  # Normalize priority (1-5 scale)

        # Combined score with weights
        score = (
            priority * 0.4  # Priority is most important
            + frequency * 0.3  # Frequency matters
            + recency * 0.2  # Recent access
            + (1.0 / max(1, age / 60)) * 0.1  # Inverse age (newer better)
        )

        self.promotion_score = score
        return score


class HierarchicalCache:
    """
    Multi-level cache system for working memory items.

    Implements L1/L2/L3 cache hierarchy with automatic promotion/demotion
    based on access patterns and cognitive load.
    """

    def __init__(
        self,
        l1_capacity: int = 15,  # Slightly above Miller's 7±2 for burst capacity
        l2_capacity: int = 75,  # 5x L1 capacity
        l2_ttl: float = 3600.0,  # 1 hour TTL for L2
        store: Optional[WorkingMemoryStore] = None,
    ):
        self.l1_capacity = l1_capacity
        self.l2_capacity = l2_capacity
        self.l2_ttl = l2_ttl
        self.store = store

        # Cache storage
        self._l1_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._l2_cache: Dict[str, CacheEntry] = {}

        # Metrics per cache level
        self._metrics = {
            CacheLevel.L1: CacheMetrics(),
            CacheLevel.L2: CacheMetrics(),
            CacheLevel.L3: CacheMetrics(),
        }

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start background cache maintenance."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._background_cleanup())
        logger.info("Hierarchical cache started with background maintenance")

    async def stop(self) -> None:
        """Stop background cache maintenance."""
        if not self._running:
            return

        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Hierarchical cache stopped")

    async def get(self, item_id: str) -> Optional[WorkingMemoryItem]:
        """
        Get item from cache hierarchy with automatic promotion.

        Args:
            item_id: Item identifier

        Returns:
            Working memory item or None if not found
        """
        start_time = time.perf_counter_ns()

        try:
            # Try L1 cache first (fastest)
            if item_id in self._l1_cache:
                entry = self._l1_cache[item_id]
                entry.access_count += 1
                entry.last_accessed = time.time()

                # Move to end (most recently used)
                self._l1_cache.move_to_end(item_id)

                self._metrics[CacheLevel.L1].hits += 1
                logger.debug(f"L1 cache hit for item {item_id}")

                return entry.item

            # Try L2 cache
            if item_id in self._l2_cache:
                entry = self._l2_cache[item_id]

                # Check if expired
                if entry.is_expired:
                    del self._l2_cache[item_id]
                    self._metrics[CacheLevel.L2].evictions += 1
                else:
                    entry.access_count += 1
                    entry.last_accessed = time.time()

                    # Promote to L1 if score is high enough
                    if entry.calculate_promotion_score() > 0.7:
                        await self._promote_to_l1(item_id, entry)

                    self._metrics[CacheLevel.L2].hits += 1
                    logger.debug(f"L2 cache hit for item {item_id}")

                    return entry.item

            # Try L3 (persistent storage)
            if self.store:
                item = self.store.get_item(item_id)
                if item:
                    # Create cache entry and add to L2
                    entry = CacheEntry(item=item, access_count=1, ttl=self.l2_ttl)

                    await self._add_to_l2(item_id, entry)

                    self._metrics[CacheLevel.L3].hits += 1
                    logger.debug(f"L3 cache hit for item {item_id}")

                    return item

            # Cache miss at all levels
            self._metrics[CacheLevel.L1].misses += 1
            self._metrics[CacheLevel.L2].misses += 1
            self._metrics[CacheLevel.L3].misses += 1

            return None

        finally:
            access_time = time.perf_counter_ns() - start_time
            # Record access time in the highest level that was accessed
            if item_id in self._l1_cache:
                self._metrics[CacheLevel.L1].total_access_time_ns += access_time
            elif item_id in self._l2_cache:
                self._metrics[CacheLevel.L2].total_access_time_ns += access_time
            else:
                self._metrics[CacheLevel.L3].total_access_time_ns += access_time

    async def put(
        self, item: WorkingMemoryItem, target_level: CacheLevel = CacheLevel.L1
    ) -> None:
        """
        Put item into cache hierarchy.

        Args:
            item: Working memory item to cache
            target_level: Target cache level
        """
        entry = CacheEntry(
            item=item,
            access_count=1,
            ttl=self.l2_ttl if target_level == CacheLevel.L2 else None,
        )

        if target_level == CacheLevel.L1:
            await self._add_to_l1(item.id, entry)
        elif target_level == CacheLevel.L2:
            await self._add_to_l2(item.id, entry)
        elif target_level == CacheLevel.L3 and self.store:
            self.store.store_item(item)
            self._metrics[CacheLevel.L3].hits += 1

    async def remove(self, item_id: str) -> bool:
        """
        Remove item from all cache levels.

        Args:
            item_id: Item identifier

        Returns:
            True if item was removed from any level
        """
        removed = False

        # Remove from L1
        if item_id in self._l1_cache:
            del self._l1_cache[item_id]
            removed = True
            logger.debug(f"Removed item {item_id} from L1 cache")

        # Remove from L2
        if item_id in self._l2_cache:
            del self._l2_cache[item_id]
            removed = True
            logger.debug(f"Removed item {item_id} from L2 cache")

        # Remove from L3 (persistent storage)
        if self.store:
            if self.store.remove_item(item_id):
                removed = True
                logger.debug(f"Removed item {item_id} from L3 storage")

        return removed

    async def _add_to_l1(self, item_id: str, entry: CacheEntry) -> None:
        """Add entry to L1 cache with eviction if needed."""
        # Remove from L2 if present (promotion)
        if item_id in self._l2_cache:
            del self._l2_cache[item_id]
            self._metrics[CacheLevel.L1].promotions += 1

        # Evict LRU if at capacity
        if len(self._l1_cache) >= self.l1_capacity:
            lru_id, lru_entry = self._l1_cache.popitem(last=False)

            # Demote to L2
            lru_entry.ttl = self.l2_ttl
            await self._add_to_l2(lru_id, lru_entry)

            self._metrics[CacheLevel.L1].evictions += 1
            self._metrics[CacheLevel.L1].demotions += 1

        self._l1_cache[item_id] = entry
        logger.debug(f"Added item {item_id} to L1 cache")

    async def _add_to_l2(self, item_id: str, entry: CacheEntry) -> None:
        """Add entry to L2 cache with eviction if needed."""
        # Evict expired entries first
        await self._cleanup_l2_expired()

        # Evict LRU if at capacity
        if len(self._l2_cache) >= self.l2_capacity:
            # Find least recently used item
            lru_id = min(
                self._l2_cache.keys(), key=lambda k: self._l2_cache[k].last_accessed
            )

            lru_entry = self._l2_cache.pop(lru_id)

            # Demote to L3 if store available
            if self.store:
                self.store.store_item(lru_entry.item)
                self._metrics[CacheLevel.L2].demotions += 1

            self._metrics[CacheLevel.L2].evictions += 1

        self._l2_cache[item_id] = entry
        logger.debug(f"Added item {item_id} to L2 cache")

    async def _promote_to_l1(self, item_id: str, entry: CacheEntry) -> None:
        """Promote item from L2 to L1."""
        del self._l2_cache[item_id]
        await self._add_to_l1(item_id, entry)
        logger.debug(f"Promoted item {item_id} from L2 to L1")

    async def _cleanup_l2_expired(self) -> None:
        """Remove expired entries from L2 cache."""
        expired_ids = [
            item_id for item_id, entry in self._l2_cache.items() if entry.is_expired
        ]

        for item_id in expired_ids:
            del self._l2_cache[item_id]
            self._metrics[CacheLevel.L2].evictions += 1

        if expired_ids:
            logger.debug(f"Cleaned up {len(expired_ids)} expired L2 cache entries")

    async def _background_cleanup(self) -> None:
        """Background task for cache maintenance."""
        while self._running:
            try:
                # Clean up expired L2 entries
                await self._cleanup_l2_expired()

                # Recalculate promotion scores
                for entry in self._l2_cache.values():
                    entry.calculate_promotion_score()

                # Sleep for 30 seconds
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            "l1": {
                "size": len(self._l1_cache),
                "capacity": self.l1_capacity,
                "utilization": len(self._l1_cache) / self.l1_capacity,
                "metrics": {
                    "hits": self._metrics[CacheLevel.L1].hits,
                    "misses": self._metrics[CacheLevel.L1].misses,
                    "hit_rate": self._metrics[CacheLevel.L1].hit_rate,
                    "promotions": self._metrics[CacheLevel.L1].promotions,
                    "demotions": self._metrics[CacheLevel.L1].demotions,
                    "evictions": self._metrics[CacheLevel.L1].evictions,
                    "avg_access_time_ns": self._metrics[
                        CacheLevel.L1
                    ].avg_access_time_ns,
                },
            },
            "l2": {
                "size": len(self._l2_cache),
                "capacity": self.l2_capacity,
                "utilization": len(self._l2_cache) / self.l2_capacity,
                "ttl": self.l2_ttl,
                "metrics": {
                    "hits": self._metrics[CacheLevel.L2].hits,
                    "misses": self._metrics[CacheLevel.L2].misses,
                    "hit_rate": self._metrics[CacheLevel.L2].hit_rate,
                    "promotions": self._metrics[CacheLevel.L2].promotions,
                    "demotions": self._metrics[CacheLevel.L2].demotions,
                    "evictions": self._metrics[CacheLevel.L2].evictions,
                    "avg_access_time_ns": self._metrics[
                        CacheLevel.L2
                    ].avg_access_time_ns,
                },
            },
            "l3": {
                "enabled": self.store is not None,
                "metrics": {
                    "hits": self._metrics[CacheLevel.L3].hits,
                    "misses": self._metrics[CacheLevel.L3].misses,
                    "hit_rate": self._metrics[CacheLevel.L3].hit_rate,
                    "avg_access_time_ns": self._metrics[
                        CacheLevel.L3
                    ].avg_access_time_ns,
                },
            },
            "overall": {
                "total_hits": sum(m.hits for m in self._metrics.values()),
                "total_misses": sum(m.misses for m in self._metrics.values()),
                "overall_hit_rate": self._calculate_overall_hit_rate(),
                "cache_efficiency": self._calculate_cache_efficiency(),
            },
        }

    def _calculate_overall_hit_rate(self) -> float:
        """Calculate overall hit rate across all cache levels."""
        total_hits = sum(m.hits for m in self._metrics.values())
        total_misses = sum(m.misses for m in self._metrics.values())
        total = total_hits + total_misses
        return (total_hits / total * 100) if total > 0 else 0.0

    def _calculate_cache_efficiency(self) -> float:
        """
        Calculate cache efficiency score based on hit rates and access times.

        Returns score between 0-100 where higher is better.
        """
        l1_weight = 0.5  # L1 hits are most valuable
        l2_weight = 0.3  # L2 hits are moderately valuable
        l3_weight = 0.2  # L3 hits are least valuable

        l1_score = self._metrics[CacheLevel.L1].hit_rate * l1_weight
        l2_score = self._metrics[CacheLevel.L2].hit_rate * l2_weight
        l3_score = self._metrics[CacheLevel.L3].hit_rate * l3_weight

        return l1_score + l2_score + l3_score

    def reset_metrics(self) -> None:
        """Reset all cache metrics."""
        for metrics in self._metrics.values():
            metrics.reset()
        logger.info("Cache metrics reset")

    async def flush_all(self) -> None:
        """Flush all cache levels."""
        self._l1_cache.clear()
        self._l2_cache.clear()
        logger.info("All cache levels flushed")

    async def get_items_by_level(self, level: CacheLevel) -> List[WorkingMemoryItem]:
        """Get all items from a specific cache level."""
        if level == CacheLevel.L1:
            return [entry.item for entry in self._l1_cache.values()]
        elif level == CacheLevel.L2:
            return [
                entry.item for entry in self._l2_cache.values() if not entry.is_expired
            ]
        elif level == CacheLevel.L3 and self.store:
            # This would require a session ID - implementation depends on usage
            return []
        return []

    def get_cache_level(self, item_id: str) -> Optional[CacheLevel]:
        """Get the cache level where an item is currently stored."""
        if item_id in self._l1_cache:
            return CacheLevel.L1
        elif item_id in self._l2_cache and not self._l2_cache[item_id].is_expired:
            return CacheLevel.L2
        elif self.store and self.store.get_item(item_id):
            return CacheLevel.L3
        return None

"""
Working Memory Manager - Prefrontal Cortex Executive Control with Hierarchical Cache
==================================================================================

This module implements the brain's working memory system with a hierarchical cache
architecture (L1/L2/L3) that mirrors both cognitive neuroscience and computer
architecture principles for optimal performance and persistence.

**Cache Architecture:**
- L1 Cache: Ultra-fast in-memory buffer (~15 items, nanosecond access)
- L2 Cache: Fast session-local cache (~75 items, microsecond access, 1hr TTL)
- L3 Cache: Persistent storage (unlimited, millisecond access, UoW integration)

**Neuroscience Inspiration:**
The prefrontal cortex maintains active representations through sustained neural firing
(L1), short-term synaptic plasticity (L2), and long-term structural changes (L3).
This mirrors the brain's memory hierarchy from immediate activation to consolidation.

**Research Backing:**
- Baddeley & Hitch (1974): Working memory model with multiple components
- Goldman-Rakic (1995): Prefrontal cortex and working memory
- Miller & Cohen (2001): Integrative theory of prefrontal cortex function
- Cowan (2001): Focus of attention and activated memory
- Oberauer (2002): Working memory capacity limits and time-based decay
- Atkinson & Shiffrin (1968): Multi-store memory model

The implementation provides sophisticated buffer management, hierarchical caching,
and UoW-integrated persistence for production-grade working memory performance.
"""

import asyncio
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from observability.logging import get_json_logger
from observability.trace import start_span
from storage.core.unit_of_work import UnitOfWork

from .storage import (
    CacheLevel,
    HierarchicalCache,
    WorkingMemoryStore,
)
from .storage import (
    WorkingMemoryItem as StorageItem,
)

logger = get_json_logger(__name__)


class Priority(Enum):
    """Priority levels for working memory items."""

    CRITICAL = 5  # Must maintain (current task goals)
    HIGH = 4  # Important for current context
    MEDIUM = 3  # Useful background information
    LOW = 2  # Nice to have
    MINIMAL = 1  # Evict first


class WorkingMemoryType(Enum):
    """Types of working memory content."""

    GOAL = "goal"  # Task goals and objectives
    CONTEXT = "context"  # Current situational context
    RETRIEVAL = "retrieval"  # Recently retrieved memories
    COMPUTATION = "computation"  # Intermediate calculations
    ATTENTION = "attention"  # Attentional focus items
    BUFFER = "buffer"  # Temporary storage


@dataclass
class WorkingMemoryItem:
    """Individual item in working memory."""

    id: str
    session_id: str
    content: Any
    content_type: WorkingMemoryType
    priority: Priority
    salience_score: float
    created_at: datetime
    accessed_at: datetime
    access_count: int = 0
    decay_rate: float = 0.1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_access(self) -> None:
        """Update access tracking."""
        self.accessed_at = datetime.now(timezone.utc)
        self.access_count += 1

    def calculate_activation(self) -> float:
        """Calculate current activation level based on recency and frequency."""
        now = datetime.now(timezone.utc)
        time_since_access = (now - self.accessed_at).total_seconds()

        # Decay function: activation = base * exp(-decay_rate * time)
        recency_factor = max(0.1, 1.0 - (time_since_access * self.decay_rate / 3600))
        frequency_factor = min(2.0, 1.0 + (self.access_count * 0.1))

        return self.salience_score * recency_factor * frequency_factor


@dataclass
class WorkingMemoryCapacity:
    """Working memory capacity configuration."""

    max_items: int = 7  # Miller's magical number 7±2
    max_total_size_mb: float = 50.0  # Memory size limit
    priority_reserved_slots: int = 3  # Reserved for CRITICAL items
    decay_interval_seconds: int = 30  # How often to apply decay


@dataclass
class WorkingMemoryStats:
    """Working memory performance statistics."""

    total_items: int = 0
    items_by_priority: Dict[Priority, int] = field(default_factory=dict)
    items_by_type: Dict[WorkingMemoryType, int] = field(default_factory=dict)
    capacity_utilization: float = 0.0
    memory_utilization_mb: float = 0.0
    average_activation: float = 0.0
    eviction_count: int = 0
    admission_rejections: int = 0


class WorkingMemoryManager:
    """
    Implements prefrontal cortex-inspired working memory management with hierarchical cache.

    Provides session-scoped buffer management with L1/L2/L3 cache hierarchy,
    sophisticated admission control, and UoW-integrated persistence that
    mirrors both cognitive neuroscience and computer architecture principles.

    **Cache Architecture:**
    - L1: Ultra-fast in-memory buffer (15 items, nanosecond access)
    - L2: Fast session cache (75 items, microsecond access, 1hr TTL)
    - L3: Persistent storage (unlimited, millisecond access, UoW transactions)

    **Key Functions:**
    - Hierarchical cache with automatic promotion/demotion
    - Salience-based admission control with cache awareness
    - Priority-aware eviction across cache levels
    - Activation-based content maintenance
    - UoW-integrated transactional persistence
    """

    def __init__(
        self,
        uow: UnitOfWork,
        capacity: Optional[WorkingMemoryCapacity] = None,
        config: Optional[Dict[str, Any]] = None,
        l1_capacity: int = 15,
        l2_capacity: int = 75,
        l2_ttl: float = 3600.0,
    ):
        # Configuration
        self.capacity = capacity or WorkingMemoryCapacity()
        self.config = config or {}
        self.uow = uow

        # Initialize storage components
        self.store = WorkingMemoryStore()
        self.uow.register_store(self.store)

        # Initialize hierarchical cache
        self.cache = HierarchicalCache(
            l1_capacity=l1_capacity,
            l2_capacity=l2_capacity,
            l2_ttl=l2_ttl,
            store=self.store,
        )

        # Legacy storage for backward compatibility (will be migrated to cache)
        self.items: OrderedDict[str, WorkingMemoryItem] = OrderedDict()
        self.sessions: Dict[str, Set[str]] = {}  # session_id -> item_ids

        # Performance tracking
        self.stats = WorkingMemoryStats()
        self.eviction_history: List[Dict[str, Any]] = []

        # Background maintenance
        self._decay_task: Optional[asyncio.Task[None]] = None
        self._maintenance_running = False

        logger.info(
            "WorkingMemoryManager initialized with hierarchical cache",
            extra={
                "max_items": self.capacity.max_items,
                "max_size_mb": self.capacity.max_total_size_mb,
                "l1_capacity": l1_capacity,
                "l2_capacity": l2_capacity,
                "l2_ttl_hours": l2_ttl / 3600,
                "uow_integrated": True,
            },
        )

    async def start_maintenance(self) -> None:
        """Start background maintenance tasks."""
        if self._maintenance_running:
            return

        self._maintenance_running = True

        # Start cache background tasks
        await self.cache.start()

        # Start decay maintenance
        self._decay_task = asyncio.create_task(self._maintenance_loop())

        logger.info("Working memory maintenance started with hierarchical cache")

    async def stop_maintenance(self) -> None:
        """Stop background maintenance tasks."""
        self._maintenance_running = False

        # Stop cache background tasks
        await self.cache.stop()

        if self._decay_task and not self._decay_task.done():
            self._decay_task.cancel()
            try:
                await self._decay_task
            except asyncio.CancelledError:
                pass

        logger.info("Working memory maintenance stopped")

    def _convert_to_storage_item(self, item: WorkingMemoryItem) -> StorageItem:
        """Convert manager item to storage item format."""
        return StorageItem(
            id=item.id,
            session_id=item.session_id,
            content=item.content,
            item_type=item.content_type.value,
            priority=item.priority.value,
            activation=item.calculate_activation(),
            added_at=item.created_at.timestamp(),
            last_accessed=item.accessed_at.timestamp(),
            access_count=item.access_count,
            tags=list(item.metadata.get("tags", [])),
            metadata=item.metadata,
            space_id=item.metadata.get("space_id"),
            actor_id=item.metadata.get("actor_id"),
        )

    def _convert_from_storage_item(
        self, storage_item: StorageItem
    ) -> WorkingMemoryItem:
        """Convert storage item to manager item format."""
        return WorkingMemoryItem(
            id=storage_item.id,
            session_id=storage_item.session_id,
            content=storage_item.content,
            content_type=WorkingMemoryType(storage_item.item_type),
            priority=Priority(storage_item.priority),
            salience_score=storage_item.activation,  # Use activation as salience
            created_at=datetime.fromtimestamp(storage_item.added_at, tz=timezone.utc),
            accessed_at=datetime.fromtimestamp(
                storage_item.last_accessed, tz=timezone.utc
            ),
            access_count=storage_item.access_count,
            metadata=storage_item.metadata or {},
        )

    async def add_item(
        self,
        session_id: str,
        content: Any,
        content_type: WorkingMemoryType,
        priority: Priority,
        salience_score: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Add item to working memory with admission control.

        Implements salience-based admission control that determines whether
        new information should enter working memory based on current capacity,
        priority levels, and activation states of existing items.

        Args:
            session_id: Session identifier for multi-session support
            content: The content to store in working memory
            content_type: Type of working memory content
            priority: Priority level of the item
            salience_score: Salience/importance score (0.0-1.0)
            metadata: Optional metadata for the item

        Returns:
            Item ID if successfully added, None if rejected
        """
        with start_span("working_memory.manager.add_item") as span:
            try:
                # Validate inputs
                if not (0.0 <= salience_score <= 1.0):
                    raise ValueError("Salience score must be between 0.0 and 1.0")

                # Check admission control
                admission_result = await self._evaluate_admission(
                    session_id, content_type, priority, salience_score
                )

                if not admission_result["admitted"]:
                    self.stats.admission_rejections += 1

                    if span:
                        span.set_attribute("admission_rejected", True)
                        span.set_attribute(
                            "rejection_reason", admission_result["reason"]
                        )

                    logger.debug(
                        "Working memory admission rejected",
                        extra={
                            "session_id": session_id,
                            "content_type": content_type.value,
                            "priority": priority.value,
                            "salience_score": salience_score,
                            "reason": admission_result["reason"],
                        },
                    )

                    return None

                # Create working memory item
                item_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc)

                item = WorkingMemoryItem(
                    id=item_id,
                    session_id=session_id,
                    content=content,
                    content_type=content_type,
                    priority=priority,
                    salience_score=salience_score,
                    created_at=now,
                    accessed_at=now,
                    access_count=1,
                    metadata=metadata or {},
                )

                # Convert to storage format and add to cache hierarchy
                storage_item = self._convert_to_storage_item(item)

                # Determine target cache level based on priority and salience
                if priority == Priority.CRITICAL or salience_score >= 0.8:
                    target_level = CacheLevel.L1
                elif priority.value >= Priority.HIGH.value or salience_score >= 0.6:
                    target_level = CacheLevel.L2
                else:
                    target_level = CacheLevel.L3

                # Add to hierarchical cache
                await self.cache.put(storage_item, target_level)

                # Legacy storage for backward compatibility (will be phased out)
                self.items[item_id] = item

                # Track session membership
                if session_id not in self.sessions:
                    self.sessions[session_id] = set()
                self.sessions[session_id].add(item_id)

                # Update statistics
                await self._update_stats()

                if span:
                    span.set_attribute("item_id", item_id)
                    span.set_attribute("admitted", True)
                    span.set_attribute(
                        "eviction_performed",
                        admission_result.get("eviction_needed", False),
                    )

                logger.info(
                    "Working memory item added",
                    extra={
                        "item_id": item_id,
                        "session_id": session_id,
                        "content_type": content_type.value,
                        "priority": priority.value,
                        "salience_score": salience_score,
                        "current_capacity": len(self.items),
                    },
                )

                return item_id

            except Exception as e:
                self.stats.admission_rejections += 1

                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))

                logger.error(
                    "Failed to add working memory item",
                    extra={
                        "session_id": session_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

                return None

    async def get_item(self, item_id: str) -> Optional[WorkingMemoryItem]:
        """Get item from hierarchical cache with automatic promotion."""

        # Try hierarchical cache first (L1 -> L2 -> L3)
        storage_item = await self.cache.get(item_id)
        if storage_item:
            # Convert back to manager format
            item = self._convert_from_storage_item(storage_item)

            # Update legacy storage for backward compatibility
            self.items[item_id] = item
            self.items.move_to_end(item_id)

            cache_level = self.cache.get_cache_level(item_id)
            logger.debug(
                "Working memory item accessed via cache",
                extra={
                    "item_id": item_id,
                    "session_id": item.session_id,
                    "access_count": item.access_count,
                    "activation": item.calculate_activation(),
                    "cache_level": cache_level.value if cache_level else "unknown",
                },
            )

            return item

        # Fallback to legacy storage
        item = self.items.get(item_id)
        if item:
            # Update access tracking
            item.update_access()
            self.items.move_to_end(item_id)

            # Add to cache for future access
            storage_item = self._convert_to_storage_item(item)
            await self.cache.put(storage_item, CacheLevel.L2)

            logger.debug(
                "Working memory item accessed via legacy storage",
                extra={
                    "item_id": item_id,
                    "session_id": item.session_id,
                    "access_count": item.access_count,
                    "activation": item.calculate_activation(),
                },
            )

        return item

    async def get_session_items(
        self,
        session_id: str,
        content_type: Optional[WorkingMemoryType] = None,
        min_priority: Optional[Priority] = None,
    ) -> List[WorkingMemoryItem]:
        """Get all items for a specific session with optional filtering."""

        session_item_ids = self.sessions.get(session_id, set())
        session_items = []

        for item_id in session_item_ids:
            item = self.items.get(item_id)
            if not item:
                continue

            # Apply filters
            if content_type and item.content_type != content_type:
                continue

            if min_priority and item.priority.value < min_priority.value:
                continue

            # Update access tracking
            item.update_access()
            session_items.append(item)

        # Sort by activation level (highest first)
        session_items.sort(key=lambda x: x.calculate_activation(), reverse=True)

        return session_items

    async def update_item_priority(
        self, item_id: str, new_priority: Priority, new_salience: Optional[float] = None
    ) -> bool:
        """Update item priority and optionally salience score."""

        item = self.items.get(item_id)
        if not item:
            return False

        old_priority = item.priority
        item.priority = new_priority

        if new_salience is not None:
            if not (0.0 <= new_salience <= 1.0):
                raise ValueError("Salience score must be between 0.0 and 1.0")
            item.salience_score = new_salience

        item.update_access()
        await self._update_stats()

        logger.debug(
            "Working memory item priority updated",
            extra={
                "item_id": item_id,
                "old_priority": old_priority.value,
                "new_priority": new_priority.value,
                "new_salience": new_salience,
                "activation": item.calculate_activation(),
            },
        )

        return True

    async def remove_item(self, item_id: str) -> bool:
        """Remove item from working memory and all cache levels."""

        # Remove from hierarchical cache
        cache_removed = await self.cache.remove(item_id)

        # Remove from legacy storage
        item = self.items.pop(item_id, None)
        legacy_removed = item is not None

        if item:
            # Remove from session tracking
            if item.session_id in self.sessions:
                self.sessions[item.session_id].discard(item_id)
                if not self.sessions[item.session_id]:
                    del self.sessions[item.session_id]

            await self._update_stats()

            logger.debug(
                "Working memory item removed",
                extra={
                    "item_id": item_id,
                    "session_id": item.session_id,
                    "cache_removed": cache_removed,
                    "legacy_removed": legacy_removed,
                },
            )

        return cache_removed or legacy_removed

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache performance statistics."""
        return self.cache.get_cache_stats()

    async def flush_cache(self, level: Optional[CacheLevel] = None) -> None:
        """Flush specific cache level or all levels."""
        if level is None:
            await self.cache.flush_all()
            logger.info("All cache levels flushed")
        else:
            # Specific level flushing would need to be implemented in cache
            logger.info(f"Cache level {level.value} flush requested")

    async def get_items_by_cache_level(
        self, level: CacheLevel
    ) -> List[WorkingMemoryItem]:
        """Get all items from a specific cache level."""
        storage_items = await self.cache.get_items_by_level(level)
        return [self._convert_from_storage_item(item) for item in storage_items]

    async def clear_session(self, session_id: str) -> int:
        """Clear all items for a specific session."""

        session_item_ids = self.sessions.get(session_id, set()).copy()
        removed_count = 0

        for item_id in session_item_ids:
            if await self.remove_item(item_id):
                removed_count += 1

        logger.info(
            "Working memory session cleared",
            extra={"session_id": session_id, "items_removed": removed_count},
        )

        return removed_count

    async def get_stats(self) -> WorkingMemoryStats:
        """Get current working memory statistics."""
        await self._update_stats()
        return self.stats

    async def add_item_with_cache_optimization(
        self,
        session_id: str,
        content: Any,
        content_type: WorkingMemoryType,
        priority: Priority,
        salience_score: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Enhanced add_item with cache-aware admission control and optimization.

        Integrates hierarchical cache performance metrics into admission decisions
        and optimizes cache placement based on access patterns and system load.
        """
        with start_span("working_memory.manager.add_item_cache_optimized") as span:
            try:
                # Get current cache statistics
                cache_stats = await self.get_cache_stats()

                # Get current cognitive load with cache awareness
                cognitive_load_metrics = await self.get_cognitive_load_with_cache()

                # Use cache-aware admission controller if available
                if hasattr(self, "admission_controller"):
                    admission_result = await self.admission_controller.evaluate_admission_with_cache_awareness(
                        content,
                        content_type,
                        priority,
                        salience_score,
                        session_id,
                        metadata,
                        list(self.items.values()),
                        cognitive_load_metrics.get("overall_load", 0.0),
                        cache_stats,
                    )
                else:
                    # Fallback to standard evaluation
                    admission_result = await self._evaluate_admission(
                        session_id, content_type, priority, salience_score
                    )

                if not admission_result.get("admitted", False):
                    self.stats.admission_rejections += 1

                    if span:
                        span.set_attribute("admission_rejected", True)
                        span.set_attribute(
                            "rejection_reason",
                            admission_result.get("reason", "unknown"),
                        )

                    return None

                # Create working memory item
                item_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc)

                item = WorkingMemoryItem(
                    id=item_id,
                    session_id=session_id,
                    content=content,
                    content_type=content_type,
                    priority=priority,
                    salience_score=salience_score,
                    created_at=now,
                    accessed_at=now,
                    access_count=1,
                    metadata=metadata or {},
                )

                # Determine optimal cache level based on admission decision and cache state
                target_level = await self._determine_optimal_cache_level(
                    item, admission_result, cache_stats, cognitive_load_metrics
                )

                # Convert to storage format and add to cache hierarchy
                storage_item = self._convert_to_storage_item(item)
                await self.cache.put(storage_item, target_level)

                # Legacy storage for backward compatibility
                self.items[item_id] = item

                # Track session membership
                if session_id not in self.sessions:
                    self.sessions[session_id] = set()
                self.sessions[session_id].add(item_id)

                # Update statistics
                await self._update_stats()

                if span:
                    span.set_attribute("item_id", item_id)
                    span.set_attribute("admitted", True)
                    span.set_attribute("target_cache_level", target_level.value)
                    span.set_attribute("cache_optimized", True)

                logger.info(
                    "Cache-optimized working memory item added",
                    extra={
                        "item_id": item_id,
                        "session_id": session_id,
                        "content_type": content_type.value,
                        "priority": priority.value,
                        "salience_score": salience_score,
                        "target_cache_level": target_level.value,
                        "cache_efficiency": cache_stats.get("overall", {}).get(
                            "cache_efficiency", 0.0
                        ),
                        "cognitive_load": cognitive_load_metrics.get(
                            "overall_load", 0.0
                        ),
                    },
                )

                return item_id

            except Exception as e:
                self.stats.admission_rejections += 1

                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))

                logger.error(
                    "Failed to add cache-optimized working memory item",
                    extra={
                        "session_id": session_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

                return None

    async def _determine_optimal_cache_level(
        self,
        item: WorkingMemoryItem,
        admission_result: Any,
        cache_stats: Dict[str, Any],
        cognitive_load_metrics: Dict[str, Any],
    ) -> CacheLevel:
        """Determine optimal cache level for new item based on system state."""

        # High priority items and high salience go to L1 if there's space
        l1_utilization = cache_stats.get("l1", {}).get("utilization", 0.0)
        l2_utilization = cache_stats.get("l2", {}).get("utilization", 0.0)
        overall_load = cognitive_load_metrics.get("overall_load", 0.0)

        # Critical items always aim for L1
        if item.priority == Priority.CRITICAL:
            return CacheLevel.L1

        # High priority or high salience items
        if item.priority.value >= Priority.HIGH.value or item.salience_score >= 0.8:
            # Go to L1 if not too full
            if l1_utilization < 0.85:
                return CacheLevel.L1
            else:
                return CacheLevel.L2

        # Medium priority items
        if item.priority.value >= Priority.MEDIUM.value or item.salience_score >= 0.6:
            # Prefer L2, but can go to L1 if plenty of space
            if l1_utilization < 0.5 and overall_load < 0.4:
                return CacheLevel.L1
            elif l2_utilization < 0.8:
                return CacheLevel.L2
            else:
                return CacheLevel.L3

        # Lower priority items
        if l2_utilization < 0.6 and overall_load < 0.6:
            return CacheLevel.L2
        else:
            return CacheLevel.L3

    async def get_cognitive_load_with_cache(self) -> Dict[str, Any]:
        """Get cognitive load metrics with cache performance integration."""

        if not hasattr(self, "load_monitor"):
            # Create load monitor if not exists
            from .cognitive_load_monitor import CognitiveLoadMonitor

            self.load_monitor = CognitiveLoadMonitor()

        # Get current cache stats
        cache_stats = await self.get_cache_stats()

        # Get load metrics with cache awareness
        load_metrics = (
            await self.load_monitor.measure_cognitive_load_with_cache_metrics(
                list(self.items.values()),
                len(self.sessions),
                None,  # Processing operations
                None,  # Performance data
                cache_stats,
            )
        )

        return {
            "overall_load": load_metrics.overall_load,
            "load_level": load_metrics.load_level.value,
            "capacity_utilization": load_metrics.capacity_utilization,
            "processing_complexity": load_metrics.processing_complexity,
            "attention_fragmentation": load_metrics.attention_fragmentation,
            "temporal_pressure": load_metrics.temporal_pressure,
            "interference_level": load_metrics.interference_level,
            "resource_competition": load_metrics.resource_competition,
        }

    async def optimize_cache_placement(self) -> Dict[str, Any]:
        """Optimize cache placement based on current access patterns."""

        with start_span("working_memory.manager.optimize_cache") as span:
            optimizations = {
                "promotions": 0,
                "demotions": 0,
                "relocations": 0,
                "efficiency_gain": 0.0,
            }

            try:
                # Get current cache stats
                cache_stats = await self.get_cache_stats()

                # Get items from each cache level
                l1_items = await self.cache.get_items_by_level(CacheLevel.L1)
                l2_items = await self.cache.get_items_by_level(CacheLevel.L2)

                # Analyze access patterns for optimization opportunities
                for item in l1_items:
                    wm_item = self.items.get(item.id)
                    if wm_item:
                        # Consider demoting low-activation L1 items
                        activation = wm_item.calculate_activation()
                        if (
                            activation < 0.3
                            and wm_item.priority.value < Priority.HIGH.value
                        ):
                            # Demote to L2
                            await self.cache.remove(item.id)
                            await self.cache.put(item, CacheLevel.L2)
                            optimizations["demotions"] += 1

                for item in l2_items:
                    wm_item = self.items.get(item.id)
                    if wm_item:
                        # Consider promoting high-activation L2 items
                        activation = wm_item.calculate_activation()
                        if activation > 0.8 or wm_item.priority == Priority.CRITICAL:
                            # Check if L1 has space
                            l1_utilization = cache_stats.get("l1", {}).get(
                                "utilization", 0.0
                            )
                            if l1_utilization < 0.85:
                                await self.cache.remove(item.id)
                                await self.cache.put(item, CacheLevel.L1)
                                optimizations["promotions"] += 1

                # Calculate efficiency gain estimate
                new_cache_stats = await self.get_cache_stats()
                old_efficiency = cache_stats.get("overall", {}).get(
                    "cache_efficiency", 0.0
                )
                new_efficiency = new_cache_stats.get("overall", {}).get(
                    "cache_efficiency", 0.0
                )
                optimizations["efficiency_gain"] = new_efficiency - old_efficiency

                if span:
                    span.set_attribute("promotions", optimizations["promotions"])
                    span.set_attribute("demotions", optimizations["demotions"])
                    span.set_attribute(
                        "efficiency_gain", optimizations["efficiency_gain"]
                    )

                logger.info(
                    "Cache placement optimized",
                    extra={
                        "optimizations": optimizations,
                        "total_changes": optimizations["promotions"]
                        + optimizations["demotions"],
                    },
                )

                return optimizations

            except Exception as e:
                if span:
                    span.set_attribute("error", True)
                    span.set_attribute("error.message", str(e))

                logger.error(
                    "Cache optimization failed",
                    extra={"error": str(e)},
                    exc_info=True,
                )

                return optimizations

    async def get_comprehensive_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report including cache and load metrics."""

        # Get base statistics
        base_stats = await self.get_stats()

        # Get cache statistics
        cache_stats = await self.get_cache_stats()

        # Get cognitive load with cache awareness
        cognitive_load = await self.get_cognitive_load_with_cache()

        # Get admission controller stats if available
        admission_stats = {}
        if hasattr(self, "admission_controller"):
            admission_stats = await self.admission_controller.get_admission_stats()

        # Calculate performance metrics
        performance_metrics = {
            "cache_efficiency_score": cache_stats.get("overall", {}).get(
                "cache_efficiency", 0.0
            ),
            "cognitive_load_score": cognitive_load.get("overall_load", 0.0) * 100,
            "working_memory_health": self._calculate_working_memory_health(
                base_stats, cache_stats, cognitive_load
            ),
            "optimization_opportunities": await self._identify_optimization_opportunities(
                cache_stats, cognitive_load
            ),
        }

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "working_memory_stats": {
                "total_items": base_stats.total_items,
                "capacity_utilization": base_stats.capacity_utilization,
                "eviction_count": base_stats.eviction_count,
                "admission_rejections": base_stats.admission_rejections,
            },
            "cache_performance": cache_stats,
            "cognitive_load": cognitive_load,
            "admission_control": admission_stats,
            "performance_metrics": performance_metrics,
            "recommendations": await self._generate_performance_recommendations(
                cache_stats, cognitive_load, performance_metrics
            ),
        }

    def _calculate_working_memory_health(
        self,
        stats: WorkingMemoryStats,
        cache_stats: Dict[str, Any],
        cognitive_load: Dict[str, Any],
    ) -> float:
        """Calculate overall working memory system health score (0-100)."""

        # Component health scores
        capacity_health = 100 * (1.0 - min(1.0, stats.capacity_utilization))
        cache_health = cache_stats.get("overall", {}).get("cache_efficiency", 50.0)
        load_health = 100 * (1.0 - cognitive_load.get("overall_load", 0.0))

        # Admission control health
        admission_health = 100.0
        if stats.admission_rejections > 0:
            total_attempts = stats.total_items + stats.admission_rejections
            admission_rate = stats.total_items / total_attempts
            admission_health = 100 * admission_rate

        # Weighted average
        overall_health = (
            capacity_health * 0.25
            + cache_health * 0.30
            + load_health * 0.30
            + admission_health * 0.15
        )

        return round(overall_health, 1)

    async def _identify_optimization_opportunities(
        self, cache_stats: Dict[str, Any], cognitive_load: Dict[str, Any]
    ) -> List[str]:
        """Identify optimization opportunities for working memory performance."""

        opportunities = []

        # Cache optimization opportunities
        l1_hit_rate = cache_stats.get("l1", {}).get("metrics", {}).get("hit_rate", 0.0)
        l2_hit_rate = cache_stats.get("l2", {}).get("metrics", {}).get("hit_rate", 0.0)
        cache_efficiency = cache_stats.get("overall", {}).get("cache_efficiency", 0.0)

        if l1_hit_rate < 80.0:
            opportunities.append("improve_l1_cache_hit_rate")

        if l2_hit_rate < 70.0:
            opportunities.append("optimize_l2_cache_strategy")

        if cache_efficiency < 60.0:
            opportunities.append("comprehensive_cache_tuning_needed")

        # Load optimization opportunities
        overall_load = cognitive_load.get("overall_load", 0.0)
        attention_fragmentation = cognitive_load.get("attention_fragmentation", 0.0)

        if overall_load > 0.8:
            opportunities.append("reduce_cognitive_load")

        if attention_fragmentation > 0.7:
            opportunities.append("improve_attention_focus")

        # Capacity optimization
        capacity_util = cognitive_load.get("capacity_utilization", 0.0)
        if capacity_util > 0.9:
            opportunities.append("increase_working_memory_capacity")
        elif capacity_util < 0.3:
            opportunities.append("optimize_working_memory_usage")

        return opportunities

    async def _generate_performance_recommendations(
        self,
        cache_stats: Dict[str, Any],
        cognitive_load: Dict[str, Any],
        performance_metrics: Dict[str, Any],
    ) -> List[str]:
        """Generate actionable performance recommendations."""

        recommendations = []

        health_score = performance_metrics.get("working_memory_health", 100.0)
        cache_efficiency = performance_metrics.get("cache_efficiency_score", 0.0)
        load_score = performance_metrics.get("cognitive_load_score", 0.0)

        # Health-based recommendations
        if health_score < 60.0:
            recommendations.append("immediate_performance_intervention_required")
            recommendations.append("consider_working_memory_capacity_expansion")
        elif health_score < 80.0:
            recommendations.append("performance_optimization_recommended")

        # Cache-specific recommendations
        if cache_efficiency < 50.0:
            recommendations.append("implement_better_cache_admission_policies")
            recommendations.append("review_cache_size_configuration")

        # Load-specific recommendations
        if load_score > 80.0:
            recommendations.append("implement_load_shedding_strategies")
            recommendations.append("prioritize_critical_items_only")

        # Specific optimizations from opportunities
        opportunities = performance_metrics.get("optimization_opportunities", [])
        for opportunity in opportunities:
            if opportunity == "improve_l1_cache_hit_rate":
                recommendations.append("tune_l1_cache_promotion_thresholds")
            elif opportunity == "reduce_cognitive_load":
                recommendations.append("implement_more_aggressive_eviction_policies")
            elif opportunity == "improve_attention_focus":
                recommendations.append("reduce_concurrent_session_count")

        return recommendations
        """Calculate cognitive load metrics."""

        if not self.items:
            return {
                "capacity_load": 0.0,
                "activation_load": 0.0,
                "priority_load": 0.0,
                "session_load": 0.0,
                "overall_load": 0.0,
            }

        # Capacity load (utilization)
        capacity_load = len(self.items) / self.capacity.max_items

        # Activation load (average activation)
        total_activation = sum(
            item.calculate_activation() for item in self.items.values()
        )
        activation_load = total_activation / len(self.items)

        # Priority load (weighted by priority)
        priority_weights = {
            Priority.CRITICAL: 5,
            Priority.HIGH: 4,
            Priority.MEDIUM: 3,
            Priority.LOW: 2,
            Priority.MINIMAL: 1,
        }
        total_priority_weight = sum(
            priority_weights[item.priority] for item in self.items.values()
        )
        max_priority_weight = len(self.items) * priority_weights[Priority.CRITICAL]
        priority_load = (
            total_priority_weight / max_priority_weight
            if max_priority_weight > 0
            else 0.0
        )

        # Session load (number of active sessions)
        session_load = min(1.0, len(self.sessions) / 3.0)  # Normalize to max 3 sessions

        # Overall cognitive load (weighted combination)
        overall_load = (
            0.3 * capacity_load
            + 0.25 * activation_load
            + 0.25 * priority_load
            + 0.2 * session_load
        )

        return {
            "capacity_load": capacity_load,
            "activation_load": activation_load,
            "priority_load": priority_load,
            "session_load": session_load,
            "overall_load": overall_load,
        }

    async def _evaluate_admission(
        self,
        session_id: str,
        content_type: WorkingMemoryType,
        priority: Priority,
        salience_score: float,
    ) -> Dict[str, Any]:
        """Evaluate whether new item should be admitted to working memory."""

        # Always admit CRITICAL priority items
        if priority == Priority.CRITICAL:
            eviction_needed = len(self.items) >= self.capacity.max_items
            return {
                "admitted": True,
                "reason": "critical_priority",
                "eviction_needed": eviction_needed,
                "evict_count": 1 if eviction_needed else 0,
            }

        # Check basic capacity
        if len(self.items) < self.capacity.max_items:
            return {
                "admitted": True,
                "reason": "capacity_available",
                "eviction_needed": False,
            }

        # Check if we can evict lower priority items
        evictable_items = [
            item
            for item in self.items.values()
            if item.priority.value < priority.value and item.session_id != session_id
        ]

        if evictable_items:
            # Sort by activation (lowest first for eviction)
            evictable_items.sort(key=lambda x: x.calculate_activation())

            # Check if new item is more salient than least active evictable item
            if salience_score > evictable_items[0].salience_score:
                return {
                    "admitted": True,
                    "reason": "higher_salience",
                    "eviction_needed": True,
                    "evict_count": 1,
                }

        # Check if we can evict same priority items with lower activation
        same_priority_items = [
            item
            for item in self.items.values()
            if item.priority == priority and item.session_id != session_id
        ]

        if same_priority_items:
            same_priority_items.sort(key=lambda x: x.calculate_activation())
            min_activation = same_priority_items[0].calculate_activation()
            new_item_activation = salience_score  # Approximation for new item

            if new_item_activation > min_activation:
                return {
                    "admitted": True,
                    "reason": "higher_activation",
                    "eviction_needed": True,
                    "evict_count": 1,
                }

        return {
            "admitted": False,
            "reason": "insufficient_salience",
            "eviction_needed": False,
        }

    async def _evict_items(
        self, count: int = 1, exclude_session: Optional[str] = None
    ) -> List[str]:
        """Evict items using priority-aware LRU strategy."""

        evicted_item_ids: List[str] = []

        # Get evictable items (exclude CRITICAL and optionally specific session)
        evictable_items = [
            (item_id, item)
            for item_id, item in self.items.items()
            if item.priority != Priority.CRITICAL
            and (exclude_session is None or item.session_id != exclude_session)
        ]

        if not evictable_items:
            logger.warning("No evictable items found in working memory")
            return evicted_item_ids

        # Sort by priority (lower first) then by activation (lower first)
        evictable_items.sort(
            key=lambda x: (x[1].priority.value, x[1].calculate_activation())
        )

        # Evict items
        for i in range(min(count, len(evictable_items))):
            item_id, item = evictable_items[i]

            # Record eviction
            eviction_record = {
                "item_id": item_id,
                "session_id": item.session_id,
                "content_type": item.content_type.value,
                "priority": item.priority.value,
                "salience_score": item.salience_score,
                "activation": item.calculate_activation(),
                "evicted_at": datetime.now(timezone.utc).isoformat(),
                "reason": "capacity_eviction",
            }

            self.eviction_history.append(eviction_record)
            self.stats.eviction_count += 1

            # Remove item
            await self.remove_item(item_id)
            evicted_item_ids.append(item_id)

            logger.debug("Working memory item evicted", extra=eviction_record)

        # Limit eviction history size
        if len(self.eviction_history) > 100:
            self.eviction_history = self.eviction_history[-50:]

        return evicted_item_ids

    async def _update_stats(self) -> None:
        """Update working memory statistics."""

        self.stats.total_items = len(self.items)

        # Reset counters
        self.stats.items_by_priority.clear()
        self.stats.items_by_type.clear()

        # Count by priority and type
        for item in self.items.values():
            self.stats.items_by_priority[item.priority] = (
                self.stats.items_by_priority.get(item.priority, 0) + 1
            )
            self.stats.items_by_type[item.content_type] = (
                self.stats.items_by_type.get(item.content_type, 0) + 1
            )

        # Calculate utilization
        self.stats.capacity_utilization = len(self.items) / self.capacity.max_items

        # Calculate average activation
        if self.items:
            total_activation = sum(
                item.calculate_activation() for item in self.items.values()
            )
            self.stats.average_activation = total_activation / len(self.items)
        else:
            self.stats.average_activation = 0.0

    async def _maintenance_loop(self) -> None:
        """Background maintenance loop for decay and cleanup."""

        while self._maintenance_running:
            try:
                await asyncio.sleep(self.capacity.decay_interval_seconds)

                if not self._maintenance_running:
                    break

                # Apply decay to all items
                items_to_evict = []

                for item_id, item in self.items.items():
                    activation = item.calculate_activation()

                    # Evict items with very low activation (except CRITICAL)
                    if activation < 0.1 and item.priority != Priority.CRITICAL:
                        items_to_evict.append(item_id)

                # Evict low-activation items
                for item_id in items_to_evict:
                    await self.remove_item(item_id)

                    self.eviction_history.append(
                        {
                            "item_id": item_id,
                            "evicted_at": datetime.now(timezone.utc).isoformat(),
                            "reason": "activation_decay",
                        }
                    )

                if items_to_evict:
                    logger.debug(
                        "Working memory decay eviction",
                        extra={
                            "evicted_count": len(items_to_evict),
                            "remaining_items": len(self.items),
                        },
                    )

                # Update statistics
                await self._update_stats()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Working memory maintenance error",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                # Continue maintenance despite errors
                await asyncio.sleep(1)


# TODO: Production enhancements needed:
# - Implement persistent working memory state for session recovery
# - Add support for multimedia content in working memory
# - Implement cross-session context transfer mechanisms
# - Add machine learning-based salience prediction
# - Implement adaptive capacity adjustment based on cognitive load
# - Add support for hierarchical working memory organization
# - Implement working memory content compression for efficiency

"""
Working Memory - Hierarchical Cache System with UoW Integration
==============================================================

The Working Memory module implements a production-grade hierarchical cache system
that combines cognitive neuroscience principles with computer architecture optimization
for ultra-fast working memory operations with persistent storage.

**Cache Architecture:**
- **L1 Cache**: Ultra-fast in-memory buffer (~15 items, nanosecond access, volatile)
- **L2 Cache**: Fast session-local cache (~75 items, microsecond access, 1hr TTL)
- **L3 Cache**: Persistent storage (unlimited, millisecond access, UoW transactions)

**Core Components:**

1. **manager.py** - Central working memory orchestrator with hierarchical cache
   integration, automatic promotion/demotion, and UoW-integrated persistence.

2. **storage/hierarchical_cache.py** - Multi-level cache system with automatic
   item promotion based on access patterns and priority scoring.

3. **storage/working_memory_store.py** - UoW-integrated persistent storage
   following StoreProtocol for transactional operations.

4. **admission_controller.py** - Cache-aware admission control with multi-level
   resource management and intelligent placement decisions.

5. **cognitive_load_monitor.py** - Enhanced monitoring with cache efficiency
   metrics, hit rates, and performance correlation analysis.

**Neuroscience + Architecture Foundation:**
Mirrors the brain's memory hierarchy from immediate neural activation (L1) through
short-term synaptic plasticity (L2) to long-term structural changes (L3), while
applying CPU cache principles for optimal performance.

**Research Backing:**
- Atkinson & Shiffrin (1968): Multi-store memory model
- Baddeley & Hitch (1974): Working memory with multiple components
- Goldman-Rakic (1995): Prefrontal cortex sustained neural firing
- Oberauer (2002): Working memory capacity limits and time-based decay

**Usage Example:**
```python
from storage.core.unit_of_work import UnitOfWork
from working_memory import WorkingMemoryManager, Priority, WorkingMemoryType, CacheLevel

# Initialize with UoW for transactional storage
uow = UnitOfWork(db_path="memory.db")
with uow:
    manager = WorkingMemoryManager(
        uow=uow,
        l1_capacity=15,  # Ultra-fast cache
        l2_capacity=75,  # Session cache
        l2_ttl=3600.0,   # 1 hour TTL
    )

    await manager.start_maintenance()

    # Add critical item (automatic L1 placement)
    item_id = await manager.add_item(
        session_id="user123_session",
        content={"task": "urgent review", "doc_id": "doc_789"},
        content_type=WorkingMemoryType.GOAL,
        priority=Priority.CRITICAL,
        salience_score=0.95
    )

    # Retrieve with automatic cache promotion
    item = await manager.get_item(item_id)

    # Monitor cache performance
    cache_stats = await manager.get_cache_stats()
    print(f"L1 hit rate: {cache_stats['l1']['metrics']['hit_rate']:.1f}%")
    print(f"Cache efficiency: {cache_stats['overall']['cache_efficiency']:.1f}")

    # Get items by cache level
    l1_items = await manager.get_items_by_cache_level(CacheLevel.L1)

    await manager.stop_maintenance()
```

**Production Features:**
- Hierarchical cache with automatic promotion/demotion
- UoW-integrated transactional persistence
- Cache-aware admission control and eviction
- Comprehensive performance monitoring
- Session isolation and cleanup
- Contract-compliant storage operations
- Real-time cognitive load monitoring with cache metrics
"""

# Import storage components
# Import core working memory components
from .admission_controller import (
    AdmissionController,
    AdmissionCriteria,
    AdmissionDecision,
    AdmissionPolicy,
)
from .cognitive_load_monitor import (
    CognitiveLoadMonitor,
    LoadAlert,
    LoadLevel,
    LoadMetrics,
    LoadThresholds,
    PerformanceIndicators,
)
from .lru_eviction import (
    EvictionCandidate,
    EvictionMetrics,
    EvictionStrategy,
    LRUEvictionManager,
)
from .manager import (
    Priority,
    WorkingMemoryCapacity,
    WorkingMemoryItem,
    WorkingMemoryManager,
    WorkingMemoryStats,
    WorkingMemoryType,
)
from .storage import (
    CacheLevel,
    HierarchicalCache,
    WorkingMemoryStore,
)

__all__ = [
    # Core manager
    "WorkingMemoryManager",
    "WorkingMemoryItem",
    "WorkingMemoryType",
    "Priority",
    "WorkingMemoryCapacity",
    "WorkingMemoryStats",
    # Hierarchical cache system
    "HierarchicalCache",
    "CacheLevel",
    "WorkingMemoryStore",
    # Admission control
    "AdmissionController",
    "AdmissionPolicy",
    "AdmissionCriteria",
    "AdmissionDecision",
    # Eviction management
    "LRUEvictionManager",
    "EvictionStrategy",
    "EvictionCandidate",
    "EvictionMetrics",
    # Load monitoring
    "CognitiveLoadMonitor",
    "LoadLevel",
    "LoadMetrics",
    "LoadThresholds",
    "LoadAlert",
    "PerformanceIndicators",
]

# Module version
__version__ = "2.0.0"  # Hierarchical cache integration

# Module metadata
__author__ = "MemoryOS Team"
__description__ = "Hierarchical cache working memory with UoW integration"
__license__ = "MIT"

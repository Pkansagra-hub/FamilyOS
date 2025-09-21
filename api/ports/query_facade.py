"""
Query Facade Port - Issue #23 Implementation
============================================

World-class query facade implementation with advanced features:
- Sub-issue #23.1: Query optimization and caching (2 days)
- Sub-issue #23.2: Multi-source data aggregation (2 days)
- Sub-issue #23.3: Access control filtering (2 days)

Port abstraction for routing read operations (queries) to backend services.
From MMD diagram: Queries → QueryFacadePort → Data Sources

This port handles all read operations:
- Memory operations: memory_recall, receipt_get
- Privacy operations: dsar_status
- Registry operations: registry_tools, registry_prompts
- System operations: flags_get, connectors_list, things_list
- Admin operations: rbac_roles, index_status

Architecture:
HTTP Handler → IngressAdapter → QueryFacadePort → Data Services → Response
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..schemas.core import Envelope

logger = logging.getLogger(__name__)


# =====================================================
# Sub-issue #23.1: Query Optimization and Caching
# =====================================================


class QueryType(Enum):
    """Types of queries for optimization."""

    MEMORY_RECALL = "memory_recall"
    REGISTRY_TOOLS = "registry_tools"
    REGISTRY_PROMPTS = "registry_prompts"
    FLAGS_GET = "flags_get"
    RBAC_ROLES = "rbac_roles"
    RECEIPT_GET = "receipt_get"
    DSAR_STATUS = "dsar_status"
    INDEX_STATUS = "index_status"
    CONNECTORS_LIST = "connectors_list"
    THINGS_LIST = "things_list"


@dataclass
class QueryCacheEntry:
    """Cache entry with TTL and metadata."""

    data: Any
    created_at: float
    ttl_seconds: int
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    cache_hit_rate: float = 0.0
    source_services: List[str] = field(default_factory=list)


@dataclass
class QueryOptimizationHint:
    """Optimization hints for query execution."""

    use_cache: bool = True
    cache_ttl: int = 300  # 5 minutes default
    parallel_execution: bool = False
    priority: int = 5  # 1-10 scale
    estimated_cost: float = 1.0
    required_services: List[str] = field(default_factory=list)
    can_be_partial: bool = False


class QueryOptimizer:
    """
    Advanced query optimization engine.

    Features:
    - Query plan optimization
    - Cost-based execution planning
    - Adaptive caching strategies
    - Performance prediction
    """

    def __init__(self):
        self.query_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "execution_count": 0,
                "avg_latency_ms": 0.0,
                "cache_hit_rate": 0.0,
                "error_rate": 0.0,
                "last_optimization": 0.0,
            }
        )
        self.optimization_rules = self._initialize_optimization_rules()

    def _initialize_optimization_rules(self) -> Dict[QueryType, QueryOptimizationHint]:
        """Initialize optimization rules for different query types."""
        return {
            QueryType.MEMORY_RECALL: QueryOptimizationHint(
                use_cache=True,
                cache_ttl=60,  # Short TTL for dynamic data
                parallel_execution=True,
                priority=8,
                estimated_cost=5.0,
                required_services=["retrieval", "policy", "indexing"],
                can_be_partial=True,
            ),
            QueryType.REGISTRY_TOOLS: QueryOptimizationHint(
                use_cache=True,
                cache_ttl=3600,  # Long TTL for relatively static data
                parallel_execution=False,
                priority=5,
                estimated_cost=1.0,
                required_services=["registry"],
                can_be_partial=False,
            ),
            QueryType.REGISTRY_PROMPTS: QueryOptimizationHint(
                use_cache=True,
                cache_ttl=3600,
                parallel_execution=False,
                priority=5,
                estimated_cost=1.0,
                required_services=["registry"],
                can_be_partial=False,
            ),
            QueryType.FLAGS_GET: QueryOptimizationHint(
                use_cache=True,
                cache_ttl=300,  # Medium TTL for config data
                parallel_execution=False,
                priority=3,
                estimated_cost=0.5,
                required_services=["config"],
                can_be_partial=False,
            ),
            QueryType.RBAC_ROLES: QueryOptimizationHint(
                use_cache=True,
                cache_ttl=1800,  # 30 min TTL for security data
                parallel_execution=False,
                priority=7,
                estimated_cost=2.0,
                required_services=["rbac", "policy"],
                can_be_partial=False,
            ),
        }

    async def optimize_query(
        self,
        query_type: QueryType,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> QueryOptimizationHint:
        """Generate optimal execution plan for query."""
        start_time = time.time()

        # Get base optimization hint
        hint = self.optimization_rules.get(query_type, QueryOptimizationHint())

        # Adaptive optimization based on historical performance
        query_key = self._generate_query_key(query_type, params)
        stats = self.query_stats[query_key]

        # Adjust cache TTL based on hit rate
        if stats["cache_hit_rate"] > 0.8:
            hint.cache_ttl = min(hint.cache_ttl * 2, 7200)  # Extend up to 2 hours
        elif stats["cache_hit_rate"] < 0.3:
            hint.cache_ttl = max(hint.cache_ttl // 2, 30)  # Reduce to min 30 seconds

        # Adjust priority based on QoS requirements
        qos = metadata.get("qos", {})
        if qos.get("latency_budget_ms", 1000) < 100:
            hint.priority = min(hint.priority + 3, 10)

        # TODO: Replace with actual system load monitoring service
        system_load = await self._get_system_load()
        if system_load > 0.8:
            hint.parallel_execution = False  # Reduce load under stress

        # Update optimization timestamp
        stats["last_optimization"] = time.time()

        optimization_time = time.time() - start_time
        logger.debug(
            f"Query optimization completed in {optimization_time:.3f}s for {query_type.value}"
        )

        return hint

    def _generate_query_key(self, query_type: QueryType, params: Dict[str, Any]) -> str:
        """Generate cache key for query."""
        # Create stable hash from query type and normalized parameters
        normalized_params = json.dumps(params, sort_keys=True, default=str)
        return f"{query_type.value}:{hashlib.sha256(normalized_params.encode()).hexdigest()[:16]}"

    async def _get_system_load(self) -> float:
        """Get current system load - TODO: implement actual system monitoring."""
        # In real implementation, this would check actual system metrics
        return 0.5

    def update_query_stats(
        self,
        query_type: QueryType,
        params: Dict[str, Any],
        execution_time: float,
        cache_hit: bool,
        success: bool,
    ) -> None:
        """Update query performance statistics."""
        query_key = self._generate_query_key(query_type, params)
        stats = self.query_stats[query_key]

        # Update execution count
        stats["execution_count"] += 1

        # Update average latency with exponential moving average
        alpha = 0.1
        current_avg = stats["avg_latency_ms"]
        stats["avg_latency_ms"] = (1 - alpha) * current_avg + alpha * (
            execution_time * 1000
        )

        # Update cache hit rate
        total_requests = stats["execution_count"]
        if cache_hit:
            stats["cache_hit_rate"] = (
                stats["cache_hit_rate"] * (total_requests - 1) + 1
            ) / total_requests
        else:
            stats["cache_hit_rate"] = (
                stats["cache_hit_rate"] * (total_requests - 1)
            ) / total_requests

        # Update error rate
        if not success:
            stats["error_rate"] = (
                stats["error_rate"] * (total_requests - 1) + 1
            ) / total_requests
        else:
            stats["error_rate"] = (
                stats["error_rate"] * (total_requests - 1)
            ) / total_requests


class QueryCache:
    """
    High-performance query cache with adaptive eviction.

    Features:
    - TTL-based expiration
    - LRU eviction policy
    - Memory usage monitoring
    - Cache hit rate optimization
    """

    def __init__(self, max_size: int = 10000, max_memory_mb: int = 512):
        self.cache: Dict[str, QueryCacheEntry] = {}
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory_bytes = 0
        self.total_requests = 0
        self.cache_hits = 0

    async def get(self, cache_key: str) -> Optional[Any]:
        """Get cached result if valid."""
        self.total_requests += 1

        if cache_key not in self.cache:
            return None

        entry = self.cache[cache_key]
        current_time = time.time()

        # Check TTL expiration
        if current_time - entry.created_at > entry.ttl_seconds:
            await self._evict_entry(cache_key)
            return None

        # Update access statistics
        entry.access_count += 1
        entry.last_accessed = current_time
        self.cache_hits += 1

        logger.debug(f"Cache hit for key: {cache_key[:16]}...")
        return entry.data

    async def set(
        self,
        cache_key: str,
        data: Any,
        ttl_seconds: int,
        source_services: Optional[List[str]] = None,
    ) -> None:
        """Store result in cache."""
        current_time = time.time()

        # Estimate memory usage (rough approximation)
        data_size = len(json.dumps(data, default=str).encode())

        # Evict if cache is full
        while (
            len(self.cache) >= self.max_size
            or self.current_memory_bytes + data_size > self.max_memory_bytes
        ):
            await self._evict_lru()

        # Store cache entry
        entry = QueryCacheEntry(
            data=data,
            created_at=current_time,
            ttl_seconds=ttl_seconds,
            source_services=source_services or [],
        )

        self.cache[cache_key] = entry
        self.current_memory_bytes += data_size

        logger.debug(
            f"Cached result for key: {cache_key[:16]}... (TTL: {ttl_seconds}s)"
        )

    async def invalidate_by_service(self, service_name: str) -> int:
        """Invalidate all cache entries from a specific service."""
        keys_to_remove: List[str] = []

        for cache_key, entry in self.cache.items():
            if service_name in entry.source_services:
                keys_to_remove.append(cache_key)

        for cache_key in keys_to_remove:
            await self._evict_entry(cache_key)

        logger.info(
            f"Invalidated {len(keys_to_remove)} cache entries for service: {service_name}"
        )
        return len(keys_to_remove)

    async def _evict_entry(self, cache_key: str) -> None:
        """Remove specific cache entry."""
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            data_size = len(json.dumps(entry.data, default=str).encode())
            self.current_memory_bytes -= data_size
            del self.cache[cache_key]

    async def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.cache:
            return

        # Find LRU entry
        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k].last_accessed)
        await self._evict_entry(lru_key)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        hit_rate = self.cache_hits / max(self.total_requests, 1)

        return {
            "total_entries": len(self.cache),
            "max_size": self.max_size,
            "memory_usage_mb": self.current_memory_bytes / (1024 * 1024),
            "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
            "cache_hit_rate": hit_rate,
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
        }


# =====================================================
# Sub-issue #23.2: Multi-source Data Aggregation
# =====================================================


@dataclass
class DataSourceMetadata:
    """Metadata for data source configuration."""

    name: str
    service_type: str
    base_url: Optional[str] = None
    timeout_ms: int = 5000
    retry_attempts: int = 3
    circuit_breaker_threshold: float = 0.5
    priority: int = 5
    supports_parallel: bool = True
    data_freshness_seconds: int = 300


class DataSourceRegistry:
    """Registry of available data sources."""

    def __init__(self):
        self.sources: Dict[str, DataSourceMetadata] = {
            "retrieval": DataSourceMetadata(
                name="retrieval",
                service_type="memory_service",
                timeout_ms=2000,
                priority=9,
                supports_parallel=True,
                data_freshness_seconds=60,
            ),
            "registry": DataSourceMetadata(
                name="registry",
                service_type="registry_service",
                timeout_ms=1000,
                priority=5,
                supports_parallel=False,
                data_freshness_seconds=3600,
            ),
            "policy": DataSourceMetadata(
                name="policy",
                service_type="policy_service",
                timeout_ms=1500,
                priority=8,
                supports_parallel=True,
                data_freshness_seconds=1800,
            ),
            "rbac": DataSourceMetadata(
                name="rbac",
                service_type="rbac_service",
                timeout_ms=1000,
                priority=7,
                supports_parallel=False,
                data_freshness_seconds=1800,
            ),
            "config": DataSourceMetadata(
                name="config",
                service_type="config_service",
                timeout_ms=500,
                priority=3,
                supports_parallel=False,
                data_freshness_seconds=300,
            ),
            "indexing": DataSourceMetadata(
                name="indexing",
                service_type="indexing_service",
                timeout_ms=3000,
                priority=6,
                supports_parallel=True,
                data_freshness_seconds=120,
            ),
        }

        # Circuit breaker state
        self.circuit_breaker_state: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "failure_count": 0,
                "last_failure_time": 0,
                "state": "CLOSED",  # CLOSED, OPEN, HALF_OPEN
            }
        )

    def get_sources_for_query(self, query_type: QueryType) -> List[DataSourceMetadata]:
        """Get required data sources for query type."""
        source_mapping = {
            QueryType.MEMORY_RECALL: ["retrieval", "policy", "indexing"],
            QueryType.REGISTRY_TOOLS: ["registry"],
            QueryType.REGISTRY_PROMPTS: ["registry"],
            QueryType.FLAGS_GET: ["config"],
            QueryType.RBAC_ROLES: ["rbac", "policy"],
            QueryType.RECEIPT_GET: ["retrieval"],
            QueryType.DSAR_STATUS: ["policy", "retrieval"],
            QueryType.INDEX_STATUS: ["indexing"],
            QueryType.CONNECTORS_LIST: ["config", "registry"],
            QueryType.THINGS_LIST: ["registry"],
        }

        source_names = source_mapping.get(query_type, [])
        return [self.sources[name] for name in source_names if name in self.sources]

    def is_source_healthy(self, source_name: str) -> bool:
        """Check if data source is healthy (circuit breaker logic)."""
        breaker = self.circuit_breaker_state[source_name]
        current_time = time.time()

        if breaker["state"] == "OPEN":
            # Check if we should try half-open
            if current_time - breaker["last_failure_time"] > 30:  # 30 second timeout
                breaker["state"] = "HALF_OPEN"
                logger.info(f"Circuit breaker for {source_name} moved to HALF_OPEN")
                return True
            return False

        return True

    def record_success(self, source_name: str) -> None:
        """Record successful operation."""
        breaker = self.circuit_breaker_state[source_name]
        breaker["failure_count"] = 0
        if breaker["state"] == "HALF_OPEN":
            breaker["state"] = "CLOSED"
            logger.info(f"Circuit breaker for {source_name} moved to CLOSED")

    def record_failure(self, source_name: str) -> None:
        """Record failed operation."""
        source = self.sources.get(source_name)
        if not source:
            return

        breaker = self.circuit_breaker_state[source_name]
        breaker["failure_count"] += 1
        breaker["last_failure_time"] = time.time()

        # Trip circuit breaker if failure threshold exceeded
        failure_rate = breaker["failure_count"] / 10  # Over last 10 operations
        if failure_rate >= source.circuit_breaker_threshold:
            breaker["state"] = "OPEN"
            logger.warning(f"Circuit breaker for {source_name} moved to OPEN")


class DataAggregator:
    """
    Multi-source data aggregation engine.

    Features:
    - Parallel data fetching
    - Error resilience and fallbacks
    - Response merging and conflict resolution
    - Performance optimization
    """

    def __init__(self, source_registry: DataSourceRegistry):
        self.source_registry = source_registry
        self.request_timeout = 10.0  # Overall request timeout

    async def aggregate_data(
        self,
        query_type: QueryType,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
        optimization_hint: QueryOptimizationHint,
    ) -> Dict[str, Any]:
        """Aggregate data from multiple sources."""
        start_time = time.time()

        # Get required data sources
        sources = self.source_registry.get_sources_for_query(query_type)
        healthy_sources = [
            s for s in sources if self.source_registry.is_source_healthy(s.name)
        ]

        if not healthy_sources:
            raise RuntimeError(
                f"No healthy data sources available for {query_type.value}"
            )

        # Execute data fetching
        if optimization_hint.parallel_execution and len(healthy_sources) > 1:
            results = await self._fetch_parallel(
                healthy_sources, query_type, params, envelope, metadata
            )
        else:
            results = await self._fetch_sequential(
                healthy_sources, query_type, params, envelope, metadata
            )

        # Merge results
        merged_result = await self._merge_results(query_type, results, params)

        execution_time = time.time() - start_time
        logger.info(
            f"Data aggregation completed in {execution_time:.3f}s for {query_type.value}"
        )

        return merged_result

    async def _fetch_parallel(
        self,
        sources: List[DataSourceMetadata],
        query_type: QueryType,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fetch data from multiple sources in parallel."""
        tasks: List[tuple[str, Any]] = []

        for source in sources:
            task = asyncio.create_task(
                self._fetch_from_source(source, query_type, params, envelope, metadata)
            )
            tasks.append((source.name, task))

        results: Dict[str, Any] = {}
        for source_name, task in tasks:
            try:
                result = await asyncio.wait_for(task, timeout=self.request_timeout)
                results[source_name] = result
                self.source_registry.record_success(source_name)
            except Exception as e:
                logger.error(f"Failed to fetch from {source_name}: {e}")
                self.source_registry.record_failure(source_name)
                results[source_name] = {"error": str(e)}

        return results

    async def _fetch_sequential(
        self,
        sources: List[DataSourceMetadata],
        query_type: QueryType,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fetch data from sources sequentially."""
        results: Dict[str, Any] = {}

        # Sort by priority (highest first)
        sorted_sources = sorted(sources, key=lambda s: s.priority, reverse=True)

        for source in sorted_sources:
            try:
                result = await self._fetch_from_source(
                    source, query_type, params, envelope, metadata
                )
                results[source.name] = result
                self.source_registry.record_success(source.name)
            except Exception as e:
                logger.error(f"Failed to fetch from {source.name}: {e}")
                self.source_registry.record_failure(source.name)
                results[source.name] = {"error": str(e)}

        return results

    async def _fetch_from_source(
        self,
        source: DataSourceMetadata,
        query_type: QueryType,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Any:
        """Fetch data from a specific source."""
        start_time = time.time()

        # Mock implementation - in real system, this would call actual services
        # Removed artificial sleep - this was causing performance bottleneck

        if source.name == "retrieval" and query_type == QueryType.MEMORY_RECALL:
            result: Dict[str, Any] = {
                "items": [
                    {
                        "id": "mem_001",
                        "score": 0.95,
                        "topic": "conversation",
                        "band": "GREEN",
                        "snippet": "Sample memory snippet",
                        "space_id": params.get("space_id", "personal:default"),
                        "payload": {"type": "memory", "source": "episodic"},
                    }
                ],
                "total": 1,
                "has_more": False,
            }
        elif source.name == "registry" and query_type in [
            QueryType.REGISTRY_TOOLS,
            QueryType.REGISTRY_PROMPTS,
        ]:
            if query_type == QueryType.REGISTRY_TOOLS:
                result = {
                    "items": [
                        {
                            "id": "tool_001",
                            "name": "Memory Recall Tool",
                            "caps": ["recall", "search"],
                        },
                        {
                            "id": "tool_002",
                            "name": "Analysis Tool",
                            "caps": ["analyze", "summarize"],
                        },
                    ]
                }
            else:
                result = {
                    "items": [
                        {
                            "id": "prompt_001",
                            "name": "Creative Writing",
                            "content": "Generate creative...",
                        },
                        {
                            "id": "prompt_002",
                            "name": "Code Review",
                            "content": "Review this code...",
                        },
                    ]
                }
        elif source.name == "config" and query_type == QueryType.FLAGS_GET:
            result = {
                "items": [
                    {"key": "feature_x", "enabled": True},
                    {"key": "feature_y", "enabled": False},
                ]
            }
        elif source.name == "rbac" and query_type == QueryType.RBAC_ROLES:
            result = {
                "items": [
                    {
                        "name": "admin",
                        "caps": ["WRITE", "RECALL", "PROJECT", "SCHEDULE"],
                    },
                    {"name": "user", "caps": ["RECALL", "PROJECT"]},
                ]
            }
        else:
            result = {
                "source": source.name,
                "query_type": query_type.value,
                "mock": True,
            }

        fetch_time = time.time() - start_time
        logger.debug(f"Fetched from {source.name} in {fetch_time:.3f}s")

        return result

    async def _merge_results(
        self,
        query_type: QueryType,
        results: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge results from multiple sources."""
        # Remove failed results
        successful_results = {k: v for k, v in results.items() if "error" not in v}

        if not successful_results:
            raise RuntimeError("All data sources failed")

        # Query-specific merging logic
        if query_type == QueryType.MEMORY_RECALL:
            return await self._merge_memory_recall_results(successful_results, params)
        elif query_type in [QueryType.REGISTRY_TOOLS, QueryType.REGISTRY_PROMPTS]:
            return await self._merge_registry_results(successful_results)
        elif query_type == QueryType.FLAGS_GET:
            return await self._merge_config_results(successful_results)
        elif query_type == QueryType.RBAC_ROLES:
            return await self._merge_rbac_results(successful_results)
        else:
            # Default merge: return first successful result
            return next(iter(successful_results.values()))

    async def _merge_memory_recall_results(
        self, results: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge memory recall results from multiple sources."""
        all_items = []

        # Collect items from all sources
        for source_name, result in results.items():
            if "items" in result:
                for item in result["items"]:
                    item["_source"] = source_name
                    all_items.append(item)

        # Sort by score (highest first)
        all_items.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Apply limit
        k = params.get("k", 10)
        limited_items = all_items[:k]

        return {
            "items": limited_items,
            "total": len(all_items),
            "has_more": len(all_items) > k,
            "sources": list(results.keys()),
        }

    async def _merge_registry_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Merge registry results."""
        all_items = []

        for source_name, result in results.items():
            if "items" in result:
                all_items.extend(result["items"])

        # Remove duplicates by id
        seen_ids = set()
        unique_items = []
        for item in all_items:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                unique_items.append(item)

        return {"items": unique_items}

    async def _merge_config_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configuration results."""
        all_items = []

        for source_name, result in results.items():
            if "items" in result:
                all_items.extend(result["items"])

        return {"items": all_items}

    async def _merge_rbac_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Merge RBAC results."""
        all_items = []

        for source_name, result in results.items():
            if "items" in result:
                all_items.extend(result["items"])

        return {"items": all_items}


# =====================================================
# Sub-issue #23.3: Access Control Filtering
# =====================================================


@dataclass
class SecurityContext:
    """Security context for access control."""

    user_id: str
    device_id: str
    authenticated: bool
    auth_method: str
    capabilities: List[str]
    mls_group: Optional[str] = None
    trust_level: str = "green"
    space_access: Dict[str, str] = field(default_factory=dict)


class AccessControlPolicy:
    """Access control policy rules."""

    def __init__(self):
        self.band_hierarchy = ["BLACK", "RED", "AMBER", "GREEN"]
        self.capability_requirements = {
            QueryType.MEMORY_RECALL: ["RECALL"],
            QueryType.REGISTRY_TOOLS: ["RECALL"],
            QueryType.REGISTRY_PROMPTS: ["RECALL"],
            QueryType.FLAGS_GET: [],  # No special capability required
            QueryType.RBAC_ROLES: ["ADMIN"],
            QueryType.RECEIPT_GET: ["RECALL"],
            QueryType.DSAR_STATUS: ["PRIVACY"],
            QueryType.INDEX_STATUS: ["ADMIN"],
            QueryType.CONNECTORS_LIST: ["ADMIN"],
            QueryType.THINGS_LIST: ["RECALL"],
        }

    def check_query_access(
        self,
        query_type: QueryType,
        params: Dict[str, Any],
        security_context: SecurityContext,
    ) -> bool:
        """Check if user has access to execute query."""
        required_caps = self.capability_requirements.get(query_type, [])

        # Check if user has required capabilities
        for cap in required_caps:
            if cap not in security_context.capabilities:
                return False

        # Additional space-based access control for memory queries
        if query_type == QueryType.MEMORY_RECALL:
            space_id = params.get("space_id")
            if space_id and not self._check_space_access(space_id, security_context):
                return False

        return True

    def _check_space_access(
        self, space_id: str, security_context: SecurityContext
    ) -> bool:
        """Check if user has access to specific space."""
        # Extract space type from space_id (format: "type:id")
        if ":" not in space_id:
            return False

        space_type = space_id.split(":")[0]

        # Space access rules
        if space_type == "personal":
            return True  # Always allow access to personal space
        elif space_type in ["selective", "shared"]:
            return security_context.trust_level in ["green", "amber"]
        elif space_type == "extended":
            return security_context.trust_level == "green"
        elif space_type == "interfamily":
            return "ADMIN" in security_context.capabilities

        return False

    def get_data_filter_level(
        self,
        security_context: SecurityContext,
        requested_bands: Optional[List[str]] = None,
    ) -> str:
        """Determine data filtering level based on security context."""
        trust_level = security_context.trust_level.upper()

        # Map trust level to band access
        trust_to_band = {
            "GREEN": "GREEN",
            "AMBER": "AMBER",
            "RED": "RED",
            "BLACK": "BLACK",
        }

        max_allowed_band = trust_to_band.get(trust_level, "BLACK")

        # If specific bands requested, use most restrictive
        if requested_bands:
            # Find most restrictive band that user can access
            accessible_bands: List[str] = []
            for band in requested_bands:
                band_index = self.band_hierarchy.index(band)
                max_index = self.band_hierarchy.index(max_allowed_band)
                if band_index >= max_index:
                    accessible_bands.append(band)

            if accessible_bands:
                # Return most restrictive accessible band
                return min(accessible_bands, key=lambda b: self.band_hierarchy.index(b))

        return max_allowed_band


class AccessControlFilter:
    """
    Access control filtering engine.

    Features:
    - Band-based data filtering
    - PII redaction and masking
    - Space-based access control
    - Audit logging
    """

    def __init__(self, policy: AccessControlPolicy):
        self.policy = policy
        self.audit_log: List[Dict[str, Any]] = []

    async def filter_query_result(
        self,
        query_type: QueryType,
        raw_result: Any,
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Any:
        """Apply access control filtering to query result."""
        start_time = time.time()

        # Extract security context from envelope
        security_context = self._extract_security_context(envelope)

        # Log access attempt
        await self._log_access_attempt(query_type, security_context, metadata)

        # Apply filtering based on query type
        if query_type == QueryType.MEMORY_RECALL:
            filtered_result = await self._filter_memory_recall(
                raw_result, security_context, metadata
            )
        elif query_type in [QueryType.REGISTRY_TOOLS, QueryType.REGISTRY_PROMPTS]:
            filtered_result = await self._filter_registry_data(
                raw_result, security_context
            )
        elif query_type == QueryType.RBAC_ROLES:
            filtered_result = await self._filter_rbac_data(raw_result, security_context)
        else:
            # Default: no filtering for low-sensitivity queries
            filtered_result = raw_result

        # Apply general PII redaction
        filtered_result = await self._apply_pii_redaction(
            filtered_result, security_context
        )

        filter_time = time.time() - start_time
        logger.debug(f"Access control filtering completed in {filter_time:.3f}s")

        return filtered_result

    def _extract_security_context(self, envelope: Envelope) -> SecurityContext:
        """Extract security context from request envelope."""
        # Mock implementation - in real system, this would extract from JWT/mTLS
        return SecurityContext(
            user_id=envelope.user_id or "anonymous",
            device_id="device_001",
            authenticated=True,
            auth_method="bearer",
            capabilities=["RECALL", "PROJECT"],
            trust_level="green",
        )

    async def _filter_memory_recall(
        self,
        raw_result: Dict[str, Any],
        security_context: SecurityContext,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Filter memory recall results based on security bands."""
        if "items" not in raw_result:
            return raw_result

        # Get allowed band level
        requested_bands = metadata.get("filters", {}).get("bands", [])
        max_band = self.policy.get_data_filter_level(security_context, requested_bands)

        filtered_items = []
        for item in raw_result["items"]:
            item_band = item.get("band", "GREEN")

            # Check if user can access this band level
            if self._can_access_band(item_band, max_band):
                # Apply band-specific filtering
                filtered_item = await self._apply_band_filtering(
                    item, item_band, security_context
                )
                filtered_items.append(filtered_item)

        result = raw_result.copy()
        result["items"] = filtered_items
        result["total"] = len(filtered_items)

        return result

    def _can_access_band(self, item_band: str, user_max_band: str) -> bool:
        """Check if user can access item with specific band."""
        try:
            item_index = self.policy.band_hierarchy.index(item_band)
            user_index = self.policy.band_hierarchy.index(user_max_band)
            return item_index >= user_index
        except ValueError:
            return False

    async def _apply_band_filtering(
        self,
        item: Dict[str, Any],
        band: str,
        security_context: SecurityContext,
    ) -> Dict[str, Any]:
        """Apply band-specific filtering rules."""
        filtered_item = item.copy()

        if band == "RED":
            # RED band: mask snippet_text and source_uri
            if "snippet" in filtered_item:
                filtered_item["snippet"] = "[REDACTED]"
            if "source_uri" in filtered_item:
                filtered_item["source_uri"] = "[REDACTED]"
        elif band == "BLACK":
            # BLACK band: deny access completely
            return None

        return filtered_item

    async def _filter_registry_data(
        self,
        raw_result: Dict[str, Any],
        security_context: SecurityContext,
    ) -> Dict[str, Any]:
        """Filter registry data based on user capabilities."""
        # Registry data typically doesn't need heavy filtering
        # But we could filter based on user access levels
        return raw_result

    async def _filter_rbac_data(
        self,
        raw_result: Dict[str, Any],
        security_context: SecurityContext,
    ) -> Dict[str, Any]:
        """Filter RBAC data - only show roles user can access."""
        if "ADMIN" not in security_context.capabilities:
            # Non-admin users only see basic role info
            if "items" in raw_result:
                filtered_items = []
                for item in raw_result["items"]:
                    filtered_item = {
                        "name": item["name"],
                        # Hide capabilities from non-admin users
                    }
                    filtered_items.append(filtered_item)

                result = raw_result.copy()
                result["items"] = filtered_items
                return result

        return raw_result

    async def _apply_pii_redaction(
        self,
        result: Any,
        security_context: SecurityContext,
    ) -> Any:
        """Apply PII redaction based on security context."""
        # Mock implementation - in real system, this would use ML-based PII detection
        return result

    async def _log_access_attempt(
        self,
        query_type: QueryType,
        security_context: SecurityContext,
        metadata: Dict[str, Any],
    ) -> None:
        """Log access attempt for audit purposes."""
        audit_entry = {
            "timestamp": time.time(),
            "user_id": security_context.user_id,
            "device_id": security_context.device_id,
            "query_type": query_type.value,
            "trust_level": security_context.trust_level,
            "trace_id": metadata.get("trace_id"),
        }

        self.audit_log.append(audit_entry)

        # Keep audit log bounded
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-5000:]


# =====================================================
# Main QueryFacadePort Implementation
# =====================================================


class QueryFacadePort(ABC):
    """
    Abstract base class for query facade implementations.

    The query facade is responsible for:
    1. Optimizing query execution and caching
    2. Aggregating data from multiple sources
    3. Applying access control filtering
    4. Managing query performance and limits
    5. Providing consistent query interfaces
    """

    @abstractmethod
    async def execute_query(
        self,
        operation: str,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Any:
        """
        Execute a query operation.

        Args:
            operation: Query name (e.g., "memory_recall", "registry_tools")
            params: Query parameters
            envelope: Request envelope with security context
            metadata: Additional metadata (trace_id, security_context, etc.)

        Returns:
            Query execution result

        Raises:
            QueryValidationError: If query validation fails
            AccessDeniedError: If access control fails
            DataSourceError: If data source access fails
        """
        pass

    @abstractmethod
    async def validate_query(
        self,
        operation: str,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> bool:
        """
        Validate query before execution.

        Args:
            operation: Query name
            params: Query parameters
            envelope: Request envelope
            metadata: Request metadata

        Returns:
            True if query is valid

        Raises:
            QueryValidationError: If validation fails
        """
        pass

    @abstractmethod
    async def apply_access_control(
        self,
        operation: str,
        result: Any,
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Any:
        """
        Apply access control filtering to query results.

        Args:
            operation: Query name
            result: Raw query result
            envelope: Request envelope
            metadata: Request metadata

        Returns:
            Filtered query result
        """
        pass


class QueryFacadeImplementation(QueryFacadePort):
    """
    World-class QueryFacadePort implementation.

    This implementation provides:
    - Advanced query optimization and caching
    - Multi-source data aggregation with resilience
    - Comprehensive access control filtering
    - Performance monitoring and observability
    """

    def __init__(self):
        # Initialize core components
        self.query_optimizer = QueryOptimizer()
        self.query_cache = QueryCache(max_size=10000, max_memory_mb=512)
        self.source_registry = DataSourceRegistry()
        self.data_aggregator = DataAggregator(self.source_registry)
        self.access_policy = AccessControlPolicy()
        self.access_filter = AccessControlFilter(self.access_policy)

        # Performance metrics
        self.query_metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "avg_latency_ms": 0.0,
            "error_rate": 0.0,
        }

        # Phase 2: Service integration
        from services import default_service_registry

        self.service_registry = default_service_registry
        self.retrieval_service = self.service_registry.get_retrieval_service()

        logger.info(
            "QueryFacadeImplementation initialized with advanced features and service layer"
        )

    async def execute_query(
        self,
        operation: str,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Any:
        """Execute query with full optimization and access control."""
        start_time = time.time()
        query_id = str(uuid4())

        try:
            # Convert operation to QueryType
            query_type = QueryType(operation)
        except ValueError:
            raise ValueError(f"Unsupported query operation: {operation}")

        logger.info(f"Executing query {query_id}: {operation}")
        self.query_metrics["total_queries"] += 1

        try:
            # Step 1: Validate query
            await self.validate_query(operation, params, envelope, metadata)

            # Phase 2: Try service-first routing for supported operations
            service_result = await self._try_service_routing(
                operation, params, envelope, metadata
            )
            if service_result is not None:
                execution_time = time.time() - start_time
                self._update_metrics(execution_time, success=True)
                logger.info(
                    f"Query {query_id} executed via service in {execution_time:.3f}s"
                )
                return service_result

            # Step 2: Generate optimization plan
            optimization_hint = await self.query_optimizer.optimize_query(
                query_type, params, envelope, metadata
            )

            # Step 3: Check cache (if enabled)
            cached_result = None
            cache_key = None
            if optimization_hint.use_cache:
                cache_key = self._generate_cache_key(operation, params, envelope)
                cached_result = await self.query_cache.get(cache_key)

            if cached_result is not None:
                # Cache hit
                self.query_metrics["cache_hits"] += 1
                self.query_optimizer.update_query_stats(
                    query_type,
                    params,
                    time.time() - start_time,
                    cache_hit=True,
                    success=True,
                )

                logger.info(f"Query {query_id} served from cache")
                return cached_result

            # Step 4: Aggregate data from sources
            raw_result = await self.data_aggregator.aggregate_data(
                query_type, params, envelope, metadata, optimization_hint
            )

            # Step 5: Apply access control filtering
            filtered_result = await self.access_filter.filter_query_result(
                query_type, raw_result, envelope, metadata
            )

            # Step 6: Cache result (if enabled)
            if optimization_hint.use_cache and cache_key:
                source_services = optimization_hint.required_services
                await self.query_cache.set(
                    cache_key,
                    filtered_result,
                    optimization_hint.cache_ttl,
                    source_services,
                )

            # Step 7: Update metrics
            execution_time = time.time() - start_time
            self._update_metrics(execution_time, success=True)
            self.query_optimizer.update_query_stats(
                query_type, params, execution_time, cache_hit=False, success=True
            )

            logger.info(
                f"Query {query_id} executed successfully in {execution_time:.3f}s"
            )
            return filtered_result

        except Exception as e:
            # Update error metrics
            execution_time = time.time() - start_time
            self._update_metrics(execution_time, success=False)
            self.query_optimizer.update_query_stats(
                query_type, params, execution_time, cache_hit=False, success=False
            )

            logger.error(f"Query {query_id} failed after {execution_time:.3f}s: {e}")
            raise

    async def validate_query(
        self,
        operation: str,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> bool:
        """Comprehensive query validation."""
        try:
            query_type = QueryType(operation)
        except ValueError:
            raise ValueError(f"Unknown query operation: {operation}")

        # Extract security context
        security_context = self.access_filter._extract_security_context(
            envelope
        )  # noqa: SLF001

        # Check access permissions
        if not self.access_policy.check_query_access(
            query_type, params, security_context
        ):
            raise PermissionError(f"Access denied for query: {operation}")

        # Validate query parameters
        await self._validate_query_parameters(query_type, params)

        # Check rate limits (mock implementation)
        await self._check_rate_limits(security_context, metadata)

        return True

    async def apply_access_control(
        self,
        operation: str,
        result: Any,
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Any:
        """Apply access control filtering (delegated to AccessControlFilter)."""
        try:
            query_type = QueryType(operation)
        except ValueError:
            return result

        return await self.access_filter.filter_query_result(
            query_type, result, envelope, metadata
        )

    def _generate_cache_key(
        self,
        operation: str,
        params: Dict[str, Any],
        envelope: Envelope,
    ) -> str:
        """Generate cache key for query."""
        # Include user context in cache key for security
        security_context = self.access_filter._extract_security_context(
            envelope
        )  # noqa: SLF001

        cache_data = {
            "operation": operation,
            "params": params,
            "user_id": security_context.user_id,
            "trust_level": security_context.trust_level,
            "capabilities": sorted(security_context.capabilities),
        }

        cache_str = json.dumps(cache_data, sort_keys=True, default=str)
        return hashlib.sha256(cache_str.encode()).hexdigest()

    async def _validate_query_parameters(
        self,
        query_type: QueryType,
        params: Dict[str, Any],
    ) -> None:
        """Validate query-specific parameters."""
        if query_type == QueryType.MEMORY_RECALL:
            # Validate RecallRequest schema
            if "query" not in params or not params["query"].strip():
                raise ValueError("Query text is required")

            k = params.get("k", 10)
            if not isinstance(k, int) or k < 1 or k > 200:
                raise ValueError("k must be between 1 and 200")

            # Validate space_id format if provided
            space_id = params.get("space_id")
            if space_id and not self._is_valid_space_id(space_id):
                raise ValueError("Invalid space_id format")

        # Add more parameter validation as needed

    def _is_valid_space_id(self, space_id: str) -> bool:
        """Validate space_id format."""
        valid_prefixes = [
            "personal:",
            "selective:",
            "shared:",
            "extended:",
            "interfamily:",
        ]
        return any(space_id.startswith(prefix) for prefix in valid_prefixes)

    async def _check_rate_limits(
        self,
        security_context: SecurityContext,
        metadata: Dict[str, Any],
    ) -> None:
        """Check rate limits for user."""
        # Mock implementation - in real system, this would check Redis/cache
        pass

    def _update_metrics(self, execution_time: float, success: bool) -> None:
        """Update query performance metrics."""
        # Update average latency with exponential moving average
        alpha = 0.1
        current_avg = self.query_metrics["avg_latency_ms"]
        self.query_metrics["avg_latency_ms"] = (1 - alpha) * current_avg + alpha * (
            execution_time * 1000
        )

        # Update error rate
        total_queries = self.query_metrics["total_queries"]
        if not success:
            current_error_rate = self.query_metrics["error_rate"]
            self.query_metrics["error_rate"] = (
                current_error_rate * (total_queries - 1) + 1
            ) / total_queries
        else:
            current_error_rate = self.query_metrics["error_rate"]
            self.query_metrics["error_rate"] = (
                current_error_rate * (total_queries - 1)
            ) / total_queries

    # Additional management methods

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        cache_stats = self.query_cache.get_cache_stats()

        return {
            "query_metrics": self.query_metrics,
            "cache_stats": cache_stats,
            "optimizer_stats": dict(self.query_optimizer.query_stats),
            "source_health": {
                name: self.source_registry.is_source_healthy(name)
                for name in self.source_registry.sources.keys()
            },
            "circuit_breaker_stats": dict(self.source_registry.circuit_breaker_state),
        }

    async def invalidate_cache_for_service(self, service_name: str) -> int:
        """Invalidate cache entries for a specific service."""
        return await self.query_cache.invalidate_by_service(service_name)

    async def health_check(self) -> Dict[str, Any]:
        """Get health status of query facade."""
        healthy_sources = sum(
            1
            for name in self.source_registry.sources.keys()
            if self.source_registry.is_source_healthy(name)
        )
        total_sources = len(self.source_registry.sources)

        status = "healthy"
        if healthy_sources < total_sources * 0.5:
            status = "degraded"
        elif healthy_sources == 0:
            status = "unhealthy"

        return {
            "status": status,
            "healthy_sources": healthy_sources,
            "total_sources": total_sources,
            "cache_hit_rate": self.query_metrics["cache_hits"]
            / max(self.query_metrics["total_queries"], 1),
            "avg_latency_ms": self.query_metrics["avg_latency_ms"],
            "error_rate": self.query_metrics["error_rate"],
        }

    async def _try_service_routing(
        self,
        operation: str,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Optional[Any]:
        """
        Phase 2: Service-first routing for supported query operations.

        Try to handle queries through service layer before falling back to data sources.
        This enables end-to-end testing without full data source infrastructure.

        Returns:
            Service result if operation was handled, None if should use data sources
        """
        try:
            # Map query operations to services
            if operation == "memory_recall":
                # Route to RetrievalService
                return await self._handle_memory_recall_via_service(
                    params, envelope, metadata
                )

            elif operation in ["receipt_get", "memory_details", "memory_references"]:
                # Route to RetrievalService for memory-related queries
                return await self._handle_memory_query_via_service(
                    operation, params, envelope, metadata
                )

            elif operation in ["dsar_status", "index_status"]:
                # These could be routed to services, but for now use data sources
                return None

            # For other operations (registry, flags, etc.), use existing data source routing
            return None

        except Exception as e:
            logger.warning(
                f"Service routing failed for {operation}, falling back to data sources: {e}"
            )
            return None

    async def _handle_memory_recall_via_service(
        self, params: Dict[str, Any], envelope: Envelope, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle memory_recall operation via RetrievalService."""
        # Extract security context
        security_context = metadata.get("security_context", {})

        # Call RetrievalService
        result = await self.retrieval_service.recall_memories(
            query=params.get("query", ""),
            space_id=security_context.get("space_id", "default"),
            security_context=security_context,
            limit=params.get("limit", 10),
            filters=params.get("filters", {}),
            include_content=params.get("include_content", True),
        )

        return result

    async def _handle_memory_query_via_service(
        self,
        operation: str,
        params: Dict[str, Any],
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Handle memory-related queries via RetrievalService."""
        security_context = metadata.get("security_context", {})

        if operation == "receipt_get":
            # Get receipt details
            envelope_id = params.get("envelope_id") or params.get("id", "")
            return await self.retrieval_service.get_memory_details(
                memory_id=envelope_id,
                security_context=security_context,
                include_content=False,
            )

        elif operation == "memory_details":
            # Get memory details
            memory_id = params.get("memory_id") or params.get("id", "")
            return await self.retrieval_service.get_memory_details(
                memory_id=memory_id,
                security_context=security_context,
                include_content=params.get("include_content", True),
            )

        elif operation == "memory_references":
            # Get memory references
            memory_id = params.get("memory_id") or params.get("id", "")
            return await self.retrieval_service.get_memory_references(
                memory_id=memory_id, security_context=security_context
            )

        return None


# Default instance for dependency injection
default_query_facade = QueryFacadeImplementation()

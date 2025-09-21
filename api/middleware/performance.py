"""
Middleware Performance Optimization - Sub-issue #21.3

Advanced performance optimization for the middleware chain including:
- Request routing optimization
- Caching strategies
- Connection pooling
- Batch processing
- Async optimization
- Memory management
- Profiling integration
"""

from __future__ import annotations

import asyncio
import cProfile
import gc
import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set
from weakref import WeakKeyDictionary

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """Performance optimization levels."""

    CONSERVATIVE = "conservative"  # Minimal optimizations, maximum stability
    BALANCED = "balanced"  # Balanced approach
    AGGRESSIVE = "aggressive"  # Maximum performance, potential stability trade-offs


@dataclass
class PerformanceConfig:
    """Configuration for performance optimizations."""

    optimization_level: OptimizationLevel = OptimizationLevel.BALANCED

    # Caching settings
    enable_response_caching: bool = True
    response_cache_size: int = 1000
    response_cache_ttl: int = 300  # seconds

    # Connection pooling
    enable_connection_pooling: bool = True
    max_pool_size: int = 50
    pool_recycle_time: int = 3600  # seconds

    # Batch processing
    enable_batch_processing: bool = True
    batch_size: int = 100
    batch_timeout: float = 0.1  # seconds

    # Memory management
    enable_memory_optimization: bool = True
    gc_frequency: int = 100  # requests
    weak_reference_caching: bool = True

    # Profiling
    enable_profiling: bool = False
    profile_sample_rate: float = 0.01  # 1% of requests

    # Async optimization
    enable_async_optimization: bool = True
    concurrent_limit: int = 100
    semaphore_size: int = 50


@dataclass
class PerformanceMetrics:
    """Performance metrics for middleware chain."""

    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    gc_collections: int = 0
    concurrent_requests: int = 0
    batched_requests: int = 0
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))


class ResponseCache:
    """High-performance response cache with TTL support."""

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, tuple[Response, float]] = {}
        self._access_times: Dict[str, float] = {}

    def _cleanup_expired(self) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp > self.ttl
        ]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._access_times.pop(key, None)

    def _evict_lru(self) -> None:
        """Evict least recently used entries if cache is full."""
        if len(self._cache) >= self.max_size:
            # Find LRU key
            lru_key = min(self._access_times, key=self._access_times.get)
            self._cache.pop(lru_key, None)
            self._access_times.pop(lru_key, None)

    def get(self, key: str) -> Optional[Response]:
        """Get cached response."""
        self._cleanup_expired()

        if key in self._cache:
            response, _ = self._cache[key]
            self._access_times[key] = time.time()
            return response
        return None

    def set(self, key: str, response: Response) -> None:
        """Cache response."""
        self._cleanup_expired()
        self._evict_lru()

        current_time = time.time()
        self._cache[key] = (response, current_time)
        self._access_times[key] = current_time

    def clear(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()
        self._access_times.clear()


class ConnectionPool:
    """Simple connection pool for middleware connections."""

    def __init__(self, max_size: int = 50, recycle_time: int = 3600):
        self.max_size = max_size
        self.recycle_time = recycle_time
        self._pool: deque = deque()
        self._active_connections: Set = set()
        self._connection_times: WeakKeyDictionary = WeakKeyDictionary()

    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool."""
        connection = None
        current_time = time.time()

        # Try to get from pool
        while self._pool and not connection:
            candidate = self._pool.popleft()
            # Check if connection is still valid
            creation_time = self._connection_times.get(candidate, 0)
            if current_time - creation_time < self.recycle_time:
                connection = candidate
                break

        # Create new connection if needed
        if not connection:
            connection = await self._create_connection()
            self._connection_times[connection] = current_time

        self._active_connections.add(connection)

        try:
            yield connection
        finally:
            self._active_connections.discard(connection)
            # Return to pool if not full
            if len(self._pool) < self.max_size:
                self._pool.append(connection)

    async def _create_connection(self):
        """Create new connection (placeholder)."""
        # In real implementation, this would create actual connections
        return object()


class BatchProcessor:
    """Batch processor for middleware operations."""

    def __init__(self, batch_size: int = 100, timeout: float = 0.1):
        self.batch_size = batch_size
        self.timeout = timeout
        self._pending_requests: list = []
        self._batch_futures: list = []
        self._last_batch_time = time.time()

    async def add_request(self, request_processor: Callable) -> Any:
        """Add request to batch for processing."""
        future = asyncio.Future()
        self._pending_requests.append((request_processor, future))
        self._batch_futures.append(future)

        # Process batch if conditions are met
        current_time = time.time()
        if (
            len(self._pending_requests) >= self.batch_size
            or current_time - self._last_batch_time > self.timeout
        ):
            await self._process_batch()

        return await future

    async def _process_batch(self) -> None:
        """Process current batch of requests."""
        if not self._pending_requests:
            return

        batch = self._pending_requests.copy()
        self._pending_requests.clear()
        self._last_batch_time = time.time()

        # Process all requests concurrently
        tasks = []
        for processor, future in batch:
            task = asyncio.create_task(self._process_single(processor, future))
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_single(
        self, processor: Callable, future: asyncio.Future
    ) -> None:
        """Process single request in batch."""
        try:
            result = await processor()
            if not future.done():
                future.set_result(result)
        except Exception as e:
            if not future.done():
                future.set_exception(e)


class PerformanceOptimizer:
    """Main performance optimization manager."""

    def __init__(self, config: Optional[PerformanceConfig] = None):
        self.config = config or PerformanceConfig()
        self.metrics = PerformanceMetrics()

        # Initialize components based on config
        self.response_cache = (
            ResponseCache(
                self.config.response_cache_size, self.config.response_cache_ttl
            )
            if self.config.enable_response_caching
            else None
        )

        self.connection_pool = (
            ConnectionPool(self.config.max_pool_size, self.config.pool_recycle_time)
            if self.config.enable_connection_pooling
            else None
        )

        self.batch_processor = (
            BatchProcessor(self.config.batch_size, self.config.batch_timeout)
            if self.config.enable_batch_processing
            else None
        )

        # Async optimization
        self._semaphore = (
            asyncio.Semaphore(self.config.semaphore_size)
            if self.config.enable_async_optimization
            else None
        )

        # Memory management
        self._request_count = 0
        self._weak_cache: WeakKeyDictionary = WeakKeyDictionary()

        # Profiling
        self._profiler = cProfile.Profile() if self.config.enable_profiling else None

        logger.info(
            f"🚀 PerformanceOptimizer initialized with {self.config.optimization_level.value} level"
        )

    async def optimize_request(self, request: Request, call_next: Callable) -> Response:
        """Apply optimizations to request processing."""
        start_time = time.time()

        # Increment request count
        self.metrics.total_requests += 1
        self.metrics.concurrent_requests += 1
        self._request_count += 1

        try:
            # Try cache first
            if self.response_cache:
                cache_key = self._generate_cache_key(request)
                cached_response = self.response_cache.get(cache_key)
                if cached_response:
                    self.metrics.cache_hits += 1
                    return cached_response
                self.metrics.cache_misses += 1

            # Apply async optimization
            if self._semaphore:
                async with self._semaphore:
                    response = await self._process_with_optimizations(
                        request, call_next
                    )
            else:
                response = await self._process_with_optimizations(request, call_next)

            # Cache response if enabled
            if self.response_cache and self._is_cacheable(request, response):
                cache_key = self._generate_cache_key(request)
                self.response_cache.set(cache_key, response)

            return response

        finally:
            # Update metrics
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.response_times.append(duration_ms)
            self.metrics.concurrent_requests -= 1

            # Update average response time
            total_time = (
                self.metrics.avg_response_time_ms * (self.metrics.total_requests - 1)
                + duration_ms
            )
            self.metrics.avg_response_time_ms = total_time / self.metrics.total_requests

            # Periodic cleanup
            if self._request_count % self.config.gc_frequency == 0:
                await self._perform_maintenance()

    async def _process_with_optimizations(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request with various optimizations applied."""
        # Apply profiling if enabled
        if self._profiler and self._should_profile():
            self._profiler.enable()

        try:
            # Use batch processing if enabled and appropriate
            if self.batch_processor and self._should_batch(request):

                async def processor():
                    return await call_next(request)

                response = await self.batch_processor.add_request(processor)
                self.metrics.batched_requests += 1
            else:
                response = await call_next(request)

            return response

        finally:
            if self._profiler and self._profiler.getstats():
                self._profiler.disable()

    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        # Simple cache key based on method, path, and selected headers
        key_parts = [request.method, str(request.url.path), str(request.url.query)]

        # Add relevant headers for cache key
        cache_headers = ["authorization", "content-type"]
        for header in cache_headers:
            if header in request.headers:
                key_parts.append(f"{header}:{request.headers[header]}")

        return "|".join(key_parts)

    def _is_cacheable(self, request: Request, response: Response) -> bool:
        """Determine if response is cacheable."""
        # Cache GET requests with successful responses
        if request.method != "GET":
            return False
        if response.status_code >= 400:
            return False
        if "no-cache" in response.headers.get("cache-control", ""):
            return False
        return True

    def _should_profile(self) -> bool:
        """Determine if request should be profiled."""
        import random

        return random.random() < self.config.profile_sample_rate

    def _should_batch(self, request: Request) -> bool:
        """Determine if request should be batched."""
        # Only batch read operations
        return request.method in ["GET", "HEAD"]

    async def _perform_maintenance(self) -> None:
        """Perform periodic maintenance tasks."""
        if self.config.enable_memory_optimization:
            # Force garbage collection
            collected = gc.collect()
            self.metrics.gc_collections += collected

            # Update memory usage
            import os

            import psutil

            process = psutil.Process(os.getpid())
            self.metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024

        logger.debug(
            f"🧹 Maintenance completed: {self.metrics.gc_collections} GC collections"
        )

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        # Calculate percentiles
        if self.metrics.response_times:
            sorted_times = sorted(self.metrics.response_times)
            self.metrics.p95_response_time_ms = sorted_times[
                int(len(sorted_times) * 0.95)
            ]
            self.metrics.p99_response_time_ms = sorted_times[
                int(len(sorted_times) * 0.99)
            ]

        cache_hit_rate = (
            self.metrics.cache_hits
            / max(self.metrics.cache_hits + self.metrics.cache_misses, 1)
        ) * 100

        return {
            "performance_summary": {
                "total_requests": self.metrics.total_requests,
                "avg_response_time_ms": round(self.metrics.avg_response_time_ms, 2),
                "p95_response_time_ms": round(self.metrics.p95_response_time_ms, 2),
                "p99_response_time_ms": round(self.metrics.p99_response_time_ms, 2),
                "concurrent_requests": self.metrics.concurrent_requests,
                "memory_usage_mb": round(self.metrics.memory_usage_mb, 2),
            },
            "caching": {
                "enabled": self.config.enable_response_caching,
                "cache_hits": self.metrics.cache_hits,
                "cache_misses": self.metrics.cache_misses,
                "hit_rate_percent": round(cache_hit_rate, 2),
            },
            "batching": {
                "enabled": self.config.enable_batch_processing,
                "batched_requests": self.metrics.batched_requests,
                "batch_rate_percent": round(
                    (
                        self.metrics.batched_requests
                        / max(self.metrics.total_requests, 1)
                    )
                    * 100,
                    2,
                ),
            },
            "memory_management": {
                "enabled": self.config.enable_memory_optimization,
                "gc_collections": self.metrics.gc_collections,
                "memory_usage_mb": round(self.metrics.memory_usage_mb, 2),
            },
            "configuration": {
                "optimization_level": self.config.optimization_level.value,
                "cache_size": self.config.response_cache_size,
                "batch_size": self.config.batch_size,
                "semaphore_size": self.config.semaphore_size,
            },
        }


class OptimizedMiddleware(BaseHTTPMiddleware):
    """Middleware wrapper that applies performance optimizations."""

    def __init__(
        self,
        app,
        optimizer: Optional[PerformanceOptimizer] = None,
        config: Optional[PerformanceConfig] = None,
    ):
        super().__init__(app)
        self.optimizer = optimizer or PerformanceOptimizer(config)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Dispatch with performance optimizations."""
        return await self.optimizer.optimize_request(request, call_next)


# Global optimizer instance
_optimizer: Optional[PerformanceOptimizer] = None


def get_optimizer() -> PerformanceOptimizer:
    """Get global optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = PerformanceOptimizer()
    return _optimizer


def setup_performance_optimization(
    config: Optional[PerformanceConfig] = None,
) -> PerformanceOptimizer:
    """
    Set up performance optimization for middleware chain.

    Args:
        config: Performance configuration

    Returns:
        Configured performance optimizer
    """
    global _optimizer
    _optimizer = PerformanceOptimizer(config)
    logger.info("⚡ Performance optimization setup complete")
    return _optimizer


__all__ = [
    "OptimizationLevel",
    "PerformanceConfig",
    "PerformanceMetrics",
    "ResponseCache",
    "ConnectionPool",
    "BatchProcessor",
    "PerformanceOptimizer",
    "OptimizedMiddleware",
    "get_optimizer",
    "setup_performance_optimization",
]

"""
Enterprise Connection Manager for MemoryOS Storage

World-class connection pooling with enterprise patterns:
- Advanced load balancing and health monitoring
- Circuit breaker pattern for resilience
- Connection lifecycle management with auto-recovery
- Performance-based routing and metrics
- Thread-safe operations with minimal contention
- Distributed tracing and observability integration
"""

import logging
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration for lifecycle management."""

    IDLE = "idle"
    ACTIVE = "active"
    WARMING = "warming"
    VALIDATING = "validating"
    FAILED = "failed"
    RECYCLING = "recycling"
    RETIRED = "retired"


class PoolStrategy(Enum):
    """Connection pool strategy for different workload patterns."""

    BALANCED = "balanced"  # Balance between performance and resource usage
    PERFORMANCE = "performance"  # Optimize for speed, more connections
    RESOURCE_CONSERVING = "resource_conserving"  # Minimize resource usage
    ADAPTIVE = "adaptive"  # Automatically adjust based on load


@dataclass
class ConnectionMetrics:
    """Detailed metrics for connection performance tracking."""

    connection_id: str
    created_at: float
    last_used: float
    total_queries: int = 0
    total_query_time: float = 0.0
    failed_queries: int = 0
    avg_query_time: float = 0.0
    health_score: float = 1.0
    state_changes: int = 0
    validation_failures: int = 0

    def update_query_metrics(self, query_time: float, success: bool = True) -> None:
        """Update query performance metrics."""
        self.total_queries += 1
        self.last_used = time.time()

        if success:
            self.total_query_time += query_time
            self.avg_query_time = self.total_query_time / self.total_queries
        else:
            self.failed_queries += 1
            self.health_score = max(0.1, self.health_score - 0.1)

    def get_performance_score(self) -> float:
        """Calculate overall performance score (0-1)."""
        if self.total_queries == 0:
            return 1.0

        success_rate = 1.0 - (self.failed_queries / self.total_queries)
        speed_score = max(0.1, 1.0 - (self.avg_query_time / 1.0))  # 1s baseline
        recency_score = max(
            0.1, 1.0 - ((time.time() - self.last_used) / 300)
        )  # 5min decay

        return (
            success_rate * 0.4
            + speed_score * 0.3
            + recency_score * 0.2
            + self.health_score * 0.1
        )


@dataclass
class PoolConfiguration:
    """Comprehensive pool configuration with enterprise features."""

    # Core pool settings
    min_connections: int = 2
    max_connections: int = 50
    initial_connections: int = 5
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0  # 5 minutes

    # Performance settings
    strategy: PoolStrategy = PoolStrategy.ADAPTIVE
    validation_interval: float = 60.0  # 1 minute
    health_check_interval: float = 30.0  # 30 seconds
    max_retries: int = 3
    retry_delay: float = 0.5

    # Circuit breaker settings
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3

    # SQLite optimization settings
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    cache_size: int = 20000  # 20MB cache
    temp_store: str = "MEMORY"
    mmap_size: int = 536870912  # 512MB memory map
    page_size: int = 4096
    wal_autocheckpoint: int = 1000
    busy_timeout: int = 30000

    # Advanced features
    enable_metrics: bool = True
    enable_tracing: bool = True
    enable_load_balancing: bool = True
    enable_auto_scaling: bool = True
    connection_warming: bool = True


class CircuitBreaker:
    """Circuit breaker implementation for connection resilience."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = "closed"  # closed, open, half_open
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @contextmanager
    def call(self):
        """Execute a call through the circuit breaker."""
        with self._lock:
            if self._state == "open":
                if time.time() - self._last_failure_time > self.recovery_timeout:
                    self._state = "half_open"
                    self._half_open_calls = 0
                else:
                    raise RuntimeError("Circuit breaker is OPEN - calls blocked")

            if (
                self._state == "half_open"
                and self._half_open_calls >= self.half_open_max_calls
            ):
                raise RuntimeError("Circuit breaker half-open limit exceeded")

            if self._state == "half_open":
                self._half_open_calls += 1

        try:
            yield
            # Success - reset circuit breaker
            with self._lock:
                if self._state == "half_open":
                    self._state = "closed"
                    self._failure_count = 0
        except Exception as e:
            # Failure - update circuit breaker
            with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.time()

                if (
                    self._state == "half_open"
                    or self._failure_count >= self.failure_threshold
                ):
                    self._state = "open"
            raise e

    @property
    def state(self) -> str:
        return self._state


class EnhancedConnection:
    """Enhanced SQLite connection with performance monitoring and lifecycle management."""

    def __init__(
        self,
        db_path: str,
        config: PoolConfiguration,
        connection_id: Optional[str] = None,
    ):
        self.connection_id = connection_id or str(uuid.uuid4())
        self.db_path = db_path
        self.config = config
        self.created_at = time.time()

        self._connection: Optional[sqlite3.Connection] = None
        self._state = ConnectionState.WARMING
        self._lock = threading.Lock()
        self._last_validation = 0.0

        # Performance tracking
        self.metrics = ConnectionMetrics(
            connection_id=self.connection_id,
            created_at=self.created_at,
            last_used=self.created_at,
        )

        # Initialize connection
        self._initialize_connection()

    def _initialize_connection(self) -> None:
        """Initialize SQLite connection with optimizations."""
        try:
            # Ensure directory exists
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

            # Create connection
            self._connection = sqlite3.connect(
                self.db_path,
                timeout=self.config.busy_timeout / 1000.0,
                check_same_thread=False,
            )

            # Apply optimizations
            optimizations = [
                f"PRAGMA journal_mode={self.config.journal_mode}",
                f"PRAGMA synchronous={self.config.synchronous}",
                f"PRAGMA cache_size={self.config.cache_size}",
                f"PRAGMA temp_store={self.config.temp_store}",
                f"PRAGMA mmap_size={self.config.mmap_size}",
                f"PRAGMA page_size={self.config.page_size}",
                f"PRAGMA wal_autocheckpoint={self.config.wal_autocheckpoint}",
                "PRAGMA foreign_keys=ON",
                "PRAGMA optimize",
            ]

            for pragma in optimizations:
                self._connection.execute(pragma)

            self._connection.commit()
            self._state = ConnectionState.IDLE

            logger.debug(f"Connection {self.connection_id} initialized successfully")

        except Exception as e:
            self._state = ConnectionState.FAILED
            logger.error(f"Failed to initialize connection {self.connection_id}: {e}")
            raise

    def execute(self, sql: str, parameters: Any = None) -> sqlite3.Cursor:
        """Execute SQL with performance tracking."""
        if self._state != ConnectionState.IDLE:
            raise RuntimeError(
                f"Connection {self.connection_id} not available (state: {self._state})"
            )

        with self._lock:
            start_time = time.time()
            self._state = ConnectionState.ACTIVE

            try:
                if self._connection is None:
                    raise RuntimeError(f"Connection {self.connection_id} is closed")

                if parameters:
                    cursor = self._connection.execute(sql, parameters)
                else:
                    cursor = self._connection.execute(sql)

                query_time = time.time() - start_time
                self.metrics.update_query_metrics(query_time, success=True)

                return cursor

            except Exception as e:
                query_time = time.time() - start_time
                self.metrics.update_query_metrics(query_time, success=False)
                logger.error(f"Query failed on connection {self.connection_id}: {e}")
                raise
            finally:
                self._state = ConnectionState.IDLE

    def executemany(self, sql: str, parameters: List[Any]) -> sqlite3.Cursor:
        """Execute multiple SQL statements with performance tracking."""
        if self._state != ConnectionState.IDLE:
            raise RuntimeError(
                f"Connection {self.connection_id} not available (state: {self._state})"
            )

        with self._lock:
            start_time = time.time()
            self._state = ConnectionState.ACTIVE

            try:
                if self._connection is None:
                    raise RuntimeError(f"Connection {self.connection_id} is closed")

                cursor = self._connection.executemany(sql, parameters)
                query_time = time.time() - start_time
                self.metrics.update_query_metrics(query_time, success=True)
                return cursor

            except Exception as e:
                query_time = time.time() - start_time
                self.metrics.update_query_metrics(query_time, success=False)
                logger.error(
                    f"Batch query failed on connection {self.connection_id}: {e}"
                )
                raise
            finally:
                self._state = ConnectionState.IDLE

    def commit(self) -> None:
        """Commit transaction with tracking."""
        if self._connection:
            with self._lock:
                self._connection.commit()
                self.metrics.last_used = time.time()

    def rollback(self) -> None:
        """Rollback transaction with tracking."""
        if self._connection:
            with self._lock:
                self._connection.rollback()
                self.metrics.last_used = time.time()

    def validate(self) -> bool:
        """Validate connection health."""
        if not self._connection:
            return False

        try:
            with self._lock:
                self._state = ConnectionState.VALIDATING
                cursor = self._connection.execute("SELECT 1")
                result = cursor.fetchone()
                self._last_validation = time.time()
                self._state = ConnectionState.IDLE
                return result == (1,)

        except Exception as e:
            logger.warning(f"Connection {self.connection_id} validation failed: {e}")
            self.metrics.validation_failures += 1
            self._state = ConnectionState.FAILED
            return False

    def close(self) -> None:
        """Close connection and clean up resources."""
        if self._connection:
            try:
                with self._lock:
                    self._state = ConnectionState.RETIRED
                    self._connection.close()
                    self._connection = None
                    logger.debug(f"Connection {self.connection_id} closed")
            except Exception as e:
                logger.warning(f"Error closing connection {self.connection_id}: {e}")

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_available(self) -> bool:
        return self._state == ConnectionState.IDLE

    @property
    def performance_score(self) -> float:
        return self.metrics.get_performance_score()

    @property
    def age(self) -> float:
        return time.time() - self.created_at

    @property
    def idle_time(self) -> float:
        return time.time() - self.metrics.last_used


class ConnectionPool:
    """Enterprise-grade connection pool with advanced features."""

    def __init__(self, db_path: str, config: Optional[PoolConfiguration] = None):
        self.db_path = db_path
        self.config = config or PoolConfiguration()

        # Pool state
        self._connections: List[EnhancedConnection] = []
        self._available_connections: List[EnhancedConnection] = []
        self._lock = threading.RLock()
        self._shutdown = False

        # Circuit breaker for resilience
        self._circuit_breaker = CircuitBreaker(
            self.config.failure_threshold,
            self.config.recovery_timeout,
            self.config.half_open_max_calls,
        )

        # Background tasks
        self._health_checker_thread: Optional[threading.Thread] = None
        self._pool_manager_thread: Optional[threading.Thread] = None

        # Performance tracking
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._wait_times: List[float] = []

        # Initialize the pool
        self._initialize_pool()
        self._start_background_tasks()

    def _initialize_pool(self) -> None:
        """Initialize the connection pool with initial connections."""
        logger.info(
            f"Initializing connection pool for {self.db_path} "
            f"(initial: {self.config.initial_connections}, "
            f"min: {self.config.min_connections}, "
            f"max: {self.config.max_connections})"
        )

        with self._lock:
            for i in range(self.config.initial_connections):
                try:
                    connection = self._create_connection()
                    self._connections.append(connection)
                    self._available_connections.append(connection)

                    if self.config.connection_warming:
                        self._warm_connection(connection)

                except Exception as e:
                    logger.error(f"Failed to create initial connection {i}: {e}")
                    if i == 0:  # If we can't create any connections, raise
                        raise

    def _create_connection(self) -> EnhancedConnection:
        """Create a new enhanced connection."""
        return EnhancedConnection(self.db_path, self.config)

    def _warm_connection(self, connection: EnhancedConnection) -> None:
        """Warm up a connection with a simple query."""
        try:
            connection.execute("SELECT 1")
            logger.debug(f"Connection {connection.connection_id} warmed successfully")
        except Exception as e:
            logger.warning(f"Failed to warm connection {connection.connection_id}: {e}")

    def _start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        self._health_checker_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="ConnectionPool-HealthChecker",
        )
        self._health_checker_thread.start()

        self._pool_manager_thread = threading.Thread(
            target=self._pool_management_loop,
            daemon=True,
            name="ConnectionPool-Manager",
        )
        self._pool_manager_thread.start()

    def _health_check_loop(self) -> None:
        """Background health checking of connections."""
        while not self._shutdown:
            try:
                time.sleep(self.config.health_check_interval)
                self._perform_health_checks()
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    def _perform_health_checks(self) -> None:
        """Perform health checks on all connections."""
        with self._lock:
            unhealthy_connections: List[EnhancedConnection] = []

            for connection in self._connections:
                if not connection.validate():
                    unhealthy_connections.append(connection)
                    logger.warning(
                        f"Connection {connection.connection_id} failed health check"
                    )

            # Remove unhealthy connections
            for connection in unhealthy_connections:
                self._remove_connection(connection)

    def _pool_management_loop(self) -> None:
        """Background pool size management and optimization."""
        while not self._shutdown:
            try:
                time.sleep(self.config.validation_interval)
                self._optimize_pool_size()
                self._cleanup_idle_connections()
            except Exception as e:
                logger.error(f"Pool management loop error: {e}")

    def _optimize_pool_size(self) -> None:
        """Optimize pool size based on strategy and load."""
        if self.config.strategy == PoolStrategy.ADAPTIVE:
            self._adaptive_pool_sizing()
        elif self.config.strategy == PoolStrategy.PERFORMANCE:
            self._performance_pool_sizing()
        elif self.config.strategy == PoolStrategy.RESOURCE_CONSERVING:
            self._conservative_pool_sizing()

    def _adaptive_pool_sizing(self) -> None:
        """Adaptive pool sizing based on current load."""
        with self._lock:
            total_connections = len(self._connections)
            available_connections = len(self._available_connections)
            utilization = 1.0 - (available_connections / max(1, total_connections))

            # Scale up if high utilization
            if utilization > 0.8 and total_connections < self.config.max_connections:
                self._add_connection()
                logger.debug(f"Scaled up pool to {len(self._connections)} connections")

            # Scale down if low utilization
            elif utilization < 0.2 and total_connections > self.config.min_connections:
                self._remove_oldest_idle_connection()
                logger.debug(
                    f"Scaled down pool to {len(self._connections)} connections"
                )

    def _performance_pool_sizing(self) -> None:
        """Performance-oriented sizing - favor more connections."""
        with self._lock:
            if len(self._connections) < self.config.max_connections:
                self._add_connection()

    def _conservative_pool_sizing(self) -> None:
        """Conservative sizing - favor fewer connections."""
        with self._lock:
            if len(self._connections) > self.config.min_connections:
                idle_connections = [
                    conn
                    for conn in self._available_connections
                    if conn.idle_time > self.config.idle_timeout
                ]
                if idle_connections:
                    self._remove_connection(idle_connections[0])

    def _cleanup_idle_connections(self) -> None:
        """Remove connections that have been idle too long."""
        with self._lock:
            current_time = time.time()
            idle_connections = [
                conn
                for conn in self._available_connections
                if (current_time - conn.metrics.last_used) > self.config.idle_timeout
                and len(self._connections) > self.config.min_connections
            ]

            for connection in idle_connections:
                self._remove_connection(connection)
                logger.debug(
                    f"Removed idle connection {connection.connection_id} "
                    f"(idle: {connection.idle_time:.1f}s)"
                )

    def _add_connection(self) -> None:
        """Add a new connection to the pool."""
        try:
            connection = self._create_connection()
            self._connections.append(connection)
            self._available_connections.append(connection)

            if self.config.connection_warming:
                self._warm_connection(connection)

            logger.debug(f"Added connection {connection.connection_id} to pool")
        except Exception as e:
            logger.error(f"Failed to add connection to pool: {e}")

    def _remove_connection(self, connection: EnhancedConnection) -> None:
        """Remove a connection from the pool."""
        try:
            if connection in self._connections:
                self._connections.remove(connection)
            if connection in self._available_connections:
                self._available_connections.remove(connection)

            connection.close()
            logger.debug(f"Removed connection {connection.connection_id} from pool")
        except Exception as e:
            logger.error(f"Error removing connection {connection.connection_id}: {e}")

    def _remove_oldest_idle_connection(self) -> None:
        """Remove the oldest idle connection."""
        if not self._available_connections:
            return

        oldest_connection = min(
            self._available_connections, key=lambda conn: conn.metrics.last_used
        )
        self._remove_connection(oldest_connection)

    def _select_best_connection(self) -> Optional[EnhancedConnection]:
        """Select the best available connection using load balancing."""
        if not self._available_connections:
            return None

        if not self.config.enable_load_balancing:
            return self._available_connections[0]

        # Performance-based selection
        return max(self._available_connections, key=lambda conn: conn.performance_score)

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool with circuit breaker protection."""
        start_time = time.time()
        connection = None

        try:
            with self._circuit_breaker.call():
                self._total_requests += 1

                # Get connection with timeout
                connection = self._acquire_connection_with_timeout()

                if connection is None:
                    raise RuntimeError("No connection available from pool")

                wait_time = time.time() - start_time
                self._wait_times.append(wait_time)

                yield connection

                self._successful_requests += 1

        except Exception as e:
            self._failed_requests += 1
            logger.error(f"Error using connection from pool: {e}")
            raise
        finally:
            if connection:
                self._return_connection(connection)

    def _acquire_connection_with_timeout(self) -> Optional[EnhancedConnection]:
        """Acquire a connection with timeout and retry logic."""
        timeout_end = time.time() + self.config.connection_timeout
        retry_count = 0

        while time.time() < timeout_end and retry_count < self.config.max_retries:
            with self._lock:
                connection = self._select_best_connection()
                if connection:
                    self._available_connections.remove(connection)
                    return connection

                # Try to add a new connection if we're below max
                if len(self._connections) < self.config.max_connections:
                    try:
                        new_connection = self._create_connection()
                        self._connections.append(new_connection)
                        return new_connection
                    except Exception as e:
                        logger.warning(f"Failed to create new connection: {e}")

            # Wait before retry
            time.sleep(self.config.retry_delay)
            retry_count += 1

        return None

    def _return_connection(self, connection: EnhancedConnection) -> None:
        """Return a connection to the pool."""
        with self._lock:
            if connection.state == ConnectionState.IDLE:
                self._available_connections.append(connection)
            else:
                # Connection is in bad state, remove it
                logger.warning(
                    f"Removing connection {connection.connection_id} "
                    f"in bad state: {connection.state}"
                )
                self._remove_connection(connection)

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            active_connections = len(self._connections) - len(
                self._available_connections
            )

            avg_wait_time = (
                sum(self._wait_times) / len(self._wait_times)
                if self._wait_times
                else 0.0
            )

            success_rate = self._successful_requests / max(1, self._total_requests)

            return {
                "total_connections": len(self._connections),
                "available_connections": len(self._available_connections),
                "active_connections": active_connections,
                "total_requests": self._total_requests,
                "successful_requests": self._successful_requests,
                "failed_requests": self._failed_requests,
                "success_rate": success_rate,
                "avg_wait_time": avg_wait_time,
                "circuit_breaker_state": self._circuit_breaker.state,
                "pool_utilization": active_connections / max(1, len(self._connections)),
            }

    def shutdown(self) -> None:
        """Shutdown the connection pool gracefully."""
        logger.info(f"Shutting down connection pool for {self.db_path}")

        self._shutdown = True

        # Wait for background threads to stop
        if self._health_checker_thread:
            self._health_checker_thread.join(timeout=5.0)
        if self._pool_manager_thread:
            self._pool_manager_thread.join(timeout=5.0)

        # Close all connections
        with self._lock:
            for connection in self._connections[:]:
                self._remove_connection(connection)

        logger.info("Connection pool shutdown complete")

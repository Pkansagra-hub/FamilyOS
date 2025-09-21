"""SQLite Utilities - Enhanced connection management and performance optimization"""

import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Configuration for SQLite connections."""

    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    cache_size: int = 10000  # Pages (10MB with 1KB page size)
    temp_store: str = "MEMORY"
    mmap_size: int = 268435456  # 256MB
    foreign_keys: bool = True
    busy_timeout: int = 30000  # 30 seconds
    page_size: int = 4096  # 4KB pages for better performance
    wal_autocheckpoint: int = 1000  # Checkpoint every 1000 pages


@dataclass
class ConnectionStats:
    """Performance statistics for a connection."""

    created_at: float = field(default_factory=time.time)
    queries_executed: int = 0
    total_query_time: float = 0.0
    transactions_committed: int = 0
    transactions_rolled_back: int = 0
    last_used: float = field(default_factory=time.time)
    errors: int = 0

    def get_avg_query_time(self) -> float:
        """Get average query execution time."""
        if self.queries_executed == 0:
            return 0.0
        return self.total_query_time / self.queries_executed


class PerformanceMonitor:
    """Performance monitoring for SQLite operations."""

    def __init__(self):
        self._lock = threading.Lock()
        self._stats: Dict[str, ConnectionStats] = {}
        self._hooks: List[Callable[[str, Dict[str, Any]], None]] = []

    def add_hook(self, hook: Callable[[str, Dict[str, Any]], None]) -> None:
        """Add a performance monitoring hook."""
        with self._lock:
            self._hooks.append(hook)

    def record_query(self, conn_id: str, query_time: float) -> None:
        """Record query execution time."""
        with self._lock:
            stats = self._stats.setdefault(conn_id, ConnectionStats())
            stats.queries_executed += 1
            stats.total_query_time += query_time
            stats.last_used = time.time()

            # Call hooks
            metrics = {
                "type": "query",
                "conn_id": conn_id,
                "query_time": query_time,
                "total_queries": stats.queries_executed,
                "avg_query_time": stats.get_avg_query_time(),
            }
            for hook in self._hooks:
                try:
                    hook(conn_id, metrics)
                except Exception as e:
                    logger.warning(f"Performance hook failed: {e}")

    def record_transaction(self, conn_id: str, committed: bool) -> None:
        """Record transaction completion."""
        with self._lock:
            stats = self._stats.setdefault(conn_id, ConnectionStats())
            if committed:
                stats.transactions_committed += 1
            else:
                stats.transactions_rolled_back += 1
            stats.last_used = time.time()

            # Call hooks
            metrics = {
                "type": "transaction",
                "conn_id": conn_id,
                "committed": committed,
                "total_commits": stats.transactions_committed,
                "total_rollbacks": stats.transactions_rolled_back,
            }
            for hook in self._hooks:
                try:
                    hook(conn_id, metrics)
                except Exception as e:
                    logger.warning(f"Performance hook failed: {e}")

    def record_error(self, conn_id: str, error: Exception) -> None:
        """Record an error."""
        with self._lock:
            stats = self._stats.setdefault(conn_id, ConnectionStats())
            stats.errors += 1
            stats.last_used = time.time()

            # Call hooks
            metrics = {
                "type": "error",
                "conn_id": conn_id,
                "error": str(error),
                "total_errors": stats.errors,
            }
            for hook in self._hooks:
                try:
                    hook(conn_id, metrics)
                except Exception as e:
                    logger.warning(f"Performance hook failed: {e}")

    def get_stats(self, conn_id: Optional[str] = None) -> Dict[str, ConnectionStats]:
        """Get performance statistics."""
        with self._lock:
            if conn_id:
                return {conn_id: self._stats.get(conn_id, ConnectionStats())}
            return self._stats.copy()

    def reset_stats(self, conn_id: Optional[str] = None) -> None:
        """Reset performance statistics."""
        with self._lock:
            if conn_id:
                self._stats.pop(conn_id, None)
            else:
                self._stats.clear()


class EnhancedConnection:
    """Wrapper around sqlite3.Connection with performance monitoring."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        conn_id: str,
        monitor: Optional[PerformanceMonitor] = None,
    ):
        self._conn = conn
        self._conn_id = conn_id
        self._monitor = monitor
        self._in_transaction = False

    def execute(self, sql: str, parameters: Any = None) -> sqlite3.Cursor:
        """Execute SQL with performance monitoring."""
        start_time = time.time()
        try:
            if parameters is None:
                cursor = self._conn.execute(sql)
            else:
                cursor = self._conn.execute(sql, parameters)

            if self._monitor:
                query_time = time.time() - start_time
                self._monitor.record_query(self._conn_id, query_time)

            return cursor
        except Exception as e:
            if self._monitor:
                self._monitor.record_error(self._conn_id, e)
            raise

    def executemany(self, sql: str, parameters: List[Any]) -> sqlite3.Cursor:
        """Execute SQL many times with performance monitoring."""
        start_time = time.time()
        try:
            cursor = self._conn.executemany(sql, parameters)

            if self._monitor:
                query_time = time.time() - start_time
                self._monitor.record_query(self._conn_id, query_time)

            return cursor
        except Exception as e:
            if self._monitor:
                self._monitor.record_error(self._conn_id, e)
            raise

    def commit(self) -> None:
        """Commit transaction with monitoring."""
        try:
            self._conn.commit()
            self._in_transaction = False
            if self._monitor:
                self._monitor.record_transaction(self._conn_id, True)
        except Exception as e:
            if self._monitor:
                self._monitor.record_error(self._conn_id, e)
            raise

    def rollback(self) -> None:
        """Rollback transaction with monitoring."""
        try:
            self._conn.rollback()
            self._in_transaction = False
            if self._monitor:
                self._monitor.record_transaction(self._conn_id, False)
        except Exception as e:
            if self._monitor:
                self._monitor.record_error(self._conn_id, e)
            raise

    def close(self) -> None:
        """Close the connection."""
        self._conn.close()

    @property
    def row_factory(self):
        """Get row factory."""
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, factory):
        """Set row factory."""
        self._conn.row_factory = factory

    def __enter__(self):
        """Enter transaction context."""
        self._in_transaction = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction context."""
        if exc_type:
            self.rollback()
        else:
            self.commit()


class EnhancedConnectionPool:
    """Enhanced connection pool with performance monitoring and health checks."""

    def __init__(
        self,
        db_path: str,
        max_connections: int = 20,
        config: Optional[ConnectionConfig] = None,
        monitor: Optional[PerformanceMonitor] = None,
    ):
        self.db_path = db_path
        self.max_connections = max_connections
        self.config = config or ConnectionConfig()
        self.monitor = monitor or PerformanceMonitor()

        self._connections: List[EnhancedConnection] = []
        self._in_use: Set[EnhancedConnection] = set()
        self._lock = threading.Lock()
        self._next_conn_id = 1

        # Ensure database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> EnhancedConnection:
        """Get a connection from the pool."""
        with self._lock:
            # Try to reuse an existing connection
            for conn in self._connections:
                if conn not in self._in_use:
                    self._in_use.add(conn)
                    return conn

            # Create new connection if under limit
            if len(self._connections) < self.max_connections:
                conn = self._create_connection()
                self._connections.append(conn)
                self._in_use.add(conn)
                return conn

            # Pool is full - in production we might wait or queue
            # For now, raise an exception
            raise RuntimeError(
                f"Connection pool exhausted. Max connections: {self.max_connections}"
            )

    def return_connection(self, conn: EnhancedConnection) -> None:
        """Return a connection to the pool."""
        with self._lock:
            self._in_use.discard(conn)

    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing pooled connection: {e}")
            self._connections.clear()
            self._in_use.clear()

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                "total_connections": len(self._connections),
                "in_use": len(self._in_use),
                "available": len(self._connections) - len(self._in_use),
                "max_connections": self.max_connections,
                "utilization": (
                    len(self._in_use) / self.max_connections
                    if self.max_connections > 0
                    else 0
                ),
                "performance_stats": self.monitor.get_stats(),
            }

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the pool."""
        try:
            with self.get_connection() as conn:
                start_time = time.time()
                cursor = conn.execute("SELECT 1")
                result = cursor.fetchone()
                query_time = time.time() - start_time

                return {
                    "healthy": result is not None,
                    "response_time_ms": query_time * 1000,
                    "pool_stats": self.get_pool_stats(),
                }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "pool_stats": self.get_pool_stats(),
            }

    def _create_connection(self) -> EnhancedConnection:
        """Create a new enhanced SQLite connection."""
        conn_id = f"conn_{self._next_conn_id}"
        self._next_conn_id += 1

        # Create raw connection
        raw_conn = sqlite3.connect(self.db_path)

        # Apply configuration
        self._configure_connection(raw_conn)

        # Wrap in enhanced connection
        enhanced_conn = EnhancedConnection(raw_conn, conn_id, self.monitor)

        logger.debug(f"Created new connection: {conn_id}")
        return enhanced_conn

    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """Apply configuration to a connection."""
        try:
            # Set page size (must be done before other pragmas)
            conn.execute(f"PRAGMA page_size={self.config.page_size}")

            # Enable WAL mode for durability and concurrent access
            conn.execute(f"PRAGMA journal_mode={self.config.journal_mode}")

            # Set synchronous mode
            conn.execute(f"PRAGMA synchronous={self.config.synchronous}")

            # Set cache size
            conn.execute(f"PRAGMA cache_size={self.config.cache_size}")

            # Set temp store
            conn.execute(f"PRAGMA temp_store={self.config.temp_store}")

            # Set memory map size
            conn.execute(f"PRAGMA mmap_size={self.config.mmap_size}")

            # Enable/disable foreign keys
            foreign_key_setting = "ON" if self.config.foreign_keys else "OFF"
            conn.execute(f"PRAGMA foreign_keys={foreign_key_setting}")

            # Set busy timeout
            conn.execute(f"PRAGMA busy_timeout={self.config.busy_timeout}")

            # Set WAL autocheckpoint
            conn.execute(f"PRAGMA wal_autocheckpoint={self.config.wal_autocheckpoint}")

            # Optimize for performance
            conn.execute("PRAGMA optimize")

        except Exception as e:
            logger.error(f"Failed to configure connection: {e}")
            raise


def create_optimized_connection(
    db_path: str, config: Optional[ConnectionConfig] = None
) -> sqlite3.Connection:
    """Create a single optimized SQLite connection."""
    config = config or ConnectionConfig()

    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)

    # Apply optimizations
    try:
        # Set page size (must be done before other pragmas)
        conn.execute(f"PRAGMA page_size={config.page_size}")

        # Enable WAL mode for durability and concurrent access
        conn.execute(f"PRAGMA journal_mode={config.journal_mode}")
        conn.execute(f"PRAGMA synchronous={config.synchronous}")

        # Performance optimizations
        conn.execute(f"PRAGMA cache_size={config.cache_size}")
        conn.execute(f"PRAGMA temp_store={config.temp_store}")
        conn.execute(f"PRAGMA mmap_size={config.mmap_size}")

        # Safety settings
        foreign_key_setting = "ON" if config.foreign_keys else "OFF"
        conn.execute(f"PRAGMA foreign_keys={foreign_key_setting}")

        # Timeout settings
        conn.execute(f"PRAGMA busy_timeout={config.busy_timeout}")

        # WAL settings
        conn.execute(f"PRAGMA wal_autocheckpoint={config.wal_autocheckpoint}")

        # General optimization
        conn.execute("PRAGMA optimize")

        logger.debug(f"Created optimized connection to {db_path}")
        return conn

    except Exception as e:
        conn.close()
        logger.error(f"Failed to create optimized connection: {e}")
        raise


def migrate_database(
    db_path: str, migrations: List[str], config: Optional[ConnectionConfig] = None
) -> None:
    """Apply database migrations."""
    conn = create_optimized_connection(db_path, config)

    try:
        # Create migrations table if it doesn't exist
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Get current version
        cursor = conn.execute("SELECT MAX(version) FROM schema_migrations")
        current_version = cursor.fetchone()[0] or 0

        # Apply new migrations
        for i, migration in enumerate(migrations, 1):
            if i > current_version:
                logger.info(f"Applying migration {i}")
                conn.execute(migration)
                conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (i,))

        conn.commit()
        logger.info(f"Database migrations complete. Current version: {len(migrations)}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


# Global performance monitor instance
global_monitor = PerformanceMonitor()


def get_global_monitor() -> PerformanceMonitor:
    """Get the global performance monitor."""
    return global_monitor

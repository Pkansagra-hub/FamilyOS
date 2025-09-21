"""
Enhanced SQLite Utilities - Connection Pool and Maintenance Enhancements
Supporting Issue 1.2.2 SQLite Utilities Enhancement for Epic 1.2 Storage Foundation
"""

import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, Generator, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Configuration for connection pooling."""

    min_connections: int = 2
    max_connections: int = 10
    max_idle_time: int = 300  # 5 minutes
    connection_timeout: int = 30  # seconds
    pool_recycle_time: int = 3600  # 1 hour
    validate_connections: bool = True
    retry_attempts: int = 3


@dataclass
class VacuumConfig:
    """Configuration for database maintenance."""

    auto_vacuum_interval: int = 3600  # 1 hour
    incremental_vacuum_pages: int = 1000
    wal_checkpoint_interval: int = 300  # 5 minutes
    analyze_interval: int = 7200  # 2 hours
    integrity_check_interval: int = 86400  # 24 hours


@dataclass
class PoolStats:
    """Statistics for connection pool."""

    created_at: float = field(default_factory=time.time)
    total_connections_created: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    pool_hits: int = 0
    pool_misses: int = 0
    connection_errors: int = 0
    last_vacuum: Optional[float] = None
    last_checkpoint: Optional[float] = None
    last_analyze: Optional[float] = None

    def get_hit_ratio(self) -> float:
        """Calculate pool hit ratio."""
        total = self.pool_hits + self.pool_misses
        if total == 0:
            return 0.0
        return self.pool_hits / total


class PooledConnection:
    """Wrapper for pooled SQLite connections with lifecycle management."""

    def __init__(self, conn: sqlite3.Connection, conn_id: str, created_at: float):
        self.conn = conn
        self.conn_id = conn_id
        self.created_at = created_at
        self.last_used = time.time()
        self.in_use = False
        self.use_count = 0
        self._closed = False

    def mark_used(self) -> None:
        """Mark connection as recently used."""
        self.last_used = time.time()
        self.use_count += 1

    def is_expired(self, max_idle_time: int, recycle_time: int) -> bool:
        """Check if connection should be recycled."""
        now = time.time()
        idle_expired = not self.in_use and (now - self.last_used) > max_idle_time
        age_expired = (now - self.created_at) > recycle_time
        return idle_expired or age_expired

    def is_valid(self) -> bool:
        """Validate connection is still working."""
        if self._closed:
            return False
        try:
            self.conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close the connection."""
        if not self._closed:
            try:
                self.conn.close()
            except Exception:
                pass
            self._closed = True


class EnhancedConnectionPool:
    """Advanced connection pool with lifecycle management and maintenance."""

    def __init__(
        self, db_path: str, pool_config: PoolConfig, vacuum_config: VacuumConfig
    ):
        self.db_path = db_path
        self.pool_config = pool_config
        self.vacuum_config = vacuum_config

        self._lock = threading.RLock()
        self._pool: Queue[PooledConnection] = Queue()
        self._active_connections: Dict[str, PooledConnection] = {}
        self._stats = PoolStats()

        # Maintenance threading
        self._maintenance_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        # Initialize minimum connections
        self._initialize_pool()
        self._start_maintenance()

    def _initialize_pool(self) -> None:
        """Initialize pool with minimum connections."""
        with self._lock:
            for _ in range(self.pool_config.min_connections):
                try:
                    conn = self._create_connection()
                    self._pool.put(conn)
                    self._stats.idle_connections += 1
                except Exception as e:
                    logger.error(f"Failed to initialize connection: {e}")
                    self._stats.connection_errors += 1

    def _create_connection(self) -> PooledConnection:
        """Create a new pooled connection."""
        conn_id = f"pool_{int(time.time())}_{self._stats.total_connections_created}"

        # Create connection with enhanced configuration
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.pool_config.connection_timeout,
            isolation_level=None,  # autocommit mode for better control
        )

        # Apply enhanced SQLite configuration
        self._configure_connection(conn)

        pooled_conn = PooledConnection(conn, conn_id, time.time())
        self._stats.total_connections_created += 1

        logger.debug(f"Created new pooled connection: {conn_id}")
        return pooled_conn

    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """Apply enhanced SQLite configuration to connection."""
        config_queries = [
            "PRAGMA journal_mode = WAL",
            "PRAGMA synchronous = NORMAL",
            "PRAGMA cache_size = 10000",
            "PRAGMA temp_store = MEMORY",
            "PRAGMA mmap_size = 268435456",  # 256MB
            "PRAGMA foreign_keys = ON",
            "PRAGMA busy_timeout = 30000",  # 30 seconds
            "PRAGMA wal_autocheckpoint = 1000",
            "PRAGMA optimize",  # Query planner optimization
        ]

        for query in config_queries:
            try:
                conn.execute(query)
            except Exception as e:
                logger.warning(f"Failed to apply config '{query}': {e}")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a connection from the pool."""
        pooled_conn = None
        try:
            pooled_conn = self._acquire_connection()
            yield pooled_conn.conn
        finally:
            if pooled_conn:
                self._release_connection(pooled_conn)

    def _acquire_connection(self) -> PooledConnection:
        """Acquire a connection from the pool."""
        with self._lock:
            # Try to get from pool
            try:
                pooled_conn = self._pool.get_nowait()
                if self.pool_config.validate_connections and not pooled_conn.is_valid():
                    # Connection is invalid, discard and create new
                    pooled_conn.close()
                    self._stats.connection_errors += 1
                    pooled_conn = self._create_connection()

                self._stats.pool_hits += 1
                self._stats.idle_connections -= 1

            except Empty:
                # Pool is empty, create new if under limit
                if len(self._active_connections) < self.pool_config.max_connections:
                    pooled_conn = self._create_connection()
                    self._stats.pool_misses += 1
                else:
                    raise RuntimeError("Connection pool exhausted")

            # Mark as active
            pooled_conn.in_use = True
            pooled_conn.mark_used()
            self._active_connections[pooled_conn.conn_id] = pooled_conn
            self._stats.active_connections += 1

            return pooled_conn

    def _release_connection(self, pooled_conn: PooledConnection) -> None:
        """Release connection back to pool."""
        with self._lock:
            # Remove from active
            self._active_connections.pop(pooled_conn.conn_id, None)
            self._stats.active_connections -= 1

            # Check if should be recycled
            if pooled_conn.is_expired(
                self.pool_config.max_idle_time, self.pool_config.pool_recycle_time
            ):
                pooled_conn.close()
                logger.debug(f"Recycled expired connection: {pooled_conn.conn_id}")
            else:
                # Return to pool
                pooled_conn.in_use = False
                self._pool.put(pooled_conn)
                self._stats.idle_connections += 1

    def _start_maintenance(self) -> None:
        """Start background maintenance thread."""
        self._maintenance_thread = threading.Thread(
            target=self._maintenance_worker, daemon=True, name="sqlite-pool-maintenance"
        )
        self._maintenance_thread.start()

    def _maintenance_worker(self) -> None:
        """Background maintenance operations."""
        while not self._shutdown_event.is_set():
            try:
                self._perform_maintenance()
                # TODO: Use event-driven maintenance instead of sleep polling
                if not self._shutdown_event.wait(60):  # Check every minute
                    continue
                else:
                    break
            except Exception as e:
                logger.error(f"Maintenance error: {e}")

    def _perform_maintenance(self) -> None:
        """Perform periodic maintenance operations."""
        now = time.time()

        # WAL checkpoint
        if (
            not self._stats.last_checkpoint
            or now - self._stats.last_checkpoint
            > self.vacuum_config.wal_checkpoint_interval
        ):
            self._wal_checkpoint()
            self._stats.last_checkpoint = now

        # Incremental vacuum
        if (
            not self._stats.last_vacuum
            or now - self._stats.last_vacuum > self.vacuum_config.auto_vacuum_interval
        ):
            self._incremental_vacuum()
            self._stats.last_vacuum = now

        # Analyze statistics
        if (
            not self._stats.last_analyze
            or now - self._stats.last_analyze > self.vacuum_config.analyze_interval
        ):
            self._analyze_database()
            self._stats.last_analyze = now

        # Clean expired connections
        self._clean_expired_connections()

    def _wal_checkpoint(self) -> None:
        """Perform WAL checkpoint."""
        try:
            with self.get_connection() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                logger.debug("WAL checkpoint completed")
        except Exception as e:
            logger.warning(f"WAL checkpoint failed: {e}")

    def _incremental_vacuum(self) -> None:
        """Perform incremental vacuum."""
        try:
            with self.get_connection() as conn:
                vacuum_pages = self.vacuum_config.incremental_vacuum_pages
                conn.execute(f"PRAGMA incremental_vacuum({vacuum_pages})")
                logger.debug("Incremental vacuum completed")
        except Exception as e:
            logger.warning(f"Incremental vacuum failed: {e}")

    def _analyze_database(self) -> None:
        """Update database statistics."""
        try:
            with self.get_connection() as conn:
                conn.execute("ANALYZE")
                logger.debug("Database analysis completed")
        except Exception as e:
            logger.warning(f"Database analysis failed: {e}")

    def _clean_expired_connections(self) -> None:
        """Remove expired connections from pool."""
        with self._lock:
            expired_connections: List[PooledConnection] = []

            # Check pool connections
            temp_pool: Queue[PooledConnection] = Queue()
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    if conn.is_expired(
                        self.pool_config.max_idle_time,
                        self.pool_config.pool_recycle_time,
                    ):
                        expired_connections.append(conn)
                    else:
                        temp_pool.put(conn)
                except Empty:
                    break

            # Restore non-expired connections
            self._pool = temp_pool
            self._stats.idle_connections = self._pool.qsize()

            # Close expired connections
            for conn in expired_connections:
                conn.close()
                logger.debug(f"Cleaned expired connection: {conn.conn_id}")

    def get_stats(self) -> PoolStats:
        """Get pool statistics."""
        with self._lock:
            # Update current counts
            self._stats.active_connections = len(self._active_connections)
            self._stats.idle_connections = self._pool.qsize()
            return self._stats

    def close(self) -> None:
        """Close the connection pool."""
        logger.info("Closing connection pool...")

        # Signal shutdown
        self._shutdown_event.set()

        # Wait for maintenance thread
        if self._maintenance_thread and self._maintenance_thread.is_alive():
            self._maintenance_thread.join(timeout=5)

        with self._lock:
            # Close all active connections
            for conn in list(self._active_connections.values()):
                conn.close()
            self._active_connections.clear()

            # Close all pooled connections
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except Empty:
                    break

        logger.info("Connection pool closed")


class EnhancedSQLiteManager:
    """High-level manager for enhanced SQLite operations."""

    def __init__(
        self,
        db_path: str,
        pool_config: Optional[PoolConfig] = None,
        vacuum_config: Optional[VacuumConfig] = None,
    ):
        self.db_path = db_path
        self.pool_config = pool_config or PoolConfig()
        self.vacuum_config = vacuum_config or VacuumConfig()

        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection pool
        self.pool = EnhancedConnectionPool(
            db_path, self.pool_config, self.vacuum_config
        )

        # Initialize database
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize database with optimal settings."""
        with self.pool.get_connection() as conn:
            # Ensure WAL mode and optimal settings
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA optimize")

            logger.info(f"Initialized enhanced SQLite database: {self.db_path}")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a managed connection."""
        with self.pool.get_connection() as conn:
            yield conn

    def execute_with_retry(
        self, query: str, params: Optional[Tuple[Any, ...]] = None, max_retries: int = 3
    ) -> sqlite3.Cursor:
        """Execute query with automatic retry on failure."""
        last_error = None

        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    if params:
                        return conn.execute(query, params)
                    else:
                        return conn.execute(query)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # TODO: Implement proper backoff strategy without sleep
                    # time.sleep(0.1 * (2**attempt))  # Exponential backoff
                    continue
                break

        raise last_error or RuntimeError("Query execution failed")

    def get_database_info(self) -> Dict[str, Any]:
        """Get comprehensive database information."""
        with self.get_connection() as conn:
            info: Dict[str, Any] = {}

            # Basic info
            info["database_path"] = self.db_path
            db_file = Path(self.db_path)
            info["database_size"] = db_file.stat().st_size if db_file.exists() else 0

            # PRAGMA info
            pragma_queries = [
                ("journal_mode", "PRAGMA journal_mode"),
                ("synchronous", "PRAGMA synchronous"),
                ("cache_size", "PRAGMA cache_size"),
                ("page_count", "PRAGMA page_count"),
                ("page_size", "PRAGMA page_size"),
                ("freelist_count", "PRAGMA freelist_count"),
                ("wal_checkpoint", "PRAGMA wal_checkpoint"),
            ]

            for key, query in pragma_queries:
                try:
                    result = conn.execute(query).fetchone()
                    info[key] = result[0] if result else None
                except Exception as e:
                    info[key] = f"Error: {e}"

            # Pool statistics
            info["pool_stats"] = self.pool.get_stats()

            return info

    def force_checkpoint(self) -> bool:
        """Force WAL checkpoint."""
        try:
            with self.get_connection() as conn:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                return True
        except Exception as e:
            logger.error(f"Force checkpoint failed: {e}")
            return False

    def vacuum(self, full: bool = False) -> bool:
        """Perform database vacuum."""
        try:
            with self.get_connection() as conn:
                if full:
                    conn.execute("VACUUM")
                else:
                    vacuum_pages = self.vacuum_config.incremental_vacuum_pages
                    conn.execute(f"PRAGMA incremental_vacuum({vacuum_pages})")
                return True
        except Exception as e:
            logger.error(f"Vacuum failed: {e}")
            return False

    def close(self) -> None:
        """Close the SQLite manager."""
        self.pool.close()


# Global enhanced manager instance (lazy initialization)
_global_manager: Optional[EnhancedSQLiteManager] = None
_manager_lock = threading.Lock()


def get_enhanced_manager(db_path: Optional[str] = None) -> EnhancedSQLiteManager:
    """Get or create the global enhanced SQLite manager."""
    global _global_manager

    with _manager_lock:
        if _global_manager is None:
            if db_path is None:
                raise ValueError("db_path required for first initialization")
            _global_manager = EnhancedSQLiteManager(db_path)
        return _global_manager


def close_global_manager() -> None:
    """Close the global manager."""
    global _global_manager

    with _manager_lock:
        if _global_manager:
            _global_manager.close()
            _global_manager = None

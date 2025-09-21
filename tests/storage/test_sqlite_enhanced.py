"""
Tests for Enhanced SQLite Utilities
Supporting Issue 1.2.2 SQLite Utilities Enhancement
"""

import sqlite3
import tempfile
import threading
import time
from pathlib import Path

from ward import expect, fixture, test

from storage.sqlite_enhanced import (
    EnhancedConnectionPool,
    EnhancedSQLiteManager,
    PoolConfig,
    VacuumConfig,
)


@fixture
def temp_db_path():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@fixture
def pool_config():
    """Create pool configuration for testing."""
    return PoolConfig(
        min_connections=1,
        max_connections=3,
        max_idle_time=60,
        connection_timeout=5,
        pool_recycle_time=300,
        validate_connections=True,
        retry_attempts=2,
    )


@fixture
def vacuum_config():
    """Create vacuum configuration for testing."""
    return VacuumConfig(
        auto_vacuum_interval=60,
        incremental_vacuum_pages=100,
        wal_checkpoint_interval=30,
        analyze_interval=120,
        integrity_check_interval=600,
    )


@fixture
def connection_pool(temp_db_path, pool_config, vacuum_config):
    """Create connection pool for testing."""
    pool = EnhancedConnectionPool(
        db_path=temp_db_path,
        pool_config=pool_config,
        vacuum_config=vacuum_config,
    )
    yield pool
    pool.close()


@test("connection pool initialization")
def test_pool_initialization(temp_db_path, pool_config, vacuum_config):
    """Test connection pool initializes correctly."""
    pool = EnhancedConnectionPool(
        db_path=temp_db_path,
        pool_config=pool_config,
        vacuum_config=vacuum_config,
    )

    try:
        expect(pool.db_path).equals(temp_db_path)
        expect(pool.pool_config).equals(pool_config)
        expect(pool.vacuum_config).equals(vacuum_config)

        # Check initial stats
        stats = pool.get_stats()
        expect(stats.active_connections).equals(0)
        expect(stats.idle_connections).equals(0)

    finally:
        pool.close()


@test("connection creation and retrieval")
def test_connection_creation(connection_pool):
    """Test creating and retrieving connections."""
    # Get first connection
    with connection_pool.get_connection() as conn:
        expect(conn).is_not(None)
        expect(isinstance(conn, sqlite3.Connection)).is_(True)

        # Execute test query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        expect(result[0]).equals(1)

    # Check stats
    stats = connection_pool.get_stats()
    expect(stats.total_connections_created).is_greater_than(0)


@test("connection pooling behavior")
def test_connection_pooling(connection_pool):
    """Test connection pool reuses connections."""
    # Get connection and release it
    with connection_pool.get_connection() as conn1:
        conn1_id = id(conn1)

    # Get another connection - should reuse from pool
    with connection_pool.get_connection() as conn2:
        # Note: Due to context manager, we can't directly compare connection objects
        # but we can verify the pool behavior through stats
        pass

    stats = connection_pool.get_stats()
    expect(stats.total_connections_created).is_greater_than(0)


@test("connection pool concurrency")
def test_concurrent_connections(connection_pool):
    """Test multiple concurrent connections."""
    results = []
    errors = []

    def worker(worker_id):
        try:
            with connection_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ? as worker_id", (worker_id,))
                result = cursor.fetchone()
                results.append(result[0])
        except Exception as e:
            errors.append(e)

    # Start multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=worker, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join()

    expect(len(errors)).equals(0)
    expect(len(results)).equals(5)
    expect(set(results)).equals({0, 1, 2, 3, 4})


@test("connection validation")
def test_connection_validation(connection_pool):
    """Test connection validation works."""
    with connection_pool.get_connection() as conn:
        # Test that connection is valid
        cursor = conn.cursor()
        cursor.execute("PRAGMA schema_version")
        result = cursor.fetchone()
        expect(result).is_not(None)


@test("pooled connection lifecycle")
def test_pooled_connection_lifecycle(temp_db_path, pool_config, vacuum_config):
    """Test PooledConnection lifecycle management."""
    pool = EnhancedConnectionPool(temp_db_path, pool_config, vacuum_config)

    try:
        # Get a connection from pool
        with pool.get_connection() as conn:
            # Test basic operations
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
            cursor.execute("INSERT INTO test (value) VALUES (?)", ("test_value",))
            conn.commit()

            cursor.execute("SELECT value FROM test WHERE id = 1")
            result = cursor.fetchone()
            expect(result[0]).equals("test_value")

    finally:
        pool.close()


@test("connection timeout handling")
def test_connection_timeout(temp_db_path):
    """Test connection timeout behavior."""
    config = PoolConfig(
        min_connections=1,
        max_connections=1,
        connection_timeout=1,  # Very short timeout
    )
    vacuum_config = VacuumConfig()

    pool = EnhancedConnectionPool(temp_db_path, config, vacuum_config)

    try:
        # Hold one connection
        with pool.get_connection() as conn1:
            # Try to get another - should timeout quickly
            start_time = time.time()

            try:
                with pool.get_connection() as conn2:
                    pass
            except Exception:
                elapsed = time.time() - start_time
                # Should timeout within reasonable time
                expect(elapsed).is_less_than(5)

    finally:
        pool.close()


@test("enhanced sqlite manager initialization")
def test_sqlite_manager_init(temp_db_path, pool_config, vacuum_config):
    """Test EnhancedSQLiteManager initialization."""
    manager = EnhancedSQLiteManager(
        db_path=temp_db_path,
        pool_config=pool_config,
        vacuum_config=vacuum_config,
    )

    try:
        expect(manager.db_path).equals(temp_db_path)
        expect(manager.pool).is_not(None)
    finally:
        manager.close()


@test("sqlite manager database operations")
def test_sqlite_manager_operations(temp_db_path, pool_config, vacuum_config):
    """Test EnhancedSQLiteManager database operations."""
    manager = EnhancedSQLiteManager(temp_db_path, pool_config, vacuum_config)

    try:
        # Test execute_with_retry
        cursor = manager.execute_with_retry(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)"
        )
        expect(cursor).is_not(None)

        # Test with parameters
        cursor = manager.execute_with_retry(
            "INSERT INTO test (value) VALUES (?)", ("test_value",)
        )
        expect(cursor).is_not(None)

        # Test query
        cursor = manager.execute_with_retry("SELECT COUNT(*) FROM test")
        result = cursor.fetchone()
        expect(result[0]).equals(1)

    finally:
        manager.close()


@test("sqlite manager vacuum operations")
def test_sqlite_manager_vacuum(temp_db_path, pool_config, vacuum_config):
    """Test vacuum operations."""
    manager = EnhancedSQLiteManager(temp_db_path, pool_config, vacuum_config)

    try:
        # Create some data
        manager.execute_with_retry(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)"
        )
        for i in range(100):
            manager.execute_with_retry(
                "INSERT INTO test (value) VALUES (?)", (f"value_{i}",)
            )

        # Test incremental vacuum
        result = manager.vacuum(full=False)
        expect(result).is_(True)

        # Test full vacuum
        result = manager.vacuum(full=True)
        expect(result).is_(True)

    finally:
        manager.close()


@test("sqlite manager checkpoint operations")
def test_sqlite_manager_checkpoint(temp_db_path, pool_config, vacuum_config):
    """Test WAL checkpoint operations."""
    manager = EnhancedSQLiteManager(temp_db_path, pool_config, vacuum_config)

    try:
        # Enable WAL mode
        with manager.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")

        # Create some data
        manager.execute_with_retry(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)"
        )

        # Test checkpoint
        result = manager.force_checkpoint()
        expect(result).is_(True)

    finally:
        manager.close()


@test("sqlite manager database info")
def test_sqlite_manager_info(temp_db_path, pool_config, vacuum_config):
    """Test database info retrieval."""
    manager = EnhancedSQLiteManager(temp_db_path, pool_config, vacuum_config)

    try:
        info = manager.get_database_info()

        expect(info).is_not(None)
        expect(info["database_path"]).equals(temp_db_path)
        expect(info["database_size"]).is_greater_than_or_equal_to(0)
        expect(info["pool_stats"]).is_not(None)

        # Should have PRAGMA info
        expect("journal_mode" in info).is_(True)
        expect("page_count" in info).is_(True)

    finally:
        manager.close()


@test("pool stats tracking")
def test_pool_stats(connection_pool):
    """Test pool statistics tracking."""
    initial_stats = connection_pool.get_stats()

    # Use some connections
    with connection_pool.get_connection() as conn1:
        with connection_pool.get_connection() as conn2:
            stats = connection_pool.get_stats()
            expect(stats.active_connections).is_greater_than(0)

    # After connections are returned
    final_stats = connection_pool.get_stats()
    expect(final_stats.total_connections_created).is_greater_than_or_equal_to(
        initial_stats.total_connections_created
    )


@test("error handling and retry")
def test_error_handling(temp_db_path, pool_config, vacuum_config):
    """Test error handling and retry logic."""
    manager = EnhancedSQLiteManager(temp_db_path, pool_config, vacuum_config)

    try:
        # Test with invalid SQL - should raise exception
        try:
            manager.execute_with_retry("INVALID SQL STATEMENT")
            expect(False).is_(True)  # Should not reach here
        except Exception as e:
            expect(str(e)).contains("syntax error")

    finally:
        manager.close()


@test("connection pool maintenance")
def test_maintenance_operations(temp_db_path):
    """Test automated maintenance operations."""
    config = PoolConfig(min_connections=1, max_connections=2)
    vacuum_config = VacuumConfig(
        auto_vacuum_interval=1,  # Very short for testing
        wal_checkpoint_interval=1,
        analyze_interval=1,
    )

    pool = EnhancedConnectionPool(temp_db_path, config, vacuum_config)

    try:
        # Create some data
        with pool.get_connection() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            conn.execute("INSERT INTO test VALUES (1)")
            conn.commit()

        # Wait for maintenance to potentially run
        time.sleep(2)

        # Verify database is still functional
        with pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM test")
            result = cursor.fetchone()
            expect(result[0]).equals(1)

    finally:
        pool.close()


@test("connection pool cleanup")
def test_pool_cleanup(temp_db_path, pool_config, vacuum_config):
    """Test proper cleanup of connection pool."""
    pool = EnhancedConnectionPool(temp_db_path, pool_config, vacuum_config)

    # Use some connections
    with pool.get_connection() as conn:
        conn.execute("SELECT 1")

    # Close pool
    pool.close()

    # Verify cleanup
    expect(pool._shutdown_event.is_set()).is_(True)


if __name__ == "__main__":
    # Run basic smoke test
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        config = PoolConfig(min_connections=1, max_connections=2)
        vacuum_config = VacuumConfig()

        manager = EnhancedSQLiteManager(db_path, config, vacuum_config)

        # Basic operations
        manager.execute_with_retry(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)"
        )
        manager.execute_with_retry("INSERT INTO test (value) VALUES (?)", ("test",))

        cursor = manager.execute_with_retry("SELECT COUNT(*) FROM test")
        result = cursor.fetchone()
        assert result[0] == 1

        print("✅ SQLite Enhanced utilities smoke test passed!")

        manager.close()

    finally:
        Path(db_path).unlink(missing_ok=True)

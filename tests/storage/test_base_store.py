"""Tests for BaseStore abstract class and SQLite utilities."""

import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ward import raises, test

from storage.core.base_store import BaseStore, MockStore, StoreConfig
from storage.core.sqlite_util import (
    ConnectionConfig,
    EnhancedConnectionPool,
    PerformanceMonitor,
    create_optimized_connection,
    migrate_database,
)
from storage.core.unit_of_work import UnitOfWork


class TestStore(BaseStore):
    """Test store implementation for BaseStore testing."""

    def __init__(self, name: str = "test", config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._store_name = name
        self._records: Dict[str, Dict[str, Any]] = {}
        self._next_id = 1
        self._schema_initialized = False

    def _get_schema(self) -> Dict[str, Any]:
        """Test schema."""
        return {
            "type": "object",
            "required": ["name", "value"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "value": {"type": "integer"},
                "optional": {"type": "string"},
            },
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize test schema."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_records (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER NOT NULL,
                optional TEXT
            )
        """
        )
        self._schema_initialized = True

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a test record."""
        record_id = f"{self._store_name}_{self._next_id}"
        self._next_id += 1

        # Store in memory for simplicity
        record = {"id": record_id, **data}
        self._records[record_id] = record

        # Also store in database if in transaction
        if self._connection:
            self._connection.execute(
                "INSERT INTO test_records (id, name, value, optional) VALUES (?, ?, ?, ?)",
                (record_id, data["name"], data["value"], data.get("optional")),
            )

        return record

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a test record."""
        if self._connection:
            cursor = self._connection.execute(
                "SELECT id, name, value, optional FROM test_records WHERE id = ?",
                (record_id,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "value": row[2],
                    "optional": row[3],
                }
        return self._records.get(record_id)

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a test record."""
        if record_id not in self._records:
            raise ValueError(f"Record {record_id} not found")

        self._records[record_id].update(data)

        # Update in database if in transaction
        if self._connection:
            updates = []
            params = []
            for key, value in data.items():
                if key != "id":
                    updates.append(f"{key} = ?")
                    params.append(value)

            if updates:
                sql = f"UPDATE test_records SET {', '.join(updates)} WHERE id = ?"
                params.append(record_id)
                self._connection.execute(sql, params)

        return self._records[record_id]

    def _delete_record(self, record_id: str) -> bool:
        """Delete a test record."""
        deleted = record_id in self._records

        if deleted:
            del self._records[record_id]

            # Delete from database if in transaction
            if self._connection:
                self._connection.execute(
                    "DELETE FROM test_records WHERE id = ?", (record_id,)
                )

        return deleted

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List test records."""
        if self._connection:
            sql = "SELECT id, name, value, optional FROM test_records"
            params = []

            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(f"{key} = ?")
                    params.append(value)
                sql += " WHERE " + " AND ".join(conditions)

            if limit:
                sql += f" LIMIT {limit}"
            if offset:
                sql += f" OFFSET {offset}"

            cursor = self._connection.execute(sql, params)
            return [
                {"id": row[0], "name": row[1], "value": row[2], "optional": row[3]}
                for row in cursor.fetchall()
            ]

        # Fallback to in-memory records
        records = list(self._records.values())

        if filters:
            filtered_records = []
            for record in records:
                match = True
                for key, value in filters.items():
                    if key not in record or record[key] != value:
                        match = False
                        break
                if match:
                    filtered_records.append(record)
            records = filtered_records

        if offset:
            records = records[offset:]
        if limit:
            records = records[:limit]

        return records


# BaseStore Tests


@test("BaseStore initialization")
def test_base_store_initialization():
    """Test BaseStore initialization."""
    store = TestStore("test")

    assert store.get_store_name() == "test"
    assert not store.is_in_transaction()
    assert store.get_current_connection() is None

    stats = store.get_stats()
    assert stats["store_name"] == "test"
    assert stats["operation_count"] == 0
    assert stats["error_count"] == 0


@test("BaseStore StoreProtocol compliance")
def test_store_protocol_compliance():
    """Test that BaseStore implements StoreProtocol correctly."""
    store = TestStore("test")

    # Test store name
    assert store.get_store_name() == "test"

    # Test connection requirements
    requirements = store.get_connection_requirements()
    assert "timeout" in requirements
    assert "enable_wal" in requirements
    assert "enable_foreign_keys" in requirements


@test("BaseStore transaction lifecycle")
def test_transaction_lifecycle():
    """Test BaseStore transaction lifecycle."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        store = TestStore("test")
        conn = create_optimized_connection(db_path)

        # Begin transaction
        store.begin_transaction(conn)
        assert store.is_in_transaction()
        assert store.get_current_connection() is conn

        # Commit transaction
        store.commit_transaction(conn)
        assert not store.is_in_transaction()
        assert store.get_current_connection() is None

        conn.close()

    finally:
        Path(db_path).unlink(missing_ok=True)


@test("BaseStore transaction rollback")
def test_transaction_rollback():
    """Test BaseStore transaction rollback."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        store = TestStore("test")
        conn = create_optimized_connection(db_path)

        # Begin transaction
        store.begin_transaction(conn)
        assert store.is_in_transaction()

        # Rollback transaction
        store.rollback_transaction(conn)
        assert not store.is_in_transaction()
        assert store.get_current_connection() is None

        conn.close()

    finally:
        Path(db_path).unlink(missing_ok=True)


@test("BaseStore CRUD operations")
def test_crud_operations():
    """Test BaseStore CRUD operations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    conn = None
    try:
        store = TestStore("test")
        conn = create_optimized_connection(db_path)

        store.begin_transaction(conn)

        # Create
        data: Dict[str, Any] = {"name": "test_item", "value": 42}
        record = store.create(data)
        assert record["name"] == "test_item"
        assert record["value"] == 42
        assert "id" in record

        record_id = record["id"]

        # Read
        read_record = store.read(record_id)
        assert read_record is not None
        assert read_record["name"] == "test_item"
        assert read_record["value"] == 42

        # Update
        update_data: Dict[str, Any] = {"value": 84}
        updated_record = store.update(record_id, update_data)
        assert updated_record["value"] == 84
        assert updated_record["name"] == "test_item"  # Should be preserved

        # List
        all_records = store.list()
        assert len(all_records) == 1
        assert all_records[0]["id"] == record_id

        # List with filters
        filtered_records = store.list(filters={"name": "test_item"})
        assert len(filtered_records) == 1

        # Delete
        deleted = store.delete(record_id)
        assert deleted is True

        # Verify deletion
        deleted_record = store.read(record_id)
        assert deleted_record is None

        store.commit_transaction(conn)

    finally:
        if conn:
            conn.close()
        # Give Windows time to release the file handle
        time.sleep(0.1)
        try:
            Path(db_path).unlink()
        except (OSError, PermissionError):
            pass  # Best effort cleanup on Windows


@test("BaseStore validation")
def test_validation():
    """Test BaseStore data validation."""
    store = TestStore("test")

    # Valid data
    valid_data: Dict[str, Any] = {"name": "test", "value": 42}
    result = store.validate_data(valid_data)
    assert result.is_valid
    assert len(result.errors) == 0

    # Missing required field
    invalid_data: Dict[str, Any] = {"name": "test"}  # Missing "value"
    result = store.validate_data(invalid_data)
    assert not result.is_valid
    assert len(result.errors) > 0

    # Invalid type
    invalid_type_data: Dict[str, Any] = {"name": "test", "value": "not_an_integer"}
    result = store.validate_data(invalid_type_data)
    assert not result.is_valid

    # Partial validation (for updates)
    partial_data = {"value": 84}
    result = store.validate_data(partial_data, allow_partial=True)
    assert result.is_valid


@test("BaseStore operation without transaction")
def test_operations_without_transaction():
    """Test that operations fail when not in transaction."""
    store = TestStore("test")

    with raises(RuntimeError):
        store.create({"name": "test", "value": 42})

    with raises(RuntimeError):
        store.read("1")

    with raises(RuntimeError):
        store.update("1", {"value": 84})

    with raises(RuntimeError):
        store.delete("1")

    with raises(RuntimeError):
        store.list()


@test("BaseStore performance tracking")
def test_performance_tracking():
    """Test BaseStore performance tracking."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        store = TestStore("test")
        conn = create_optimized_connection(db_path)

        store.begin_transaction(conn)

        # Perform operations
        store.create({"name": "test1", "value": 1})
        store.create({"name": "test2", "value": 2})
        store.list()

        stats = store.get_stats()
        assert stats["operation_count"] == 3
        assert stats["error_count"] == 0
        assert stats["error_rate"] == 0.0

        # Reset stats
        store.reset_stats()
        stats = store.get_stats()
        assert stats["operation_count"] == 0

        store.commit_transaction(conn)
        conn.close()

    finally:
        Path(db_path).unlink(missing_ok=True)


# UnitOfWork Integration Tests


@test("BaseStore integration with UnitOfWork")
def test_uow_integration():
    """Test BaseStore integration with UnitOfWork."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        store1 = TestStore("store1")
        store2 = TestStore("store2")

        uow = UnitOfWork(db_path, use_connection_pool=False)
        uow.register_store(store1)
        uow.register_store(store2)

        with uow:
            # Create records in both stores
            record1 = store1.create({"name": "item1", "value": 100})
            record2 = store2.create({"name": "item2", "value": 200})

            uow.track_write("store1", record1["id"])
            uow.track_write("store2", record2["id"])

        # Verify both stores were committed
        assert uow.status == UnitOfWork.STATUS_COMMITTED

        # Check writes
        writes_by_store = uow.get_writes_by_store()
        assert "store1" in writes_by_store
        assert "store2" in writes_by_store

        uow.cleanup()

    finally:
        Path(db_path).unlink(missing_ok=True)


# SQLite Utilities Tests


@test("ConnectionConfig default values")
def test_connection_config():
    """Test ConnectionConfig default values."""
    config = ConnectionConfig()

    assert config.journal_mode == "WAL"
    assert config.synchronous == "NORMAL"
    assert config.cache_size == 10000
    assert config.foreign_keys is True
    assert config.busy_timeout == 30000


@test("PerformanceMonitor basic functionality")
def test_performance_monitor():
    """Test PerformanceMonitor basic functionality."""
    monitor = PerformanceMonitor()

    # Record query
    monitor.record_query("conn1", 0.05)
    monitor.record_query("conn1", 0.03)

    # Record transaction
    monitor.record_transaction("conn1", True)
    monitor.record_transaction("conn1", False)

    # Record error
    monitor.record_error("conn1", Exception("test error"))

    # Get stats
    stats = monitor.get_stats("conn1")
    assert "conn1" in stats

    conn_stats = stats["conn1"]
    assert conn_stats.queries_executed == 2
    assert conn_stats.transactions_committed == 1
    assert conn_stats.transactions_rolled_back == 1
    assert conn_stats.errors == 1
    assert conn_stats.get_avg_query_time() == 0.04


@test("PerformanceMonitor hooks")
def test_performance_monitor_hooks():
    """Test PerformanceMonitor hooks."""
    monitor = PerformanceMonitor()
    hook_calls: List[Tuple[str, str]] = []

    def test_hook(conn_id: str, metrics: Dict[str, Any]) -> None:
        hook_calls.append((conn_id, metrics["type"]))

    monitor.add_hook(test_hook)

    monitor.record_query("conn1", 0.05)
    monitor.record_transaction("conn1", True)
    monitor.record_error("conn1", Exception("test"))

    assert len(hook_calls) == 3
    assert hook_calls[0] == ("conn1", "query")
    assert hook_calls[1] == ("conn1", "transaction")
    assert hook_calls[2] == ("conn1", "error")


@test("EnhancedConnectionPool basic operations")
def test_connection_pool():
    """Test EnhancedConnectionPool basic operations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        pool = EnhancedConnectionPool(db_path, max_connections=3)

        # Get connections
        conn1 = pool.get_connection()
        conn2 = pool.get_connection()
        conn3 = pool.get_connection()

        # Pool should be full
        with raises(RuntimeError):
            pool.get_connection()

        # Return a connection
        pool.return_connection(conn1)

        # Should be able to get one more
        conn4 = pool.get_connection()
        assert conn4 is conn1  # Should reuse the returned connection

        # Get pool stats
        stats = pool.get_pool_stats()
        assert stats["total_connections"] == 3
        assert stats["in_use"] == 3
        assert stats["available"] == 0

        # Clean up
        pool.return_connection(conn2)
        pool.return_connection(conn3)
        pool.return_connection(conn4)
        pool.close_all()

    finally:
        Path(db_path).unlink(missing_ok=True)


@test("EnhancedConnectionPool health check")
def test_connection_pool_health_check():
    """Test EnhancedConnectionPool health check."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        pool = EnhancedConnectionPool(db_path, max_connections=2)

        health = pool.health_check()
        assert health["healthy"] is True
        assert "response_time_ms" in health
        assert "pool_stats" in health

        pool.close_all()

    finally:
        Path(db_path).unlink(missing_ok=True)


@test("create_optimized_connection")
def test_create_optimized_connection():
    """Test create_optimized_connection function."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        config = ConnectionConfig(cache_size=5000, foreign_keys=False)
        conn = create_optimized_connection(db_path, config)

        # Test connection works
        cursor = conn.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1

        # Test WAL mode is enabled
        cursor = conn.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode.upper() == "WAL"

        conn.close()

    finally:
        Path(db_path).unlink(missing_ok=True)


@test("database migrations")
def test_database_migrations():
    """Test database migration functionality."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        migrations = [
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
            "CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT)",
            "ALTER TABLE posts ADD COLUMN content TEXT",
        ]

        migrate_database(db_path, migrations)

        # Verify migrations were applied
        conn = create_optimized_connection(db_path)

        # Check migrations table
        cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version")
        versions = [row[0] for row in cursor.fetchall()]
        assert versions == [1, 2, 3]

        # Check tables exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "users" in tables
        assert "posts" in tables
        assert "schema_migrations" in tables

        # Test that running migrations again is idempotent
        migrate_database(db_path, migrations)

        cursor = conn.execute("SELECT COUNT(*) FROM schema_migrations")
        count = cursor.fetchone()[0]
        assert count == 3  # Should still be 3, not 6

        conn.close()

    finally:
        Path(db_path).unlink(missing_ok=True)


@test("MockStore functionality")
def test_mock_store():
    """Test MockStore functionality."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        store = MockStore("mock_test")
        conn = create_optimized_connection(db_path)

        store.begin_transaction(conn)

        # Test CRUD operations
        record = store.create({"data": "test_data"})
        assert record["data"] == "test_data"
        assert "id" in record

        record_id = record["id"]
        read_record = store.read(record_id)
        assert read_record is not None
        assert read_record["data"] == "test_data"

        # Test list with filters
        store.create({"data": "other_data"})
        filtered = store.list(filters={"data": "test_data"})
        assert len(filtered) == 1
        assert filtered[0]["data"] == "test_data"

        store.commit_transaction(conn)
        conn.close()

    finally:
        Path(db_path).unlink(missing_ok=True)

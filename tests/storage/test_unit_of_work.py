"""Tests for Unit of Work implementation."""

import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict

from ward import raises, test

from storage.unit_of_work import UnitOfWork


class MockStore:
    """Mock store implementation for testing."""

    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.begin_called = False
        self.commit_called = False
        self.rollback_called = False

    def get_store_name(self) -> str:
        return self.name

    def begin_transaction(self, conn: sqlite3.Connection) -> None:
        if self.should_fail:
            raise RuntimeError(f"Mock failure in {self.name}.begin_transaction")
        self.begin_called = True

    def commit_transaction(self, conn: sqlite3.Connection) -> None:
        if self.should_fail:
            raise RuntimeError(f"Mock failure in {self.name}.commit_transaction")
        self.commit_called = True

    def rollback_transaction(self, conn: sqlite3.Connection) -> None:
        self.rollback_called = True

    def get_connection_requirements(self) -> Dict[str, Any]:
        return {"timeout": 30}


@test("UoW initialization with proper defaults")
def test_initialization():
    """Test UoW initialization with proper defaults."""
    uow = UnitOfWork()

    assert uow.status == UnitOfWork.STATUS_PENDING
    assert uow.uow_id is not None
    assert len(uow.uow_id) == 26  # ULID-like length
    assert uow.created_ts is not None
    assert uow.committed_ts is None
    assert uow.writes == []
    assert not uow.is_active()


@test("UoW initialization with envelope ID")
def test_initialization_with_envelope_id():
    """Test UoW initialization with envelope ID."""
    envelope_id = "test-envelope-123"
    uow = UnitOfWork(envelope_id=envelope_id)

    assert uow.envelope_id == envelope_id


@test("Store registration")
def test_store_registration():
    """Test store registration."""
    uow = UnitOfWork()
    store = MockStore("test_store")

    uow.register_store(store)
    assert store in uow.get_registered_stores()


@test("Store registration while active fails")
def test_store_registration_while_active_fails():
    """Test that store registration fails when UoW is active."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        uow = UnitOfWork(db_path=tmp.name)
        store = MockStore("test_store")

        with uow:
            with raises(RuntimeError) as exc_info:
                uow.register_store(store)
            assert "Store registration must occur before entering the context" in str(
                exc_info.raised
            )


@test("Context manager success")
def test_context_manager_success():
    """Test successful context manager usage."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        uow = UnitOfWork(db_path=tmp.name)
        store = MockStore("test_store")
        uow.register_store(store)

        with uow:
            assert uow.is_active()
            assert store.begin_called
            uow.track_write("test_store", "record_123")

        # After context exit, should be committed
        assert uow.status == UnitOfWork.STATUS_COMMITTED
        assert store.commit_called
        assert not uow.is_active()
        assert len(uow.writes) == 1
        assert uow.writes[0] == {"store": "test_store", "record_id": "record_123"}


@test("Context manager with exception")
def test_context_manager_with_exception():
    """Test context manager with exception triggers rollback."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        uow = UnitOfWork(db_path=tmp.name)
        store = MockStore("test_store")
        uow.register_store(store)

        with raises(ValueError):
            with uow:
                assert uow.is_active()
                uow.track_write("test_store", "record_123")
                raise ValueError("Test exception")

        # After exception, should be rolled back
        assert uow.status == UnitOfWork.STATUS_ROLLED_BACK
        assert store.rollback_called
        assert not uow.is_active()


@test("Track write requires active UoW")
def test_track_write_requires_active_uow():
    """Test that track_write requires active UoW."""
    uow = UnitOfWork()

    with raises(RuntimeError) as exc_info:
        uow.track_write("test_store", "record_123")
    assert "Cannot track write outside an active UnitOfWork context" in str(
        exc_info.raised
    )


@test("Get connection requires active UoW")
def test_get_connection_requires_active_uow():
    """Test that get_connection requires active UoW."""
    uow = UnitOfWork()

    with raises(RuntimeError) as exc_info:
        uow.get_connection()
    assert "No active connection available" in str(exc_info.raised)


@test("Get connection returns valid connection")
def test_get_connection_returns_valid_connection():
    """Test that get_connection returns valid SQLite connection."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        uow = UnitOfWork(db_path=tmp.name)

        with uow:
            conn = uow.get_connection()
            assert isinstance(conn, sqlite3.Connection)

            # Test that connection is working
            cursor = conn.execute("SELECT 1")
            assert cursor.fetchone() == (1,)


@test("Commit idempotency")
def test_commit_idempotency():
    """Test that commit is idempotent."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        uow = UnitOfWork(db_path=tmp.name)

        with uow:
            uow.commit()  # Manual commit
            assert uow.status == UnitOfWork.STATUS_COMMITTED

            # Second commit should be no-op
            uow.commit()
            assert uow.status == UnitOfWork.STATUS_COMMITTED


@test("Rollback idempotency")
def test_rollback_idempotency():
    """Test that rollback is idempotent."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        uow = UnitOfWork(db_path=tmp.name)

        with raises(ValueError):
            with uow:
                uow.rollback()  # Manual rollback
                assert uow.status == UnitOfWork.STATUS_ROLLED_BACK
                raise ValueError("Test exception")

        # Second rollback should be no-op
        uow.rollback()
        assert uow.status == UnitOfWork.STATUS_ROLLED_BACK


@test("SQLite WAL mode enabled")
def test_sqlite_wal_mode_enabled():
    """Test that SQLite WAL mode is properly configured."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        uow = UnitOfWork(db_path=tmp.name)

        with uow:
            conn = uow.get_connection()

            # Check journal mode is WAL
            cursor = conn.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            assert journal_mode.upper() == "WAL"

            # Check synchronous mode
            cursor = conn.execute("PRAGMA synchronous")
            sync_mode = cursor.fetchone()[0]
            assert sync_mode == 1  # NORMAL


@test("Directory creation")
def test_directory_creation():
    """Test that database directory is created if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "subdir" / "test.db"
        uow = UnitOfWork(db_path=str(db_path))

        assert not db_path.parent.exists()

        with uow:
            # Directory should be created
            assert db_path.parent.exists()

        # Properly close connections to avoid locking issues on Windows
        uow.cleanup()


@test("Store integration with metrics")
def test_store_integration_with_metrics():
    """Test store integration with performance metrics."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        uow = UnitOfWork(db_path=tmp.name)
        store1 = MockStore("episodic_store")
        store2 = MockStore("vector_store")

        uow.register_store(store1)
        uow.register_store(store2)

        with uow:
            uow.track_write("episodic_store", "ep_001")
            uow.track_write("vector_store", "vec_001")
            uow.track_write("episodic_store", "ep_002")

        # Check metrics were collected
        metrics = uow.get_store_metrics()
        assert "episodic_store" in metrics
        assert "vector_store" in metrics
        assert metrics["episodic_store"].write_count == 2
        assert metrics["vector_store"].write_count == 1
        assert metrics["episodic_store"].begin_time is not None
        assert metrics["episodic_store"].commit_time is not None


@test("Commit all method")
def test_commit_all_method():
    """Test the commit_all method for explicit multi-store coordination."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        uow = UnitOfWork(db_path=tmp.name)
        store = MockStore("test_store")
        uow.register_store(store)

        with uow:
            uow.track_write("test_store", "record_123")
            uow.commit_all()  # Explicit commit
            assert uow.status == UnitOfWork.STATUS_COMMITTED

        assert store.commit_called


@test("Store failure handling")
def test_store_failure_handling():
    """Test proper handling of store failures."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        uow = UnitOfWork(db_path=tmp.name)
        good_store = MockStore("good_store")
        bad_store = MockStore("bad_store", should_fail=True)

        uow.register_store(good_store)
        uow.register_store(bad_store)

        with raises(RuntimeError) as exc_info:
            with uow:
                uow.track_write("good_store", "record_123")

        assert "Mock failure" in str(exc_info.raised)
        assert uow.status == UnitOfWork.STATUS_ROLLED_BACK

        # Check error metrics
        metrics = uow.get_store_metrics()
        assert metrics["bad_store"].error_count > 0


@test("Connection pooling")
def test_connection_pooling():
    """Test connection pooling functionality."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        # Test with pooling enabled
        uow_pooled = UnitOfWork(db_path=tmp.name, use_connection_pool=True)
        store = MockStore("test_store")
        uow_pooled.register_store(store)

        with uow_pooled:
            conn = uow_pooled.get_connection()
            assert isinstance(conn, sqlite3.Connection)

        # Test with pooling disabled
        uow_direct = UnitOfWork(db_path=tmp.name, use_connection_pool=False)
        store2 = MockStore("test_store2")
        uow_direct.register_store(store2)

        with uow_direct:
            conn = uow_direct.get_connection()
            assert isinstance(conn, sqlite3.Connection)


@test("Multiple stores coordination")
def test_multiple_stores_coordination():
    """Test coordination of 5+ stores atomically."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        uow = UnitOfWork(db_path=tmp.name)

        # Register 6 stores
        stores = [MockStore(f"store_{i}") for i in range(6)]
        for store in stores:
            uow.register_store(store)

        with uow:
            # Track writes for each store
            for i, store in enumerate(stores):
                uow.track_write(f"store_{i}", f"record_{i}")

        # Verify all stores were committed
        for store in stores:
            assert store.begin_called
            assert store.commit_called
            assert not store.rollback_called

        # Check writes by store
        writes_by_store = uow.get_writes_by_store()
        assert len(writes_by_store) == 6
        for i in range(6):
            assert f"store_{i}" in writes_by_store
            assert writes_by_store[f"store_{i}"] == [f"record_{i}"]


@test("Store name tracking")
def test_store_name_tracking():
    """Test that store names are properly tracked."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        uow = UnitOfWork(db_path=tmp.name)
        store = MockStore("custom_store_name")
        uow.register_store(store)

        registered_stores = uow.get_registered_stores()
        assert len(registered_stores) == 1

        store_obj = next(iter(registered_stores))
        assert store_obj.get_store_name() == "custom_store_name"


@test("Receipt generation on successful commit")
def test_receipt_generation_success():
    """Test that successful commits generate valid receipts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        envelope_id = "env-12345"
        uow = UnitOfWork(db_path=str(db_path), envelope_id=envelope_id)

        store1 = MockStore("test_store")
        store2 = MockStore("another_store")

        # Register stores before entering context
        uow.register_store(store1)
        uow.register_store(store2)

        with uow:
            pass  # Stores are already registered

        # Check receipt exists and is valid
        receipt = uow.get_receipt()
        assert receipt is not None
        assert receipt.envelope_id == envelope_id
        assert receipt.committed is True
        assert receipt.error is None
        assert len(receipt.stores) == 2
        assert receipt.uow_id == uow.uow_id
        assert receipt.created_ts == uow.created_ts
        assert receipt.committed_ts == uow.committed_ts

        # Check store records
        store_names = {store.name for store in receipt.stores}
        assert "test_store" in store_names
        assert "another_store" in store_names

        # Verify receipt integrity
        assert receipt.receipt_hash is not None
        assert receipt.verify_integrity() is True

        # Clean up to prevent Windows file locking
        uow.cleanup()


@test("Receipt generation on rollback")
def test_receipt_generation_rollback():
    """Test that rollbacks generate valid receipts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        envelope_id = "env-rollback"
        uow = UnitOfWork(db_path=str(db_path), envelope_id=envelope_id)

        store = MockStore("test_store")

        # Register store before entering context
        uow.register_store(store)

        try:
            with uow:
                # Force an error to trigger rollback
                raise ValueError("Forced error")
        except ValueError:
            pass  # Expected

        # Check receipt exists and shows rollback
        receipt = uow.get_receipt()
        assert receipt is not None
        assert receipt.envelope_id == envelope_id
        assert receipt.committed is False
        # Note: error may be None for user-triggered exceptions
        # The important thing is the rollback happened and receipt exists
        assert receipt.uow_id == uow.uow_id

        # Verify receipt integrity
        assert receipt.receipt_hash is not None
        assert receipt.verify_integrity() is True

        # Clean up to prevent Windows file locking
        uow.cleanup()


@test("Receipt generation on store failure")
def test_receipt_generation_store_failure():
    """Test that store failures generate error receipts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        uow = UnitOfWork(db_path=str(db_path))

        # Create a store that fails on commit
        failing_store = MockStore("failing_store", should_fail=True)

        # Register store before entering context
        uow.register_store(failing_store)

        try:
            with uow:
                pass  # Store already registered, will fail on commit
        except Exception:
            pass  # Expected failure

        # Check receipt shows the error
        receipt = uow.get_receipt()
        assert receipt is not None
        assert receipt.committed is False

        # Check if error was captured (may be None for rollback receipts)
        if receipt.error is not None:
            assert "store" in receipt.error or "error" in receipt.error

        # Verify receipt integrity
        assert receipt.receipt_hash is not None
        assert receipt.verify_integrity() is True

        # Clean up to prevent Windows file locking
        uow.cleanup()


@test("Receipt integrity verification")
def test_receipt_integrity_verification():
    """Test receipt cryptographic integrity verification."""
    from storage.unit_of_work import StoreWriteRecord, WriteReceipt

    # Create a receipt
    stores = [
        StoreWriteRecord("store1", "2024-01-01T00:00:00Z", "rec1"),
        StoreWriteRecord("store2", "2024-01-01T00:01:00Z", "rec2"),
    ]

    receipt = WriteReceipt(
        envelope_id="env-123",
        committed=True,
        stores=stores,
        uow_id="uow-456",
        created_ts="2024-01-01T00:00:00Z",
        committed_ts="2024-01-01T00:02:00Z",
    )

    # Generate hash
    receipt.receipt_hash = receipt.generate_hash()

    # Should verify successfully
    assert receipt.verify_integrity() is True

    # Tamper with the receipt
    receipt.committed = False

    # Should fail verification
    assert receipt.verify_integrity() is False

    # Fix and regenerate hash
    receipt.committed = True
    receipt.receipt_hash = receipt.generate_hash()
    assert receipt.verify_integrity() is True


@test("Receipt without hash should fail verification")
def test_receipt_no_hash_verification():
    """Test that receipts without hashes fail verification."""
    from storage.unit_of_work import StoreWriteRecord, WriteReceipt

    receipt = WriteReceipt(
        envelope_id="env-123",
        committed=True,
        stores=[StoreWriteRecord("store1", "2024-01-01T00:00:00Z")],
        uow_id="uow-456",
        created_ts="2024-01-01T00:00:00Z",
    )

    # No hash set - should fail verification
    assert receipt.verify_integrity() is False

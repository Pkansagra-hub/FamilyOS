"""
Comprehensive tests for the IdempotencyStore and UnitOfWork idempotency integration.

Tests verify:
- IdempotencyStore creation and schema initialization
- Deterministic key generation
- Duplicate operation detection with result caching
- TTL-based expiration and cleanup
- UnitOfWork integration for transactional idempotency
"""

import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

from ward import test

from storage.idempotency_store import IdempotencyStore
from storage.unit_of_work import UnitOfWork


def safe_cleanup_db(db_path: str, tmp_file: Any) -> None:
    """Safely cleanup test database files on Windows."""
    tmp_file.close()
    try:
        Path(db_path).unlink(missing_ok=True)
    except PermissionError:
        # Windows file locking issue - acceptable in tests
        pass


@test("IdempotencyStore initialization and schema creation")
def test_idempotency_store_initialization():
    """Test IdempotencyStore initialization and schema creation."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    conn = None
    try:
        # UnitOfWork now automatically initializes IdempotencyStore
        uow = UnitOfWork(db_path)

        with uow:
            pass  # Schema gets created automatically

        # Verify schema was created
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='idempotency_keys'
        """
        )
        assert cursor.fetchone() is not None, "Idempotency table should exist"

        # Check indexes exist
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='index' AND tbl_name='idempotency_keys'
        """
        )
        indexes = [row[0] for row in cursor.fetchall()]
        assert "idx_idempotency_expires" in indexes
        assert "idx_idempotency_operation" in indexes
        assert "idx_idempotency_payload_hash" in indexes

    finally:
        if conn:
            conn.close()
        safe_cleanup_db(db_path, tmp_file)


@test("IdempotencyStore key generation is deterministic")
def test_key_generation_deterministic():
    """Test that key generation is deterministic for same inputs."""
    store = IdempotencyStore()

    operation = "create_user"
    payload = {"email": "test@example.com", "name": "Test User"}

    # Generate keys multiple times
    key1 = store.generate_key(operation, payload)
    key2 = store.generate_key(operation, payload)
    key3 = store.generate_key(operation, payload)

    # Should all be identical
    assert key1 == key2 == key3
    assert len(key1) == 64, "Key should be SHA256 hash"

    # Different operation should produce different key
    key_diff_op = store.generate_key("update_user", payload)
    assert key_diff_op != key1

    # Different payload should produce different key
    key_diff_payload = store.generate_key(operation, {"email": "other@example.com"})
    assert key_diff_payload != key1


@test("IdempotencyStore stores and retrieves keys")
def test_store_and_retrieve_keys():
    """Test storing and retrieving idempotency keys with results."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        uow = UnitOfWork(db_path)

        with uow:
            operation = "create_user"
            payload = {"email": "test@example.com", "name": "Test User"}
            result = {"user_id": "123", "status": "created"}

            # Generate key
            key = uow.generate_idempotency_key(operation, payload)

            # Should not exist initially
            existing = uow.check_idempotency(key)
            assert existing is None, "Key should not exist initially"

            # Store the key with result
            record = uow.store_idempotency_key(
                key=key,
                operation=operation,
                payload=payload,
                result=result,
                request_id="req_123",
                actor_id="user_456",
            )

            assert record.key == key
            assert record.operation == operation
            assert record.result == result
            assert record.request_id == "req_123"
            assert record.actor_id == "user_456"

            # Should be able to retrieve it
            retrieved = uow.check_idempotency(key)
            assert retrieved is not None
            assert retrieved.key == key
            assert retrieved.operation == operation
            assert retrieved.result == result

    finally:
        safe_cleanup_db(db_path, tmp_file)


@test("IdempotencyStore handles TTL expiration")
def test_ttl_expiration():
    """Test TTL-based expiration of idempotency keys."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        uow = UnitOfWork(db_path)

        with uow:
            operation = "create_user"
            payload = {"email": "test@example.com", "name": "Test User"}

            # Generate and store key with very short TTL
            key = uow.generate_idempotency_key(operation, payload)
            uow.store_idempotency_key(
                key=key,
                operation=operation,
                payload=payload,
                result={"user_id": "123"},
                ttl=1,  # 1 second TTL
            )

            # Should exist immediately
            assert uow.check_idempotency(key) is not None

            # Wait for expiration
            time.sleep(1.1)

            # Should be expired and return None
            assert uow.check_idempotency(key) is None

    finally:
        safe_cleanup_db(db_path, tmp_file)


@test("IdempotencyStore cleanup expired keys")
def test_cleanup_expired_keys():
    """Test cleanup of expired keys."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        uow = UnitOfWork(db_path)

        with uow:
            # Create multiple keys with different TTLs
            keys: list[str] = []
            for i in range(5):
                operation = f"operation_{i}"
                payload = {"data": f"test_{i}"}
                key = uow.generate_idempotency_key(operation, payload)
                keys.append(key)

                # First 3 with short TTL, last 2 with long TTL
                ttl = 1 if i < 3 else 3600
                uow.store_idempotency_key(
                    key=key,
                    operation=operation,
                    payload=payload,
                    result={"result": i},
                    ttl=ttl,
                )

            # All should exist initially
            for key in keys:
                assert uow.check_idempotency(key) is not None

            # Wait for first 3 to expire
            time.sleep(1.1)

            # Clean up expired keys through UoW idempotency store
            if uow._idempotency_store:
                removed_count = uow._idempotency_store.cleanup_expired()
                assert (
                    removed_count >= 3
                ), f"Should remove at least 3 expired keys, got {removed_count}"

            # First 3 should be gone, last 2 should remain
            for i, key in enumerate(keys):
                if i < 3:
                    assert uow.check_idempotency(key) is None
                else:
                    assert uow.check_idempotency(key) is not None

    finally:
        safe_cleanup_db(db_path, tmp_file)


@test("UnitOfWork idempotency key generation")
def test_uow_key_generation():
    """Test UnitOfWork idempotency key generation."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        uow = UnitOfWork(db_path)

        with uow:
            operation = "create_user"
            payload = {"email": "test@example.com", "name": "Test User"}

            # Generate keys multiple times
            key1 = uow.generate_idempotency_key(operation, payload)
            key2 = uow.generate_idempotency_key(operation, payload)

            # Should be deterministic
            assert key1 == key2
            assert len(key1) == 64, "Key should be SHA256 hash"

    finally:
        safe_cleanup_db(db_path, tmp_file)


@test("UnitOfWork idempotency checking and storage")
def test_uow_idempotency_checking():
    """Test UnitOfWork idempotency checking and storage."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    try:
        uow = UnitOfWork(db_path)

        with uow:
            operation = "create_user"
            payload = {"email": "test@example.com", "name": "Test User"}
            result = {"user_id": "123", "status": "created"}

            # Generate key
            key = uow.generate_idempotency_key(operation, payload)

            # Should not exist initially
            assert uow.check_idempotency(key) is None

            # Store the key
            record = uow.store_idempotency_key(
                key=key,
                operation=operation,
                payload=payload,
                result=result,
                request_id="req_123",
                actor_id="user_456",
            )

            assert record.key == key
            assert record.result == result

            # Should be able to retrieve it
            retrieved = uow.check_idempotency(key)
            assert retrieved is not None
            assert retrieved.key == key
            assert retrieved.result == result

    finally:
        safe_cleanup_db(db_path, tmp_file)


@test("UnitOfWork execute_idempotent - simple test")
def test_uow_execute_idempotent_simple():
    """Test UnitOfWork execute_idempotent basic functionality."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    execution_count = 0

    def test_operation() -> Dict[str, Any]:
        nonlocal execution_count
        execution_count += 1
        return {"user_id": "123", "status": "created", "execution": execution_count}

    try:
        uow = UnitOfWork(db_path)

        with uow:
            operation = "create_user"
            payload = {"email": "test@example.com", "name": "Test User"}

            result = uow.execute_idempotent(
                operation=operation,
                payload=payload,
                operation_func=test_operation,
                request_id="req_123",
                actor_id="user_456",
            )

            # Should execute and return result
            assert result["result"]["execution"] == 1
            assert result["was_duplicate"] is False
            assert result["idempotency_key"] is not None
            assert execution_count == 1, "Operation should be executed once"

    finally:
        safe_cleanup_db(db_path, tmp_file)


@test("UnitOfWork execute_idempotent - duplicate detection")
def test_uow_execute_idempotent_duplicate():
    """Test UnitOfWork execute_idempotent duplicate detection."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    execution_count = 0

    def test_operation() -> Dict[str, Any]:
        nonlocal execution_count
        execution_count += 1
        return {"user_id": "123", "status": "created", "execution": execution_count}

    try:
        operation = "create_user"
        payload = {"email": "test@example.com", "name": "Test User"}

        # First execution
        uow1 = UnitOfWork(db_path)
        with uow1:
            result1 = uow1.execute_idempotent(
                operation=operation, payload=payload, operation_func=test_operation
            )

        # Second execution with same operation and payload
        uow2 = UnitOfWork(db_path)
        with uow2:
            result2 = uow2.execute_idempotent(
                operation=operation, payload=payload, operation_func=test_operation
            )

        # First should execute, second should be duplicate
        assert result1["was_duplicate"] is False
        assert result2["was_duplicate"] is True
        assert result1["result"] == result2["result"]  # Same cached result
        assert execution_count == 1, "Operation should only be executed once"

    finally:
        safe_cleanup_db(db_path, tmp_file)

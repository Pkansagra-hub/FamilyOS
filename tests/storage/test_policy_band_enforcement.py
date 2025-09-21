"""Tests for policy band enforcement in BaseStore."""

import tempfile
from pathlib import Path

from ward import raises, test

from storage.policy_enforcement import PolicyViolation
from storage.sqlite_util import create_optimized_connection

# Import TestStore from the base_store test module
from tests.storage.test_base_store import TestStore


@test("Policy band GREEN allows all operations")
def test_green_band_allows_operations():
    """Test that GREEN band allows all write operations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        store = TestStore("test")
        conn = create_optimized_connection(db_path)

        store.begin_transaction(conn)

        # GREEN band context
        context = {"policy_band": "GREEN", "operation": "CREATE"}
        data = {"name": "test_item", "value": 42}

        # Should not raise any exception
        record = store.create(data, context)
        assert record["name"] == "test_item"

        # Update should also work
        update_context = {"policy_band": "GREEN", "operation": "UPDATE"}
        updated = store.update(record["id"], {"value": 84}, update_context)
        assert updated["value"] == 84

        # Delete should also work
        delete_context = {"policy_band": "GREEN", "operation": "DELETE"}
        deleted = store.delete(record["id"], delete_context)
        assert deleted is True

        store.commit_transaction(conn)
        conn.close()
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("Policy band AMBER allows operations")
def test_amber_band_allows_operations():
    """Test that AMBER band allows write operations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        store = TestStore("test")
        conn = create_optimized_connection(db_path)

        store.begin_transaction(conn)

        # AMBER band context
        context = {"policy_band": "AMBER", "operation": "CREATE"}
        data = {"name": "test_item", "value": 42}

        # Should not raise any exception
        record = store.create(data, context)
        assert record["name"] == "test_item"

        store.commit_transaction(conn)
        conn.close()
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("Policy band RED requires override token")
def test_red_band_requires_override():
    """Test that RED band requires override token for operations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        store = TestStore("test")
        conn = create_optimized_connection(db_path)

        store.begin_transaction(conn)

        # RED band without override token
        context = {"policy_band": "RED", "operation": "CREATE"}
        data = {"name": "test_item", "value": 42}

        # Should raise PolicyViolation
        with raises(PolicyViolation) as exc_info:
            store.create(data, context)

        assert exc_info.raised.band == "RED"
        # The new policy system uses configured messages or fallback
        error_msg = str(exc_info.raised)
        assert "RED band" in error_msg and (
            "writes prohibited" in error_msg or "override token" in error_msg
        )

        # RED band with override token should work
        context_with_override = {
            "policy_band": "RED",
            "operation": "CREATE",
            "override_token": "valid_token",
        }

        # Should not raise any exception
        record = store.create(data, context_with_override)
        assert record["name"] == "test_item"

        store.commit_transaction(conn)
        conn.close()
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("Policy band BLACK prohibits all operations")
def test_black_band_prohibits_operations():
    """Test that BLACK band prohibits all write operations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        store = TestStore("test")
        conn = create_optimized_connection(db_path)

        store.begin_transaction(conn)

        # BLACK band context
        context = {"policy_band": "BLACK", "operation": "CREATE"}
        data = {"name": "test_item", "value": 42}

        # Should raise PolicyViolation
        with raises(PolicyViolation) as exc_info:
            store.create(data, context)

        assert exc_info.raised.band == "BLACK"
        assert "writes prohibited" in str(exc_info.raised)

        # Even with override token, BLACK band should still be blocked
        context_with_override = {
            "policy_band": "BLACK",
            "operation": "CREATE",
            "override_token": "valid_token",
        }

        with raises(PolicyViolation):
            store.create(data, context_with_override)

        store.commit_transaction(conn)
        conn.close()
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("Policy band enforcement works for update and delete operations")
def test_band_enforcement_update_delete():
    """Test that policy band enforcement works for update and delete operations."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        store = TestStore("test")
        conn = create_optimized_connection(db_path)

        store.begin_transaction(conn)

        # First create a record with GREEN band
        green_context = {"policy_band": "GREEN", "operation": "CREATE"}
        data = {"name": "test_item", "value": 42}
        record = store.create(data, green_context)
        record_id = record["id"]

        # Try to update with BLACK band - should fail
        black_update_context = {"policy_band": "BLACK", "operation": "UPDATE"}
        with raises(PolicyViolation):
            store.update(record_id, {"value": 84}, black_update_context)

        # Try to delete with RED band without override - should fail
        red_delete_context = {"policy_band": "RED", "operation": "DELETE"}
        with raises(PolicyViolation):
            store.delete(record_id, red_delete_context)

        # Delete with RED band and override should work
        red_delete_with_override = {
            "policy_band": "RED",
            "operation": "DELETE",
            "override_token": "valid_token",
        }
        deleted = store.delete(record_id, red_delete_with_override)
        assert deleted is True

        store.commit_transaction(conn)
        conn.close()
    finally:
        Path(db_path).unlink(missing_ok=True)


@test("Operations without context work normally")
def test_operations_without_context():
    """Test that operations without policy context work normally."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        store = TestStore("test")
        conn = create_optimized_connection(db_path)

        store.begin_transaction(conn)

        # Operations without context should work normally
        data = {"name": "test_item", "value": 42}
        record = store.create(data)  # No context provided
        assert record["name"] == "test_item"

        updated = store.update(record["id"], {"value": 84})  # No context
        assert updated["value"] == 84

        deleted = store.delete(record["id"])  # No context
        assert deleted is True

        store.commit_transaction(conn)
        conn.close()
    finally:
        Path(db_path).unlink(missing_ok=True)

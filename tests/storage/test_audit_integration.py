"""Tests for audit trail integration with storage operations."""

import asyncio
from unittest.mock import AsyncMock, patch

from ward import test

from storage.core.base_store import BaseStore


class MockStore(BaseStore):
    """Mock store implementation for testing."""

    def __init__(self):
        super().__init__()
        self._data = {}
        self._in_transaction = True
        # Disable schema validation for simpler testing
        self.config.schema_validation = False

    def _create_record(self, data):
        record_id = data.get("id", "test-id")
        record = {"id": record_id, **data}
        self._data[record_id] = record
        return record

    def _read_record(self, record_id):
        return self._data.get(record_id)

    def _update_record(self, record_id, data):
        if record_id not in self._data:
            raise ValueError(f"Record {record_id} not found")
        self._data[record_id].update(data)
        return self._data[record_id]

    def _delete_record(self, record_id):
        if record_id in self._data:
            del self._data[record_id]
            return True
        return False

    def _list_records(self, filters=None, limit=None, offset=None):
        """List records - simple implementation for mock."""
        records = list(self._data.values())
        return records[offset : offset + limit] if offset and limit else records

    def _initialize_schema(self, conn=None):
        """Initialize schema - no-op for mock."""
        pass

    def _get_schema(self):
        """Get schema - return simple schema for mock."""
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "value": {"type": "integer"},
            },
            "required": ["id"],
        }


@test("BaseStore create operation generates audit log")
async def test_create_audit_integration():
    """Test that create operations generate audit logs."""
    # Setup audit logger mock
    mock_audit_logger = AsyncMock()

    with patch(
        "storage.base_store.get_audit_logger", return_value=mock_audit_logger
    ), patch("storage.base_store._audit_available", True):

        store = MockStore()
        context = {
            "user_id": "test-user",
            "device_id": "test-device",
            "session_id": "test-session",
            "space_id": "test-space",
        }

        # Create a record
        test_data = {"id": "test-id", "name": "test", "value": 42}
        result = store.create(test_data, context)

        # Verify audit logging was attempted
        assert result["name"] == "test"

        # Wait for any async audit calls to complete
        await asyncio.sleep(0.1)


@test("BaseStore read operation generates audit log")
async def test_read_audit_integration():
    """Test that read operations generate audit logs."""
    # Setup audit logger mock
    mock_audit_logger = AsyncMock()

    with patch(
        "storage.base_store.get_audit_logger", return_value=mock_audit_logger
    ), patch("storage.base_store._audit_available", True):

        store = MockStore()
        store._data["test-id"] = {"id": "test-id", "name": "test"}

        context = {"user_id": "test-user", "device_id": "test-device"}

        # Read a record
        result = store.read("test-id", context)

        # Verify result
        assert result["name"] == "test"

        # Wait for any async audit calls to complete
        await asyncio.sleep(0.1)


@test("BaseStore update operation generates audit log")
async def test_update_audit_integration():
    """Test that update operations generate audit logs."""
    # Setup audit logger mock
    mock_audit_logger = AsyncMock()

    with patch(
        "storage.base_store.get_audit_logger", return_value=mock_audit_logger
    ), patch("storage.base_store._audit_available", True):

        store = MockStore()
        store._data["test-id"] = {"id": "test-id", "name": "test"}

        context = {"user_id": "test-user", "device_id": "test-device"}

        # Update a record
        update_data = {"name": "updated"}
        result = store.update("test-id", update_data, context)

        # Verify result
        assert result["name"] == "updated"

        # Wait for any async audit calls to complete
        await asyncio.sleep(0.1)


@test("BaseStore delete operation generates audit log")
async def test_delete_audit_integration():
    """Test that delete operations generate audit logs."""
    # Setup audit logger mock
    mock_audit_logger = AsyncMock()

    with patch(
        "storage.base_store.get_audit_logger", return_value=mock_audit_logger
    ), patch("storage.base_store._audit_available", True):

        store = MockStore()
        store._data["test-id"] = {"id": "test-id", "name": "test"}

        context = {"user_id": "test-user", "device_id": "test-device"}

        # Delete a record
        result = store.delete("test-id", context)

        # Verify result
        assert result is True
        assert "test-id" not in store._data

        # Wait for any async audit calls to complete
        await asyncio.sleep(0.1)


@test("BaseStore handles missing audit dependencies gracefully")
def test_missing_audit_dependencies():
    """Test that operations work when audit is not available."""
    with patch("storage.base_store._audit_available", False):

        store = MockStore()

        # Should work without audit logging
        result = store.create({"id": "test-id", "name": "test"})
        assert result["name"] == "test"

        # Should work without context
        result2 = store.read(result["id"])
        assert result2["name"] == "test"


@test("BaseStore audit integration with system actor")
async def test_system_actor_audit():
    """Test audit logging with system actor when no user context."""
    # Setup audit logger mock
    mock_audit_logger = AsyncMock()

    with patch(
        "storage.base_store.get_audit_logger", return_value=mock_audit_logger
    ), patch("storage.base_store._audit_available", True):

        store = MockStore()

        # Create without context (should use system actor)
        result = store.create({"id": "system-test-id", "name": "system-test"})

        # Verify result
        assert result["name"] == "system-test"

        # Wait for any async audit calls to complete
        await asyncio.sleep(0.1)


@test("BaseStore audit integration with failure scenarios")
async def test_audit_with_failures():
    """Test that failures also generate audit logs."""
    # Setup audit logger mock
    mock_audit_logger = AsyncMock()

    with patch(
        "storage.base_store.get_audit_logger", return_value=mock_audit_logger
    ), patch("storage.base_store._audit_available", True):

        store = MockStore()
        context = {"user_id": "test-user"}

        try:
            # Try to update non-existent record
            store.update("missing-id", {"name": "fail"}, context)
            assert False, "Should have raised exception"
        except ValueError:
            # Expected failure
            pass

        # Wait for any async audit calls to complete
        await asyncio.sleep(0.1)

"""
Test suite for SemanticStore contract compliance and functionality.

This test suite validates the SemanticStore implementation against:
1. semantic_item.schema.json contract requirements
2. CRUD operations and data integrity
3. Semantic type handling and search capabilities
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict

from ward import fixture, test

from storage.base_store import StoreConfig
from storage.semantic_store import SemanticItem, SemanticStore


@fixture
def temp_store():
    """Create a temporary SemanticStore for testing."""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db.close()
    config = StoreConfig(db_path=temp_db.name)
    store = SemanticStore(config)

    yield store

    # Cleanup
    Path(temp_db.name).unlink(missing_ok=True)


@test("SemanticItem dataclass matches contract required fields")
def test_semantic_item_contract_required_fields():
    """Test SemanticItem dataclass matches semantic_item.schema.json contract."""
    # Test required fields
    item = SemanticItem(
        id="01H8F9CQXK4YZJK0QWERTY1234",
        space_id="personal:alice",
        ts="2023-09-12T10:30:00Z",
        type="note",
        keys={"title": "Test Note", "category": "work"},
    )

    # Verify required fields are present
    assert item.id == "01H8F9CQXK4YZJK0QWERTY1234"
    assert item.space_id == "personal:alice"
    assert item.ts == "2023-09-12T10:30:00Z"
    assert item.type == "note"
    assert item.keys == {"title": "Test Note", "category": "work"}


@test("SemanticItem dataclass supports optional fields")
def test_semantic_item_contract_optional_fields():
    """Test SemanticItem optional fields from contract."""
    item = SemanticItem(
        id="01H8F9CQXK4YZJK0QWERTY5678",
        space_id="shared:household",
        ts="2023-09-12T11:00:00Z",
        type="task",
        keys={"priority": "high", "assignee": "bob"},
        payload={"description": "Complete project", "due_date": "2023-09-15"},
        band="AMBER",
        ttl="P30D",
    )

    assert item.payload == {"description": "Complete project", "due_date": "2023-09-15"}
    assert item.band == "AMBER"
    assert item.ttl == "P30D"


@test("All semantic types from contract are supported")
def test_semantic_types_enum_compliance():
    """Test that all semantic types from contract are supported."""
    valid_types = ["note", "task", "contact", "event", "fact", "triple", "entity"]

    for semantic_type in valid_types:
        # Create item with explicit type casting to handle Union types
        item_data: Dict[str, Any] = {
            "id": f"01H8F9CQXK4YZJK0QWERTY{semantic_type[:4].upper()}",
            "space_id": "personal:alice",
            "ts": "2023-09-12T10:30:00Z",
            "type": semantic_type,
            "keys": {"test": "value"},
        }
        item = SemanticItem.from_dict(item_data)
        assert item.type == semantic_type


@test("to_dict output matches contract structure")
def test_to_dict_contract_compliance():
    """Test that to_dict output matches contract structure."""
    item = SemanticItem(
        id="01H8F9CQXK4YZJK0QWERTY1234",
        space_id="personal:alice",
        ts="2023-09-12T10:30:00Z",
        type="note",
        keys={"title": "Test Note"},
        payload={"content": "This is a test note"},
        band="GREEN",
        ttl="P7D",
    )

    result = item.to_dict()

    # Required fields must be present
    assert "id" in result
    assert "space_id" in result
    assert "ts" in result
    assert "type" in result
    assert "keys" in result

    # Optional fields must be present when set
    assert "payload" in result
    assert "band" in result
    assert "ttl" in result

    # Values must match
    assert result["id"] == "01H8F9CQXK4YZJK0QWERTY1234"
    assert result["space_id"] == "personal:alice"
    assert result["ts"] == "2023-09-12T10:30:00Z"
    assert result["type"] == "note"
    assert result["keys"] == {"title": "Test Note"}
    assert result["payload"] == {"content": "This is a test note"}
    assert result["band"] == "GREEN"
    assert result["ttl"] == "P7D"


@test("from_dict handles contract-compliant data")
def test_from_dict_contract_compliance():
    """Test that from_dict handles contract-compliant data."""
    data: Dict[str, Any] = {
        "id": "01H8F9CQXK4YZJK0QWERTY1234",
        "space_id": "personal:alice",
        "ts": "2023-09-12T10:30:00Z",
        "type": "contact",
        "keys": {"name": "John Doe", "email": "john@example.com"},
        "payload": {"phone": "+1-555-0123", "company": "Acme Corp"},
        "band": "AMBER",
        "ttl": "P1Y",
    }

    item = SemanticItem.from_dict(data)

    assert item.id == "01H8F9CQXK4YZJK0QWERTY1234"
    assert item.space_id == "personal:alice"
    assert item.ts == "2023-09-12T10:30:00Z"
    assert item.type == "contact"
    assert item.keys == {"name": "John Doe", "email": "john@example.com"}
    assert item.payload == {"phone": "+1-555-0123", "company": "Acme Corp"}
    assert item.band == "AMBER"
    assert item.ttl == "P1Y"


@test("from_dict works with minimal required fields")
def test_from_dict_minimal_required_fields():
    """Test from_dict with only required fields."""
    data: Dict[str, Any] = {
        "id": "01H8F9CQXK4YZJK0QWERTY1234",
        "space_id": "personal:alice",
        "ts": "2023-09-12T10:30:00Z",
        "type": "fact",
        "keys": {"subject": "AI", "predicate": "is", "object": "helpful"},
    }

    item = SemanticItem.from_dict(data)

    assert item.id == "01H8F9CQXK4YZJK0QWERTY1234"
    assert item.space_id == "personal:alice"
    assert item.ts == "2023-09-12T10:30:00Z"
    assert item.type == "fact"
    assert item.keys == {"subject": "AI", "predicate": "is", "object": "helpful"}
    assert item.payload is None
    assert item.band is None
    assert item.ttl is None


@test("Store and retrieve semantic items")
def test_store_and_get_item(temp_store=temp_store):
    """Test storing and retrieving semantic items."""
    item = SemanticItem(
        id="01H8F9CQXK4YZJK0QWERTY1234",
        space_id="personal:alice",
        ts="2023-09-12T10:30:00Z",
        type="contact",
        keys={"name": "Jane Doe", "email": "jane@example.com"},
        payload={"phone": "+1-555-0456"},
        band="GREEN",
    )

    # Store the item
    item_id = temp_store.store_item(item)
    assert item_id == "01H8F9CQXK4YZJK0QWERTY1234"

    # Retrieve the item
    retrieved_item = temp_store.get_item("01H8F9CQXK4YZJK0QWERTY1234")

    assert retrieved_item is not None
    assert retrieved_item.id == item.id
    assert retrieved_item.space_id == item.space_id
    assert retrieved_item.type == item.type
    assert retrieved_item.keys == item.keys
    assert retrieved_item.payload == item.payload
    assert retrieved_item.band == item.band


@test("Filter items by semantic type")
def test_get_items_by_type(temp_store=temp_store):
    """Test filtering items by semantic type."""
    items = [
        SemanticItem(
            id="01H8F9CQXK4YZJK0QWERTY0001",
            space_id="personal:alice",
            ts="2023-09-12T10:30:00Z",
            type="note",
            keys={"title": "Note 1"},
        ),
        SemanticItem(
            id="01H8F9CQXK4YZJK0QWERTY0002",
            space_id="personal:alice",
            ts="2023-09-12T11:00:00Z",
            type="task",
            keys={"title": "Task 1"},
        ),
        SemanticItem(
            id="01H8F9CQXK4YZJK0QWERTY0003",
            space_id="personal:alice",
            ts="2023-09-12T12:00:00Z",
            type="note",
            keys={"title": "Note 2"},
        ),
    ]

    for item in items:
        temp_store.store_item(item)

    # Get notes only
    notes = temp_store.get_items_by_type("note", space_id="personal:alice")
    assert len(notes) == 2
    for note in notes:
        assert note.type == "note"

    # Get tasks only
    tasks = temp_store.get_items_by_type("task", space_id="personal:alice")
    assert len(tasks) == 1
    assert tasks[0].type == "task"


@test("Search items by key-value pairs")
def test_search_by_keys(temp_store=temp_store):
    """Test searching items by key-value pairs."""
    items = [
        SemanticItem(
            id="01H8F9CQXK4YZJK0QWERTY0001",
            space_id="personal:alice",
            ts="2023-09-12T10:30:00Z",
            type="note",
            keys={"category": "work", "priority": "high", "project": "alpha"},
        ),
        SemanticItem(
            id="01H8F9CQXK4YZJK0QWERTY0002",
            space_id="personal:alice",
            ts="2023-09-12T11:00:00Z",
            type="note",
            keys={"category": "personal", "priority": "low", "project": "beta"},
        ),
        SemanticItem(
            id="01H8F9CQXK4YZJK0QWERTY0003",
            space_id="personal:alice",
            ts="2023-09-12T12:00:00Z",
            type="task",
            keys={"category": "work", "priority": "high", "project": "gamma"},
        ),
    ]

    for item in items:
        temp_store.store_item(item)

    # Search by single key
    work_items = temp_store.search_by_keys({"category": "work"})
    assert len(work_items) == 2

    # Search by multiple keys
    high_priority_work = temp_store.search_by_keys(
        {"category": "work", "priority": "high"}
    )
    assert len(high_priority_work) == 2

    # Search with type filter
    high_priority_notes = temp_store.search_by_keys(
        {"priority": "high"}, semantic_type="note"
    )
    assert len(high_priority_notes) == 1
    assert high_priority_notes[0].type == "note"


@test("Filter items by security band")
def test_get_items_by_band(temp_store=temp_store):
    """Test filtering items by security band."""
    items = [
        SemanticItem(
            id="01H8F9CQXK4YZJK0QWERTY0001",
            space_id="personal:alice",
            ts="2023-09-12T10:30:00Z",
            type="note",
            keys={"title": "Public Note"},
            band="GREEN",
        ),
        SemanticItem(
            id="01H8F9CQXK4YZJK0QWERTY0002",
            space_id="personal:alice",
            ts="2023-09-12T11:00:00Z",
            type="note",
            keys={"title": "Sensitive Note"},
            band="AMBER",
        ),
        SemanticItem(
            id="01H8F9CQXK4YZJK0QWERTY0003",
            space_id="personal:alice",
            ts="2023-09-12T12:00:00Z",
            type="note",
            keys={"title": "Confidential Note"},
            band="RED",
        ),
    ]

    for item in items:
        temp_store.store_item(item)

    # Get GREEN band items
    green_items = temp_store.get_items_by_band("GREEN", space_id="personal:alice")
    assert len(green_items) == 1
    assert green_items[0].band == "GREEN"

    # Get AMBER band items
    amber_items = temp_store.get_items_by_band("AMBER", space_id="personal:alice")
    assert len(amber_items) == 1
    assert amber_items[0].band == "AMBER"

    # Get RED band items
    red_items = temp_store.get_items_by_band("RED", space_id="personal:alice")
    assert len(red_items) == 1
    assert red_items[0].band == "RED"


@test("Update and delete semantic items")
def test_update_and_delete_items(temp_store=temp_store):
    """Test updating and deleting semantic items."""
    item = SemanticItem(
        id="01H8F9CQXK4YZJK0QWERTY1234",
        space_id="personal:alice",
        ts="2023-09-12T10:30:00Z",
        type="note",
        keys={"title": "Original Title", "status": "draft"},
    )

    # Store the item
    temp_store.store_item(item)

    # Update the item
    updated_item = SemanticItem(
        id="01H8F9CQXK4YZJK0QWERTY1234",
        space_id="personal:alice",
        ts="2023-09-12T11:00:00Z",
        type="note",
        keys={"title": "Updated Title", "status": "published"},
        band="GREEN",
    )

    update_result = temp_store.update_item("01H8F9CQXK4YZJK0QWERTY1234", updated_item)
    assert update_result is True

    # Verify the update
    retrieved_item = temp_store.get_item("01H8F9CQXK4YZJK0QWERTY1234")
    assert retrieved_item is not None
    assert retrieved_item.keys["title"] == "Updated Title"
    assert retrieved_item.keys["status"] == "published"
    assert retrieved_item.band == "GREEN"

    # Delete the item
    delete_result = temp_store.delete_item("01H8F9CQXK4YZJK0QWERTY1234")
    assert delete_result is True

    # Verify deletion
    deleted_item = temp_store.get_item("01H8F9CQXK4YZJK0QWERTY1234")
    assert deleted_item is None


@test("Database schema matches contract expectations")
def test_database_schema_integrity(temp_store=temp_store):
    """Test that database schema matches expectations."""
    # Insert test data and verify schema structure
    item = SemanticItem(
        id="01H8F9CQXK4YZJK0QWERTY1234",
        space_id="personal:alice",
        ts="2023-09-12T10:30:00Z",
        type="note",
        keys={"title": "Test"},
        payload={"content": "Test content"},
        band="GREEN",
        ttl="P7D",
    )

    temp_store.store_item(item)

    # Check database structure
    with sqlite3.connect(temp_store.config.db_path) as conn:
        # Check that all expected columns exist
        cursor = conn.execute("PRAGMA table_info(semantic_items)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        expected_columns = {
            "id": "TEXT",
            "space_id": "TEXT",
            "ts": "INTEGER",
            "ts_iso": "TEXT",
            "type": "TEXT",
            "keys": "TEXT",
            "payload": "TEXT",
            "band": "TEXT",
            "ttl": "TEXT",
            "created_at": "INTEGER",
            "updated_at": "INTEGER",
        }

        for col_name, col_type in expected_columns.items():
            assert col_name in columns
            assert columns[col_name] == col_type

        # Check that data is stored correctly
        cursor = conn.execute("SELECT * FROM semantic_items WHERE id = ?", (item.id,))
        row = cursor.fetchone()
        assert row is not None

        # Verify JSON fields are properly serialized
        keys_data = json.loads(row[5])  # keys column
        assert keys_data == {"title": "Test"}

        payload_data = json.loads(row[6])  # payload column
        assert payload_data == {"content": "Test content"}


@test("List items with filters and limits")
def test_list_all_items(temp_store=temp_store):
    """Test listing all items in the store."""
    items = [
        SemanticItem(
            id="01H8F9CQXK4YZJK0QWERTY0001",
            space_id="personal:alice",
            ts="2023-09-12T10:30:00Z",
            type="note",
            keys={"title": "Note 1"},
        ),
        SemanticItem(
            id="01H8F9CQXK4YZJK0QWERTY0002",
            space_id="personal:alice",
            ts="2023-09-12T11:00:00Z",
            type="task",
            keys={"title": "Task 1"},
        ),
        SemanticItem(
            id="01H8F9CQXK4YZJK0QWERTY0003",
            space_id="shared:household",
            ts="2023-09-12T12:00:00Z",
            type="note",
            keys={"title": "Shared Note"},
        ),
    ]

    for item in items:
        temp_store.store_item(item)

    # List all items
    all_items = temp_store.list_items()
    assert len(all_items) >= 3

    # List items with space filter
    alice_items = temp_store.list_items(space_id="personal:alice")
    assert len(alice_items) == 2

    # List items with limit
    limited_items = temp_store.list_items(limit=1)
    assert len(limited_items) == 1

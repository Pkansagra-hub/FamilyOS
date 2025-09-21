"""
Comprehensive tests for Epic 2.1 Issue 2.1.2 - Sequence Management.

Tests that the EpisodicStore sequence management implementation exactly follows:
- contracts/storage/schemas/episodic_sequence.schema.json

Epic 2.1 Issue 2.1.2: Sequence Store Implementation

This validates all sequence management methods and contract compliance.
"""

import os
# Add parent directory to path for imports
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from storage.base_store import StoreConfig
from storage.episodic_store import (EpisodicRecord, EpisodicSequence,
                                    EpisodicStore)


def generate_ulid() -> str:
    """Generate a simple ULID-like ID for testing."""
    import random
    import string
    import time

    # Simple ULID-like format: timestamp + random
    timestamp = int(time.time() * 1000)
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    return f"{timestamp:013d}{random_part}"


"""
Comprehensive tests for Epic 2.1 Issue 2.1.2 - Sequence Management.

Tests that the EpisodicStore sequence management implementation exactly follows:
- contracts/storage/schemas/episodic_sequence.schema.json

Epic 2.1 Issue 2.1.2: Sequence Store Implementation

This validates all sequence management methods and contract compliance.
"""

import os
# Add parent directory to path for imports
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))



def generate_ulid() -> str:
    """Generate a simple ULID-like ID for testing."""
    import random
    import string
    import time

    # Simple ULID-like format: timestamp + random
    timestamp = int(time.time() * 1000)
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    return f"{timestamp:013d}{random_part}"


def test_sequence_creation_and_retrieval():
    """Test creating and retrieving episodic sequences."""
    print("\nTesting sequence creation and retrieval...")

    with tempfile.TemporaryDirectory() as temp_dir:
        config = StoreConfig(db_path=f"{temp_dir}/test_sequence.db")
        store = EpisodicStore(config)

        # Create a test sequence
        sequence_id = generate_ulid()
        space_id = "space_test_001"
        ts = datetime.fromisoformat("2024-01-01T10:00:00")

        test_sequence = EpisodicSequence(
            sequence_id=sequence_id,
            space_id=space_id,
            ts=ts,
            label="Test Sequence",
            items=[
                {"id": generate_ulid(), "ts": ts},
                {"id": generate_ulid(), "ts": ts, "weight": 0.8}
            ],
            closed=False
        )

        # Create the sequence (using store transaction)
        with store:
            created_id = store.create_sequence(test_sequence)
            assert created_id == sequence_id, f"Expected {sequence_id}, got {created_id}"

            # Retrieve the sequence
            retrieved = store.get_sequence(sequence_id)
            assert retrieved is not None, "Sequence should be retrievable"
            assert retrieved.sequence_id == sequence_id
            assert retrieved.space_id == space_id
            assert retrieved.label == "Test Sequence"
            assert len(retrieved.items) == 2
            assert not retrieved.closed

            # Test items structure
            assert retrieved.items[0]["id"] == test_sequence.items[0]["id"]
            assert retrieved.items[1]["weight"] == 0.8

        print("✅ Sequence creation and retrieval passed")


def test_sequence_contract_compliance():
    """Test that sequences follow episodic_sequence.schema.json exactly."""
    print("\nTesting EpisodicSequence contract compliance...")

    # Test required fields
    sequence_id = generate_ulid()
    space_id = "space_test_001"
    ts = datetime.fromisoformat("2024-01-01T10:00:00")

    # Valid sequence with required fields only
    minimal_sequence = EpisodicSequence(
        sequence_id=sequence_id,
        space_id=space_id,
        ts=ts,
        items=[]
    )

    sequence_dict = minimal_sequence.to_dict()

    # Verify required fields
    required_fields = ["sequence_id", "space_id", "items", "ts"]
    for field in required_fields:
        assert field in sequence_dict, f"Required field {field} missing"

    # Verify ULID format for sequence_id (basic check)
    assert len(sequence_dict["sequence_id"]) == 26, "sequence_id should be ULID format"

    # Verify space_id pattern (basic check)
    assert sequence_dict["space_id"].startswith("space_"), "space_id should follow pattern"

    # Verify items is array
    assert isinstance(sequence_dict["items"], list), "items should be array"

    # Test sequence with all fields
    full_sequence = EpisodicSequence(
        sequence_id=generate_ulid(),
        space_id="space_test_002",
        ts=ts,
        label="Full Test Sequence",
        items=[
            {"id": generate_ulid(), "ts": ts, "weight": 1.0},
            {"id": generate_ulid(), "ts": ts}
        ],
        closed=True
    )

    full_dict = full_sequence.to_dict()

    # Verify optional fields
    assert "label" in full_dict
    assert "closed" in full_dict
    assert full_dict["closed"] is True

    # Verify items structure
    for item in full_dict["items"]:
        assert "id" in item, "Item must have id"
        assert "ts" in item, "Item must have ts"
        assert len(item["id"]) == 26, "Item id should be ULID"

    # Test round-trip conversion
    reconstructed = EpisodicSequence.from_dict(full_dict)
    assert reconstructed.sequence_id == full_sequence.sequence_id
    assert reconstructed.label == full_sequence.label
    assert reconstructed.closed == full_sequence.closed
    assert len(reconstructed.items) == len(full_sequence.items)

    print("✅ EpisodicSequence contract compliance passed")


def test_sequence_update_and_delete():
    """Test updating and deleting episodic sequences."""
    print("\nTesting sequence update and delete...")

    with tempfile.TemporaryDirectory() as temp_dir:
        config = StoreConfig(db_path=f"{temp_dir}/test_sequence_update.db")
        store = EpisodicStore(config)

        # Create a test sequence
        sequence_id = generate_ulid()
        space_id = "space_test_001"
        ts = datetime.fromisoformat("2024-01-01T10:00:00")

        original_sequence = EpisodicSequence(
            sequence_id=sequence_id,
            space_id=space_id,
            ts=ts,
            label="Original Sequence",
            items=[{"id": generate_ulid(), "ts": ts}],
            closed=False
        )

        with store:
            store.create_sequence(original_sequence)

            # Update the sequence
            updated_sequence = EpisodicSequence(
                sequence_id=sequence_id,
                space_id=space_id,
                ts=ts,
                label="Updated Sequence",
                items=[
                    {"id": generate_ulid(), "ts": ts},
                    {"id": generate_ulid(), "ts": ts}
                ],
                closed=True
            )

            update_result = store.update_sequence(updated_sequence)
            assert update_result is True, "Update should succeed"

            # Verify the update
            retrieved = store.get_sequence(sequence_id)
            assert retrieved is not None
            assert retrieved.label == "Updated Sequence"
            assert len(retrieved.items) == 2
            assert retrieved.closed is True

            # Test updating non-existent sequence
            fake_sequence = EpisodicSequence(
                sequence_id=generate_ulid(),
                space_id=space_id,
                ts=ts,
                items=[]
            )
            update_result = store.update_sequence(fake_sequence)
            assert update_result is False, "Update of non-existent sequence should fail"

            # Delete the sequence
            delete_result = store.delete_sequence(sequence_id)
            assert delete_result is True, "Delete should succeed"

            # Verify deletion
            retrieved = store.get_sequence(sequence_id)
            assert retrieved is None, "Deleted sequence should not be retrievable"

            # Test deleting non-existent sequence
            delete_result = store.delete_sequence(generate_ulid())
            assert delete_result is False, "Delete of non-existent sequence should fail"

        print("✅ Sequence update and delete passed")


def test_sequence_listing_and_filtering():
    """Test listing sequences with filtering options."""
    print("\nTesting sequence listing and filtering...")

    with tempfile.TemporaryDirectory() as temp_dir:
        config = StoreConfig(db_path=f"{temp_dir}/test_sequence_list.db")
        store = EpisodicStore(config)

        space_id = "space_test_001"
        ts = datetime.fromisoformat("2024-01-01T10:00:00")

        with store:
            # Create multiple sequences
            sequences = []
            for i in range(5):
                sequence = EpisodicSequence(
                    sequence_id=generate_ulid(),
                    space_id=space_id,
                    ts=datetime.fromisoformat(f"2024-01-01T{10+i}:00:00"),
                    label=f"Sequence {i}",
                    items=[],
                    closed=(i % 2 == 0)  # Even indices are closed
                )
                store.create_sequence(sequence)
                sequences.append(sequence)

            # Create sequences in different space
            other_space_id = "space_test_002"
            for i in range(2):
                sequence = EpisodicSequence(
                    sequence_id=generate_ulid(),
                    space_id=other_space_id,
                    ts=datetime.fromisoformat(f"2024-01-01T{10+i}:00:00"),
                    items=[],
                    closed=False
                )
                store.create_sequence(sequence)

            # Test listing all sequences for space
            all_sequences = store.list_sequences(space_id)
            assert len(all_sequences) == 5, f"Expected 5 sequences, got {len(all_sequences)}"

            # Verify ordering (should be DESC by ts)
            for i in range(1, len(all_sequences)):
                assert all_sequences[i-1].ts >= all_sequences[i].ts, "Sequences should be ordered by ts DESC"

            # Test filtering by closed status
            closed_sequences = store.list_sequences(space_id, closed=True)
            assert len(closed_sequences) == 3, f"Expected 3 closed sequences, got {len(closed_sequences)}"
            for seq in closed_sequences:
                assert seq.closed is True, "All returned sequences should be closed"

            open_sequences = store.list_sequences(space_id, closed=False)
            assert len(open_sequences) == 2, f"Expected 2 open sequences, got {len(open_sequences)}"
            for seq in open_sequences:
                assert seq.closed is False, "All returned sequences should be open"

            # Test pagination
            limited_sequences = store.list_sequences(space_id, limit=2)
            assert len(limited_sequences) == 2, "Should respect limit"

            offset_sequences = store.list_sequences(space_id, limit=2, offset=2)
            assert len(offset_sequences) == 2, "Should respect offset and limit"

            # Verify offset works correctly
            assert offset_sequences[0].sequence_id != limited_sequences[0].sequence_id, "Offset should return different results"

            # Test other space isolation
            other_sequences = store.list_sequences(other_space_id)
            assert len(other_sequences) == 2, "Should only return sequences for specified space"

        print("✅ Sequence listing and filtering passed")


def test_sequence_record_management():
    """Test adding and removing records from sequences."""
    print("\nTesting sequence record management...")

    with tempfile.TemporaryDirectory() as temp_dir:
        config = StoreConfig(db_path=f"{temp_dir}/test_sequence_records.db")
        store = EpisodicStore(config)

        space_id = "space_test_001"
        ts = datetime.fromisoformat("2024-01-01T10:00:00")

        with store:
            # Create some episodic records first
            records = []
            for i in range(3):
                record = EpisodicRecord(
                    id=generate_ulid(),
                    envelope_id=generate_ulid(),
                    space_id=space_id,
                    ts=datetime.fromisoformat(f"2024-01-01T{10+i}:00:00"),
                    band="GREEN",
                    author="test_author",
                    content={"message": f"Test record {i}"},
                    features={"category": "test"},
                    mls_group="test_group"
                )
                store.store_record(record)
                records.append(record)

            # Create an empty sequence
            sequence_id = generate_ulid()
            empty_sequence = EpisodicSequence(
                sequence_id=sequence_id,
                space_id=space_id,
                ts=ts,
                items=[]
            )
            store.create_sequence(empty_sequence)

            # Add records to sequence
            for i, record in enumerate(records):
                weight = 0.5 + (i * 0.2)  # Different weights
                result = store.add_to_sequence(sequence_id, record.id, space_id, weight)
                assert result is True, f"Adding record {i} should succeed"

            # Verify sequence was updated
            updated_sequence = store.get_sequence(sequence_id)
            assert updated_sequence is not None
            assert len(updated_sequence.items) == 3, "Sequence should have 3 items"

            # Verify items have correct structure
            for i, item in enumerate(updated_sequence.items):
                assert item["id"] == records[i].id
                assert item["weight"] == 0.5 + (i * 0.2)

            # Test getting sequence records
            sequence_records = store.get_sequence_records(sequence_id)
            assert len(sequence_records) == 3, "Should retrieve all sequence records"

            # Verify records are in sequence order
            for i, record in enumerate(sequence_records):
                assert record.id == records[i].id
                assert record.content["message"] == f"Test record {i}"

            # Remove a record from sequence
            remove_result = store.remove_from_sequence(sequence_id, records[1].id)
            assert remove_result is True, "Removing record should succeed"

            # Verify removal
            updated_sequence = store.get_sequence(sequence_id)
            assert len(updated_sequence.items) == 2, "Sequence should have 2 items after removal"

            remaining_ids = [item["id"] for item in updated_sequence.items]
            assert records[1].id not in remaining_ids, "Removed record should not be in sequence"
            assert records[0].id in remaining_ids, "Other records should remain"
            assert records[2].id in remaining_ids, "Other records should remain"

            # Test error cases
            fake_sequence_id = generate_ulid()

            # Adding to non-existent sequence
            add_result = store.add_to_sequence(fake_sequence_id, records[0].id, space_id)
            assert add_result is False, "Adding to non-existent sequence should fail"

            # Adding non-existent record
            fake_record_id = generate_ulid()
            add_result = store.add_to_sequence(sequence_id, fake_record_id, space_id)
            assert add_result is False, "Adding non-existent record should fail"

            # Removing from non-existent sequence
            remove_result = store.remove_from_sequence(fake_sequence_id, records[0].id)
            assert remove_result is False, "Removing from non-existent sequence should fail"

            # Removing non-existent record
            remove_result = store.remove_from_sequence(sequence_id, fake_record_id)
            assert remove_result is False, "Removing non-existent record should fail"

        print("✅ Sequence record management passed")


def test_sequence_database_schema():
    """Test that the sequence database schema follows contracts."""
    print("\nTesting sequence database schema compliance...")

    with tempfile.TemporaryDirectory() as temp_dir:
        config = StoreConfig(db_path=f"{temp_dir}/test_sequence_schema.db")
        store = EpisodicStore(config)

        # Initialize store to create schema
        with store:
            pass

        # Check that the table was created
        with store:
            cursor = store._connection.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='episodic_sequences'
            """)
            table_exists = cursor.fetchone()
            assert table_exists is not None, "episodic_sequences table should exist"

            # Check table schema
            cursor = store._connection.execute("PRAGMA table_info(episodic_sequences)")
            columns = cursor.fetchall()

            expected_columns = {
                "sequence_id": "TEXT",
                "space_id": "TEXT",
                "ts": "INTEGER",
                "label": "TEXT",
                "items_json": "TEXT",
                "closed": "INTEGER"
            }

            actual_columns = {col[1]: col[2] for col in columns}

            for col_name, col_type in expected_columns.items():
                assert col_name in actual_columns, f"Column {col_name} should exist"
                assert actual_columns[col_name] == col_type, f"Column {col_name} should be {col_type}"

            # Check primary key
            pk_columns = [col[1] for col in columns if col[5] == 1]  # col[5] is pk flag
            assert "sequence_id" in pk_columns, "sequence_id should be primary key"

            # Check indexes exist
            cursor = store._connection.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND name='idx_episodic_sequences_space'
            """)
            index_exists = cursor.fetchone()
            assert index_exists is not None, "Space index should exist"

        print("✅ Sequence database schema compliance passed")


def test_epic_2_1_2_complete_validation():
    """Complete validation test for Epic 2.1 Issue 2.1.2."""
    print("\n🎯 Running complete Epic 2.1 Issue 2.1.2 validation...")

    with tempfile.TemporaryDirectory() as temp_dir:
        config = StoreConfig(db_path=f"{temp_dir}/test_epic_2_1_2.db")
        store = EpisodicStore(config)

        # Test all sequence management capabilities
        space_id = "space_epic_test"
        ts = datetime.fromisoformat("2024-01-01T10:00:00")

        with store:
            # 1. Create sequence
            sequence_id = generate_ulid()
            test_sequence = EpisodicSequence(
                sequence_id=sequence_id,
                space_id=space_id,
                ts=ts,
                label="Epic 2.1.2 Test Sequence",
                items=[],
                closed=False
            )

            created_id = store.create_sequence(test_sequence)
            assert created_id == sequence_id

            # 2. Retrieve sequence
            retrieved = store.get_sequence(sequence_id)
            assert retrieved is not None
            assert retrieved.label == "Epic 2.1.2 Test Sequence"

            # 3. Create records and add to sequence
            record_ids = []
            for i in range(3):
                record = EpisodicRecord(
                    id=generate_ulid(),
                    envelope_id=generate_ulid(),
                    space_id=space_id,
                    ts=datetime.fromisoformat(f"2024-01-01T{10+i}:00:00"),
                    band="GREEN",
                    author="epic_test",
                    content={"test": f"data_{i}"},
                    features={"epic": "2.1.2"},
                    mls_group="test_group"
                )
                store.store_record(record)
                record_ids.append(record.id)

                # Add to sequence
                result = store.add_to_sequence(sequence_id, record.id, space_id, float(i) * 0.3)
                assert result is True

            # 4. Verify sequence records
            sequence_records = store.get_sequence_records(sequence_id)
            assert len(sequence_records) == 3

            # 5. Update sequence
            test_sequence.label = "Updated Epic Test"
            test_sequence.closed = True
            update_result = store.update_sequence(test_sequence)
            assert update_result is True

            # 6. List sequences
            sequences = store.list_sequences(space_id)
            assert len(sequences) >= 1

            # 7. Remove record from sequence
            remove_result = store.remove_from_sequence(sequence_id, record_ids[1])
            assert remove_result is True

            # 8. Verify final state
            final_sequence = store.get_sequence(sequence_id)
            assert final_sequence is not None
            assert final_sequence.closed is True
            assert len(final_sequence.items) == 2

            # 9. Delete sequence
            delete_result = store.delete_sequence(sequence_id)
            assert delete_result is True

            # 10. Verify deletion
            deleted_sequence = store.get_sequence(sequence_id)
            assert deleted_sequence is None

        print("✅ Epic 2.1 Issue 2.1.2 complete validation passed")


if __name__ == "__main__":
    print("🧪 Testing Epic 2.1 Issue 2.1.2: Sequence Store Implementation")
    print("=" * 80)

    try:
        test_sequence_contract_compliance()
        test_sequence_creation_and_retrieval()
        test_sequence_update_and_delete()
        test_sequence_listing_and_filtering()
        test_sequence_record_management()
        test_sequence_database_schema()
        test_epic_2_1_2_complete_validation()

        print("\n" + "=" * 80)
        print("🎉 All Epic 2.1 Issue 2.1.2 tests passed!")
        print("Sequence Store Implementation follows contracts exactly.")
        print("Epic 2.1 Issue 2.1.2 is COMPLETE and contract-compliant.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    print("🧪 Testing Epic 2.1 Issue 2.1.2: Sequence Store Implementation")
    print("=" * 80)

    try:
        test_sequence_contract_compliance()
        test_sequence_creation_and_retrieval()
        test_sequence_update_and_delete()
        test_sequence_listing_and_filtering()
        test_sequence_record_management()
        test_sequence_database_schema()
        test_epic_2_1_2_complete_validation()

        print("\n" + "=" * 80)
        print("🎉 All Epic 2.1 Issue 2.1.2 tests passed!")
        print("Sequence Store Implementation follows contracts exactly.")
        print("Epic 2.1 Issue 2.1.2 is COMPLETE and contract-compliant.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)        traceback.print_exc()
        exit(1)

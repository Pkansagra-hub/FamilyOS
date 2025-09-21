"""
Test Episodic Store Contract Compliance

Tests that the EpisodicStore implementation exactly follows:
- episodic_record.schema.json
- episodic_sequence.schema.json

Epic 2.1 Issue 2.1.1: Episodic Store Implementation
"""

import tempfile
from datetime import datetime

from storage.base_store import StoreConfig
from storage.episodic_store import (
    EpisodicRecord,
    EpisodicSequence,
    EpisodicStore,
    TemporalQuery,
)


class TestEpisodicStoreContractCompliance:
    """Test contract compliance for episodic store."""

    def test_episodic_record_contract_compliance(self):
        """Test EpisodicRecord matches episodic_record.schema.json exactly."""
        # Test data following contract exactly
        test_data = {
            "id": "01BX5ZZKBKACTAV9WEVGEMMVRZ",  # Valid ULID
            "envelope_id": "550e8400-e29b-41d4-a716-446655440000",  # UUID
            "space_id": "personal:alice.memory",  # Valid SpaceId pattern
            "ts": "2024-01-01T10:00:00.000Z",  # ISO datetime
            "band": "GREEN",  # Valid band
            "author": "alice@example.com",  # ActorRef
            "content": {
                "text": "Important meeting notes",
                "lang": "en",
                "attachments": [],
            },
            "features": {
                "keywords": ["meeting", "important"],
                "simhash": "a1b2c3d4e5f6",
                "sentiment": 0.8,
            },
            "mls_group": "group_abc123",
            "device": "device_xyz789",  # Optional
            "links": {  # Optional
                "sequence_id": "01BX5ZZKBKACTAV9WEVGEMMVS0",
                "parent_id": "01BX5ZZKBKACTAV9WEVGEMMVS1",
                "link_group_id": "group_123",
            },
            "meta": {"source": "manual_entry", "confidence": 0.95},  # Optional
        }

        # Test record creation and conversion
        record = EpisodicRecord.from_dict(test_data)

        # Verify all required fields match exactly
        assert record.id == test_data["id"]
        assert record.envelope_id == test_data["envelope_id"]
        assert record.space_id == test_data["space_id"]
        assert isinstance(record.ts, datetime)
        assert record.band == test_data["band"]
        assert record.author == test_data["author"]
        assert record.content == test_data["content"]
        assert record.features == test_data["features"]
        assert record.mls_group == test_data["mls_group"]

        # Verify optional fields
        assert record.device == test_data["device"]
        assert record.links == test_data["links"]
        assert record.meta == test_data["meta"]

        # Test round-trip conversion
        dict_output = record.to_dict()
        assert dict_output["id"] == test_data["id"]
        assert dict_output["envelope_id"] == test_data["envelope_id"]
        assert dict_output["space_id"] == test_data["space_id"]
        assert dict_output["band"] == test_data["band"]
        assert dict_output["author"] == test_data["author"]
        assert dict_output["content"] == test_data["content"]
        assert dict_output["features"] == test_data["features"]
        assert dict_output["mls_group"] == test_data["mls_group"]
        assert dict_output["device"] == test_data["device"]
        assert dict_output["links"] == test_data["links"]
        assert dict_output["meta"] == test_data["meta"]

    def test_episodic_sequence_contract_compliance(self):
        """Test EpisodicSequence matches episodic_sequence.schema.json exactly."""
        # Test data following contract exactly
        test_data = {
            "sequence_id": "01BX5ZZKBKACTAV9WEVGEMMVRZ",  # Valid ULID
            "space_id": "personal:alice.memory",  # Valid SpaceId pattern
            "items": [
                {"id": "01BX5ZZKBKACTAV9WEVGEMMVS0", "ts": "2024-01-01T10:00:00.000Z"},
                {
                    "id": "01BX5ZZKBKACTAV9WEVGEMMVS1",
                    "ts": "2024-01-01T10:05:00.000Z",
                    "weight": 0.8,
                },
            ],
            "ts": "2024-01-01T10:00:00.000Z",
            "label": "Morning meeting sequence",  # Optional
            "closed": False,  # Default false
        }

        # Test sequence creation and conversion
        sequence = EpisodicSequence.from_dict(test_data)

        # Verify all required fields match exactly
        assert sequence.sequence_id == test_data["sequence_id"]
        assert sequence.space_id == test_data["space_id"]
        assert sequence.items == test_data["items"]
        assert isinstance(sequence.ts, datetime)

        # Verify optional fields
        assert sequence.label == test_data["label"]
        assert sequence.closed == test_data["closed"]

        # Test round-trip conversion
        dict_output = sequence.to_dict()
        assert dict_output["sequence_id"] == test_data["sequence_id"]
        assert dict_output["space_id"] == test_data["space_id"]
        assert dict_output["items"] == test_data["items"]
        assert dict_output["label"] == test_data["label"]
        assert dict_output["closed"] == test_data["closed"]

    def test_episodic_store_schema_validation(self):
        """Test EpisodicStore._get_schema returns contract-compliant schema."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StoreConfig(db_path=f"{temp_dir}/test.db")
            store = EpisodicStore(config)

            schema = store._get_schema()

            # Verify schema structure matches contract
            assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
            assert "episodic_record.schema.json" in schema["$id"]
            assert schema["title"] == "Episodic Memory Record"
            assert schema["type"] == "object"
            assert schema["additionalProperties"] is False

            # Verify required fields match contract exactly
            required_fields = [
                "id",
                "envelope_id",
                "space_id",
                "ts",
                "band",
                "author",
                "content",
                "features",
                "mls_group",
            ]
            assert schema["required"] == required_fields

            # Verify properties include all contract fields
            properties = schema["properties"]
            for field in required_fields:
                assert field in properties

            # Verify optional fields are present
            optional_fields = ["device", "links", "meta"]
            for field in optional_fields:
                assert field in properties

    def test_episodic_store_database_schema(self):
        """Test database schema initialization follows contracts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StoreConfig(db_path=f"{temp_dir}/test.db")
            store = EpisodicStore(config)

            # We need to simulate the transaction context that BaseStore expects
            # In the real system, this is handled by UnitOfWork
            import sqlite3

            conn = sqlite3.connect(f"{temp_dir}/test.db")

            try:
                # Initialize the store schema manually
                store._initialize_schema(conn)

                # Verify episodic_records table exists with correct schema
                cursor = conn.execute(
                    """
                    SELECT sql FROM sqlite_master
                    WHERE type='table' AND name='episodic_records'
                """
                )

                table_sql = cursor.fetchone()[0]

                # Verify all contract-required columns exist
                required_columns = [
                    "id",
                    "envelope_id",
                    "space_id",
                    "ts",
                    "ts_iso",
                    "band",
                    "author",
                    "content_json",
                    "features_json",
                    "mls_group",
                ]
                for column in required_columns:
                    assert column in table_sql

                # Verify optional columns exist
                optional_columns = ["device", "links_json", "meta_json"]
                for column in optional_columns:
                    assert column in table_sql

                # Verify band constraint matches contract
                assert "CHECK (band IN ('GREEN', 'AMBER', 'RED', 'BLACK'))" in table_sql

                # Verify episodic_sequences table exists
                cursor = conn.execute(
                    """
                    SELECT sql FROM sqlite_master
                    WHERE type='table' AND name='episodic_sequences'
                """
                )

                seq_table_sql = cursor.fetchone()[0]

                # Verify sequence columns match contract
                sequence_columns = [
                    "sequence_id",
                    "space_id",
                    "ts",
                    "ts_iso",
                    "items_json",
                    "closed",
                ]
                for column in sequence_columns:
                    assert column in seq_table_sql

            finally:
                conn.close()

    def test_temporal_query_functionality(self):
        """Test temporal query features work with contract data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StoreConfig(db_path=f"{temp_dir}/test.db")
            store = EpisodicStore(config)

            # We need to simulate the UnitOfWork transaction context
            import sqlite3

            conn = sqlite3.connect(f"{temp_dir}/test.db")

            try:
                # Initialize store and begin transaction
                store.begin_transaction(conn)

                # Create test records following contract
                test_records = [
                    EpisodicRecord(
                        id="01BX5ZZKBKACTAV9WEVGEMMV01",
                        envelope_id="550e8400-e29b-41d4-a716-446655440001",
                        space_id="personal:alice.memory",
                        ts=datetime.fromisoformat("2024-01-01T10:00:00"),
                        band="GREEN",
                        author="alice@example.com",
                        content={"text": "First event"},
                        features={"keywords": ["first"]},
                        mls_group="group_abc123",
                    ),
                    EpisodicRecord(
                        id="01BX5ZZKBKACTAV9WEVGEMMV02",
                        envelope_id="550e8400-e29b-41d4-a716-446655440002",
                        space_id="personal:alice.memory",
                        ts=datetime.fromisoformat("2024-01-01T11:00:00"),
                        band="AMBER",
                        author="bob@example.com",
                        content={"text": "Second event"},
                        features={"keywords": ["second"]},
                        mls_group="group_abc123",
                    ),
                ]

                # Store records
                for record in test_records:
                    store.store_record(record)

                # Test temporal query
                query = TemporalQuery(
                    space_id="personal:alice.memory",
                    start_time=datetime.fromisoformat("2024-01-01T09:00:00"),
                    end_time=datetime.fromisoformat("2024-01-01T12:00:00"),
                    author="alice@example.com",
                    band_filter=["GREEN"],
                    limit=10,
                )

                results = store.query_temporal(query)

                # Verify results match query parameters
                assert len(results) == 1
                assert results[0].id == "01BX5ZZKBKACTAV9WEVGEMMV01"
                assert results[0].author == "alice@example.com"
                assert results[0].band == "GREEN"

                store.commit_transaction(conn)

            except Exception:
                store.rollback_transaction(conn)
                raise
            finally:
                conn.close()

    def test_base_store_interface_compliance(self):
        """Test EpisodicStore properly implements BaseStore interface."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StoreConfig(db_path=f"{temp_dir}/test.db")
            store = EpisodicStore(config)

            # Test data following contract
            test_data = {
                "id": "01BX5ZZKBKACTAV9WEVGEMMVRZ",
                "envelope_id": "550e8400-e29b-41d4-a716-446655440000",
                "space_id": "personal:alice.memory",
                "ts": "2024-01-01T10:00:00.000Z",
                "band": "GREEN",
                "author": "alice@example.com",
                "content": {"text": "Test content"},
                "features": {"keywords": ["test"]},
                "mls_group": "group_abc123",
            }

            # We need to simulate the UnitOfWork transaction context
            import sqlite3

            conn = sqlite3.connect(f"{temp_dir}/test.db")

            try:
                # Initialize store and begin transaction
                store.begin_transaction(conn)

                # Test _create_record
                created = store._create_record(test_data)
                assert created["id"] == test_data["id"]

                # Test _read_record
                read_record = store._read_record(test_data["id"])
                assert read_record is not None
                assert read_record["id"] == test_data["id"]

                # Test _list_records
                records = store._list_records(
                    filters={"space_id": "personal:alice.memory"}, limit=10
                )
                assert len(records) == 1
                assert records[0]["id"] == test_data["id"]

                # Test _update_record
                updated_data = {"content": {"text": "Updated content"}}
                updated = store._update_record(test_data["id"], updated_data)
                assert updated["content"]["text"] == "Updated content"

                # Test _delete_record
                deleted = store._delete_record(test_data["id"])
                assert deleted is True

                # Verify deletion
                read_after_delete = store._read_record(test_data["id"])
                assert read_after_delete is None

                store.commit_transaction(conn)

            except Exception:
                store.rollback_transaction(conn)
                raise
            finally:
                conn.close()


if __name__ == "__main__":
    # Run basic tests
    test_class = TestEpisodicStoreContractCompliance()

    print("Testing EpisodicRecord contract compliance...")
    test_class.test_episodic_record_contract_compliance()
    print("✅ EpisodicRecord contract compliance passed")

    print("Testing EpisodicSequence contract compliance...")
    test_class.test_episodic_sequence_contract_compliance()
    print("✅ EpisodicSequence contract compliance passed")

    print("Testing EpisodicStore schema validation...")
    test_class.test_episodic_store_schema_validation()
    print("✅ EpisodicStore schema validation passed")

    print("Testing database schema compliance...")
    test_class.test_episodic_store_database_schema()
    print("✅ Database schema compliance passed")

    print("Testing temporal query functionality...")
    test_class.test_temporal_query_functionality()
    print("✅ Temporal query functionality passed")

    print("Testing BaseStore interface compliance...")
    test_class.test_base_store_interface_compliance()
    print("✅ BaseStore interface compliance passed")

    print("\n🎉 All Epic 2.1 Issue 2.1.1 tests passed!")
    print("EpisodicStore implementation follows contracts exactly.")

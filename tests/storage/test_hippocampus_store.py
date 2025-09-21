"""Tests for HippocampusStore implementation"""

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, ".")

from storage import HippocampusStore, StoreConfig


class TestHippocampusStore:
    """Test the HippocampusStore implementation."""

    def setup_method(self):
        """Setup test database."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()  # Close the file handle so SQLite can use it
        self.config = StoreConfig(db_path=self.temp_db.name)
        self.store = HippocampusStore(self.config)

    def teardown_method(self):
        """Cleanup test database."""
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_schema_validation(self):
        """Test that schema validation works correctly."""
        # Valid data should pass
        valid_data = {
            "id": "01J5KZQZQZQZQZQZQZQZQZQZQZ",
            "space_id": "shared:household",
            "ts": "2025-01-20T12:00:00Z",
            "simhash_hex": "a" * 128,  # 512 bits = 128 hex chars
            "minhash32": [123, 456] * 16,  # 32 values
            "novelty": 0.85,
            "meta": {"author": "alice", "mentions": ["bob"]},
        }

        validation = self.store.validate_data(valid_data)
        assert validation.is_valid, f"Valid data failed: {validation.errors}"

        # Missing required field should fail
        incomplete_data = {
            "id": "01J5KZQZQZQZQZQZQZQZQZQZQZ",
            "space_id": "shared:household",
            # Missing ts, simhash_hex, minhash32, novelty
        }

        validation = self.store.validate_data(incomplete_data)
        assert not validation.is_valid
        assert len(validation.errors) > 0

    def test_basic_crud_operations(self):
        """Test create, read, update, delete operations."""
        from storage.unit_of_work import UnitOfWork

        # Test data
        trace_data = {
            "id": "01J5KZQZQZQZQZQZQZQZQZQZQZ",
            "space_id": "shared:household",
            "ts": datetime.now(timezone.utc).isoformat(),
            "simhash_hex": "a" * 128,
            "minhash32": [123, 456] * 16,
            "novelty": 0.85,
            "meta": {"author": "alice", "mentions": ["bob"]},
        }

        uow = UnitOfWork(self.config.db_path)
        uow.register_store(self.store)

        with uow:
            # Create
            created = self.store.create(trace_data)
            assert created["id"] == trace_data["id"]
            assert created["novelty"] == 0.85
            assert "created_at" in created

            # Read
            read_result = self.store.read(trace_data["id"])
            assert read_result is not None
            assert read_result["id"] == trace_data["id"]

            # Update
            update_data = {
                "novelty": 0.92,
                "meta": {"author": "alice", "updated": True},
            }
            updated = self.store.update(trace_data["id"], update_data)
            assert updated["novelty"] == 0.92
            assert updated["meta"]["updated"] is True

            # Delete
            deleted = self.store.delete(trace_data["id"])
            assert deleted is True

            # Verify deletion
            read_after_delete = self.store.read(trace_data["id"])
            assert read_after_delete is None

    def test_space_filtering(self):
        """Test space-scoped queries."""
        from storage.unit_of_work import UnitOfWork

        # Create traces in different spaces
        traces = [
            {
                "id": f"01J5KZQZQZQZQZQZQZQZQZQZQ{i}",
                "space_id": "shared:household" if i % 2 == 0 else "personal:alice",
                "ts": datetime.now(timezone.utc).isoformat(),
                "simhash_hex": f"{i:0>128}",
                "minhash32": [i] * 32,
                "novelty": 0.1 * i,
                "meta": {"seq": i},
            }
            for i in range(5)
        ]

        uow = UnitOfWork(self.config.db_path)
        uow.register_store(self.store)

        with uow:
            # Create all traces
            for trace in traces:
                self.store.create(trace)

            # Test space filtering
            household_traces = self.store.find_by_space("shared:household")
            personal_traces = self.store.find_by_space("personal:alice")

            assert len(household_traces) == 3  # indices 0, 2, 4
            assert len(personal_traces) == 2  # indices 1, 3

            # Verify correct spaces
            for trace in household_traces:
                assert trace["space_id"] == "shared:household"
            for trace in personal_traces:
                assert trace["space_id"] == "personal:alice"

    def test_novelty_filtering(self):
        """Test novelty-based filtering."""
        from storage.unit_of_work import UnitOfWork

        # Create traces with different novelty scores
        traces = [
            {
                "id": f"01J5KZQZQZQZQZQZQZQZQZQZQ{i}",
                "space_id": "shared:household",
                "ts": datetime.now(timezone.utc).isoformat(),
                "simhash_hex": f"{i:0>128}",
                "minhash32": [i] * 32,
                "novelty": 0.2 * i,  # 0.0, 0.2, 0.4, 0.6, 0.8
                "meta": {"seq": i},
            }
            for i in range(5)
        ]

        with UnitOfWork(self.config.db_path) as uow:
            uow.register_store(self.store)

            # Create all traces
            for trace in traces:
                self.store.create(trace)

            # Test novelty filtering
            high_novelty = self.store.find_by_space("shared:household", min_novelty=0.5)
            assert len(high_novelty) == 2  # indices 3, 4 (novelty 0.6, 0.8)

            # Test novelty distribution
            distribution = self.store.get_novelty_distribution("shared:household")
            assert distribution["total_traces"] == 5
            assert distribution["min_novelty"] == 0.0
            assert distribution["max_novelty"] == 0.8
            assert distribution["high_novelty_count"] == 1  # >= 0.8
            assert distribution["low_novelty_count"] == 2  # <= 0.2

    def test_simhash_similarity(self):
        """Test SimHash-based similarity search."""
        from storage.unit_of_work import UnitOfWork

        # Create traces with similar and different SimHashes
        base_hash = "a" * 128
        similar_hash = "b" + "a" * 127  # 4 bits different
        different_hash = "f" * 128  # Many bits different

        traces = [
            {
                "id": "01J5KZQZQZQZQZQZQZQZQZQZQ0",
                "space_id": "shared:household",
                "ts": datetime.now(timezone.utc).isoformat(),
                "simhash_hex": base_hash,
                "minhash32": [1] * 32,
                "novelty": 0.5,
            },
            {
                "id": "01J5KZQZQZQZQZQZQZQZQZQZQ1",
                "space_id": "shared:household",
                "ts": datetime.now(timezone.utc).isoformat(),
                "simhash_hex": similar_hash,
                "minhash32": [2] * 32,
                "novelty": 0.6,
            },
            {
                "id": "01J5KZQZQZQZQZQZQZQZQZQZQ2",
                "space_id": "shared:household",
                "ts": datetime.now(timezone.utc).isoformat(),
                "simhash_hex": different_hash,
                "minhash32": [3] * 32,
                "novelty": 0.7,
            },
        ]

        with UnitOfWork(self.config.db_path) as uow:
            uow.register_store(self.store)

            # Create all traces
            for trace in traces:
                self.store.create(trace)

            # Test similarity search
            similar_traces = self.store.find_similar_by_simhash(
                "shared:household", base_hash, max_hamming_distance=10
            )

            # Should find the base trace (distance 0) and similar trace (distance 4)
            assert len(similar_traces) == 2
            distances = [trace["hamming_distance"] for trace in similar_traces]
            assert 0 in distances  # Exact match
            assert 4 in distances  # Similar match


if __name__ == "__main__":
    # Simple test runner
    test_instance = TestHippocampusStore()
    test_instance.setup_method()

    try:
        test_instance.test_schema_validation()
        print("✓ Schema validation test passed")

        test_instance.test_basic_crud_operations()
        print("✓ Basic CRUD operations test passed")

        test_instance.test_space_filtering()
        print("✓ Space filtering test passed")

        test_instance.test_novelty_filtering()
        print("✓ Novelty filtering test passed")

        test_instance.test_simhash_similarity()
        print("✓ SimHash similarity test passed")

        print("\nAll tests passed! ✅")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        test_instance.teardown_method()

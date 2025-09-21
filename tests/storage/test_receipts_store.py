"""
Simple tests for ReceiptsStore - focusing on core functionality

These tests validate the basic receipt storage functionality.
"""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from storage.base_store import StoreConfig
from storage.receipts_store import AuditSummary, ReceiptQuery, ReceiptsStore
from storage.unit_of_work import StoreWriteRecord, WriteReceipt


class TestReceiptsStore(unittest.TestCase):
    """Test ReceiptsStore functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = StoreConfig(db_path=str(Path(self.temp_dir) / "test_receipts.db"))
        self.store = ReceiptsStore(self.config)

        # Create test receipt data
        self.test_stores = [
            StoreWriteRecord(
                name="memory_store", ts="2024-01-01T10:00:00Z", record_id="mem_001"
            ),
            StoreWriteRecord(
                name="vector_store", ts="2024-01-01T10:00:01Z", record_id="vec_001"
            ),
        ]

        self.test_receipt = WriteReceipt(
            envelope_id="env_12345",
            committed=True,
            stores=self.test_stores,
            uow_id="uow_67890",
            created_ts="2024-01-01T10:00:00Z",
            committed_ts="2024-01-01T10:00:02Z",
        )
        self.test_receipt.generate_hash()

    def tearDown(self):
        """Clean up test environment."""
        if hasattr(self.store, "_connection") and self.store._connection:
            self.store._connection.close()
        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_store_initialization(self):
        """Test store initialization and schema creation."""
        with self.store.transaction():
            # Verify tables were created
            cursor = self.store._connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]

            self.assertIn("receipts", tables)
            self.assertIn("receipt_stores", tables)

            # Verify indexes were created
            cursor = self.store._connection.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
            indexes = [row[0] for row in cursor.fetchall()]

            expected_indexes = [
                "idx_receipts_envelope_id",
                "idx_receipts_committed",
                "idx_receipts_created_ts",
                "idx_receipts_space_id",
                "idx_receipt_stores_store_name",
            ]

            for idx in expected_indexes:
                self.assertIn(idx, indexes)

    def test_store_receipt_success(self):
        """Test successful receipt storage."""
        with self.store.transaction():
            receipt_id = self.store.store_receipt(self.test_receipt)

            # Verify receipt ID matches UoW ID
            self.assertEqual(receipt_id, self.test_receipt.uow_id)

            # Verify receipt was stored
            stored_receipt = self.store.get_receipt(receipt_id)
            self.assertIsNotNone(stored_receipt)
            self.assertEqual(stored_receipt["envelope_id"], "env_12345")
            self.assertEqual(stored_receipt["committed"], True)
            self.assertEqual(len(stored_receipt["stores"]), 2)

    def test_receipt_integrity_verification(self):
        """Test cryptographic integrity verification."""
        with self.store.transaction():
            # Store receipt with valid hash
            receipt_id = self.store.store_receipt(self.test_receipt)

            # Verify integrity
            self.assertTrue(self.store.verify_receipt_integrity(receipt_id))

            # Test corrupted receipt (manually modify hash)
            corrupted_receipt = WriteReceipt(
                envelope_id="env_corrupted",
                committed=True,
                stores=self.test_stores,
                uow_id="uow_corrupted",
                created_ts="2024-01-01T10:00:00Z",
                receipt_hash="invalid_hash",
            )

            with self.assertRaises(ValueError):
                self.store.store_receipt(corrupted_receipt)

    def test_receipt_queries(self):
        """Test receipt querying with various filters."""
        with self.store.transaction():
            # Store multiple receipts
            receipt1 = WriteReceipt(
                envelope_id="env_1",
                committed=True,
                stores=[StoreWriteRecord("store_a", "2024-01-01T10:00:00Z", "rec_1")],
                uow_id="uow_1",
                created_ts="2024-01-01T10:00:00Z",
            )
            receipt1.generate_hash()

            receipt2 = WriteReceipt(
                envelope_id="env_2",
                committed=False,
                stores=[StoreWriteRecord("store_b", "2024-01-01T11:00:00Z", "rec_2")],
                uow_id="uow_2",
                created_ts="2024-01-01T11:00:00Z",
            )
            receipt2.generate_hash()

            self.store.store_receipt(receipt1)
            self.store.store_receipt(receipt2)

            # Query by envelope_id
            query = ReceiptQuery(envelope_id="env_1")
            results = self.store.query_receipts(query)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["envelope_id"], "env_1")

            # Query by committed status
            query = ReceiptQuery(committed=True)
            results = self.store.query_receipts(query)
            self.assertEqual(len(results), 2)  # Original test receipt + receipt1

            query = ReceiptQuery(committed=False)
            results = self.store.query_receipts(query)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["envelope_id"], "env_2")

            # Query by store name
            query = ReceiptQuery(store_name="store_a")
            results = self.store.query_receipts(query)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["envelope_id"], "env_1")

    def test_audit_summary(self):
        """Test audit summary generation."""
        with self.store.transaction():
            # Store test receipt first
            self.store.store_receipt(self.test_receipt)

            # Store additional receipts for testing
            failed_receipt = WriteReceipt(
                envelope_id="env_failed",
                committed=False,
                stores=[
                    StoreWriteRecord("store_c", "2024-01-01T12:00:00Z", "rec_fail")
                ],
                uow_id="uow_failed",
                created_ts="2024-01-01T12:00:00Z",
            )
            failed_receipt.generate_hash()
            self.store.store_receipt(failed_receipt)

            # Generate audit summary
            summary = self.store.get_audit_summary()

            self.assertEqual(summary.total_receipts, 2)
            self.assertEqual(summary.committed_receipts, 1)
            self.assertEqual(summary.failed_receipts, 1)
            self.assertIn("memory_store", summary.stores_involved)
            self.assertIn("vector_store", summary.stores_involved)
            self.assertIn("store_c", summary.stores_involved)
            self.assertIn(summary.integrity_status, ["verified", "issues", "unknown"])

    def test_schema_validation(self):
        """Test receipt data validation against schema."""
        schema = self.store._get_schema()

        # Valid receipt data
        valid_data = {
            "envelope_id": "env_test",
            "committed": True,
            "stores": [
                {
                    "name": "test_store",
                    "ts": "2024-01-01T10:00:00Z",
                    "record_id": "rec_123",
                }
            ],
        }

        validation = self.store.validate_data(valid_data)
        self.assertTrue(validation.is_valid)

        # Invalid receipt data (missing required field)
        invalid_data = {
            "envelope_id": "env_test",
            # missing "committed" field
            "stores": [],
        }

        validation = self.store.validate_data(invalid_data)
        self.assertFalse(validation.is_valid)
        self.assertIn("committed", str(validation.errors))

    def test_immutability_constraints(self):
        """Test that receipts cannot be updated or deleted."""
        with self.store.transaction():
            receipt_id = self.store.store_receipt(self.test_receipt)

            # Test update not allowed
            with self.assertRaises(NotImplementedError):
                self.store._update_record(receipt_id, {"committed": False})

            # Test delete not allowed
            with self.assertRaises(NotImplementedError):
                self.store._delete_record(receipt_id)

    def test_performance_characteristics(self):
        """Test receipt storage performance."""
        import time

        receipts_to_store = 100
        start_time = time.time()

        with self.store.transaction():
            for i in range(receipts_to_store):
                receipt = WriteReceipt(
                    envelope_id=f"env_{i}",
                    committed=True,
                    stores=[
                        StoreWriteRecord(
                            f"store_{i}", "2024-01-01T10:00:00Z", f"rec_{i}"
                        )
                    ],
                    uow_id=f"uow_{i}",
                    created_ts="2024-01-01T10:00:00Z",
                )
                receipt.generate_hash()
                self.store.store_receipt(receipt)

        end_time = time.time()
        total_time = end_time - start_time

        # Should handle 100 receipts well under 1 second
        self.assertLess(total_time, 1.0)

        # Calculate throughput (should meet 10k+ receipts/second target with proper hardware)
        throughput = receipts_to_store / total_time
        print(f"Receipt storage throughput: {throughput:.0f} receipts/second")

        # For CI/test environment, expect at least 100 receipts/second
        self.assertGreater(throughput, 100)

    def test_space_id_integration(self):
        """Test space ID integration for audit trails."""
        # Create receipt with space_id
        receipt_with_space = WriteReceipt(
            envelope_id="env_space_test",
            committed=True,
            stores=self.test_stores,
            uow_id="uow_space_test",
            created_ts="2024-01-01T10:00:00Z",
        )
        # Add space_id as attribute
        receipt_with_space.space_id = "shared:household"
        receipt_with_space.actor_id = "alice"
        receipt_with_space.device_id = "phone_001"
        receipt_with_space.generate_hash()

        with self.store.transaction():
            receipt_id = self.store.store_receipt(receipt_with_space)

            stored_receipt = self.store.get_receipt(receipt_id)
            self.assertEqual(stored_receipt["space_id"], "shared:household")
            self.assertEqual(stored_receipt["actor_id"], "alice")
            self.assertEqual(stored_receipt["device_id"], "phone_001")

    def test_error_handling(self):
        """Test error handling for various failure scenarios."""
        # Test operation outside transaction
        with self.assertRaises(RuntimeError):
            self.store.store_receipt(self.test_receipt)

        with self.assertRaises(RuntimeError):
            self.store.get_receipt("test_id")

        # Test invalid receipt data
        with self.store.transaction():
            invalid_receipt = WriteReceipt(
                envelope_id="",  # Empty envelope_id
                committed=True,
                stores=[],
                uow_id="",
                created_ts="",
            )

            with self.assertRaises(ValueError):
                self.store.store_receipt(invalid_receipt)

    def test_concurrent_access_simulation(self):
        """Test behavior under simulated concurrent access."""
        # This tests the store's behavior when multiple operations happen quickly
        receipts = []
        for i in range(10):
            receipt = WriteReceipt(
                envelope_id=f"env_concurrent_{i}",
                committed=True,
                stores=[
                    StoreWriteRecord(f"store_{i}", "2024-01-01T10:00:00Z", f"rec_{i}")
                ],
                uow_id=f"uow_concurrent_{i}",
                created_ts="2024-01-01T10:00:00Z",
            )
            receipt.generate_hash()
            receipts.append(receipt)

        with self.store.transaction():
            stored_ids = []
            for receipt in receipts:
                receipt_id = self.store.store_receipt(receipt)
                stored_ids.append(receipt_id)

            # Verify all receipts were stored correctly
            for receipt_id in stored_ids:
                stored_receipt = self.store.get_receipt(receipt_id)
                self.assertIsNotNone(stored_receipt)
                self.assertTrue(self.store.verify_receipt_integrity(receipt_id))

    def test_list_records_interface(self):
        """Test the BaseStore list_records interface."""
        with self.store.transaction():
            # Store test receipts
            self.store.store_receipt(self.test_receipt)

            # Test list_records with filters
            results = self.store._list_records(
                filters={"envelope_id": "env_12345"}, limit=10, offset=0
            )

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["envelope_id"], "env_12345")

            # Test list_records without filters
            results = self.store._list_records(limit=100)
            self.assertGreaterEqual(len(results), 1)


class TestReceiptQuery(unittest.TestCase):
    """Test ReceiptQuery dataclass."""

    def test_default_values(self):
        """Test ReceiptQuery default values."""
        query = ReceiptQuery()

        self.assertIsNone(query.envelope_id)
        self.assertIsNone(query.store_name)
        self.assertIsNone(query.committed)
        self.assertIsNone(query.start_time)
        self.assertIsNone(query.end_time)
        self.assertEqual(query.limit, 100)
        self.assertEqual(query.offset, 0)

    def test_custom_values(self):
        """Test ReceiptQuery with custom values."""
        start_time = datetime.now(timezone.utc)
        end_time = datetime.now(timezone.utc)

        query = ReceiptQuery(
            envelope_id="env_test",
            store_name="test_store",
            committed=True,
            start_time=start_time,
            end_time=end_time,
            limit=50,
            offset=10,
        )

        self.assertEqual(query.envelope_id, "env_test")
        self.assertEqual(query.store_name, "test_store")
        self.assertEqual(query.committed, True)
        self.assertEqual(query.start_time, start_time)
        self.assertEqual(query.end_time, end_time)
        self.assertEqual(query.limit, 50)
        self.assertEqual(query.offset, 10)


class TestAuditSummary(unittest.TestCase):
    """Test AuditSummary dataclass."""

    def test_audit_summary_creation(self):
        """Test AuditSummary creation and properties."""
        start_time = datetime.now(timezone.utc)
        end_time = datetime.now(timezone.utc)

        summary = AuditSummary(
            total_receipts=100,
            committed_receipts=90,
            failed_receipts=10,
            stores_involved=["store_a", "store_b"],
            time_range=(start_time, end_time),
            integrity_status="verified",
        )

        self.assertEqual(summary.total_receipts, 100)
        self.assertEqual(summary.committed_receipts, 90)
        self.assertEqual(summary.failed_receipts, 10)
        self.assertEqual(len(summary.stores_involved), 2)
        self.assertEqual(summary.time_range[0], start_time)
        self.assertEqual(summary.time_range[1], end_time)
        self.assertEqual(summary.integrity_status, "verified")


if __name__ == "__main__":
    unittest.main()

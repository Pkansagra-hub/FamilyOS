"""
Basic tests for ReceiptsStore - Core functionality validation

WARD tests that validate the ReceiptsStore implementation
without complex transaction handling.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

from ward import fixture, test

from storage.base_store import StoreConfig
from storage.receipts_store import AuditSummary, ReceiptQuery, ReceiptsStore
from storage.unit_of_work import StoreWriteRecord, WriteReceipt


@fixture
def temp_receipts_store():
    """Create a temporary receipts store for testing."""
    temp_dir = tempfile.mkdtemp()
    config = StoreConfig(db_path=str(Path(temp_dir) / "test_receipts.db"))
    store = ReceiptsStore(config)

    yield store

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@fixture
def test_receipt():
    """Create a test receipt for validation."""
    test_stores = [
        StoreWriteRecord(
            name="memory_store", ts="2024-01-01T10:00:00Z", record_id="mem_001"
        ),
        StoreWriteRecord(
            name="vector_store", ts="2024-01-01T10:00:01Z", record_id="vec_001"
        ),
    ]

    receipt = WriteReceipt(
        envelope_id="env_12345",
        committed=True,
        stores=test_stores,
        uow_id="uow_67890",
        created_ts="2024-01-01T10:00:00Z",
        committed_ts="2024-01-01T10:00:02Z",
    )
    receipt.generate_hash()
    return receipt


@test("ReceiptsStore initializes correctly")
def test_store_initialization(temp_receipts_store=temp_receipts_store):
    """Test store initialization."""
    assert temp_receipts_store is not None


@test("ReceiptsStore validates schema correctly")
def test_schema_validation(temp_receipts_store=temp_receipts_store):
    """Test receipt data validation against schema."""
    # Valid receipt data
    valid_data: Dict[str, Any] = {
        "envelope_id": "env_test",
        "committed": True,
        "stores": [
            {"name": "test_store", "ts": "2024-01-01T10:00:00Z", "record_id": "rec_123"}
        ],
    }

    validation = temp_receipts_store.validate_data(valid_data)
    assert validation.is_valid

    # Invalid receipt data (missing required field)
    invalid_data: Dict[str, Any] = {
        "envelope_id": "env_test",
        # missing "committed" field
        "stores": [],
    }

    validation = temp_receipts_store.validate_data(invalid_data)
    assert not validation.is_valid
    assert any("committed" in error for error in validation.errors)


@test("ReceiptQuery has correct default values")
def test_receipt_query_defaults():
    """Test ReceiptQuery default values."""
    query = ReceiptQuery()

    assert query.envelope_id is None
    assert query.store_name is None
    assert query.committed is None
    assert query.start_time is None
    assert query.end_time is None
    assert query.limit == 100
    assert query.offset == 0


@test("AuditSummary creation works correctly")
def test_audit_summary_creation():
    """Test AuditSummary creation and properties."""
    from datetime import datetime, timezone

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

    assert summary.total_receipts == 100
    assert summary.committed_receipts == 90
    assert summary.failed_receipts == 10
    assert len(summary.stores_involved) == 2
    assert summary.time_range[0] == start_time
    assert summary.time_range[1] == end_time
    assert summary.integrity_status == "verified"


@test("Receipts are immutable - no updates or deletes allowed")
def test_immutability_constraints(temp_receipts_store=temp_receipts_store):
    """Test that receipts cannot be updated or deleted."""
    try:
        temp_receipts_store._update_record("test_id", {"committed": False})
        assert False, "Expected NotImplementedError for update"
    except NotImplementedError:
        pass  # Expected

    try:
        temp_receipts_store._delete_record("test_id")
        assert False, "Expected NotImplementedError for delete"
    except NotImplementedError:
        pass  # Expected


@test("Receipt integrity verification algorithm works correctly")
def test_receipt_integrity_verification_algorithm():
    """Test the receipt integrity verification algorithm."""
    test_stores = [
        StoreWriteRecord(
            name="memory_store", ts="2024-01-01T10:00:00Z", record_id="mem_001"
        ),
        StoreWriteRecord(
            name="vector_store", ts="2024-01-01T10:00:01Z", record_id="vec_001"
        ),
    ]

    # Test with receipt that has hash
    receipt_with_hash = WriteReceipt(
        envelope_id="env_test",
        committed=True,
        stores=test_stores,
        uow_id="uow_test",
        created_ts="2024-01-01T10:00:00Z",
    )
    receipt_with_hash.receipt_hash = receipt_with_hash.generate_hash()

    # Should verify correctly
    assert receipt_with_hash.verify_integrity()

    # Test with corrupted hash
    receipt_corrupted = WriteReceipt(
        envelope_id="env_test",
        committed=True,
        stores=test_stores,
        uow_id="uow_test",
        created_ts="2024-01-01T10:00:00Z",
        receipt_hash="invalid_hash",
    )

    # Should fail verification
    assert not receipt_corrupted.verify_integrity()

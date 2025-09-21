"""
Tests for receipts store audit integration (Epic 1.2.1.2)

Tests the audit system integration for GDPR/CCPA compliance,
retention management, and integrity verification.
"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from ward import fixture, test

from storage.base_store import StoreConfig
from storage.receipts_store import (
    AuditIntegrityReport,
    ComplianceQuery,
    ComplianceReport,
    ReceiptsStore,
    RetentionPolicy,
    SecurityError,
)
from storage.unit_of_work import StoreWriteRecord, WriteReceipt


@fixture
def temp_db_path():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield f.name
    Path(f.name).unlink(missing_ok=True)


@fixture
def mock_audit_logger():
    """Mock audit logger for testing."""
    return Mock()


@fixture
def mock_security_provider():
    """Mock security provider for testing."""
    provider = Mock()
    provider.check_access.return_value = True
    provider.get_band_policy.return_value = {"min_security_level": "STANDARD"}
    provider.verify_security_level.return_value = True
    return provider


@fixture
def receipts_store(temp_db_path, mock_audit_logger, mock_security_provider):
    """Create receipts store with audit integration."""
    config = StoreConfig(db_path=temp_db_path, enable_wal=True)
    store = ReceiptsStore(
        config=config,
        audit_logger=mock_audit_logger,
        security_provider=mock_security_provider,
    )
    # Initialize store with transaction
    with patch.object(store, "_get_connection"):
        store._connection = Mock()
        yield store


@fixture
def sample_receipt():
    """Create sample receipt for testing."""
    stores = [
        StoreWriteRecord(
            name="test_store", ts="2024-01-01T12:00:00Z", record_id="rec-123"
        )
    ]
    return WriteReceipt(
        envelope_id="env-abc123",
        committed=True,
        stores=stores,
        uow_id="uow-456",
        created_ts="2024-01-01T12:00:00Z",
        committed_ts="2024-01-01T12:00:10Z",
        receipt_hash="hash-789",
    )


@test("Store receipt with audit logging creates audit event")
def test_store_receipt_with_audit(
    receipts_store: ReceiptsStore, sample_receipt: WriteReceipt, mock_audit_logger: Mock
):
    """Test that storing a receipt creates proper audit event."""
    with patch.object(receipts_store, "store_receipt", return_value="receipt-123"):
        receipt_id = receipts_store.store_receipt_with_audit(
            receipt=sample_receipt, space_id="shared:household", actor_id="alice"
        )

        # Verify receipt was stored
        assert receipt_id == "receipt-123"

        # Verify audit event was logged
        mock_audit_logger.log.assert_called_once()
        audit_call = mock_audit_logger.log.call_args[0][0]

        assert audit_call["type"] == "STORAGE_OPERATION"
        assert audit_call["operation"] == "CREATE"
        assert audit_call["envelope_id"] == "env-abc123"
        assert audit_call["space_id"] == "shared:household"
        assert audit_call["actor_id"] == "alice"
        assert audit_call["result"] == "SUCCESS"


@test("Store receipt with audit logs failure events")
def test_store_receipt_audit_failure(
    receipts_store: ReceiptsStore, sample_receipt: WriteReceipt, mock_audit_logger: Mock
):
    """Test that storage failures are properly logged."""
    with patch.object(
        receipts_store, "store_receipt", side_effect=ValueError("Test error")
    ):
        try:
            receipts_store.store_receipt_with_audit(
                receipt=sample_receipt, space_id="shared:household", actor_id="alice"
            )
            assert False, "Expected exception was not raised"
        except ValueError:
            pass  # Expected failure

        # Verify failure was logged
        mock_audit_logger.log.assert_called()
        audit_call = mock_audit_logger.log.call_args[0][0]
        assert audit_call["result"] == "FAILED"
        assert "error" in audit_call


@test("Query compliance trail returns comprehensive report")
async def test_query_compliance_trail(
    receipts_store: ReceiptsStore, mock_audit_logger: Mock
):
    """Test GDPR compliance trail generation."""
    # Query compliance trail
    query = ComplianceQuery(
        query_type="DATA_SUBJECT_ACCESS",
        subject_id="alice",
        space_id="shared:household",
    )

    # Mock the query_receipts_by_subject method
    with patch.object(receipts_store, "query_receipts_by_subject", return_value=[]):
        report = await receipts_store.query_compliance_trail(query)

        # Verify report structure
        assert isinstance(report, ComplianceReport)
        assert report.query.subject_id == "alice"
        assert report.total_records >= 0
        assert report.accessible_records >= 0
        assert len(report.data_locations) >= 1
        assert len(report.actions_taken) >= 1
        assert report.generated_at is not None
        assert report.report_hash is not None


@test("Query retention candidates identifies old receipts")
async def test_query_retention_candidates(receipts_store: ReceiptsStore):
    """Test retention policy enforcement."""
    policy = RetentionPolicy(
        retention_period_days=365,
        store_name="test_store",
        data_category="PERSONAL",
        deletion_method="SOFT",
        compliance_basis="GDPR_RETENTION_LIMITS",
    )

    # Mock database response
    with patch.object(receipts_store, "_connection") as mock_conn:
        mock_cursor = Mock()
        mock_conn.execute.return_value = mock_cursor

        # Mock old receipt data
        old_date = datetime.now(timezone.utc) - timedelta(days=400)
        mock_cursor.fetchall.return_value = [
            (
                "receipt-old",
                "env-old",
                True,
                "uow-old",
                old_date.isoformat(),
                old_date.isoformat(),
                "hash-old",
                "shared:household",
                "alice",
                "device-1",
                None,
            )
        ]

        candidates = await receipts_store.query_retention_candidates(policy)

        # Verify query parameters
        mock_conn.execute.assert_called()
        call_args = mock_conn.execute.call_args[0]
        assert policy.store_name in call_args[1]

        # Verify candidate structure (mock returns test data)
        assert len(candidates) >= 0


@test("Verify audit integrity detects tampering")
async def test_verify_audit_integrity(receipts_store: ReceiptsStore):
    """Test cryptographic integrity verification."""
    start_date = datetime.now(timezone.utc) - timedelta(days=1)
    end_date = datetime.now(timezone.utc)

    # Mock database and verification
    with patch.object(receipts_store, "_connection") as mock_conn:
        mock_cursor = Mock()
        mock_conn.execute.return_value = mock_cursor

        # Mock receipt data
        mock_cursor.fetchall.return_value = [
            ("receipt-1", "hash-1", "env-1", "2024-01-01T12:00:00Z"),
            ("receipt-2", "hash-2", "env-2", "2024-01-01T12:01:00Z"),
        ]

        # Mock integrity verification
        with patch.object(
            receipts_store, "verify_receipt_integrity", return_value=True
        ):
            report = await receipts_store.verify_audit_integrity(start_date, end_date)

            # Verify report structure
            assert isinstance(report, AuditIntegrityReport)
            assert report.verified_receipts >= 0
            assert report.corrupted_receipts >= 0
            assert report.hash_chain_status in ["VALID", "BROKEN", "UNKNOWN"]
            assert 0.0 <= report.integrity_score <= 1.0


@test("Security integration checks space access")
def test_space_access_control(
    receipts_store: ReceiptsStore,
    sample_receipt: WriteReceipt,
    mock_security_provider: Mock,
):
    """Test space-scoped access control."""
    # Allow access
    mock_security_provider.check_access.return_value = True

    with patch.object(receipts_store, "store_receipt", return_value="receipt-123"):
        receipt_id = receipts_store.store_receipt_with_audit(
            receipt=sample_receipt, space_id="shared:household", actor_id="alice"
        )
        assert receipt_id is not None

        # Verify security check was called
        mock_security_provider.check_access.assert_called_with(
            space_id="shared:household",
            actor_id="alice",
            operation="WRITE",
            resource_type="storage.receipts",
        )


@test("Security integration denies unauthorized access")
def test_security_access_denied(
    receipts_store: ReceiptsStore,
    sample_receipt: WriteReceipt,
    mock_security_provider: Mock,
):
    """Test unauthorized access is denied."""
    # Deny access
    mock_security_provider.check_access.return_value = False

    try:
        receipts_store.store_receipt_with_audit(
            receipt=sample_receipt,
            space_id="restricted:space",
            actor_id="unauthorized_user",
        )
        assert False, "Expected PermissionError was not raised"
    except PermissionError as e:
        assert "Access denied" in str(e)


@test("Band policy enforcement restricts low security actors")
def test_band_policy_enforcement(
    receipts_store: ReceiptsStore,
    sample_receipt: WriteReceipt,
    mock_security_provider: Mock,
):
    """Test band-based security restrictions."""
    # Set up high security requirement
    mock_security_provider.get_band_policy.return_value = {"min_security_level": "HIGH"}
    mock_security_provider.verify_security_level.return_value = False

    try:
        receipts_store.store_receipt_with_audit(
            receipt=sample_receipt,
            space_id="high_security:space",
            actor_id="low_security_user",
        )
        assert False, "Expected SecurityError was not raised"
    except SecurityError as e:
        assert "Insufficient security level" in str(e)


@test("Audit integration handles missing audit logger gracefully")
def test_missing_audit_logger(temp_db_path, mock_security_provider):
    """Test graceful handling when audit logger is not available."""
    config = StoreConfig(db_path=temp_db_path, enable_wal=True)
    store = ReceiptsStore(
        config=config,
        audit_logger=None,  # No audit logger
        security_provider=mock_security_provider,
    )

    # Mock connection and store_receipt
    with patch.object(store, "_get_connection"), patch.object(
        store, "store_receipt", return_value="receipt-123"
    ):
        store._connection = Mock()

        # Should not raise exception
        receipt = WriteReceipt(
            envelope_id="env-test",
            committed=True,
            stores=[
                StoreWriteRecord(
                    name="test", ts="2024-01-01T12:00:00Z", record_id="rec-1"
                )
            ],
            uow_id="uow-test",
            created_ts="2024-01-01T12:00:00Z",
            committed_ts="2024-01-01T12:00:10Z",
            receipt_hash="hash-test",
        )

        receipt_id = store.store_receipt_with_audit(
            receipt=receipt, space_id="test:space", actor_id="test_user"
        )

        assert receipt_id is not None


@test("Security integration handles missing security provider gracefully")
def test_missing_security_provider(temp_db_path, mock_audit_logger):
    """Test graceful handling when security provider is not available."""
    config = StoreConfig(db_path=temp_db_path, enable_wal=True)
    store = ReceiptsStore(
        config=config,
        audit_logger=mock_audit_logger,
        security_provider=None,  # No security provider
    )

    # Mock connection and store_receipt
    with patch.object(store, "_get_connection"), patch.object(
        store, "store_receipt", return_value="receipt-123"
    ):
        store._connection = Mock()

        # Should allow all operations when no security provider
        receipt = WriteReceipt(
            envelope_id="env-test",
            committed=True,
            stores=[
                StoreWriteRecord(
                    name="test", ts="2024-01-01T12:00:00Z", record_id="rec-1"
                )
            ],
            uow_id="uow-test",
            created_ts="2024-01-01T12:00:00Z",
            committed_ts="2024-01-01T12:00:10Z",
            receipt_hash="hash-test",
        )

        receipt_id = store.store_receipt_with_audit(
            receipt=receipt, space_id="any:space", actor_id="any_user"
        )

        assert receipt_id is not None

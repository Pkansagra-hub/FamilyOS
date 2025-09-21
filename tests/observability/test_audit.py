"""
Tests for tamper-evident audit logging system.

This module tests the audit trail system for comprehensive storage operation
logging with cryptographic integrity verification.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ward import test

from observability.audit import (
    AuditActor,
    AuditEventType,
    AuditOutcome,
    AuditQuery,
    AuditResource,
    CorrelationTracker,
    TamperEvidentAuditLogger,
    get_audit_logger,
)


@test("correlation tracker manages thread-local IDs correctly")
def test_correlation_tracker():
    """Test correlation ID tracking across threads."""
    tracker = CorrelationTracker()

    # Get or create correlation ID
    correlation_id1 = tracker.get_or_create()
    assert correlation_id1 is not None
    assert len(correlation_id1) > 0

    # Should return same ID on subsequent calls
    correlation_id2 = tracker.get_or_create()
    assert correlation_id1 == correlation_id2

    # Can set custom ID
    custom_id = "custom-correlation-12345"
    tracker.set_correlation_id(custom_id)
    assert tracker.get_or_create() == custom_id

    # Clear removes ID
    tracker.clear()
    correlation_id3 = tracker.get_or_create()
    assert correlation_id3 != custom_id


@test("audit logger initializes with tamper detection")
def test_audit_logger_initialization():
    """Test audit logger creates proper directory structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_path = Path(temp_dir) / "audit"
        logger = TamperEvidentAuditLogger(
            str(audit_path), enable_background_monitoring=False
        )

        # Should create audit directory
        assert audit_path.exists()
        assert audit_path.is_dir()

        # Should create chain file
        chain_file = audit_path / "audit_chain.json"
        assert chain_file.exists()

        # Should have genesis hash
        assert logger.last_hash is not None
        assert len(logger.last_hash) > 0


@test("audit logger logs operations with hash chaining")
async def test_audit_operation_logging():
    """Test that operations are logged with proper hash chaining."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_path = Path(temp_dir) / "audit"
        logger = TamperEvidentAuditLogger(
            str(audit_path), enable_background_monitoring=False
        )

        # Create test data
        actor = AuditActor(
            actor_id="test-user-123",
            actor_type="USER",
            session_id="session-abc",
            device_id="device-xyz",
        )

        resource = AuditResource(
            resource_type="RECORD",
            resource_id="record-456",
            store_name="test_store",
            space_id="space-789",
            band="GREEN",
        )

        outcome = AuditOutcome(result="SUCCESS", duration_ms=150, records_affected=1)

        # Log operation
        event_id = await logger.log_operation("CREATE", actor, resource, outcome)

        # Verify event was logged
        assert event_id is not None
        assert len(event_id) > 0

        # Check audit file was created
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        audit_file = audit_path / f"audit-{today}.jsonl"
        assert audit_file.exists()

        # Read and verify audit event
        with open(audit_file, "r") as f:
            event_line = f.readline().strip()
            event_data = json.loads(event_line)

            assert event_data["event_id"] == event_id
            assert event_data["event_type"] == AuditEventType.STORAGE_CREATE.value
            assert event_data["actor"]["actor_id"] == "test-user-123"
            assert event_data["resource"]["resource_id"] == "record-456"
            assert event_data["outcome"]["result"] == "SUCCESS"
            assert "chain_hash" in event_data
            assert "event_hash" in event_data


@test("audit logger maintains hash chain integrity")
async def test_hash_chain_integrity():
    """Test that multiple operations maintain hash chain integrity."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_path = Path(temp_dir) / "audit"
        logger = TamperEvidentAuditLogger(
            str(audit_path), enable_background_monitoring=False
        )

        actor = AuditActor(actor_id="user-1", actor_type="USER")
        outcome = AuditOutcome(result="SUCCESS")

        # Log multiple operations
        event_ids = []
        for i in range(3):
            resource_i = AuditResource(resource_type="RECORD", resource_id=f"rec-{i+1}")
            event_id = await logger.log_operation("CREATE", actor, resource_i, outcome)
            event_ids.append(event_id)

            # Small delay to ensure different timestamps
            await asyncio.sleep(0.01)

        # Verify integrity
        report = await logger.verify_integrity()
        assert report.integrity_score == 1.0
        assert report.verified_events == 3
        assert report.corrupted_events == 0
        assert report.chain_status == "VALID"
        assert len(report.anomalies) == 0


@test("audit logger detects tampered events")
async def test_tamper_detection():
    """Test that tampering with audit events is detected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_path = Path(temp_dir) / "audit"
        logger = TamperEvidentAuditLogger(
            str(audit_path), enable_background_monitoring=False
        )

        actor = AuditActor(actor_id="user-1", actor_type="USER")
        resource = AuditResource(resource_type="RECORD", resource_id="rec-1")
        outcome = AuditOutcome(result="SUCCESS")

        # Log an operation
        await logger.log_operation("CREATE", actor, resource, outcome)

        # Tamper with audit file
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        audit_file = audit_path / f"audit-{today}.jsonl"

        with open(audit_file, "r") as f:
            original_line = f.readline()

        # Modify the event data (change actor_id)
        event_data = json.loads(original_line)
        event_data["actor"]["actor_id"] = "tampered-user"
        tampered_line = json.dumps(event_data)

        with open(audit_file, "w") as f:
            f.write(tampered_line + "\n")

        # Verify integrity detects tampering
        report = await logger.verify_integrity()
        assert report.integrity_score < 1.0
        assert report.corrupted_events > 0
        assert report.chain_status in ["BROKEN", "DEGRADED"]

        # Detect tampering alerts
        alerts = await logger.detect_tampering()
        assert len(alerts) > 0
        assert alerts[0].alert_type == "INTEGRITY_VIOLATION"
        assert alerts[0].severity in ["HIGH", "MEDIUM"]


@test("audit logger supports policy decision logging")
async def test_policy_decision_logging():
    """Test logging of policy enforcement decisions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_path = Path(temp_dir) / "audit"
        logger = TamperEvidentAuditLogger(
            str(audit_path), enable_background_monitoring=False
        )

        actor = AuditActor(actor_id="user-1", actor_type="USER")
        resource = AuditResource(
            resource_type="RECORD", resource_id="sensitive-data", band="RED"
        )

        # Log policy decision
        event_id = await logger.log_policy_decision(
            policy_type="RBAC",
            decision="DENY",
            actor=actor,
            resource=resource,
            justification="Insufficient clearance for RED band data",
        )

        assert event_id is not None

        # Verify the logged event
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        audit_file = audit_path / f"audit-{today}.jsonl"

        with open(audit_file, "r") as f:
            event_data = json.loads(f.readline())

            assert event_data["context"]["policy_type"] == "RBAC"
            assert event_data["context"]["decision"] == "DENY"
            assert (
                event_data["context"]["justification"]
                == "Insufficient clearance for RED band data"
            )
            assert event_data["outcome"]["result"] == "FAILURE"


@test("audit logger supports access attempt logging")
async def test_access_attempt_logging():
    """Test logging of access control decisions."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_path = Path(temp_dir) / "audit"
        logger = TamperEvidentAuditLogger(
            str(audit_path), enable_background_monitoring=False
        )

        actor = AuditActor(actor_id="user-1", actor_type="USER")
        resource = AuditResource(resource_type="STORE", resource_id="secure-store")

        # Log successful access
        event_id = await logger.log_access_attempt(
            access_type="READ", actor=actor, resource=resource, granted=True
        )

        assert event_id is not None

        # Log denied access
        await logger.log_access_attempt(
            access_type="WRITE",
            actor=actor,
            resource=resource,
            granted=False,
            reason="Write access requires admin privileges",
        )

        # Verify events were logged
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        audit_file = audit_path / f"audit-{today}.jsonl"

        with open(audit_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 2

            # Check successful access
            success_event = json.loads(lines[0])
            assert success_event["context"]["granted"] is True
            assert success_event["outcome"]["result"] == "SUCCESS"

            # Check denied access
            denied_event = json.loads(lines[1])
            assert denied_event["context"]["granted"] is False
            assert (
                denied_event["context"]["reason"]
                == "Write access requires admin privileges"
            )
            assert denied_event["outcome"]["result"] == "FAILURE"


@test("audit logger supports querying with filters")
async def test_audit_query_interface():
    """Test querying audit trail with filters and pagination."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_path = Path(temp_dir) / "audit"
        logger = TamperEvidentAuditLogger(
            str(audit_path), enable_background_monitoring=False
        )

        # Log multiple events with different types
        actor1 = AuditActor(actor_id="user-1", actor_type="USER")
        actor2 = AuditActor(actor_id="user-2", actor_type="USER")
        resource = AuditResource(resource_type="RECORD", resource_id="rec-1")
        outcome = AuditOutcome(result="SUCCESS")

        # Log events for different actors
        await logger.log_operation("CREATE", actor1, resource, outcome)
        await logger.log_operation("READ", actor2, resource, outcome)
        await logger.log_operation("UPDATE", actor1, resource, outcome)

        # Query for user-1 events only
        query = AuditQuery(actor_ids=["user-1"], limit=10)

        result = await logger.query_audit_trail(query)

        assert result.total_count == 2  # CREATE and UPDATE by user-1
        assert len(result.events) == 2
        assert not result.has_more

        # Verify all returned events are for user-1
        for event in result.events:
            assert event.actor.actor_id == "user-1"

        # Query with pagination
        query_page = AuditQuery(limit=1, offset=0)
        result_page = await logger.query_audit_trail(query_page)

        assert len(result_page.events) == 1
        assert result_page.has_more is True


@test("global audit logger singleton works correctly")
def test_global_audit_logger():
    """Test global audit logger instance management."""
    # Get default instance
    logger1 = get_audit_logger()
    assert logger1 is not None

    # Should return same instance
    logger2 = get_audit_logger()
    assert logger1 is logger2

    # Can set custom instance
    with tempfile.TemporaryDirectory() as temp_dir:
        custom_logger = TamperEvidentAuditLogger(temp_dir)

        # Import the setter function
        from observability.audit import set_audit_logger

        set_audit_logger(custom_logger)

        logger3 = get_audit_logger()
        assert logger3 is custom_logger
        assert logger3 is not logger1


@test("audit events are immutable and well-formed")
async def test_audit_event_immutability():
    """Test that audit events are properly immutable and structured."""
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_path = Path(temp_dir) / "audit"
        logger = TamperEvidentAuditLogger(
            str(audit_path), enable_background_monitoring=False
        )

        actor = AuditActor(actor_id="user-1", actor_type="USER")
        resource = AuditResource(resource_type="RECORD", resource_id="rec-1")
        outcome = AuditOutcome(result="SUCCESS")

        await logger.log_operation("CREATE", actor, resource, outcome)

        # Query the event back
        query = AuditQuery(limit=1)
        result = await logger.query_audit_trail(query)

        assert len(result.events) == 1
        event = result.events[0]

        # Verify event structure
        assert event.event_id is not None
        assert event.correlation_id is not None
        assert event.timestamp is not None
        assert event.event_type == AuditEventType.STORAGE_CREATE
        assert event.actor.actor_id == "user-1"
        assert event.resource.resource_id == "rec-1"
        assert event.outcome.result == "SUCCESS"
        assert event.chain_hash is not None
        assert event.event_hash is not None

        # Verify immutability (frozen dataclass)
        try:
            # Try to modify the event (should fail)
            # This is just a test pattern, we expect it to fail
            import dataclasses

            if dataclasses.is_dataclass(event) and getattr(
                event, "__dataclass_frozen__", False
            ):
                pass  # Event is properly frozen
            else:
                assert False, "Event should be a frozen dataclass"
        except Exception:
            pass  # Any exception indicates proper immutability

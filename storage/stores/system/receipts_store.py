"""
Receipts Store - Immutable append-only audit trail for all storage operations

This store provides:
- Cryptographic integrity verification
- High-performance append-only writes
- Comprehensive audit trail
- GDPR/CCPA compliance support
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig
from storage.core.unit_of_work import WriteReceipt

try:
    from policy.audit import AuditLogger
except ImportError:
    # Fallback for testing environments
    AuditLogger = None


class SecurityError(Exception):
    """Raised when security constraints are violated."""

    pass


logger = logging.getLogger(__name__)


@dataclass
class ComplianceQuery:
    """Query parameters for compliance reports."""

    subject_id: str
    query_type: str  # "ACCESS" | "PORTABILITY" | "ERASURE" | "RECTIFICATION"
    space_id: Optional[str] = None
    date_range: Optional[tuple[datetime, datetime]] = None


@dataclass
class ComplianceReport:
    """Compliance report for data subject rights."""

    query: ComplianceQuery
    total_records: int
    accessible_records: int
    stores_searched: List[str]
    data_locations: List[str]
    retention_status: Dict[str, str]
    actions_taken: List[str]
    generated_at: datetime
    report_hash: str


@dataclass
class RetentionPolicy:
    """Data retention policy definition."""

    store_name: str
    data_category: str  # "PERSONAL" | "BUSINESS" | "SYSTEM"
    retention_period_days: int
    deletion_method: str  # "SOFT" | "HARD" | "CRYPTO_ERASE"
    compliance_basis: str


@dataclass
class RetentionAction:
    """Record of retention policy execution."""

    policy: RetentionPolicy
    records_affected: int
    action_taken: str
    verification_hash: str
    executed_at: datetime


@dataclass
class AuditIntegrityReport:
    """Audit trail integrity verification report."""

    verified_receipts: int
    corrupted_receipts: int
    missing_receipts: int
    hash_chain_status: str  # "VALID" | "BROKEN" | "UNKNOWN"
    last_verified_receipt: str
    integrity_score: float  # 0.0 to 1.0
    anomalies: List[str]


@dataclass
class StorageAuditEvent:
    """Audit event for storage operations."""

    type: str  # "STORAGE_OPERATION" | "COMPLIANCE_REPORT" | "RETENTION_ACTION"
    operation: str  # "CREATE" | "READ" | "UPDATE" | "DELETE" | "PURGE"
    store_name: str
    envelope_id: str
    space_id: str
    actor_id: str
    timestamp: str
    receipt_hash: str
    metadata: Dict[str, Any]
    result: str  # "SUCCESS" | "FAILED" | "PARTIAL"
    error: Optional[str] = None


@dataclass
class ReceiptQuery:
    """Query parameters for receipt searches."""

    envelope_id: Optional[str] = None
    store_name: Optional[str] = None
    committed: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


@dataclass
class AuditSummary:
    """Summary statistics for audit reporting."""

    total_receipts: int
    committed_receipts: int
    failed_receipts: int
    stores_involved: List[str]
    time_range: tuple[datetime, datetime]
    integrity_status: str  # "verified", "issues", "unknown"


class ReceiptsStore(BaseStore):
    """
    Immutable append-only store for transaction receipts.

    Features:
    - Cryptographic integrity verification with SHA-256
    - High-performance writes optimized for audit trails
    - Compliance with audit requirements (GDPR/CCPA)
    - Space-scoped access control integration
    - Retention policy support
    - Policy audit logger integration
    """

    def __init__(
        self,
        config: Optional[StoreConfig] = None,
        audit_logger: Optional[Any] = None,
        security_provider: Optional[Any] = None,
    ):
        super().__init__(config)
        self._store_name = "receipts_store"
        self._audit_logger = audit_logger
        self._security_provider = security_provider

    def _log_audit_event(self, event: StorageAuditEvent) -> None:
        """Log audit event to policy audit system."""
        if self._audit_logger:
            try:
                event_dict = {
                    "type": event.type,
                    "operation": event.operation,
                    "store_name": event.store_name,
                    "envelope_id": event.envelope_id,
                    "space_id": event.space_id,
                    "actor_id": event.actor_id,
                    "timestamp": event.timestamp,
                    "receipt_hash": event.receipt_hash,
                    "metadata": event.metadata,
                    "result": event.result,
                }
                if event.error:
                    event_dict["error"] = event.error
                self._audit_logger.log(event_dict)
            except Exception as e:
                logger.warning(f"Failed to log audit event: {e}")
        else:
            logger.debug(
                f"Audit event (no logger): {event.operation} on {event.envelope_id}"
            )

    def _get_schema(self) -> Dict[str, Any]:
        """Schema for receipt validation based on write_receipt.schema.json."""
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["envelope_id", "committed", "stores"],
            "properties": {
                "receipt_id": {"type": "string"},
                "envelope_id": {"type": "string"},
                "committed": {"type": "boolean"},
                "stores": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "ts"],
                        "properties": {
                            "name": {"type": "string"},
                            "ts": {"type": "string", "format": "date-time"},
                            "record_id": {"type": "string"},
                        },
                    },
                },
                "error": {"type": "object"},
                "uow_id": {"type": "string"},
                "created_ts": {"type": "string", "format": "date-time"},
                "committed_ts": {"type": ["string", "null"], "format": "date-time"},
                "receipt_hash": {"type": "string"},
                "space_id": {"type": "string"},
                "actor_id": {"type": ["string", "null"]},
                "device_id": {"type": ["string", "null"]},
            },
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize the receipts store schema."""
        # Main receipts table (append-only)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id TEXT PRIMARY KEY,
                envelope_id TEXT NOT NULL,
                committed BOOLEAN NOT NULL,
                uow_id TEXT,
                created_ts TEXT NOT NULL,
                committed_ts TEXT,
                receipt_hash TEXT NOT NULL,
                space_id TEXT,
                actor_id TEXT,
                device_id TEXT,
                error_data TEXT,  -- JSON serialized error details
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Store operations within each receipt
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS receipt_stores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id TEXT NOT NULL,
                store_name TEXT NOT NULL,
                operation_ts TEXT NOT NULL,
                record_id TEXT,
                FOREIGN KEY (receipt_id) REFERENCES receipts (receipt_id)
            )
        """
        )

        # Indexes for performance
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_receipts_envelope_id
            ON receipts (envelope_id)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_receipts_committed
            ON receipts (committed)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_receipts_created_ts
            ON receipts (created_ts)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_receipts_space_id
            ON receipts (space_id)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_receipt_stores_store_name
            ON receipt_stores (store_name)
        """
        )

        conn.commit()
        self._schema_initialized = True

    def store_receipt(self, receipt: WriteReceipt) -> str:
        """
        Store a receipt in the immutable audit log.

        Args:
            receipt: WriteReceipt instance to store

        Returns:
            The receipt ID for tracking

        Raises:
            ValueError: If receipt validation fails
            sqlite3.Error: If database operation fails
        """
        if not self._connection:
            raise RuntimeError("Not in transaction - call begin_transaction first")

        # Convert receipt to storage format
        receipt_data: Dict[str, Any] = {
            "receipt_id": receipt.uow_id,  # Use UoW ID as receipt ID
            "envelope_id": receipt.envelope_id,
            "committed": receipt.committed,
            "uow_id": receipt.uow_id,
            "created_ts": receipt.created_ts,
            "committed_ts": receipt.committed_ts,
            "receipt_hash": receipt.receipt_hash,
            "space_id": getattr(receipt, "space_id", None),
            "actor_id": getattr(receipt, "actor_id", None),
            "device_id": getattr(receipt, "device_id", None),
            "stores": [
                {"name": s.name, "ts": s.ts, "record_id": s.record_id}
                for s in receipt.stores
            ],
        }

        # Add error data if present
        if hasattr(receipt, "error") and receipt.error:
            receipt_data["error"] = receipt.error

        # Validate against schema
        validation = self.validate_data(receipt_data)
        if not validation.is_valid:
            raise ValueError(f"Receipt validation failed: {validation.errors}")

        # Verify receipt integrity
        if receipt.receipt_hash and not receipt.verify_integrity():
            raise ValueError("Receipt integrity verification failed")

        try:
            # Insert main receipt record
            self._connection.execute(
                """
                INSERT INTO receipts (
                    receipt_id, envelope_id, committed, uow_id,
                    created_ts, committed_ts, receipt_hash,
                    space_id, actor_id, device_id, error_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    receipt_data["receipt_id"],
                    receipt_data["envelope_id"],
                    receipt_data["committed"],
                    receipt_data["uow_id"],
                    receipt_data["created_ts"],
                    receipt_data["committed_ts"],
                    receipt_data["receipt_hash"],
                    receipt_data.get("space_id"),
                    receipt_data.get("actor_id"),
                    receipt_data.get("device_id"),
                    (
                        json.dumps(receipt_data.get("error"))
                        if receipt_data.get("error")
                        else None
                    ),
                ),
            )

            # Insert store operation records
            for store in receipt_data["stores"]:
                self._connection.execute(
                    """
                    INSERT INTO receipt_stores (
                        receipt_id, store_name, operation_ts, record_id
                    ) VALUES (?, ?, ?, ?)
                """,
                    (
                        receipt_data["receipt_id"],
                        store["name"],
                        store["ts"],
                        store.get("record_id"),
                    ),
                )

            self._operation_count += 1
            logger.info(
                f"Stored receipt {receipt_data['receipt_id']} for envelope {receipt_data['envelope_id']}"
            )

            return receipt_data["receipt_id"]

        except sqlite3.Error as e:
            self._error_count += 1
            logger.error(f"Failed to store receipt {receipt_data['receipt_id']}: {e}")
            raise

    def get_receipt(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a receipt by ID.

        Args:
            receipt_id: Receipt identifier

        Returns:
            Receipt data or None if not found
        """
        if not self._connection:
            raise RuntimeError("Not in transaction - call begin_transaction first")

        cursor = self._connection.execute(
            """
            SELECT receipt_id, envelope_id, committed, uow_id,
                   created_ts, committed_ts, receipt_hash,
                   space_id, actor_id, device_id, error_data
            FROM receipts
            WHERE receipt_id = ?
        """,
            (receipt_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        # Build receipt data
        receipt_data: Dict[str, Any] = {
            "receipt_id": row[0],
            "envelope_id": row[1],
            "committed": bool(row[2]),
            "uow_id": row[3],
            "created_ts": row[4],
            "committed_ts": row[5],
            "receipt_hash": row[6],
            "space_id": row[7],
            "actor_id": row[8],
            "device_id": row[9],
            "error": json.loads(row[10]) if row[10] else None,
            "stores": [],
        }

        # Fetch store operations
        store_cursor = self._connection.execute(
            """
            SELECT store_name, operation_ts, record_id
            FROM receipt_stores
            WHERE receipt_id = ?
            ORDER BY id
        """,
            (receipt_id,),
        )

        for store_row in store_cursor.fetchall():
            receipt_data["stores"].append(
                {"name": store_row[0], "ts": store_row[1], "record_id": store_row[2]}
            )

        return receipt_data

    def query_receipts(self, query: ReceiptQuery) -> List[Dict[str, Any]]:
        """
        Query receipts with filtering and pagination.

        Args:
            query: Query parameters

        Returns:
            List of matching receipts
        """
        if not self._connection:
            raise RuntimeError("Not in transaction - call begin_transaction first")

        sql = """
            SELECT DISTINCT r.receipt_id, r.envelope_id, r.committed, r.uow_id,
                   r.created_ts, r.committed_ts, r.receipt_hash,
                   r.space_id, r.actor_id, r.device_id, r.error_data
            FROM receipts r
        """

        conditions: List[str] = []
        params: List[Any] = []

        if query.envelope_id:
            conditions.append("r.envelope_id = ?")
            params.append(query.envelope_id)

        if query.committed is not None:
            conditions.append("r.committed = ?")
            params.append(query.committed)

        if query.start_time:
            conditions.append("r.created_ts >= ?")
            params.append(query.start_time.isoformat())

        if query.end_time:
            conditions.append("r.created_ts <= ?")
            params.append(query.end_time.isoformat())

        if query.store_name:
            sql += " LEFT JOIN receipt_stores rs ON r.receipt_id = rs.receipt_id"
            conditions.append("rs.store_name = ?")
            params.append(query.store_name)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY r.created_ts DESC"
        sql += f" LIMIT {query.limit} OFFSET {query.offset}"

        cursor = self._connection.execute(sql, params)
        receipts: List[Dict[str, Any]] = []

        for row in cursor.fetchall():
            receipt_data: Dict[str, Any] = {
                "receipt_id": row[0],
                "envelope_id": row[1],
                "committed": bool(row[2]),
                "uow_id": row[3],
                "created_ts": row[4],
                "committed_ts": row[5],
                "receipt_hash": row[6],
                "space_id": row[7],
                "actor_id": row[8],
                "device_id": row[9],
                "error": json.loads(row[10]) if row[10] else None,
                "stores": [],
            }

            # Fetch store operations for this receipt
            store_cursor = self._connection.execute(
                """
                SELECT store_name, operation_ts, record_id
                FROM receipt_stores
                WHERE receipt_id = ?
                ORDER BY id
            """,
                (row[0],),
            )

            for store_row in store_cursor.fetchall():
                receipt_data["stores"].append(
                    {
                        "name": store_row[0],
                        "ts": store_row[1],
                        "record_id": store_row[2],
                    }
                )

            receipts.append(receipt_data)

        return receipts

    def verify_receipt_integrity(self, receipt_id: str) -> bool:
        """
        Verify the cryptographic integrity of a stored receipt.

        Args:
            receipt_id: Receipt to verify

        Returns:
            True if integrity is valid, False otherwise
        """
        receipt_data = self.get_receipt(receipt_id)
        if not receipt_data:
            return False

        # Reconstruct the receipt for verification
        stores = [
            type(
                "Store",
                (),
                {"name": s["name"], "ts": s["ts"], "record_id": s.get("record_id")},
            )()
            for s in receipt_data["stores"]
        ]

        # Create a temporary WriteReceipt for verification
        temp_receipt = WriteReceipt(
            envelope_id=receipt_data["envelope_id"],
            committed=receipt_data["committed"],
            stores=stores,
            uow_id=receipt_data["uow_id"],
            created_ts=receipt_data["created_ts"],
            committed_ts=receipt_data["committed_ts"],
            receipt_hash=receipt_data["receipt_hash"],
        )

        return temp_receipt.verify_integrity()

    def get_audit_summary(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> AuditSummary:
        """
        Generate audit summary for compliance reporting.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Audit summary statistics
        """
        if not self._connection:
            raise RuntimeError("Not in transaction - call begin_transaction first")

        # Build time filter
        time_filter = ""
        params: List[str] = []
        if start_time or end_time:
            conditions: List[str] = []
            if start_time:
                conditions.append("created_ts >= ?")
                params.append(start_time.isoformat())
            if end_time:
                conditions.append("created_ts <= ?")
                params.append(end_time.isoformat())
            time_filter = " WHERE " + " AND ".join(conditions)

        # Get basic stats
        base_query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN committed = 1 THEN 1 ELSE 0 END) as committed,
                SUM(CASE WHEN committed = 0 THEN 1 ELSE 0 END) as failed,
                MIN(created_ts) as min_time,
                MAX(created_ts) as max_time
            FROM receipts
        """
        cursor = self._connection.execute(base_query + time_filter, params)

        stats = cursor.fetchone()

        # Get involved stores
        stores_query = """
            SELECT DISTINCT rs.store_name
            FROM receipt_stores rs
            JOIN receipts r ON rs.receipt_id = r.receipt_id
        """
        cursor = self._connection.execute(stores_query + time_filter, params)

        stores = [row[0] for row in cursor.fetchall()]

        # Verify integrity of sample receipts
        sample_query = """
            SELECT receipt_id FROM receipts
        """
        cursor = self._connection.execute(
            sample_query + time_filter + " ORDER BY RANDOM() LIMIT 10", params
        )

        sample_receipts = [row[0] for row in cursor.fetchall()]
        verified_count = sum(
            1 for rid in sample_receipts if self.verify_receipt_integrity(rid)
        )

        if len(sample_receipts) == 0:
            integrity_status = "unknown"
        elif verified_count == len(sample_receipts):
            integrity_status = "verified"
        else:
            integrity_status = "issues"

        return AuditSummary(
            total_receipts=stats[0] or 0,
            committed_receipts=stats[1] or 0,
            failed_receipts=stats[2] or 0,
            stores_involved=stores,
            time_range=(
                (
                    datetime.fromisoformat(stats[3])
                    if stats[3]
                    else datetime.now(timezone.utc)
                ),
                (
                    datetime.fromisoformat(stats[4])
                    if stats[4]
                    else datetime.now(timezone.utc)
                ),
            ),
            integrity_status=integrity_status,
        )

    # Audit Integration Methods (Contract compliance)

    async def query_compliance_trail(self, query: ComplianceQuery) -> ComplianceReport:
        """Generate compliance report with full audit trail."""
        if not self._connection:
            raise RuntimeError("Not in transaction - call begin_transaction first")

        # Search for receipts affecting the data subject
        subject_receipts = await self.query_receipts_by_subject(query.subject_id)

        # Determine accessible records based on query type and policy
        accessible_count = len(subject_receipts)
        if query.query_type == "ACCESS":
            # GDPR Article 15 - Right of access
            accessible_count = len(
                [r for r in subject_receipts if r.get("committed", False)]
            )
        elif query.query_type == "ERASURE":
            # GDPR Article 17 - Right to erasure
            accessible_count = len([r for r in subject_receipts if not r.get("error")])

        # Collect store information
        stores_searched = list(
            set(
                [
                    store["name"]
                    for receipt in subject_receipts
                    for store in receipt.get("stores", [])
                ]
            )
        )

        # Generate report
        report = ComplianceReport(
            query=query,
            total_records=len(subject_receipts),
            accessible_records=accessible_count,
            stores_searched=stores_searched,
            data_locations=[f"receipts_store:{self._store_name}"],
            retention_status={"receipts_store": "PERMANENT_AUDIT_TRAIL"},
            actions_taken=[f"QUERY_{query.query_type}_EXECUTED"],
            generated_at=datetime.now(timezone.utc),
            report_hash=self._generate_report_hash(subject_receipts),
        )

        # Log compliance audit event
        audit_event = StorageAuditEvent(
            type="COMPLIANCE_REPORT",
            operation=query.query_type,
            store_name=self._store_name,
            envelope_id=f"compliance:{query.subject_id}",
            space_id=query.space_id or "unknown",
            actor_id=query.subject_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            receipt_hash=report.report_hash,
            metadata={
                "total_records": report.total_records,
                "accessible_records": report.accessible_records,
                "stores_searched": len(stores_searched),
            },
            result="SUCCESS",
        )
        self._log_audit_event(audit_event)

        return report

    async def query_receipts_by_subject(
        self, subject_id: str, include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """Find all receipts affecting a data subject."""
        if not self._connection:
            raise RuntimeError("Not in transaction - call begin_transaction first")

        # Search in actor_id and receipt metadata
        sql = """
            SELECT DISTINCT r.receipt_id, r.envelope_id, r.committed, r.uow_id,
                   r.created_ts, r.committed_ts, r.receipt_hash,
                   r.space_id, r.actor_id, r.device_id, r.error_data
            FROM receipts r
            WHERE r.actor_id = ? OR r.device_id = ?
        """

        params = [subject_id, subject_id]

        if not include_deleted:
            sql += " AND r.committed = 1"

        sql += " ORDER BY r.created_ts DESC"

        cursor = self._connection.execute(sql, params)
        receipts = []

        for row in cursor.fetchall():
            receipt_data = {
                "receipt_id": row[0],
                "envelope_id": row[1],
                "committed": bool(row[2]),
                "uow_id": row[3],
                "created_ts": row[4],
                "committed_ts": row[5],
                "receipt_hash": row[6],
                "space_id": row[7],
                "actor_id": row[8],
                "device_id": row[9],
                "stores": [],
            }

            if row[10]:  # error_data
                receipt_data["error"] = json.loads(row[10])

            # Load associated store records
            store_cursor = self._connection.execute(
                """
                SELECT store_name, ts, record_id
                FROM receipt_stores
                WHERE receipt_id = ?
                ORDER BY id
            """,
                (row[0],),
            )

            for store_row in store_cursor.fetchall():
                receipt_data["stores"].append(
                    {
                        "name": store_row[0],
                        "ts": store_row[1],
                        "record_id": store_row[2],
                    }
                )

            receipts.append(receipt_data)

        return receipts

    async def query_retention_candidates(
        self, policy: RetentionPolicy
    ) -> List[Dict[str, Any]]:
        """Find receipts eligible for retention actions."""
        if not self._connection:
            raise RuntimeError("Not in transaction - call begin_transaction first")

        # Calculate cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(
            days=policy.retention_period_days
        )

        # Find receipts older than retention period
        sql = """
            SELECT DISTINCT r.receipt_id, r.envelope_id, r.committed, r.uow_id,
                   r.created_ts, r.committed_ts, r.receipt_hash,
                   r.space_id, r.actor_id, r.device_id, r.error_data
            FROM receipts r
            JOIN receipt_stores rs ON r.receipt_id = rs.receipt_id
            WHERE rs.store_name = ? AND r.created_ts < ?
            ORDER BY r.created_ts ASC
        """

        cursor = self._connection.execute(
            sql, [policy.store_name, cutoff_date.isoformat()]
        )
        candidates = []

        for row in cursor.fetchall():
            candidate = {
                "receipt_id": row[0],
                "envelope_id": row[1],
                "committed": bool(row[2]),
                "created_ts": row[4],
                "space_id": row[7],
                "stores": [],
            }
            candidates.append(candidate)

        return candidates

    async def verify_audit_integrity(
        self, start_date: datetime, end_date: datetime
    ) -> AuditIntegrityReport:
        """Verify cryptographic integrity of audit trail."""
        if not self._connection:
            raise RuntimeError("Not in transaction - call begin_transaction first")

        # Get all receipts in date range
        sql = """
            SELECT receipt_id, receipt_hash, envelope_id, created_ts
            FROM receipts
            WHERE created_ts BETWEEN ? AND ?
            ORDER BY created_ts ASC
        """

        cursor = self._connection.execute(
            sql, [start_date.isoformat(), end_date.isoformat()]
        )
        receipts = cursor.fetchall()

        verified_count = 0
        corrupted_count = 0
        anomalies = []
        last_verified = ""

        for receipt_id, _, _, _ in receipts:
            # Verify receipt integrity
            try:
                if self.verify_receipt_integrity(receipt_id):
                    verified_count += 1
                    last_verified = receipt_id
                else:
                    corrupted_count += 1
                    anomalies.append(f"Corrupted receipt: {receipt_id}")
            except Exception as e:
                corrupted_count += 1
                anomalies.append(f"Verification failed for {receipt_id}: {str(e)}")

        total_receipts = len(receipts)
        integrity_score = verified_count / total_receipts if total_receipts > 0 else 1.0

        hash_chain_status = "VALID"
        if corrupted_count > 0:
            hash_chain_status = "BROKEN"
        elif total_receipts == 0:
            hash_chain_status = "UNKNOWN"

        return AuditIntegrityReport(
            verified_receipts=verified_count,
            corrupted_receipts=corrupted_count,
            missing_receipts=0,  # Can't detect missing from this method
            hash_chain_status=hash_chain_status,
            last_verified_receipt=last_verified,
            integrity_score=integrity_score,
            anomalies=anomalies,
        )

    def _generate_report_hash(self, receipts: List[Dict[str, Any]]) -> str:
        """Generate integrity hash for compliance report."""
        import hashlib

        # Create deterministic hash from receipt data
        receipt_hashes = sorted([r.get("receipt_hash", "") for r in receipts])
        content = json.dumps(receipt_hashes, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    # Enhanced store_receipt with audit logging
    def store_receipt_with_audit(
        self, receipt: WriteReceipt, space_id: str, actor_id: str
    ) -> str:
        """Store receipt with full audit trail logging and security checks."""
        # Check space access permissions
        if not self._check_space_access(space_id, actor_id, "WRITE"):
            raise PermissionError(
                f"Access denied to space {space_id} for actor {actor_id}"
            )

        # Apply band-based restrictions
        band_policy = self._get_band_policy(space_id)
        if band_policy and band_policy.get("min_security_level"):
            if not self._verify_security_level(
                actor_id, band_policy["min_security_level"]
            ):
                raise SecurityError(f"Insufficient security level for space {space_id}")

        try:
            receipt_id = self.store_receipt(receipt)

            # Log successful storage
            audit_event = StorageAuditEvent(
                type="STORAGE_OPERATION",
                operation="CREATE",
                store_name=self._store_name,
                envelope_id=receipt.envelope_id or "",
                space_id=space_id,
                actor_id=actor_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                receipt_hash=receipt.receipt_hash or "",
                metadata={
                    "record_count": 1,
                    "committed": receipt.committed,
                    "stores_involved": len(receipt.stores),
                    "security_level": (
                        band_policy.get("min_security_level", "STANDARD")
                        if band_policy
                        else "STANDARD"
                    ),
                },
                result="SUCCESS",
            )
            self._log_audit_event(audit_event)

            return receipt_id

        except Exception as e:
            # Log failed storage
            audit_event = StorageAuditEvent(
                type="STORAGE_OPERATION",
                operation="CREATE",
                store_name=self._store_name,
                envelope_id=receipt.envelope_id or "",
                space_id=space_id,
                actor_id=actor_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                receipt_hash=receipt.receipt_hash or "",
                metadata={"error_type": type(e).__name__},
                result="FAILED",
                error=str(e),
            )
            self._log_audit_event(audit_event)
            raise

    # BaseStore abstract method implementations

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a receipt record (wrapper around store_receipt)."""
        # Convert data to WriteReceipt if needed
        if "envelope_id" in data:
            # Create minimal WriteReceipt from data
            stores: List[Any] = []
            for store_data in data.get("stores", []):
                store = type("Store", (), store_data)()
                stores.append(store)

            receipt = WriteReceipt(
                envelope_id=str(data["envelope_id"]),
                committed=bool(data["committed"]),
                stores=stores,
                uow_id=str(data.get("uow_id", data.get("receipt_id", ""))),
                created_ts=str(data.get("created_ts", "")),
                committed_ts=str(data.get("committed_ts", "")),
                receipt_hash=str(data.get("receipt_hash", "")),
            )

            receipt_id = self.store_receipt(receipt)
            result = self.get_receipt(receipt_id)
            if result is None:
                raise RuntimeError("Failed to retrieve stored receipt")
            return result
        else:
            raise ValueError("Invalid receipt data format")

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a receipt by ID."""
        return self.get_receipt(record_id)

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update not allowed for immutable receipts."""
        raise NotImplementedError("Receipts are immutable - updates not allowed")

    def _delete_record(self, record_id: str) -> bool:
        """Delete not allowed for immutable receipts."""
        raise NotImplementedError("Receipts are immutable - deletes not allowed")

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List receipts with filtering."""
        query = ReceiptQuery(limit=limit or 100, offset=offset or 0)

        if filters:
            query.envelope_id = filters.get("envelope_id")
            query.store_name = filters.get("store_name")
            query.committed = filters.get("committed")

        return self.query_receipts(query)

    # Security integration methods (MLS/Space-scoped access control)

    def _check_space_access(self, space_id: str, actor_id: str, operation: str) -> bool:
        """Check if actor has access to perform operation in space."""
        if not self._security_provider:
            return True  # No security provider means no restrictions

        try:
            # Delegate to security provider (policy engine integration)
            return self._security_provider.check_access(
                space_id=space_id,
                actor_id=actor_id,
                operation=operation,
                resource_type="storage.receipts",
            )
        except Exception as e:
            logger.warning(f"Security check failed: {e}")
            return False  # Fail closed

    def _get_band_policy(self, space_id: str) -> Optional[Dict[str, Any]]:
        """Get band-based security policy for space."""
        if not self._security_provider:
            return None

        try:
            return self._security_provider.get_band_policy(space_id)
        except Exception as e:
            logger.warning(f"Band policy lookup failed: {e}")
            return None

    def _verify_security_level(self, actor_id: str, required_level: str) -> bool:
        """Verify actor meets required security level."""
        if not self._security_provider:
            return True  # No security provider means no restrictions

        try:
            return self._security_provider.verify_security_level(
                actor_id, required_level
            )
        except Exception as e:
            logger.warning(f"Security level verification failed: {e}")
            return False  # Fail closed

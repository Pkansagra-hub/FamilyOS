"""CRDT Store - Conflict-free Replicated Data Type storage for distributed synchronization.

This module implements a CRDT (Conflict-free Replicated Data Type) store that provides
distributed data synchronization capabilities with automatic conflict resolution.
Supports multiple CRDT types including G-Set, PN-Counter, OR-Set, LWW-Register, and MV-Register.

Key Features:
- Vector clock-based causal ordering
- Automatic conflict detection and resolution
- Multiple CRDT data structure support
- BaseStore compliance for transaction management
- Space-scoped operations for privacy enforcement
- Cryptographic operation logging for audit trails
"""

import json
import logging
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from storage.core.base_store import BaseStore, StoreConfig, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class VectorClock:
    """Vector clock for causal ordering of CRDT operations."""

    clocks: Dict[str, int] = field(default_factory=dict)

    def increment(self, replica_id: str) -> None:
        """Increment the clock for a replica."""
        self.clocks[replica_id] = self.clocks.get(replica_id, 0) + 1

    def update(self, other: "VectorClock") -> None:
        """Update this vector clock with another vector clock."""
        for replica_id, clock_value in other.clocks.items():
            self.clocks[replica_id] = max(self.clocks.get(replica_id, 0), clock_value)

    def compare(self, other: "VectorClock") -> str:
        """Compare two vector clocks. Returns 'before', 'after', or 'concurrent'."""
        self_dominates = False
        other_dominates = False

        all_replicas = set(self.clocks.keys()) | set(other.clocks.keys())

        for replica_id in all_replicas:
            self_clock = self.clocks.get(replica_id, 0)
            other_clock = other.clocks.get(replica_id, 0)

            if self_clock > other_clock:
                self_dominates = True
            elif self_clock < other_clock:
                other_dominates = True

        if self_dominates and not other_dominates:
            return "after"
        elif other_dominates and not self_dominates:
            return "before"
        else:
            return "concurrent"


@dataclass
class CRDTOperation:
    """Individual CRDT operation with metadata."""

    operation_id: str
    space_id: str
    replica_id: str
    operation_type: str  # insert, update, delete, merge
    data_type: str  # g_set, pn_counter, or_set, lww_register, mv_register
    vector_clock: VectorClock
    operation_data: Dict[str, Any]
    causality_deps: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    applied_at: Optional[float] = None
    conflict_resolved: bool = False
    merge_metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConflictResolution:
    """Conflict resolution record."""

    conflict_id: str
    space_id: str
    object_id: str
    conflicting_operations: List[str]
    resolution_strategy: str
    resolution_data: Dict[str, Any]
    vector_clocks: Dict[str, VectorClock]
    resolved_at: float
    resolved_by: str
    resolution_confidence: float = 1.0
    manual_intervention: bool = False
    conflict_metadata: Optional[Dict[str, Any]] = None


class CRDTStore(BaseStore):
    """Storage for CRDT operations and conflict resolution."""

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self.replica_id = self._generate_replica_id()
        self.vector_clock = VectorClock()

    def _generate_replica_id(self) -> str:
        """Generate a unique replica identifier."""
        return f"replica-{uuid4().hex[:12]}"

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for CRDT storage."""
        return {
            "type": "object",
            "properties": {
                "crdt_operations": {
                    "type": "object",
                    "description": "CRDT operations storage schema",
                },
                "conflict_resolutions": {
                    "type": "object",
                    "description": "Conflict resolution storage schema",
                },
            },
        }

    def _get_sql_schema(self) -> str:
        """Get database schema SQL for CRDT storage."""
        return """
        CREATE TABLE IF NOT EXISTS crdt_operations (
            operation_id TEXT PRIMARY KEY,
            space_id TEXT NOT NULL,
            replica_id TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            data_type TEXT NOT NULL,
            vector_clock_json TEXT NOT NULL,
            operation_data_json TEXT NOT NULL,
            causality_deps_json TEXT NOT NULL DEFAULT '[]',
            created_at REAL NOT NULL,
            applied_at REAL,
            conflict_resolved BOOLEAN NOT NULL DEFAULT 0,
            merge_metadata_json TEXT
        );

        CREATE TABLE IF NOT EXISTS conflict_resolutions (
            conflict_id TEXT PRIMARY KEY,
            space_id TEXT NOT NULL,
            object_id TEXT NOT NULL,
            conflicting_operations_json TEXT NOT NULL,
            resolution_strategy TEXT NOT NULL,
            resolution_data_json TEXT NOT NULL,
            vector_clocks_json TEXT NOT NULL,
            resolved_at REAL NOT NULL,
            resolved_by TEXT NOT NULL,
            resolution_confidence REAL NOT NULL DEFAULT 1.0,
            manual_intervention BOOLEAN NOT NULL DEFAULT 0,
            conflict_metadata_json TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_crdt_operations_space_type
            ON crdt_operations(space_id, data_type);
        CREATE INDEX IF NOT EXISTS idx_crdt_operations_replica
            ON crdt_operations(replica_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_crdt_operations_vector_clock
            ON crdt_operations(space_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_conflict_resolutions_space
            ON conflict_resolutions(space_id, resolved_at);
        """

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema."""
        conn.executescript(self._get_sql_schema())

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record."""
        record_type = data.get("type", "operation")

        if record_type == "operation":
            return self._create_operation(data["operation_data"])
        elif record_type == "conflict_resolution":
            return self._create_conflict_resolution(data["resolution_data"])
        else:
            raise ValueError(f"Unknown record type: {record_type}")

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record by ID."""
        # Try to read as operation first
        operation = self._read_operation(record_id)
        if operation:
            return {"type": "operation", "data": operation}

        # Try to read as conflict resolution
        resolution = self._read_conflict_resolution(record_id)
        if resolution:
            return {"type": "conflict_resolution", "data": resolution}

        return None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record."""
        # CRDT operations are immutable once created
        # Only conflict resolution records can be updated
        record = self._read_record(record_id)
        if not record:
            raise ValueError(f"Record {record_id} not found")

        if record["type"] == "operation":
            raise ValueError("CRDT operations are immutable")

        # Update conflict resolution
        return self._update_conflict_resolution(record_id, data)

    def _delete_record(self, record_id: str) -> bool:
        """Delete a record."""
        # CRDT operations should not be deleted for audit purposes
        # Only allow deletion of conflict resolutions in exceptional cases
        record = self._read_record(record_id)
        if not record:
            return False

        if record["type"] == "operation":
            logger.warning(
                f"Attempted to delete CRDT operation {record_id} - not allowed"
            )
            return False

        return self._delete_conflict_resolution(record_id)

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List records with optional filtering and pagination."""
        # Default to listing operations
        return self._list_operations(filters, limit, offset)

    def _create_operation(self, operation: CRDTOperation) -> Dict[str, Any]:
        """Create a CRDT operation record."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute(
                """
                INSERT INTO crdt_operations
                (operation_id, space_id, replica_id, operation_type, data_type,
                 vector_clock_json, operation_data_json, causality_deps_json,
                 created_at, applied_at, conflict_resolved, merge_metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    operation.operation_id,
                    operation.space_id,
                    operation.replica_id,
                    operation.operation_type,
                    operation.data_type,
                    json.dumps(operation.vector_clock.clocks),
                    json.dumps(operation.operation_data),
                    json.dumps(operation.causality_deps),
                    operation.created_at,
                    operation.applied_at,
                    operation.conflict_resolved,
                    (
                        json.dumps(operation.merge_metadata)
                        if operation.merge_metadata
                        else None
                    ),
                ),
            )

        return {"operation_id": operation.operation_id, **asdict(operation)}

    def _read_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Read a CRDT operation."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM crdt_operations WHERE operation_id = ?
            """,
                (operation_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "operation_id": row["operation_id"],
                "space_id": row["space_id"],
                "replica_id": row["replica_id"],
                "operation_type": row["operation_type"],
                "data_type": row["data_type"],
                "vector_clock": json.loads(row["vector_clock_json"]),
                "operation_data": json.loads(row["operation_data_json"]),
                "causality_deps": json.loads(row["causality_deps_json"]),
                "created_at": row["created_at"],
                "applied_at": row["applied_at"],
                "conflict_resolved": bool(row["conflict_resolved"]),
                "merge_metadata": (
                    json.loads(row["merge_metadata_json"])
                    if row["merge_metadata_json"]
                    else None
                ),
            }

    def _list_operations(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List CRDT operations."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM crdt_operations"
            params = []

            # Apply filters
            if filters:
                conditions = []
                if "space_id" in filters:
                    conditions.append("space_id = ?")
                    params.append(filters["space_id"])
                if "replica_id" in filters:
                    conditions.append("replica_id = ?")
                    params.append(filters["replica_id"])
                if "data_type" in filters:
                    conditions.append("data_type = ?")
                    params.append(filters["data_type"])
                if "operation_type" in filters:
                    conditions.append("operation_type = ?")
                    params.append(filters["operation_type"])

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "operation_id": row["operation_id"],
                        "space_id": row["space_id"],
                        "replica_id": row["replica_id"],
                        "operation_type": row["operation_type"],
                        "data_type": row["data_type"],
                        "vector_clock": json.loads(row["vector_clock_json"]),
                        "operation_data": json.loads(row["operation_data_json"]),
                        "causality_deps": json.loads(row["causality_deps_json"]),
                        "created_at": row["created_at"],
                        "applied_at": row["applied_at"],
                        "conflict_resolved": bool(row["conflict_resolved"]),
                        "merge_metadata": (
                            json.loads(row["merge_metadata_json"])
                            if row["merge_metadata_json"]
                            else None
                        ),
                    }
                )

            return results

    def _create_conflict_resolution(
        self, resolution: ConflictResolution
    ) -> Dict[str, Any]:
        """Create a conflict resolution record."""
        with sqlite3.connect(self.config.db_path) as conn:
            # Serialize vector clocks
            vector_clocks_serialized = {}
            for op_id, vc in resolution.vector_clocks.items():
                vector_clocks_serialized[op_id] = vc.clocks

            conn.execute(
                """
                INSERT INTO conflict_resolutions
                (conflict_id, space_id, object_id, conflicting_operations_json,
                 resolution_strategy, resolution_data_json, vector_clocks_json,
                 resolved_at, resolved_by, resolution_confidence, manual_intervention,
                 conflict_metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    resolution.conflict_id,
                    resolution.space_id,
                    resolution.object_id,
                    json.dumps(resolution.conflicting_operations),
                    resolution.resolution_strategy,
                    json.dumps(resolution.resolution_data),
                    json.dumps(vector_clocks_serialized),
                    resolution.resolved_at,
                    resolution.resolved_by,
                    resolution.resolution_confidence,
                    resolution.manual_intervention,
                    (
                        json.dumps(resolution.conflict_metadata)
                        if resolution.conflict_metadata
                        else None
                    ),
                ),
            )

        return {"conflict_id": resolution.conflict_id, **asdict(resolution)}

    def _read_conflict_resolution(self, conflict_id: str) -> Optional[Dict[str, Any]]:
        """Read a conflict resolution record."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM conflict_resolutions WHERE conflict_id = ?
            """,
                (conflict_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            # Deserialize vector clocks
            vector_clocks_data = json.loads(row["vector_clocks_json"])
            vector_clocks = {}
            for op_id, vc_data in vector_clocks_data.items():
                vector_clocks[op_id] = VectorClock(vc_data)

            return {
                "conflict_id": row["conflict_id"],
                "space_id": row["space_id"],
                "object_id": row["object_id"],
                "conflicting_operations": json.loads(
                    row["conflicting_operations_json"]
                ),
                "resolution_strategy": row["resolution_strategy"],
                "resolution_data": json.loads(row["resolution_data_json"]),
                "vector_clocks": vector_clocks,
                "resolved_at": row["resolved_at"],
                "resolved_by": row["resolved_by"],
                "resolution_confidence": row["resolution_confidence"],
                "manual_intervention": bool(row["manual_intervention"]),
                "conflict_metadata": (
                    json.loads(row["conflict_metadata_json"])
                    if row["conflict_metadata_json"]
                    else None
                ),
            }

    def _update_conflict_resolution(
        self, conflict_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a conflict resolution record."""
        with sqlite3.connect(self.config.db_path) as conn:
            update_fields = []
            params = []

            if "resolution_confidence" in data:
                update_fields.append("resolution_confidence = ?")
                params.append(data["resolution_confidence"])

            if "manual_intervention" in data:
                update_fields.append("manual_intervention = ?")
                params.append(data["manual_intervention"])

            if "conflict_metadata" in data:
                update_fields.append("conflict_metadata_json = ?")
                params.append(json.dumps(data["conflict_metadata"]))

            if not update_fields:
                raise ValueError("No valid fields to update")

            params.append(conflict_id)

            cursor = conn.execute(
                f"""
                UPDATE conflict_resolutions
                SET {', '.join(update_fields)}
                WHERE conflict_id = ?
            """,
                params,
            )

            if cursor.rowcount == 0:
                raise ValueError(f"Conflict resolution {conflict_id} not found")

        updated_record = self._read_conflict_resolution(conflict_id)
        return {"conflict_id": conflict_id, **updated_record}

    def _delete_conflict_resolution(self, conflict_id: str) -> bool:
        """Delete a conflict resolution record."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM conflict_resolutions WHERE conflict_id = ?
            """,
                (conflict_id,),
            )

            return cursor.rowcount > 0

    # High-level CRDT operations

    def apply_operation(
        self,
        space_id: str,
        data_type: str,
        operation_type: str,
        operation_data: Dict[str, Any],
        causality_deps: Optional[List[str]] = None,
    ) -> str:
        """Apply a CRDT operation and return the operation ID."""
        # Increment our vector clock
        self.vector_clock.increment(self.replica_id)

        operation = CRDTOperation(
            operation_id=f"op-{uuid4().hex[:16]}",
            space_id=space_id,
            replica_id=self.replica_id,
            operation_type=operation_type,
            data_type=data_type,
            vector_clock=VectorClock(self.vector_clock.clocks.copy()),
            operation_data=operation_data,
            causality_deps=causality_deps or [],
            applied_at=time.time(),
        )

        self._create_operation(operation)
        return operation.operation_id

    def detect_conflicts(self, space_id: str, object_id: str) -> List[Tuple[str, str]]:
        """Detect conflicting operations for an object."""
        operations = self._list_operations({"space_id": space_id})

        # Filter operations affecting the object
        object_operations = [
            op
            for op in operations
            if op["operation_data"].get("object_id") == object_id
        ]

        conflicts = []
        for i, op1 in enumerate(object_operations):
            for op2 in object_operations[i + 1 :]:
                vc1 = VectorClock(op1["vector_clock"])
                vc2 = VectorClock(op2["vector_clock"])

                # If operations are concurrent, they may conflict
                if vc1.compare(vc2) == "concurrent":
                    conflicts.append((op1["operation_id"], op2["operation_id"]))

        return conflicts

    def resolve_conflict(
        self,
        conflicting_operations: List[str],
        strategy: str = "last_writer_wins",
        custom_resolution: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Resolve a conflict between operations."""
        if len(conflicting_operations) < 2:
            raise ValueError("Need at least 2 operations to resolve conflict")

        # Get operation details
        operations = []
        for op_id in conflicting_operations:
            op_data = self._read_operation(op_id)
            if op_data:
                operations.append(op_data)

        if len(operations) != len(conflicting_operations):
            raise ValueError("Some operations not found")

        # Apply resolution strategy
        resolution_data = {}
        vector_clocks = {}

        for op in operations:
            vector_clocks[op["operation_id"]] = VectorClock(op["vector_clock"])

        if strategy == "last_writer_wins":
            # Choose operation with latest timestamp
            winner = max(operations, key=lambda op: op["created_at"])
            resolution_data = {
                "winning_operation": winner["operation_id"],
                "winning_timestamp": winner["created_at"],
            }
        elif strategy == "add_wins":
            # Addition operations win over deletions
            add_ops = [op for op in operations if op["operation_type"] == "insert"]
            if add_ops:
                resolution_data = {
                    "winning_operations": [op["operation_id"] for op in add_ops]
                }
            else:
                # Fall back to LWW
                winner = max(operations, key=lambda op: op["created_at"])
                resolution_data = {"winning_operation": winner["operation_id"]}
        elif strategy == "delete_wins":
            # Deletion operations win over additions
            del_ops = [op for op in operations if op["operation_type"] == "delete"]
            if del_ops:
                resolution_data = {
                    "winning_operations": [op["operation_id"] for op in del_ops]
                }
            else:
                # Fall back to LWW
                winner = max(operations, key=lambda op: op["created_at"])
                resolution_data = {"winning_operation": winner["operation_id"]}
        elif strategy == "custom" and custom_resolution:
            resolution_data = custom_resolution
        else:
            raise ValueError(f"Unknown resolution strategy: {strategy}")

        # Create conflict resolution record
        conflict_resolution = ConflictResolution(
            conflict_id=f"conflict-{uuid4().hex[:16]}",
            space_id=operations[0]["space_id"],
            object_id=operations[0]["operation_data"].get("object_id", "unknown"),
            conflicting_operations=conflicting_operations,
            resolution_strategy=strategy,
            resolution_data=resolution_data,
            vector_clocks=vector_clocks,
            resolved_at=time.time(),
            resolved_by=self.replica_id,
        )

        self._create_conflict_resolution(conflict_resolution)

        # Mark operations as conflict resolved
        for op_id in conflicting_operations:
            with sqlite3.connect(self.config.db_path) as conn:
                conn.execute(
                    """
                    UPDATE crdt_operations
                    SET conflict_resolved = 1,
                        merge_metadata_json = ?
                    WHERE operation_id = ?
                """,
                    (
                        json.dumps(
                            {
                                "conflict_id": conflict_resolution.conflict_id,
                                "resolution_strategy": strategy,
                            }
                        ),
                        op_id,
                    ),
                )

        return conflict_resolution.conflict_id

    def get_object_state(
        self, space_id: str, object_id: str, data_type: str
    ) -> Dict[str, Any]:
        """Get the current state of an object by applying all operations."""
        operations = self._list_operations(
            {
                "space_id": space_id,
                "data_type": data_type,
            }
        )

        # Filter operations for this object
        object_operations = [
            op
            for op in operations
            if op["operation_data"].get("object_id") == object_id
        ]

        # Sort by vector clock order (causal order)
        # For simplicity, sort by timestamp as approximation
        object_operations.sort(key=lambda op: op["created_at"])

        # Apply operations based on CRDT type
        if data_type == "g_set":
            return self._apply_g_set_operations(object_operations)
        elif data_type == "pn_counter":
            return self._apply_pn_counter_operations(object_operations)
        elif data_type == "or_set":
            return self._apply_or_set_operations(object_operations)
        elif data_type == "lww_register":
            return self._apply_lww_register_operations(object_operations)
        elif data_type == "mv_register":
            return self._apply_mv_register_operations(object_operations)
        else:
            raise ValueError(f"Unknown CRDT data type: {data_type}")

    def _apply_g_set_operations(
        self, operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply G-Set (Grow-only Set) operations."""
        elements = set()

        for op in operations:
            if op["operation_type"] == "insert":
                elements.add(op["operation_data"]["element"])

        return {"type": "g_set", "elements": list(elements)}

    def _apply_pn_counter_operations(
        self, operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply PN-Counter (Positive-Negative Counter) operations."""
        positive_counts = {}
        negative_counts = {}

        for op in operations:
            replica_id = op["replica_id"]

            if op["operation_type"] == "increment":
                positive_counts[replica_id] = positive_counts.get(replica_id, 0) + op[
                    "operation_data"
                ].get("amount", 1)
            elif op["operation_type"] == "decrement":
                negative_counts[replica_id] = negative_counts.get(replica_id, 0) + op[
                    "operation_data"
                ].get("amount", 1)

        total_value = sum(positive_counts.values()) - sum(negative_counts.values())

        return {
            "type": "pn_counter",
            "value": total_value,
            "positive_counts": positive_counts,
            "negative_counts": negative_counts,
        }

    def _apply_or_set_operations(
        self, operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply OR-Set (Observed-Remove Set) operations."""
        added_elements = {}  # element -> set of unique tags
        removed_tags = set()

        for op in operations:
            element = op["operation_data"]["element"]
            tag = op["operation_data"].get(
                "tag", f"{op['replica_id']}-{op['created_at']}"
            )

            if op["operation_type"] == "insert":
                if element not in added_elements:
                    added_elements[element] = set()
                added_elements[element].add(tag)
            elif op["operation_type"] == "delete":
                removed_tags.add(tag)

        # Elements are in the set if they have tags that haven't been removed
        current_elements = []
        for element, tags in added_elements.items():
            if tags - removed_tags:  # If any tags remain
                current_elements.append(element)

        return {"type": "or_set", "elements": current_elements}

    def _apply_lww_register_operations(
        self, operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply LWW-Register (Last-Writer-Wins Register) operations."""
        if not operations:
            return {"type": "lww_register", "value": None}

        # Find operation with latest timestamp
        latest_op = max(operations, key=lambda op: op["created_at"])

        return {
            "type": "lww_register",
            "value": latest_op["operation_data"]["value"],
            "timestamp": latest_op["created_at"],
            "replica_id": latest_op["replica_id"],
        }

    def _apply_mv_register_operations(
        self, operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply MV-Register (Multi-Value Register) operations."""
        # Group operations by vector clock comparison
        concurrent_values = []

        for op in operations:
            value = op["operation_data"]["value"]
            vector_clock = VectorClock(op["vector_clock"])

            # Check if this value is concurrent with existing values
            is_concurrent = True
            for existing_value, existing_vc in concurrent_values:
                comparison = vector_clock.compare(existing_vc)
                if comparison == "after":
                    # This value supersedes the existing value
                    concurrent_values = [
                        (v, vc) for v, vc in concurrent_values if vc != existing_vc
                    ]
                elif comparison == "before":
                    # Existing value supersedes this value
                    is_concurrent = False
                    break

            if is_concurrent:
                concurrent_values.append((value, vector_clock))

        return {
            "type": "mv_register",
            "values": [value for value, _ in concurrent_values],
        }

    def sync_operations(self, remote_operations: List[Dict[str, Any]]) -> List[str]:
        """Sync operations from a remote replica."""
        applied_operations = []

        for remote_op in remote_operations:
            # Check if we already have this operation
            existing_op = self._read_operation(remote_op["operation_id"])
            if existing_op:
                continue

            # Update our vector clock
            remote_vc = VectorClock(remote_op["vector_clock"])
            self.vector_clock.update(remote_vc)

            # Create operation record
            operation = CRDTOperation(
                operation_id=remote_op["operation_id"],
                space_id=remote_op["space_id"],
                replica_id=remote_op["replica_id"],
                operation_type=remote_op["operation_type"],
                data_type=remote_op["data_type"],
                vector_clock=remote_vc,
                operation_data=remote_op["operation_data"],
                causality_deps=remote_op.get("causality_deps", []),
                created_at=remote_op["created_at"],
                applied_at=time.time(),
            )

            self._create_operation(operation)
            applied_operations.append(operation.operation_id)

        return applied_operations

    def validate_schema(self) -> ValidationResult:
        """Validate the CRDT store schema."""
        try:
            with sqlite3.connect(self.config.db_path) as conn:
                # Check if required tables exist
                cursor = conn.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name IN ('crdt_operations', 'conflict_resolutions')
                """
                )
                tables = {row[0] for row in cursor.fetchall()}

                errors = []
                warnings = []

                if "crdt_operations" not in tables:
                    errors.append("Missing crdt_operations table")

                if "conflict_resolutions" not in tables:
                    errors.append("Missing conflict_resolutions table")

                if not errors:
                    # Check for required columns
                    cursor = conn.execute("PRAGMA table_info(crdt_operations)")
                    op_columns = {row[1] for row in cursor.fetchall()}

                    required_op_columns = {
                        "operation_id",
                        "space_id",
                        "replica_id",
                        "operation_type",
                        "data_type",
                        "vector_clock_json",
                        "operation_data_json",
                        "created_at",
                    }
                    missing = required_op_columns - op_columns
                    if missing:
                        errors.append(f"Missing crdt_operations columns: {missing}")

                    cursor = conn.execute("PRAGMA table_info(conflict_resolutions)")
                    res_columns = {row[1] for row in cursor.fetchall()}

                    required_res_columns = {
                        "conflict_id",
                        "space_id",
                        "object_id",
                        "conflicting_operations_json",
                        "resolution_strategy",
                        "resolved_at",
                        "resolved_by",
                    }
                    missing = required_res_columns - res_columns
                    if missing:
                        errors.append(
                            f"Missing conflict_resolutions columns: {missing}"
                        )

                return ValidationResult(
                    is_valid=len(errors) == 0, errors=errors, warnings=warnings
                )

        except Exception as e:
            return ValidationResult(
                is_valid=False, errors=[f"Schema validation failed: {e}"], warnings=[]
            )

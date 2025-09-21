"""Imagination Store - Storage for simulation snapshots and dream scenarios.

This module implements storage for imagination simulation snapshots following the
imagination_snapshot.schema.json contract. Stores world state and policy state
snapshots for "what-if" scenario analysis and offline dreaming.

Key Features:
- Simulation snapshot storage with ULID identifiers
- World state and policy state preservation
- Space-scoped access control for family contexts
- Score tracking for simulation quality/relevance
- BaseStore compliance for transaction management
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


@dataclass
class ImaginationSnapshot:
    """Imagination simulation snapshot model matching the contract schema."""

    id: str  # ULID
    ts: str  # ISO timestamp
    space_id: str  # Space scope
    world_state: Dict[str, Any]  # Simulated world state
    policy_state: Dict[str, Any]  # Policy configuration at time of snapshot
    score: Optional[float] = None  # Quality/relevance score for this snapshot


class ImaginationStore(BaseStore):
    """
    Storage for imagination simulation snapshots.

    Implements storage for simulation scenarios and their outcomes,
    enabling "what-if" analysis and offline dreaming capabilities.
    Stores both world state and policy state for complete context.
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._store_name = "imagination"

    def _get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for imagination snapshot validation."""
        return {
            "type": "object",
            "required": ["id", "ts", "space_id", "world_state", "policy_state"],
            "properties": {
                "id": {
                    "type": "string",
                    "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$",  # ULID format
                    "description": "ULID snapshot identifier",
                },
                "ts": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO timestamp of snapshot",
                },
                "space_id": {
                    "type": "string",
                    "pattern": "^[a-zA-Z0-9_:-]+$",
                    "description": "Space scope for access control",
                },
                "world_state": {
                    "type": "object",
                    "description": "Simulated world state at snapshot time",
                    "additionalProperties": True,
                },
                "policy_state": {
                    "type": "object",
                    "description": "Policy configuration at snapshot time",
                    "additionalProperties": True,
                },
                "score": {
                    "type": ["number", "null"],
                    "description": "Quality/relevance score for this snapshot",
                },
            },
            "additionalProperties": False,
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize imagination snapshots table with optimized indexes."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS imagination_snapshots (
                id TEXT PRIMARY KEY,
                ts TEXT NOT NULL,
                space_id TEXT NOT NULL,
                world_state TEXT NOT NULL,
                policy_state TEXT NOT NULL,
                score REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indexes for common queries
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_imagination_space ON imagination_snapshots(space_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_imagination_ts ON imagination_snapshots(ts)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_imagination_score ON imagination_snapshots(score)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_imagination_created ON imagination_snapshots(created_at)"
        )

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new imagination snapshot record."""
        if not self._connection:
            raise RuntimeError("ImaginationStore not in transaction")

        snapshot = ImaginationSnapshot(**data)
        created_at = datetime.now(timezone.utc).isoformat()

        self._connection.execute(
            """
            INSERT INTO imagination_snapshots
            (id, ts, space_id, world_state, policy_state, score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                snapshot.id,
                snapshot.ts,
                snapshot.space_id,
                json.dumps(snapshot.world_state),
                json.dumps(snapshot.policy_state),
                snapshot.score,
                created_at,
            ),
        )

        return data

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read an imagination snapshot by ID."""
        if not self._connection:
            raise RuntimeError("ImaginationStore not in transaction")

        cursor = self._connection.execute(
            """
            SELECT id, ts, space_id, world_state, policy_state, score
            FROM imagination_snapshots
            WHERE id = ?
        """,
            (record_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "ts": row[1],
            "space_id": row[2],
            "world_state": json.loads(row[3]),
            "policy_state": json.loads(row[4]),
            "score": row[5],
        }

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing imagination snapshot record."""
        if not self._connection:
            raise RuntimeError("ImaginationStore not in transaction")

        # Build dynamic update query for provided fields
        update_fields: List[str] = []
        values: List[Any] = []

        for field_name in ["ts", "world_state", "policy_state", "score"]:
            if field_name in data:
                update_fields.append(f"{field_name} = ?")
                if field_name in ["world_state", "policy_state"]:
                    values.append(json.dumps(data[field_name]))
                else:
                    values.append(data[field_name])

        if not update_fields:
            # Nothing to update
            return self._read_record(record_id) or {}

        values.append(record_id)

        self._connection.execute(
            f"UPDATE imagination_snapshots SET {', '.join(update_fields)} WHERE id = ?",
            values,
        )

        return self._read_record(record_id) or {}

    def _delete_record(self, record_id: str) -> bool:
        """Delete an imagination snapshot record."""
        if not self._connection:
            raise RuntimeError("ImaginationStore not in transaction")

        cursor = self._connection.execute(
            "DELETE FROM imagination_snapshots WHERE id = ?", (record_id,)
        )
        return cursor.rowcount > 0

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List imagination snapshot records with filtering."""
        if not self._connection:
            raise RuntimeError("ImaginationStore not in transaction")

        filters = filters or {}
        conditions: List[str] = []
        params: List[Any] = []

        # Add filtering conditions
        if "space_id" in filters:
            conditions.append("space_id = ?")
            params.append(filters["space_id"])

        if "min_score" in filters:
            conditions.append("score >= ?")
            params.append(filters["min_score"])

        if "max_score" in filters:
            conditions.append("score <= ?")
            params.append(filters["max_score"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit or 100, offset or 0])

        cursor = self._connection.execute(
            f"""
            SELECT id, ts, space_id, world_state, policy_state, score
            FROM imagination_snapshots
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """,
            params,
        )

        records = []
        for row in cursor.fetchall():
            records.append(
                {
                    "id": row[0],
                    "ts": row[1],
                    "space_id": row[2],
                    "world_state": json.loads(row[3]),
                    "policy_state": json.loads(row[4]),
                    "score": row[5],
                }
            )

        return records

    # Imagination-specific methods

    def create_snapshot(
        self,
        snapshot_id: str,
        space_id: str,
        world_state: Dict[str, Any],
        policy_state: Dict[str, Any],
        score: Optional[float] = None,
        timestamp: Optional[str] = None,
    ) -> str:
        """Create a new imagination snapshot.

        Args:
            snapshot_id: ULID identifier for the snapshot
            space_id: Space context for the simulation
            world_state: Current/simulated world state
            policy_state: Policy configuration at snapshot time
            score: Optional quality/relevance score
            timestamp: Optional timestamp (defaults to now)

        Returns:
            The snapshot ID
        """
        ts = timestamp or datetime.now(timezone.utc).isoformat()

        snapshot_data = {
            "id": snapshot_id,
            "ts": ts,
            "space_id": space_id,
            "world_state": world_state,
            "policy_state": policy_state,
            "score": score,
        }

        self._create_record(snapshot_data)
        logger.info(f"Created imagination snapshot {snapshot_id} for space {space_id}")
        return snapshot_id

    def get_snapshot(self, snapshot_id: str) -> Optional[ImaginationSnapshot]:
        """Retrieve an imagination snapshot by ID."""
        data = self._read_record(snapshot_id)
        if data:
            return ImaginationSnapshot(**data)
        return None

    def list_snapshots_by_space(
        self, space_id: str, limit: int = 100, offset: int = 0
    ) -> List[ImaginationSnapshot]:
        """List imagination snapshots for a specific space."""
        records = self._list_records(
            filters={"space_id": space_id}, limit=limit, offset=offset
        )
        return [ImaginationSnapshot(**record) for record in records]

    def list_snapshots_by_score(
        self,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        space_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ImaginationSnapshot]:
        """List imagination snapshots filtered by score range."""
        filters: Dict[str, Any] = {}
        if min_score is not None:
            filters["min_score"] = min_score
        if max_score is not None:
            filters["max_score"] = max_score
        if space_id:
            filters["space_id"] = space_id

        records = self._list_records(filters=filters, limit=limit, offset=offset)
        return [ImaginationSnapshot(**record) for record in records]

    def update_snapshot_score(self, snapshot_id: str, score: float) -> bool:
        """Update the score for an existing snapshot."""
        updated = self._update_record(snapshot_id, {"score": score})
        return bool(updated)

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete an imagination snapshot."""
        return self._delete_record(snapshot_id)

    def cleanup_old_snapshots(self, space_id: str, keep_count: int = 1000) -> int:
        """Clean up old snapshots, keeping only the most recent ones.

        Args:
            space_id: Space to clean up
            keep_count: Number of most recent snapshots to keep

        Returns:
            Number of snapshots deleted
        """
        if not self._connection:
            raise RuntimeError("ImaginationStore not in transaction")

        # Get snapshots to delete (oldest ones beyond keep_count)
        cursor = self._connection.execute(
            """
            SELECT id FROM imagination_snapshots
            WHERE space_id = ?
            ORDER BY created_at DESC
            LIMIT -1 OFFSET ?
        """,
            (space_id, keep_count),
        )

        snapshot_ids = [row[0] for row in cursor.fetchall()]

        if not snapshot_ids:
            return 0

        # Delete the old snapshots
        placeholders = ",".join("?" * len(snapshot_ids))
        cursor = self._connection.execute(
            f"DELETE FROM imagination_snapshots WHERE id IN ({placeholders})",
            snapshot_ids,
        )

        deleted_count = cursor.rowcount
        logger.info(
            f"Cleaned up {deleted_count} old imagination snapshots for space {space_id}"
        )
        return deleted_count

    def get_statistics(self, space_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about stored imagination snapshots."""
        if not self._connection:
            raise RuntimeError("ImaginationStore not in transaction")

        conditions = []
        params = []

        if space_id:
            conditions.append("space_id = ?")
            params.append(space_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor = self._connection.execute(
            f"""
            SELECT
                COUNT(*) as total_snapshots,
                COUNT(DISTINCT space_id) as unique_spaces,
                AVG(score) as avg_score,
                MIN(score) as min_score,
                MAX(score) as max_score,
                MIN(created_at) as earliest_snapshot,
                MAX(created_at) as latest_snapshot
            FROM imagination_snapshots
            {where_clause}
        """,
            params,
        )

        row = cursor.fetchone()
        if not row:
            return {}

        return {
            "total_snapshots": row[0],
            "unique_spaces": row[1],
            "avg_score": row[2],
            "min_score": row[3],
            "max_score": row[4],
            "earliest_snapshot": row[5],
            "latest_snapshot": row[6],
        }

"""
Index Checkpoint Store for P13 Pipeline Integration.

This module provides checkpoint management for search index state, supporting:
- Index rebuild coordination
- Graceful degradation during rebuilds
- Position tracking and state management
- Atomic updates with rollback support
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


@dataclass
class IndexCheckpoint:
    """Represents a checkpoint for index rebuild state management."""

    id: str  # ULID
    index_name: str  # Must match IndexName pattern ^[A-Za-z0-9._:-]{2,64}$
    shard_id: str  # Shard identifier for this checkpoint
    position: int  # Current position in the rebuild process
    content_hash: str  # SHA-256 hash of content at this position
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "index_name": self.index_name,
            "shard_id": self.shard_id,
            "position": self.position,
            "content_hash": self.content_hash,
            "ts": self.ts.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IndexCheckpoint":
        """Create from dictionary."""
        data = data.copy()
        if "ts" in data and isinstance(data["ts"], str):
            data["ts"] = datetime.fromisoformat(data["ts"].replace("Z", "+00:00"))
        return cls(**data)


@dataclass
class CheckpointQuery:
    """Query parameters for finding checkpoints."""

    index_name: Optional[str] = None
    shard_id: Optional[str] = None
    position_min: Optional[int] = None
    position_max: Optional[int] = None
    limit: int = 100


@dataclass
class RebuildStatus:
    """Status information for index rebuild operations."""

    index_name: str
    total_shards: int
    completed_shards: int
    current_position: int
    target_position: int
    started_at: datetime
    estimated_completion: Optional[datetime] = None
    is_degraded: bool = False

    @property
    def progress_percent(self) -> float:
        """Calculate rebuild progress percentage."""
        if self.target_position == 0:
            return 100.0
        return min(100.0, (self.current_position / self.target_position) * 100.0)


class IndexCheckpointStore(BaseStore):
    """
    Storage for index checkpoint management with P13 pipeline integration.

    Supports:
    - Checkpoint creation and retrieval
    - Rebuild state tracking
    - Graceful degradation coordination
    - Atomic position updates
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._active_rebuilds: Set[str] = set()

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for checkpoint validation."""
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$"},
                "index_name": {"type": "string", "pattern": "^[A-Za-z0-9._:-]{2,64}$"},
                "shard_id": {"type": "string"},
                "position": {"type": "integer", "minimum": 0},
                "content_hash": {"type": "string"},
                "ts": {"type": "string", "format": "date-time"},
                "metadata": {"type": "object"},
            },
            "required": [
                "id",
                "index_name",
                "shard_id",
                "position",
                "content_hash",
                "ts",
            ],
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema and tables."""
        # Main checkpoints table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS index_checkpoints (
                id TEXT PRIMARY KEY,
                index_name TEXT NOT NULL,
                shard_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                ts TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(index_name, shard_id)
            )
        """
        )

        # Indexes for efficient queries
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_index_checkpoints_index_name
            ON index_checkpoints(index_name)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_index_checkpoints_position
            ON index_checkpoints(index_name, position)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_index_checkpoints_ts
            ON index_checkpoints(ts)
        """
        )

        # Rebuild status tracking table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rebuild_status (
                index_name TEXT PRIMARY KEY,
                total_shards INTEGER NOT NULL,
                completed_shards INTEGER DEFAULT 0,
                current_position INTEGER DEFAULT 0,
                target_position INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                estimated_completion TEXT,
                is_degraded INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )
        """
        )

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new checkpoint record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        checkpoint_id = data["id"]

        # Insert or update checkpoint (upsert by index_name + shard_id)
        self._connection.execute(
            """
            INSERT OR REPLACE INTO index_checkpoints
            (id, index_name, shard_id, position, content_hash, ts, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
            (
                checkpoint_id,
                data["index_name"],
                data["shard_id"],
                data["position"],
                data["content_hash"],
                data["ts"],
                json.dumps(data.get("metadata", {})),
            ),
        )

        return data

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a checkpoint record by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            """
            SELECT id, index_name, shard_id, position, content_hash, ts, metadata
            FROM index_checkpoints
            WHERE id = ?
        """,
            (record_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_dict(row)

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing checkpoint record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Build update query
        set_clauses: List[str] = []
        params: List[Any] = []

        for field_name in ["index_name", "shard_id", "position", "content_hash", "ts"]:
            if field_name in data:
                set_clauses.append(f"{field_name} = ?")
                params.append(data[field_name])

        if "metadata" in data:
            set_clauses.append("metadata = ?")
            params.append(json.dumps(data["metadata"]))

        if set_clauses:
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            params.append(record_id)
            self._connection.execute(
                f"""
                UPDATE index_checkpoints
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """,
                params,
            )

        return data

    def _delete_record(self, record_id: str) -> bool:
        """Delete a checkpoint record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            """
            DELETE FROM index_checkpoints WHERE id = ?
        """,
            (record_id,),
        )

        return cursor.rowcount > 0

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List checkpoint records with optional filtering and pagination."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Build query with filters
        where_clauses: List[str] = []
        params: List[Any] = []

        if filters:
            for key, value in filters.items():
                if key in ["index_name", "shard_id", "content_hash"]:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
                elif key == "position_min":
                    where_clauses.append("position >= ?")
                    params.append(value)
                elif key == "position_max":
                    where_clauses.append("position <= ?")
                    params.append(value)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Build full query
        query = f"""
            SELECT id, index_name, shard_id, position, content_hash, ts, metadata
            FROM index_checkpoints
            WHERE {where_sql}
            ORDER BY index_name, shard_id, position DESC
        """

        if limit is not None:
            query += f" LIMIT {limit}"
            if offset is not None:
                query += f" OFFSET {offset}"

        cursor = self._connection.execute(query, params)
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    # High-level checkpoint operations

    def create_checkpoint(self, checkpoint: IndexCheckpoint) -> str:
        """Create a new index checkpoint."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Validate index name pattern
        if not self._validate_index_name(checkpoint.index_name):
            raise ValueError(f"Invalid index name format: {checkpoint.index_name}")

        data = checkpoint.to_dict()
        self._create_record(data)

        logger.info(
            f"Created checkpoint {checkpoint.id} for index {checkpoint.index_name}:{checkpoint.shard_id} "
            f"at position {checkpoint.position}"
        )

        return checkpoint.id

    def get_checkpoint(self, checkpoint_id: str) -> Optional[IndexCheckpoint]:
        """Get a checkpoint by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        data = self._read_record(checkpoint_id)
        if not data:
            return None

        return IndexCheckpoint.from_dict(data)

    def get_latest_checkpoint(
        self, index_name: str, shard_id: str
    ) -> Optional[IndexCheckpoint]:
        """Get the latest checkpoint for an index shard."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            """
            SELECT id, index_name, shard_id, position, content_hash, ts, metadata
            FROM index_checkpoints
            WHERE index_name = ? AND shard_id = ?
            ORDER BY position DESC, ts DESC
            LIMIT 1
        """,
            (index_name, shard_id),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return IndexCheckpoint.from_dict(self._row_to_dict(row))

    def query_checkpoints(self, query: CheckpointQuery) -> List[IndexCheckpoint]:
        """Query checkpoints based on criteria."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Build dynamic query
        where_clauses = []
        params = []

        if query.index_name:
            where_clauses.append("index_name = ?")
            params.append(query.index_name)

        if query.shard_id:
            where_clauses.append("shard_id = ?")
            params.append(query.shard_id)

        if query.position_min is not None:
            where_clauses.append("position >= ?")
            params.append(query.position_min)

        if query.position_max is not None:
            where_clauses.append("position <= ?")
            params.append(query.position_max)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        cursor = self._connection.execute(
            f"""
            SELECT id, index_name, shard_id, position, content_hash, ts, metadata
            FROM index_checkpoints
            WHERE {where_sql}
            ORDER BY index_name, shard_id, position DESC
            LIMIT ?
        """,
            params + [query.limit],
        )

        return [
            IndexCheckpoint.from_dict(self._row_to_dict(row))
            for row in cursor.fetchall()
        ]

    # Rebuild status operations

    def start_rebuild(
        self, index_name: str, target_position: int, total_shards: int
    ) -> None:
        """Start an index rebuild operation."""
        if not self._connection:
            raise RuntimeError("No active connection")

        now = datetime.now(timezone.utc)
        self._connection.execute(
            """
            INSERT OR REPLACE INTO rebuild_status
            (index_name, total_shards, completed_shards, current_position, target_position,
             started_at, is_degraded, metadata)
            VALUES (?, ?, 0, 0, ?, ?, 0, '{}')
        """,
            (index_name, total_shards, target_position, now.isoformat()),
        )

        self._active_rebuilds.add(index_name)

        logger.info(
            f"Started rebuild for index {index_name} with target position {target_position}"
        )

    def update_rebuild_progress(
        self, index_name: str, current_position: int, completed_shards: int
    ) -> None:
        """Update rebuild progress."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            """
            UPDATE rebuild_status
            SET current_position = ?, completed_shards = ?
            WHERE index_name = ?
        """,
            (current_position, completed_shards, index_name),
        )

        if cursor.rowcount == 0:
            raise ValueError(f"No active rebuild found for index {index_name}")

    def complete_rebuild(self, index_name: str) -> None:
        """Mark an index rebuild as complete."""
        if not self._connection:
            raise RuntimeError("No active connection")

        self._connection.execute(
            """
            DELETE FROM rebuild_status WHERE index_name = ?
        """,
            (index_name,),
        )

        self._active_rebuilds.discard(index_name)

        logger.info(f"Completed rebuild for index {index_name}")

    def get_rebuild_status(self, index_name: str) -> Optional[RebuildStatus]:
        """Get rebuild status for an index."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            """
            SELECT index_name, total_shards, completed_shards, current_position,
                   target_position, started_at, estimated_completion, is_degraded
            FROM rebuild_status
            WHERE index_name = ?
        """,
            (index_name,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return RebuildStatus(
            index_name=row[0],
            total_shards=row[1],
            completed_shards=row[2],
            current_position=row[3],
            target_position=row[4],
            started_at=datetime.fromisoformat(row[5].replace("Z", "+00:00")),
            estimated_completion=(
                datetime.fromisoformat(row[6].replace("Z", "+00:00"))
                if row[6]
                else None
            ),
            is_degraded=bool(row[7]),
        )

    def set_degraded_mode(self, index_name: str, is_degraded: bool) -> None:
        """Set degraded mode status for an index rebuild."""
        if not self._connection:
            raise RuntimeError("No active connection")

        self._connection.execute(
            """
            UPDATE rebuild_status
            SET is_degraded = ?
            WHERE index_name = ?
        """,
            (int(is_degraded), index_name),
        )

        mode = "degraded" if is_degraded else "normal"
        logger.info(f"Set index {index_name} to {mode} mode")

    def cleanup_old_checkpoints(self, index_name: str, keep_latest: int) -> int:
        """Clean up old checkpoints, keeping only the latest N per shard."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Get checkpoints to delete (keep latest N per shard)
        cursor = self._connection.execute(
            """
            DELETE FROM index_checkpoints
            WHERE index_name = ? AND id NOT IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY shard_id
                               ORDER BY position DESC, ts DESC
                           ) as rn
                    FROM index_checkpoints
                    WHERE index_name = ?
                ) ranked
                WHERE rn <= ?
            )
        """,
            (index_name, index_name, keep_latest),
        )

        deleted_count = cursor.rowcount

        if deleted_count > 0:
            logger.info(
                f"Cleaned up {deleted_count} old checkpoints for index {index_name}"
            )

        return deleted_count

    def is_rebuild_active(self, index_name: str) -> bool:
        """Check if a rebuild is currently active for an index."""
        return index_name in self._active_rebuilds

    def get_all_active_rebuilds(self) -> List[RebuildStatus]:
        """Get status for all active rebuilds."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            """
            SELECT index_name, total_shards, completed_shards, current_position,
                   target_position, started_at, estimated_completion, is_degraded
            FROM rebuild_status
            ORDER BY started_at
        """
        )

        rebuilds = []
        for row in cursor.fetchall():
            rebuilds.append(
                RebuildStatus(
                    index_name=row[0],
                    total_shards=row[1],
                    completed_shards=row[2],
                    current_position=row[3],
                    target_position=row[4],
                    started_at=datetime.fromisoformat(row[5].replace("Z", "+00:00")),
                    estimated_completion=(
                        datetime.fromisoformat(row[6].replace("Z", "+00:00"))
                        if row[6]
                        else None
                    ),
                    is_degraded=bool(row[7]),
                )
            )

        return rebuilds

    # Helper methods

    def _row_to_dict(self, row: Tuple[Any, ...]) -> Dict[str, Any]:
        """Convert database row to dictionary."""
        return {
            "id": row[0],
            "index_name": row[1],
            "shard_id": row[2],
            "position": row[3],
            "content_hash": row[4],
            "ts": row[5],
            "metadata": json.loads(row[6]) if row[6] else {},
        }

    def _validate_index_name(self, index_name: str) -> bool:
        """Validate index name against contract pattern ^[A-Za-z0-9._:-]{2,64}$."""
        import re

        pattern = r"^[A-Za-z0-9._:-]{2,64}$"
        return bool(re.match(pattern, index_name))

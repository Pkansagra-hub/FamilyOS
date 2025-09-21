"""
ML Store - Machine Learning run tracking with BaseStore compliance.

Implements storage for ML runs following ml_run.schema.json contract.
Tracks ML experiments, model training runs, and evaluation results.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore

logger = logging.getLogger(__name__)


@dataclass
class MLRun:
    """
    ML run record following ml_run.schema.json contract.

    Represents a machine learning training or evaluation run with parameters and status tracking.
    """

    id: str  # ULID
    ts: str  # Timestamp
    space_id: str
    name: str
    params: Dict[str, Any]
    status: str = "pending"  # pending, running, complete, failed


class MLStore(BaseStore):
    """
    ML Store for machine learning run tracking.

    Provides comprehensive ML run management with:
    - Run lifecycle tracking (pending → running → complete/failed)
    - Parameter and configuration storage
    - Space-scoped access controls
    - Run querying and filtering capabilities

    Storage Model:
    - ml_runs table: Run metadata with JSON params
    """

    def __init__(self, config: Any) -> None:
        """Initialize ML store with runs table schema."""
        super().__init__(config)
        logger.info("MLStore initialized for ML run tracking")

    def _get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for ML run validation."""
        return {
            "type": "object",
            "required": ["id", "ts", "space_id", "name", "params"],
            "properties": {
                "id": {"type": "string"},
                "ts": {"type": "string", "format": "date-time"},
                "space_id": {"type": "string"},
                "name": {"type": "string"},
                "params": {"type": "object"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "running", "complete", "failed"],
                },
            },
        }

    def _get_sql_schema(self) -> str:
        """Return SQL schema for ML runs table."""
        return """
        CREATE TABLE IF NOT EXISTS ml_runs (
            id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            space_id TEXT NOT NULL,
            name TEXT NOT NULL,
            params TEXT NOT NULL,  -- JSON object
            status TEXT NOT NULL DEFAULT 'pending',
            created_ts TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_ts TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_ml_runs_space_id ON ml_runs(space_id);
        CREATE INDEX IF NOT EXISTS idx_ml_runs_ts ON ml_runs(ts);
        CREATE INDEX IF NOT EXISTS idx_ml_runs_status ON ml_runs(status);
        CREATE INDEX IF NOT EXISTS idx_ml_runs_name ON ml_runs(name);
        CREATE INDEX IF NOT EXISTS idx_ml_runs_space_status ON ml_runs(space_id, status);
        """

    def _initialize_schema(self, conn: Any) -> None:
        """Initialize ML runs database schema."""
        conn.executescript(self._get_sql_schema())
        logger.info("ML store schema initialized with runs table")

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a generic record (converts to MLRun and calls create_run)."""
        ml_run = MLRun(
            id=data["id"],
            ts=data["ts"],
            space_id=data["space_id"],
            name=data["name"],
            params=data["params"],
            status=data.get("status", "pending"),
        )
        self.create_run(ml_run)
        return asdict(ml_run)

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a generic record (calls get_run and converts to dict)."""
        ml_run = self.get_run(record_id)
        return asdict(ml_run) if ml_run else None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a generic record (calls update_run and returns updated record)."""
        self.update_run(record_id, data)
        updated_run = self.get_run(record_id)
        if not updated_run:
            raise ValueError(f"Failed to update ML run {record_id}")
        return asdict(updated_run)

    def _delete_record(self, record_id: str) -> bool:
        """Delete a generic record (calls delete_run)."""
        try:
            self.delete_run(record_id)
            return True
        except Exception:
            return False

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List generic records (returns ML runs as dicts)."""
        # Extract space_id from filters if provided
        space_id = filters.get("space_id") if filters else None
        runs = self.list_runs(space_id, limit)

        # Apply offset if specified
        if offset and offset > 0:
            runs = runs[offset:]

        return [asdict(run) for run in runs]

    # ML Run Management
    def create_run(self, ml_run: MLRun) -> str:
        """
        Create a new ML run.

        Args:
            ml_run: MLRun instance to store

        Returns:
            run_id: The ID of the created run
        """
        if not self._connection:
            raise RuntimeError("MLStore not in transaction")

        self._connection.execute(
            """
            INSERT INTO ml_runs (id, ts, space_id, name, params, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                ml_run.id,
                ml_run.ts,
                ml_run.space_id,
                ml_run.name,
                json.dumps(ml_run.params),
                ml_run.status,
            ),
        )

        logger.info(
            f"Created ML run {ml_run.id} ({ml_run.name}) in space {ml_run.space_id}"
        )
        return ml_run.id

    def get_run(self, run_id: str) -> Optional[MLRun]:
        """
        Retrieve an ML run by ID.

        Args:
            run_id: The run ID to retrieve

        Returns:
            MLRun instance or None if not found
        """
        if not self._connection:
            raise RuntimeError("MLStore not in transaction")

        cursor = self._connection.execute(
            """
            SELECT id, ts, space_id, name, params, status
            FROM ml_runs WHERE id = ?
        """,
            (run_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return MLRun(
            id=row[0],
            ts=row[1],
            space_id=row[2],
            name=row[3],
            params=json.loads(row[4]),
            status=row[5],
        )

    def update_run(self, run_id: str, updates: Dict[str, Any]) -> None:
        """
        Update an ML run.

        Args:
            run_id: The run ID to update
            updates: Dictionary of fields to update
        """
        if not self._connection:
            raise RuntimeError("MLStore not in transaction")

        # Build dynamic update query
        update_fields: List[str] = []
        values: List[Any] = []

        if "status" in updates:
            update_fields.append("status = ?")
            values.append(updates["status"])

        if "params" in updates:
            update_fields.append("params = ?")
            values.append(json.dumps(updates["params"]))

        if "name" in updates:
            update_fields.append("name = ?")
            values.append(updates["name"])

        if not update_fields:
            return

        update_fields.append("updated_ts = CURRENT_TIMESTAMP")
        values.append(run_id)

        self._connection.execute(
            f"""
            UPDATE ml_runs SET {', '.join(update_fields)}
            WHERE id = ?
        """,
            values,
        )

        logger.info(f"Updated ML run {run_id}")

    def update_run_status(self, run_id: str, status: str) -> None:
        """
        Update the status of an ML run.

        Args:
            run_id: The run ID to update
            status: New status (pending, running, complete, failed)
        """
        self.update_run(run_id, {"status": status})

    def delete_run(self, run_id: str) -> None:
        """
        Delete an ML run.

        Args:
            run_id: The run ID to delete
        """
        if not self._connection:
            raise RuntimeError("MLStore not in transaction")

        self._connection.execute("DELETE FROM ml_runs WHERE id = ?", (run_id,))

        logger.info(f"Deleted ML run {run_id}")

    def list_runs(
        self, space_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[MLRun]:
        """
        List ML runs, optionally filtered by space.

        Args:
            space_id: Optional space filter
            limit: Optional result limit

        Returns:
            List of MLRun instances
        """
        if not self._connection:
            raise RuntimeError("MLStore not in transaction")

        if space_id:
            query = """
                SELECT id, ts, space_id, name, params, status
                FROM ml_runs WHERE space_id = ?
                ORDER BY ts DESC
            """
            params = (space_id,)
        else:
            query = """
                SELECT id, ts, space_id, name, params, status
                FROM ml_runs
                ORDER BY ts DESC
            """
            params = ()

        if limit:
            query += f" LIMIT {limit}"

        cursor = self._connection.execute(query, params)
        rows = cursor.fetchall()

        runs = []
        for row in rows:
            run = MLRun(
                id=row[0],
                ts=row[1],
                space_id=row[2],
                name=row[3],
                params=json.loads(row[4]),
                status=row[5],
            )
            runs.append(run)

        return runs

    def list_runs_by_status(
        self, status: str, space_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[MLRun]:
        """
        List ML runs filtered by status.

        Args:
            status: Status filter (pending, running, complete, failed)
            space_id: Optional space filter
            limit: Optional result limit

        Returns:
            List of MLRun instances with specified status
        """
        if not self._connection:
            raise RuntimeError("MLStore not in transaction")

        if space_id:
            query = """
                SELECT id, ts, space_id, name, params, status
                FROM ml_runs WHERE space_id = ? AND status = ?
                ORDER BY ts DESC
            """
            params = (space_id, status)
        else:
            query = """
                SELECT id, ts, space_id, name, params, status
                FROM ml_runs WHERE status = ?
                ORDER BY ts DESC
            """
            params = (status,)

        if limit:
            query += f" LIMIT {limit}"

        cursor = self._connection.execute(query, params)
        rows = cursor.fetchall()

        runs = []
        for row in rows:
            run = MLRun(
                id=row[0],
                ts=row[1],
                space_id=row[2],
                name=row[3],
                params=json.loads(row[4]),
                status=row[5],
            )
            runs.append(run)

        return runs

    def list_runs_by_name(
        self, name: str, space_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[MLRun]:
        """
        List ML runs filtered by name.

        Args:
            name: Run name filter
            space_id: Optional space filter
            limit: Optional result limit

        Returns:
            List of MLRun instances with specified name
        """
        if not self._connection:
            raise RuntimeError("MLStore not in transaction")

        if space_id:
            query = """
                SELECT id, ts, space_id, name, params, status
                FROM ml_runs WHERE space_id = ? AND name = ?
                ORDER BY ts DESC
            """
            params = (space_id, name)
        else:
            query = """
                SELECT id, ts, space_id, name, params, status
                FROM ml_runs WHERE name = ?
                ORDER BY ts DESC
            """
            params = (name,)

        if limit:
            query += f" LIMIT {limit}"

        cursor = self._connection.execute(query, params)
        rows = cursor.fetchall()

        runs = []
        for row in rows:
            run = MLRun(
                id=row[0],
                ts=row[1],
                space_id=row[2],
                name=row[3],
                params=json.loads(row[4]),
                status=row[5],
            )
            runs.append(run)

        return runs

    def get_run_stats(self, space_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get ML run statistics.

        Args:
            space_id: Optional space filter

        Returns:
            Dictionary with run counts by status and other stats
        """
        if not self._connection:
            raise RuntimeError("MLStore not in transaction")

        # Get total count
        if space_id:
            cursor = self._connection.execute(
                "SELECT COUNT(*) FROM ml_runs WHERE space_id = ?", (space_id,)
            )
        else:
            cursor = self._connection.execute("SELECT COUNT(*) FROM ml_runs")
        total_runs = cursor.fetchone()[0]

        # Get status breakdown
        if space_id:
            cursor = self._connection.execute(
                """
                SELECT status, COUNT(*) FROM ml_runs WHERE space_id = ? GROUP BY status
            """,
                (space_id,),
            )
        else:
            cursor = self._connection.execute(
                "SELECT status, COUNT(*) FROM ml_runs GROUP BY status"
            )

        status_counts = {}
        for row in cursor.fetchall():
            status_counts[row[0]] = row[1]

        # Get unique run names
        if space_id:
            cursor = self._connection.execute(
                """
                SELECT COUNT(DISTINCT name) FROM ml_runs WHERE space_id = ?
            """,
                (space_id,),
            )
        else:
            cursor = self._connection.execute(
                "SELECT COUNT(DISTINCT name) FROM ml_runs"
            )
        unique_names = cursor.fetchone()[0]

        return {
            "total_runs": total_runs,
            "status_counts": status_counts,
            "unique_run_names": unique_names,
        }

    def cleanup_old_runs(
        self,
        older_than_days: int,
        status_filter: Optional[str] = None,
        space_id: Optional[str] = None,
    ) -> int:
        """
        Clean up old ML runs based on age and optionally status.

        Args:
            older_than_days: Delete runs older than this many days
            status_filter: Optional status filter (only delete runs with this status)
            space_id: Optional space filter

        Returns:
            Number of runs deleted
        """
        if not self._connection:
            raise RuntimeError("MLStore not in transaction")

        cutoff_ts = datetime.now(timezone.utc).timestamp() - (
            older_than_days * 24 * 60 * 60
        )
        cutoff_iso = datetime.fromtimestamp(cutoff_ts, timezone.utc).isoformat()

        # Build dynamic query
        where_clauses = ["ts < ?"]
        params: List[Any] = [cutoff_iso]

        if space_id:
            where_clauses.append("space_id = ?")
            params.append(space_id)

        if status_filter:
            where_clauses.append("status = ?")
            params.append(status_filter)

        where_clause = " AND ".join(where_clauses)

        # First count what we'll delete
        cursor = self._connection.execute(
            f"SELECT COUNT(*) FROM ml_runs WHERE {where_clause}", params
        )
        delete_count = cursor.fetchone()[0]

        # Then delete
        if delete_count > 0:
            self._connection.execute(
                f"DELETE FROM ml_runs WHERE {where_clause}", params
            )
            logger.info(
                f"Cleaned up {delete_count} old ML runs (older than {older_than_days} days)"
            )

        return delete_count

"""
ProspectiveStore - Storage for prospective memory triggers and tasks.

Stores and manages prospective triggers, schedules, actions, and state tracking
for future-oriented cognition in MemoryOS.
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig


def _default_dict() -> Dict[str, Any]:
    """Return empty dict for default values."""
    return {}


@dataclass
class ProspectiveTask:
    """Prospective task/trigger with schedule and action."""

    id: str
    space_id: str
    due_ts: datetime
    state: str  # scheduled, deferred, fired, completed, cancelled
    payload: Dict[str, Any]

    # Optional fields
    created_ts: Optional[datetime] = None
    band: str = "GREEN"
    repeat: Optional[str] = None  # cron or RRULE format
    ttl: Optional[str] = None

    # Metadata
    title: Optional[str] = None
    person_id: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=_default_dict)
    action: Dict[str, Any] = field(default_factory=_default_dict)
    schedule: Dict[str, Any] = field(default_factory=_default_dict)

    # Execution tracking
    last_fired_ts: Optional[datetime] = None
    fire_count: int = 0
    skip_count: int = 0
    eligibility_score: float = 1.0


class ProspectiveStore(BaseStore):
    """Storage for prospective memory triggers and tasks."""

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for this store's data."""
        return {
            "prospective_task": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "space_id": {"type": "string"},
                    "due_ts": {"type": "string"},
                    "state": {
                        "type": "string",
                        "enum": [
                            "scheduled",
                            "deferred",
                            "fired",
                            "completed",
                            "cancelled",
                        ],
                    },
                    "payload": {"type": "object"},
                },
                "required": ["id", "space_id", "due_ts", "state", "payload"],
            }
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema."""
        conn.executescript(
            """
        CREATE TABLE IF NOT EXISTS prospective_tasks (
            id TEXT PRIMARY KEY,
            space_id TEXT NOT NULL,
            due_ts TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'scheduled',
            payload TEXT NOT NULL,              -- JSON object
            created_ts TEXT,
            band TEXT DEFAULT 'GREEN',
            repeat_rule TEXT,                   -- cron or RRULE format
            ttl TEXT,
            title TEXT,
            person_id TEXT,
            conditions TEXT,                    -- JSON object for gating conditions
            action TEXT,                        -- JSON object for action spec
            schedule TEXT,                      -- JSON object for schedule spec
            last_fired_ts TEXT,
            fire_count INTEGER DEFAULT 0,
            skip_count INTEGER DEFAULT 0,
            eligibility_score REAL DEFAULT 1.0
        );

        CREATE INDEX IF NOT EXISTS idx_prospective_tasks_space
        ON prospective_tasks (space_id);

        CREATE INDEX IF NOT EXISTS idx_prospective_tasks_due
        ON prospective_tasks (due_ts);

        CREATE INDEX IF NOT EXISTS idx_prospective_tasks_state
        ON prospective_tasks (state);

        CREATE INDEX IF NOT EXISTS idx_prospective_tasks_person
        ON prospective_tasks (person_id);

        CREATE INDEX IF NOT EXISTS idx_prospective_tasks_band
        ON prospective_tasks (band);
        """
        )

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new prospective task record."""
        # Generate ID if not provided
        if "id" not in data:
            data["id"] = f"pros-{uuid.uuid4().hex}"

        # Handle timestamps
        now = datetime.now(timezone.utc)

        if "due_ts" in data:
            if isinstance(data["due_ts"], str):
                due_ts = datetime.fromisoformat(data["due_ts"].replace("Z", "+00:00"))
            else:
                due_ts = data["due_ts"]
        else:
            raise ValueError("due_ts is required for prospective tasks")

        if "created_ts" in data:
            if isinstance(data["created_ts"], str):
                created_ts = datetime.fromisoformat(
                    data["created_ts"].replace("Z", "+00:00")
                )
            else:
                created_ts = data["created_ts"]
        else:
            created_ts = now

        if "last_fired_ts" in data and data["last_fired_ts"]:
            if isinstance(data["last_fired_ts"], str):
                last_fired_ts = datetime.fromisoformat(
                    data["last_fired_ts"].replace("Z", "+00:00")
                )
            else:
                last_fired_ts = data["last_fired_ts"]
        else:
            last_fired_ts = None

        task = ProspectiveTask(
            id=data["id"],
            space_id=data.get("space_id", "default"),
            due_ts=due_ts,
            state=data.get("state", "scheduled"),
            payload=data.get("payload", {}),
            created_ts=created_ts,
            band=data.get("band", "GREEN"),
            repeat=data.get("repeat"),
            ttl=data.get("ttl"),
            title=data.get("title"),
            person_id=data.get("person_id"),
            conditions=data.get("conditions", {}),
            action=data.get("action", {}),
            schedule=data.get("schedule", {}),
            last_fired_ts=last_fired_ts,
            fire_count=data.get("fire_count", 0),
            skip_count=data.get("skip_count", 0),
            eligibility_score=data.get("eligibility_score", 1.0),
        )

        if not self._connection:
            raise RuntimeError("No database connection")

        self._connection.execute(
            """
            INSERT INTO prospective_tasks
            (id, space_id, due_ts, state, payload, created_ts, band, repeat_rule,
             ttl, title, person_id, conditions, action, schedule, last_fired_ts,
             fire_count, skip_count, eligibility_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                task.id,
                task.space_id,
                task.due_ts.isoformat(),
                task.state,
                json.dumps(task.payload),
                task.created_ts.isoformat() if task.created_ts else None,
                task.band,
                task.repeat,
                task.ttl,
                task.title,
                task.person_id,
                json.dumps(task.conditions),
                json.dumps(task.action),
                json.dumps(task.schedule),
                task.last_fired_ts.isoformat() if task.last_fired_ts else None,
                task.fire_count,
                task.skip_count,
                task.eligibility_score,
            ),
        )

        return {
            "record_id": task.id,
            "id": task.id,
            "space_id": task.space_id,
            "due_ts": task.due_ts.isoformat(),
            "state": task.state,
            "payload": task.payload,
            "created_ts": task.created_ts.isoformat() if task.created_ts else None,
            "band": task.band,
            "repeat": task.repeat,
            "ttl": task.ttl,
            "title": task.title,
            "person_id": task.person_id,
            "conditions": task.conditions,
            "action": task.action,
            "schedule": task.schedule,
            "last_fired_ts": (
                task.last_fired_ts.isoformat() if task.last_fired_ts else None
            ),
            "fire_count": task.fire_count,
            "skip_count": task.skip_count,
            "eligibility_score": task.eligibility_score,
        }

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a prospective task record by ID."""
        if not self._connection:
            raise RuntimeError("No database connection")

        cursor = self._connection.execute(
            "SELECT * FROM prospective_tasks WHERE id = ?", (record_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "space_id": row[1],
            "due_ts": row[2],
            "state": row[3],
            "payload": json.loads(row[4] or "{}"),
            "created_ts": row[5],
            "band": row[6],
            "repeat": row[7],
            "ttl": row[8],
            "title": row[9],
            "person_id": row[10],
            "conditions": json.loads(row[11] or "{}"),
            "action": json.loads(row[12] or "{}"),
            "schedule": json.loads(row[13] or "{}"),
            "last_fired_ts": row[14],
            "fire_count": row[15] or 0,
            "skip_count": row[16] or 0,
            "eligibility_score": row[17] or 1.0,
        }

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing prospective task record."""
        if not self._connection:
            raise RuntimeError("No database connection")

        # Read current record
        current = self._read_record(record_id)
        if not current:
            raise ValueError(f"Record {record_id} not found")

        # Update fields
        for key in [
            "state",
            "due_ts",
            "payload",
            "band",
            "repeat",
            "ttl",
            "title",
            "person_id",
            "conditions",
            "action",
            "schedule",
            "last_fired_ts",
            "fire_count",
            "skip_count",
            "eligibility_score",
        ]:
            if key in data:
                current[key] = data[key]

        # Handle timestamp conversion for due_ts and last_fired_ts
        if "due_ts" in data and isinstance(data["due_ts"], datetime):
            current["due_ts"] = data["due_ts"].isoformat()
        if "last_fired_ts" in data and isinstance(data["last_fired_ts"], datetime):
            current["last_fired_ts"] = data["last_fired_ts"].isoformat()

        self._connection.execute(
            """
            UPDATE prospective_tasks
            SET state = ?, due_ts = ?, payload = ?, band = ?, repeat_rule = ?,
                ttl = ?, title = ?, person_id = ?, conditions = ?, action = ?,
                schedule = ?, last_fired_ts = ?, fire_count = ?, skip_count = ?,
                eligibility_score = ?
            WHERE id = ?
        """,
            (
                current["state"],
                current["due_ts"],
                json.dumps(current["payload"]),
                current["band"],
                current["repeat"],
                current["ttl"],
                current["title"],
                current["person_id"],
                json.dumps(current["conditions"]),
                json.dumps(current["action"]),
                json.dumps(current["schedule"]),
                current["last_fired_ts"],
                current["fire_count"],
                current["skip_count"],
                current["eligibility_score"],
                record_id,
            ),
        )

        return current

    def _delete_record(self, record_id: str) -> bool:
        """Delete a prospective task record."""
        if not self._connection:
            raise RuntimeError("No database connection")

        cursor = self._connection.execute(
            "DELETE FROM prospective_tasks WHERE id = ?", (record_id,)
        )
        return cursor.rowcount > 0

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List prospective task records with optional filtering and pagination."""
        if not self._connection:
            raise RuntimeError("No database connection")

        query = "SELECT * FROM prospective_tasks"
        params: List[Any] = []

        if filters:
            conditions: List[str] = []
            if "space_id" in filters:
                conditions.append("space_id = ?")
                params.append(filters["space_id"])
            if "person_id" in filters:
                conditions.append("person_id = ?")
                params.append(filters["person_id"])
            if "state" in filters:
                conditions.append("state = ?")
                params.append(filters["state"])
            if "band" in filters:
                conditions.append("band = ?")
                params.append(filters["band"])
            if "due_before" in filters:
                conditions.append("due_ts <= ?")
                params.append(filters["due_before"])
            if "due_after" in filters:
                conditions.append("due_ts >= ?")
                params.append(filters["due_after"])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY due_ts ASC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)

        cursor = self._connection.execute(query, params)
        results: List[Dict[str, Any]] = []

        for row in cursor.fetchall():
            results.append(
                {
                    "id": row[0],
                    "space_id": row[1],
                    "due_ts": row[2],
                    "state": row[3],
                    "payload": json.loads(row[4] or "{}"),
                    "created_ts": row[5],
                    "band": row[6],
                    "repeat": row[7],
                    "ttl": row[8],
                    "title": row[9],
                    "person_id": row[10],
                    "conditions": json.loads(row[11] or "{}"),
                    "action": json.loads(row[12] or "{}"),
                    "schedule": json.loads(row[13] or "{}"),
                    "last_fired_ts": row[14],
                    "fire_count": row[15] or 0,
                    "skip_count": row[16] or 0,
                    "eligibility_score": row[17] or 1.0,
                }
            )

        return results

    # High-level API methods

    def get_due_tasks(
        self, space_id: str, cutoff_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get tasks that are due for execution."""
        if cutoff_time is None:
            cutoff_time = datetime.now(timezone.utc)

        filters = {
            "space_id": space_id,
            "state": "scheduled",
            "due_before": cutoff_time.isoformat(),
        }

        return self._list_records(filters=filters, limit=100)

    def get_upcoming_tasks(
        self, space_id: str, hours_ahead: int = 24, person_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get tasks due in the next N hours."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(hours=hours_ahead)

        filters = {
            "space_id": space_id,
            "state": "scheduled",
            "due_after": now.isoformat(),
            "due_before": cutoff.isoformat(),
        }

        if person_id:
            filters["person_id"] = person_id

        return self._list_records(filters=filters, limit=50)

    def mark_task_fired(
        self, task_id: str, eligibility_score: float = 1.0
    ) -> Dict[str, Any]:
        """Mark a task as fired and update statistics."""
        task = self._read_record(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        fire_count = task.get("fire_count", 0) + 1

        update_data: Dict[str, Any] = {
            "state": "fired",
            "last_fired_ts": datetime.now(timezone.utc),
            "fire_count": fire_count,
            "eligibility_score": eligibility_score,
        }

        return self._update_record(task_id, update_data)

    def mark_task_skipped(
        self, task_id: str, next_due_ts: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Mark a task as skipped and optionally reschedule."""
        task = self._read_record(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        skip_count = task.get("skip_count", 0) + 1

        update_data = {"skip_count": skip_count}

        if next_due_ts:
            update_data["due_ts"] = next_due_ts
            update_data["state"] = "scheduled"
        else:
            update_data["state"] = "deferred"

        return self._update_record(task_id, update_data)

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a task."""
        return self._update_record(task_id, {"state": "cancelled"})

    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Mark a task as completed."""
        return self._update_record(task_id, {"state": "completed"})

    def store_prospective_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """High-level method to store a prospective task."""
        return self.create(task_data)

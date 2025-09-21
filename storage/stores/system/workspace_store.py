"""
WorkspaceStore - Global workspace state storage for MemoryOS.

Stores and manages global workspace state including working memory items,
salience scores, attention focus, and workspace broadcasts.
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig


@dataclass
class WorkspaceItem:
    """Working memory item with salience and metadata."""

    item_id: str
    content: str
    item_type: str  # "memory", "goal", "context", "reminder"
    salience: float
    embedding: Optional[List[float]] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    decay_rate: float = 0.1
    space_id: str = "default"
    person_id: Optional[str] = None


@dataclass
class WorkspaceState:
    """Current state of global workspace."""

    state_id: str
    focus: List[str] = field(default_factory=list)  # item_ids in focus
    summary: str = ""
    band: str = "GREEN"
    salience: List[Dict[str, Any]] = field(default_factory=list)  # [{id, score}]
    space_id: str = "default"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: Dict[str, Any] = field(default_factory=dict)


class WorkspaceStore(BaseStore):
    """Storage for global workspace state and working memory."""

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for this store's data."""
        return {
            "workspace_state": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "space_id": {"type": "string"},
                    "focus": {"type": "array", "items": {"type": "string"}},
                    "summary": {"type": "string"},
                    "band": {"type": "string"},
                    "salience": {"type": "array"},
                    "timestamp": {"type": "string"},
                    "context": {"type": "object"},
                },
            }
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema."""
        conn.executescript(
            """
        CREATE TABLE IF NOT EXISTS workspace_states (
            id TEXT PRIMARY KEY,
            space_id TEXT NOT NULL,
            focus TEXT,      -- JSON array of item_ids
            summary TEXT NOT NULL,
            band TEXT DEFAULT 'GREEN',
            salience TEXT,   -- JSON array of {id, score} objects
            timestamp TEXT NOT NULL,
            context TEXT     -- JSON object
        );

        CREATE INDEX IF NOT EXISTS idx_workspace_states_space
        ON workspace_states (space_id);

        CREATE INDEX IF NOT EXISTS idx_workspace_states_timestamp
        ON workspace_states (timestamp DESC);
        """
        )

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workspace state record."""
        # Generate ID if not provided
        if "id" not in data:
            data["id"] = f"ws-{uuid.uuid4().hex}"

        workspace_state = WorkspaceState(
            state_id=data["id"],
            focus=data.get("focus", []),
            summary=data.get("summary", ""),
            band=data.get("band", "GREEN"),
            salience=data.get("salience", []),
            space_id=data.get("space_id", "default"),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data
                else datetime.now(timezone.utc)
            ),
            context=data.get("context", {}),
        )

        if not self._connection:
            raise RuntimeError("No database connection")

        self._connection.execute(
            """
            INSERT INTO workspace_states
            (id, space_id, focus, summary, band, salience, timestamp, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                workspace_state.state_id,
                workspace_state.space_id,
                json.dumps(workspace_state.focus),
                workspace_state.summary,
                workspace_state.band,
                json.dumps(workspace_state.salience),
                workspace_state.timestamp.isoformat(),
                json.dumps(workspace_state.context),
            ),
        )

        return {
            "record_id": workspace_state.state_id,
            "id": workspace_state.state_id,
            "space_id": workspace_state.space_id,
            "focus": workspace_state.focus,
            "summary": workspace_state.summary,
            "band": workspace_state.band,
            "salience": workspace_state.salience,
            "timestamp": workspace_state.timestamp.isoformat(),
            "context": workspace_state.context,
        }

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a workspace state record by ID."""
        if not self._connection:
            raise RuntimeError("No database connection")

        cursor = self._connection.execute(
            "SELECT * FROM workspace_states WHERE id = ?", (record_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "space_id": row[1],
            "focus": json.loads(row[2] or "[]"),
            "summary": row[3],
            "band": row[4],
            "salience": json.loads(row[5] or "[]"),
            "timestamp": row[6],
            "context": json.loads(row[7] or "{}"),
        }

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing workspace state record."""
        if not self._connection:
            raise RuntimeError("No database connection")

        # Read current record
        current = self._read_record(record_id)
        if not current:
            raise ValueError(f"Record {record_id} not found")

        # Update fields
        current.update(data)

        self._connection.execute(
            """
            UPDATE workspace_states
            SET space_id = ?, focus = ?, summary = ?, band = ?,
                salience = ?, timestamp = ?, context = ?
            WHERE id = ?
        """,
            (
                current["space_id"],
                json.dumps(current["focus"]),
                current["summary"],
                current["band"],
                json.dumps(current["salience"]),
                current["timestamp"],
                json.dumps(current["context"]),
                record_id,
            ),
        )

        return current

    def _delete_record(self, record_id: str) -> bool:
        """Delete a workspace state record."""
        if not self._connection:
            raise RuntimeError("No database connection")

        cursor = self._connection.execute(
            "DELETE FROM workspace_states WHERE id = ?", (record_id,)
        )
        return cursor.rowcount > 0

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List workspace state records with optional filtering and pagination."""
        if not self._connection:
            raise RuntimeError("No database connection")

        query = "SELECT * FROM workspace_states"
        params = []

        if filters:
            conditions = []
            if "space_id" in filters:
                conditions.append("space_id = ?")
                params.append(filters["space_id"])
            if "band" in filters:
                conditions.append("band = ?")
                params.append(filters["band"])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)

        cursor = self._connection.execute(query, params)
        results = []

        for row in cursor.fetchall():
            results.append(
                {
                    "id": row[0],
                    "space_id": row[1],
                    "focus": json.loads(row[2] or "[]"),
                    "summary": row[3],
                    "band": row[4],
                    "salience": json.loads(row[5] or "[]"),
                    "timestamp": row[6],
                    "context": json.loads(row[7] or "{}"),
                }
            )

        return results

    # High-level API methods

    def get_current_workspace_state(self, space_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent workspace state for a space."""
        records = self._list_records(filters={"space_id": space_id}, limit=1)
        return records[0] if records else None

    def get_workspace_summary(self, space_id: str) -> str:
        """Get workspace summary for a space."""
        state = self.get_current_workspace_state(space_id)
        return state["summary"] if state else "No workspace state available"

    def update_workspace_focus(
        self, space_id: str, focus_items: List[str]
    ) -> Dict[str, Any]:
        """Update the focus items in workspace."""
        current_state = self.get_current_workspace_state(space_id)

        if current_state:
            return self._update_record(
                current_state["id"],
                {
                    "focus": focus_items,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            # Create new state
            return self._create_record(
                {
                    "space_id": space_id,
                    "focus": focus_items,
                    "summary": "New workspace state",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

    def update_salience_scores(
        self, space_id: str, salience_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Update salience scores in workspace."""
        current_state = self.get_current_workspace_state(space_id)

        if current_state:
            return self._update_record(
                current_state["id"],
                {
                    "salience": salience_data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        else:
            # Create new state
            return self._create_record(
                {
                    "space_id": space_id,
                    "salience": salience_data,
                    "summary": "New workspace state with salience",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

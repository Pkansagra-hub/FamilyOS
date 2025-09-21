"""
WorkspaceStore - Global workspace state storage for MemoryOS.

Stores and manages global workspace state including working memory items,
salience scores, attention focus, and workspace broadcasts.
"""

import json
import logging
import sqlite3
from dataclasses import asdict, dataclass, field
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

    active_items: List[WorkspaceItem] = field(default_factory=list)
    attention_focus: Optional[str] = None  # Current focus item_id
    total_salience: float = 0.0
    capacity_used: int = 0
    max_capacity: int = 8  # Working memory capacity
    last_broadcast: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkspaceBroadcast:
    """Workspace broadcast event."""

    broadcast_id: str
    workspace_state: WorkspaceState
    recipients: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: Optional[str] = None


class WorkspaceStore(BaseStore):
    """Storage for global workspace state and working memory."""

    def __init__(self, config: StoreConfig):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema."""
        conn.executescript(self._get_schema())

    def _get_schema(self) -> str:
        """Get the database schema for workspace storage."""
        return """
        CREATE TABLE IF NOT EXISTS workspace_items (
            item_id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            item_type TEXT NOT NULL,
            salience REAL NOT NULL,
            embedding TEXT,  -- JSON array
            tags TEXT,       -- JSON array
            created_at TEXT NOT NULL,
            last_accessed TEXT NOT NULL,
            access_count INTEGER DEFAULT 0,
            decay_rate REAL DEFAULT 0.1,
            space_id TEXT NOT NULL,
            person_id TEXT
        );

        CREATE TABLE IF NOT EXISTS workspace_states (
            state_id TEXT PRIMARY KEY,
            active_items TEXT,      -- JSON array of item_ids
            attention_focus TEXT,
            total_salience REAL,
            capacity_used INTEGER,
            max_capacity INTEGER DEFAULT 8,
            last_broadcast TEXT,
            context TEXT,           -- JSON object
            timestamp TEXT NOT NULL,
            space_id TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS workspace_broadcasts (
            broadcast_id TEXT PRIMARY KEY,
            workspace_state TEXT NOT NULL,  -- JSON WorkspaceState
            recipients TEXT,                -- JSON array
            timestamp TEXT NOT NULL,
            trace_id TEXT,
            space_id TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_workspace_items_salience
        ON workspace_items (salience DESC);

        CREATE INDEX IF NOT EXISTS idx_workspace_items_space
        ON workspace_items (space_id);

        CREATE INDEX IF NOT EXISTS idx_workspace_states_timestamp
        ON workspace_states (timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_workspace_broadcasts_timestamp
        ON workspace_broadcasts (timestamp DESC);
        """

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record."""
        # Determine record type from data structure
        if "item_id" in data and "content" in data and "salience" in data:
            record_id = self._create_workspace_item(data)
            return {"record_id": record_id, **data}
        elif "active_items" in data and "attention_focus" in data:
            record_id = self._create_workspace_state(data)
            return {"record_id": record_id, **data}
        elif "broadcast_id" in data and "workspace_state" in data:
            record_id = self._create_workspace_broadcast(data)
            return {"record_id": record_id, **data}
        else:
            raise ValueError("Unknown record type for workspace store")

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record by ID."""
        # Try workspace item first
        item = self._read_workspace_item(record_id)
        if item:
            return item

        # Try workspace state
        state = self._read_workspace_state(record_id)
        if state:
            return state

        # Try workspace broadcast
        broadcast = self._read_workspace_broadcast(record_id)
        if broadcast:
            return broadcast

        return None

    def _update_record(
        self,
        conn: sqlite3.Connection,
        record_type: str,
        record_id: str,
        data: Dict[str, Any],
    ) -> bool:
        """Update an existing record."""
        if record_type == "workspace_item":
            # Update workspace item salience and access info
            conn.execute(
                """
                UPDATE workspace_items
                SET salience = ?, last_accessed = ?, access_count = access_count + 1
                WHERE item_id = ?
            """,
                (
                    data.get("salience", 0.0),
                    datetime.now(timezone.utc).isoformat(),
                    record_id,
                ),
            )
            return True

        elif record_type == "workspace_state":
            # Update workspace state
            conn.execute(
                """
                UPDATE workspace_states
                SET attention_focus = ?, total_salience = ?, capacity_used = ?
                WHERE state_id = ?
            """,
                (
                    data.get("attention_focus"),
                    data.get("total_salience", 0.0),
                    data.get("capacity_used", 0),
                    record_id,
                ),
            )
            return True

        return False

    def _delete_record(
        self, conn: sqlite3.Connection, record_type: str, record_id: str
    ) -> bool:
        """Delete a record."""
        if record_type == "workspace_item":
            cursor = conn.execute(
                "DELETE FROM workspace_items WHERE item_id = ?", (record_id,)
            )
            return cursor.rowcount > 0

        elif record_type == "workspace_state":
            cursor = conn.execute(
                "DELETE FROM workspace_states WHERE state_id = ?", (record_id,)
            )
            return cursor.rowcount > 0

        elif record_type == "workspace_broadcast":
            cursor = conn.execute(
                "DELETE FROM workspace_broadcasts WHERE broadcast_id = ?", (record_id,)
            )
            return cursor.rowcount > 0

        return False

    def _list_records(
        self,
        conn: sqlite3.Connection,
        record_type: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List records with optional filtering."""
        if record_type == "workspace_item":
            query = "SELECT * FROM workspace_items"
            params = []

            if filters:
                conditions = []
                if "space_id" in filters:
                    conditions.append("space_id = ?")
                    params.append(filters["space_id"])
                if "item_type" in filters:
                    conditions.append("item_type = ?")
                    params.append(filters["item_type"])
                if "min_salience" in filters:
                    conditions.append("salience >= ?")
                    params.append(filters["min_salience"])

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY salience DESC"
            if limit:
                query += f" LIMIT {limit}"

            cursor = conn.execute(query, params)
            return [self._row_to_workspace_item(row) for row in cursor.fetchall()]

        elif record_type == "workspace_state":
            query = "SELECT * FROM workspace_states"
            params = []

            if filters and "space_id" in filters:
                query += " WHERE space_id = ?"
                params.append(filters["space_id"])

            query += " ORDER BY timestamp DESC"
            if limit:
                query += f" LIMIT {limit}"

            cursor = conn.execute(query, params)
            return [
                self._row_to_workspace_state(row, conn) for row in cursor.fetchall()
            ]

        elif record_type == "workspace_broadcast":
            query = "SELECT * FROM workspace_broadcasts"
            params = []

            if filters and "space_id" in filters:
                query += " WHERE space_id = ?"
                params.append(filters["space_id"])

            query += " ORDER BY timestamp DESC"
            if limit:
                query += f" LIMIT {limit}"

            cursor = conn.execute(query, params)
            return [self._row_to_workspace_broadcast(row) for row in cursor.fetchall()]

        return []

    def _row_to_workspace_item(self, row) -> Dict[str, Any]:
        """Convert database row to WorkspaceItem dict."""
        return {
            "item_id": row[0],
            "content": row[1],
            "item_type": row[2],
            "salience": row[3],
            "embedding": json.loads(row[4]) if row[4] else None,
            "tags": json.loads(row[5]) if row[5] else [],
            "created_at": datetime.fromisoformat(row[6]),
            "last_accessed": datetime.fromisoformat(row[7]),
            "access_count": row[8],
            "decay_rate": row[9],
            "space_id": row[10],
            "person_id": row[11],
        }

    def _row_to_workspace_state(self, row, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Convert database row to WorkspaceState dict."""
        # Load active items
        active_item_ids = json.loads(row[1]) if row[1] else []
        active_items = []
        for item_id in active_item_ids:
            item_data = self._read_record(conn, "workspace_item", item_id)
            if item_data:
                active_items.append(WorkspaceItem(**item_data))

        return {
            "state_id": row[0],
            "active_items": active_items,
            "attention_focus": row[2],
            "total_salience": row[3],
            "capacity_used": row[4],
            "max_capacity": row[5],
            "last_broadcast": datetime.fromisoformat(row[6]) if row[6] else None,
            "context": json.loads(row[7]) if row[7] else {},
            "timestamp": datetime.fromisoformat(row[8]),
            "space_id": row[9],
        }

    def _row_to_workspace_broadcast(self, row) -> Dict[str, Any]:
        """Convert database row to WorkspaceBroadcast dict."""
        return {
            "broadcast_id": row[0],
            "workspace_state": json.loads(row[1]),
            "recipients": json.loads(row[2]) if row[2] else [],
            "timestamp": datetime.fromisoformat(row[3]),
            "trace_id": row[4],
            "space_id": row[5],
        }

    def _serialize_workspace_state(self, state: WorkspaceState) -> Dict[str, Any]:
        """Serialize WorkspaceState for JSON storage."""
        return {
            "active_items": [asdict(item) for item in state.active_items],
            "attention_focus": state.attention_focus,
            "total_salience": state.total_salience,
            "capacity_used": state.capacity_used,
            "max_capacity": state.max_capacity,
            "last_broadcast": (
                state.last_broadcast.isoformat() if state.last_broadcast else None
            ),
            "context": state.context,
        }

    # High-level API methods

    def add_workspace_item(self, item: WorkspaceItem) -> str:
        """Add item to workspace."""
        return self.create_record("workspace_item", asdict(item))

    def get_workspace_item(self, item_id: str) -> Optional[WorkspaceItem]:
        """Get workspace item by ID."""
        data = self.read_record("workspace_item", item_id)
        return WorkspaceItem(**data) if data else None

    def update_item_salience(self, item_id: str, salience: float) -> bool:
        """Update item salience and access time."""
        return self.update_record("workspace_item", item_id, {"salience": salience})

    def get_active_items(self, space_id: str, limit: int = 8) -> List[WorkspaceItem]:
        """Get most salient active items."""
        items_data = self.list_records(
            "workspace_item",
            filters={"space_id": space_id, "min_salience": 0.1},
            limit=limit,
        )
        return [WorkspaceItem(**item) for item in items_data]

    def save_workspace_state(self, state: WorkspaceState, space_id: str) -> str:
        """Save current workspace state."""
        state_data = asdict(state)
        state_data["space_id"] = space_id
        return self.create_record("workspace_state", state_data)

    def get_latest_workspace_state(self, space_id: str) -> Optional[WorkspaceState]:
        """Get latest workspace state."""
        states = self.list_records(
            "workspace_state", filters={"space_id": space_id}, limit=1
        )
        if states:
            state_data = states[0]
            return WorkspaceState(
                active_items=state_data["active_items"],
                attention_focus=state_data["attention_focus"],
                total_salience=state_data["total_salience"],
                capacity_used=state_data["capacity_used"],
                max_capacity=state_data["max_capacity"],
                last_broadcast=state_data["last_broadcast"],
                context=state_data["context"],
            )
        return None

    def record_broadcast(self, broadcast: WorkspaceBroadcast, space_id: str) -> str:
        """Record workspace broadcast event."""
        broadcast_data = asdict(broadcast)
        broadcast_data["space_id"] = space_id
        return self.create_record("workspace_broadcast", broadcast_data)

    def get_recent_broadcasts(
        self, space_id: str, limit: int = 10
    ) -> List[WorkspaceBroadcast]:
        """Get recent workspace broadcasts."""
        broadcasts_data = self.list_records(
            "workspace_broadcast", filters={"space_id": space_id}, limit=limit
        )
        return [WorkspaceBroadcast(**broadcast) for broadcast in broadcasts_data]

    def cleanup_old_items(self, space_id: str, max_age_hours: int = 24) -> int:
        """Clean up old workspace items."""
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        cutoff_str = datetime.fromtimestamp(cutoff, timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM workspace_items
                WHERE space_id = ? AND last_accessed < ? AND salience < 0.1
            """,
                (space_id, cutoff_str),
            )
            return cursor.rowcount

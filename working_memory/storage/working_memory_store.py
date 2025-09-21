"""
Working Memory Store - Persistent storage for working memory buffer items
========================================================================

This module implements a specialized store for working memory buffer items following
the MemoryOS StoreProtocol interface. It provides transactional storage of working
memory items with session isolation, priority tracking, and activation decay.

The store integrates with the Unit of Work system for atomic operations and proper
transaction management across the working memory subsystem.
"""

import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


@dataclass
class WorkingMemoryItem:
    """Working memory item with persistence fields."""

    id: str
    session_id: str
    content: Any
    item_type: str
    priority: int
    activation: float
    added_at: float
    last_accessed: float
    access_count: int
    tags: List[str]
    metadata: Dict[str, Any]

    # Persistence tracking
    space_id: Optional[str] = None
    actor_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "content": self.content,
            "item_type": self.item_type,
            "priority": self.priority,
            "activation": self.activation,
            "added_at": self.added_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "tags": self.tags,
            "metadata": self.metadata,
            "space_id": self.space_id,
            "actor_id": self.actor_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkingMemoryItem":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class WorkingMemorySession:
    """Working memory session metadata."""

    session_id: str
    space_id: str
    actor_id: str
    created_at: float
    last_active: float
    item_count: int
    capacity: int
    total_access_count: int
    metadata: Dict[str, Any]


class WorkingMemoryStore(BaseStore):
    """
    Storage implementation for working memory buffer items.

    Provides session-scoped persistence with transactional guarantees
    for working memory items and session metadata.
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._store_name = "working_memory"
        self._init_schema()

    def get_store_name(self) -> str:
        """Get the name of this store for tracking and metrics."""
        return self._store_name

    def _init_schema(self) -> None:
        """Initialize the working memory storage schema."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            # Working memory items table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS working_memory_items (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    activation REAL NOT NULL,
                    added_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    space_id TEXT,
                    actor_id TEXT,
                    created_at REAL NOT NULL DEFAULT (strftime('%s', 'now')),
                    updated_at REAL NOT NULL DEFAULT (strftime('%s', 'now')),
                    FOREIGN KEY (session_id) REFERENCES working_memory_sessions(session_id)
                        ON DELETE CASCADE
                )
            """
            )

            # Working memory sessions table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS working_memory_sessions (
                    session_id TEXT PRIMARY KEY,
                    space_id TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_active REAL NOT NULL,
                    item_count INTEGER NOT NULL DEFAULT 0,
                    capacity INTEGER NOT NULL DEFAULT 7,
                    total_access_count INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    updated_at REAL NOT NULL DEFAULT (strftime('%s', 'now'))
                )
            """
            )

            # Indexes for efficient queries
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_wm_items_session_priority
                ON working_memory_items(session_id, priority DESC, activation DESC)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_wm_items_session_activation
                ON working_memory_items(session_id, activation DESC, last_accessed DESC)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_wm_items_type
                ON working_memory_items(item_type, session_id)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_wm_sessions_space_actor
                ON working_memory_sessions(space_id, actor_id, last_active DESC)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_wm_sessions_last_active
                ON working_memory_sessions(last_active DESC)
            """
            )

            conn.commit()

        finally:
            conn.close()

    def store_item(self, item: WorkingMemoryItem) -> str:
        """
        Store or update a working memory item.

        Args:
            item: Working memory item to store

        Returns:
            Item ID

        Raises:
            sqlite3.Error: If storage fails
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction context")

        try:
            # Serialize complex fields
            content_json = json.dumps(item.content)
            tags_json = json.dumps(item.tags)
            metadata_json = json.dumps(item.metadata)

            # Upsert item
            self._connection.execute(
                """
                INSERT OR REPLACE INTO working_memory_items (
                    id, session_id, content_json, item_type, priority,
                    activation, added_at, last_accessed, access_count,
                    tags_json, metadata_json, space_id, actor_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    item.id,
                    item.session_id,
                    content_json,
                    item.item_type,
                    item.priority,
                    item.activation,
                    item.added_at,
                    item.last_accessed,
                    item.access_count,
                    tags_json,
                    metadata_json,
                    item.space_id,
                    item.actor_id,
                    time.time(),
                ),
            )

            logger.debug(
                f"Stored working memory item {item.id} in session {item.session_id}"
            )
            return item.id

        except Exception as e:
            logger.error(f"Failed to store working memory item {item.id}: {e}")
            raise

    def get_item(self, item_id: str) -> Optional[WorkingMemoryItem]:
        """
        Retrieve a working memory item by ID.

        Args:
            item_id: Item identifier

        Returns:
            Working memory item or None if not found
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction context")

        try:
            cursor = self._connection.execute(
                """
                SELECT id, session_id, content_json, item_type, priority,
                       activation, added_at, last_accessed, access_count,
                       tags_json, metadata_json, space_id, actor_id
                FROM working_memory_items WHERE id = ?
            """,
                (item_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            # Deserialize complex fields
            content = json.loads(row[2])
            tags = json.loads(row[9])
            metadata = json.loads(row[10])

            return WorkingMemoryItem(
                id=row[0],
                session_id=row[1],
                content=content,
                item_type=row[3],
                priority=row[4],
                activation=row[5],
                added_at=row[6],
                last_accessed=row[7],
                access_count=row[8],
                tags=tags,
                metadata=metadata,
                space_id=row[11],
                actor_id=row[12],
            )

        except Exception as e:
            logger.error(f"Failed to get working memory item {item_id}: {e}")
            raise

    def get_session_items(
        self, session_id: str, limit: Optional[int] = None, order_by: str = "priority"
    ) -> List[WorkingMemoryItem]:
        """
        Get all items for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of items to return
            order_by: Ordering criteria ("priority", "activation", "access_time")

        Returns:
            List of working memory items
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction context")

        try:
            # Build query with appropriate ordering
            if order_by == "priority":
                order_clause = "priority DESC, activation DESC"
            elif order_by == "activation":
                order_clause = "activation DESC, last_accessed DESC"
            elif order_by == "access_time":
                order_clause = "last_accessed DESC, activation DESC"
            else:
                order_clause = "priority DESC, activation DESC"

            query = f"""
                SELECT id, session_id, content_json, item_type, priority,
                       activation, added_at, last_accessed, access_count,
                       tags_json, metadata_json, space_id, actor_id
                FROM working_memory_items
                WHERE session_id = ?
                ORDER BY {order_clause}
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor = self._connection.execute(query, (session_id,))
            items = []

            for row in cursor.fetchall():
                # Deserialize complex fields
                content = json.loads(row[2])
                tags = json.loads(row[9])
                metadata = json.loads(row[10])

                items.append(
                    WorkingMemoryItem(
                        id=row[0],
                        session_id=row[1],
                        content=content,
                        item_type=row[3],
                        priority=row[4],
                        activation=row[5],
                        added_at=row[6],
                        last_accessed=row[7],
                        access_count=row[8],
                        tags=tags,
                        metadata=metadata,
                        space_id=row[11],
                        actor_id=row[12],
                    )
                )

            return items

        except Exception as e:
            logger.error(f"Failed to get session items for {session_id}: {e}")
            raise

    def remove_item(self, item_id: str) -> bool:
        """
        Remove a working memory item.

        Args:
            item_id: Item identifier

        Returns:
            True if item was removed, False if not found
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction context")

        try:
            cursor = self._connection.execute(
                """
                DELETE FROM working_memory_items WHERE id = ?
            """,
                (item_id,),
            )

            removed = cursor.rowcount > 0
            if removed:
                logger.debug(f"Removed working memory item {item_id}")

            return removed

        except Exception as e:
            logger.error(f"Failed to remove working memory item {item_id}: {e}")
            raise

    def update_item_access(
        self, item_id: str, activation: float, access_time: float
    ) -> bool:
        """
        Update item access tracking.

        Args:
            item_id: Item identifier
            activation: New activation level
            access_time: Access timestamp

        Returns:
            True if updated successfully
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction context")

        try:
            cursor = self._connection.execute(
                """
                UPDATE working_memory_items
                SET activation = ?, last_accessed = ?, access_count = access_count + 1,
                    updated_at = ?
                WHERE id = ?
            """,
                (activation, access_time, time.time(), item_id),
            )

            updated = cursor.rowcount > 0
            if updated:
                logger.debug(f"Updated access for working memory item {item_id}")

            return updated

        except Exception as e:
            logger.error(
                f"Failed to update access for working memory item {item_id}: {e}"
            )
            raise

    def store_session(self, session: WorkingMemorySession) -> str:
        """
        Store or update session metadata.

        Args:
            session: Working memory session

        Returns:
            Session ID
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction context")

        try:
            metadata_json = json.dumps(session.metadata)

            self._connection.execute(
                """
                INSERT OR REPLACE INTO working_memory_sessions (
                    session_id, space_id, actor_id, created_at, last_active,
                    item_count, capacity, total_access_count, metadata_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session.session_id,
                    session.space_id,
                    session.actor_id,
                    session.created_at,
                    session.last_active,
                    session.item_count,
                    session.capacity,
                    session.total_access_count,
                    metadata_json,
                    time.time(),
                ),
            )

            logger.debug(f"Stored working memory session {session.session_id}")
            return session.session_id

        except Exception as e:
            logger.error(
                f"Failed to store working memory session {session.session_id}: {e}"
            )
            raise

    def get_session(self, session_id: str) -> Optional[WorkingMemorySession]:
        """
        Get session metadata.

        Args:
            session_id: Session identifier

        Returns:
            Working memory session or None if not found
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction context")

        try:
            cursor = self._connection.execute(
                """
                SELECT session_id, space_id, actor_id, created_at, last_active,
                       item_count, capacity, total_access_count, metadata_json
                FROM working_memory_sessions WHERE session_id = ?
            """,
                (session_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            metadata = json.loads(row[8])

            return WorkingMemorySession(
                session_id=row[0],
                space_id=row[1],
                actor_id=row[2],
                created_at=row[3],
                last_active=row[4],
                item_count=row[5],
                capacity=row[6],
                total_access_count=row[7],
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Failed to get working memory session {session_id}: {e}")
            raise

    def cleanup_expired_sessions(self, expiry_threshold: float) -> int:
        """
        Clean up expired sessions and their items.

        Args:
            expiry_threshold: Timestamp before which sessions are expired

        Returns:
            Number of sessions cleaned up
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction context")

        try:
            # Get expired session IDs first
            cursor = self._connection.execute(
                """
                SELECT session_id FROM working_memory_sessions
                WHERE last_active < ?
            """,
                (expiry_threshold,),
            )

            expired_sessions = [row[0] for row in cursor.fetchall()]

            if not expired_sessions:
                return 0

            # Delete expired sessions (CASCADE will handle items)
            placeholders = ",".join(["?"] * len(expired_sessions))
            cursor = self._connection.execute(
                f"""
                DELETE FROM working_memory_sessions
                WHERE session_id IN ({placeholders})
            """,
                expired_sessions,
            )

            cleaned_count = cursor.rowcount
            logger.info(f"Cleaned up {cleaned_count} expired working memory sessions")

            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            raise

    def get_session_count(self, space_id: Optional[str] = None) -> int:
        """
        Get count of active sessions.

        Args:
            space_id: Optional space filter

        Returns:
            Number of active sessions
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction context")

        try:
            if space_id:
                cursor = self._connection.execute(
                    """
                    SELECT COUNT(*) FROM working_memory_sessions WHERE space_id = ?
                """,
                    (space_id,),
                )
            else:
                cursor = self._connection.execute(
                    """
                    SELECT COUNT(*) FROM working_memory_sessions
                """
                )

            return cursor.fetchone()[0]

        except Exception as e:
            logger.error(f"Failed to get session count: {e}")
            raise

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for this store's data."""
        return {
            "type": "object",
            "properties": {
                "working_memory_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "session_id": {"type": "string"},
                            "content": {},  # Any type
                            "item_type": {"type": "string"},
                            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                            "activation": {"type": "number"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                            "metadata": {"type": "object"},
                        },
                        "required": [
                            "id",
                            "session_id",
                            "content",
                            "item_type",
                            "priority",
                        ],
                    },
                },
                "working_memory_sessions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "space_id": {"type": "string"},
                            "actor_id": {"type": "string"},
                            "capacity": {"type": "integer", "minimum": 1},
                            "item_count": {"type": "integer", "minimum": 0},
                        },
                        "required": ["session_id", "space_id", "actor_id"],
                    },
                },
            },
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema and tables."""
        # This is already implemented in _init_schema()
        # BaseStore calls this during transaction begin
        pass  # Schema already initialized in constructor

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record in the store."""
        if data.get("type") == "item":
            item = WorkingMemoryItem.from_dict(data["data"])
            item_id = self.store_item(item)
            return {"id": item_id, "type": "item", "created": True}
        elif data.get("type") == "session":
            session = WorkingMemorySession(**data["data"])
            session_id = self.store_session(session)
            return {"id": session_id, "type": "session", "created": True}
        else:
            raise ValueError(f"Unknown record type: {data.get('type')}")

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record by ID."""
        # Try as item first
        item = self.get_item(record_id)
        if item:
            return {"id": record_id, "type": "item", "data": item.to_dict()}

        # Try as session
        session = self.get_session(record_id)
        if session:
            return {
                "id": record_id,
                "type": "session",
                "data": {
                    "session_id": session.session_id,
                    "space_id": session.space_id,
                    "actor_id": session.actor_id,
                    "created_at": session.created_at,
                    "last_active": session.last_active,
                    "item_count": session.item_count,
                    "capacity": session.capacity,
                    "total_access_count": session.total_access_count,
                    "metadata": session.metadata,
                },
            }

        return None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record."""
        if data.get("type") == "item":
            item = WorkingMemoryItem.from_dict(data["data"])
            item.id = record_id  # Ensure ID matches
            self.store_item(item)
            return {"id": record_id, "type": "item", "updated": True}
        elif data.get("type") == "session":
            session = WorkingMemorySession(**data["data"])
            session.session_id = record_id  # Ensure ID matches
            self.store_session(session)
            return {"id": record_id, "type": "session", "updated": True}
        else:
            raise ValueError(f"Unknown record type: {data.get('type')}")

    def _delete_record(self, record_id: str) -> bool:
        """Delete a record by ID."""
        # Try to remove as item
        if self.remove_item(record_id):
            return True

        # Try to remove as session (would cascade to items)
        if not self._connection:
            raise RuntimeError("Store not in transaction context")

        try:
            cursor = self._connection.execute(
                """
                DELETE FROM working_memory_sessions WHERE session_id = ?
            """,
                (record_id,),
            )
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete session {record_id}: {e}")
            return False

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List records with optional filtering and pagination."""
        records = []

        if not self._connection:
            raise RuntimeError("Store not in transaction context")

        try:
            # List items
            query = """
                SELECT id, session_id, content_json, item_type, priority,
                       activation, added_at, last_accessed, access_count,
                       tags_json, metadata_json, space_id, actor_id
                FROM working_memory_items
            """
            params = []

            # Apply filters
            if filters:
                conditions = []
                if "session_id" in filters:
                    conditions.append("session_id = ?")
                    params.append(filters["session_id"])
                if "item_type" in filters:
                    conditions.append("item_type = ?")
                    params.append(filters["item_type"])
                if "space_id" in filters:
                    conditions.append("space_id = ?")
                    params.append(filters["space_id"])

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY last_accessed DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)

            cursor = self._connection.execute(query, params)

            for row in cursor.fetchall():
                content = json.loads(row[2])
                tags = json.loads(row[9])
                metadata = json.loads(row[10])

                records.append(
                    {
                        "id": row[0],
                        "type": "item",
                        "data": {
                            "id": row[0],
                            "session_id": row[1],
                            "content": content,
                            "item_type": row[3],
                            "priority": row[4],
                            "activation": row[5],
                            "added_at": row[6],
                            "last_accessed": row[7],
                            "access_count": row[8],
                            "tags": tags,
                            "metadata": metadata,
                            "space_id": row[11],
                            "actor_id": row[12],
                        },
                    }
                )

            return records

        except Exception as e:
            logger.error(f"Failed to list records: {e}")
            return []

    # StoreProtocol transaction methods

    def _on_transaction_begin(self, conn: sqlite3.Connection) -> None:
        """Hook called when transaction begins."""
        logger.debug("Working memory store transaction began")

    def _on_transaction_commit(self, conn: sqlite3.Connection) -> None:
        """Hook called when transaction commits."""
        logger.debug("Working memory store transaction committed")

    def _on_transaction_rollback(self, conn: sqlite3.Connection) -> None:
        """Hook called when transaction rolls back."""
        logger.debug("Working memory store transaction rolled back")

    def get_transaction_size(self, conn: sqlite3.Connection) -> int:
        """Get estimated size of transaction in bytes."""
        try:
            # Rough estimate based on working memory items and sessions
            cursor = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM working_memory_items) * 1024 +
                    (SELECT COUNT(*) FROM working_memory_sessions) * 512
            """
            )
            return cursor.fetchone()[0]
        except Exception:
            return 0

    def validate_transaction(self, conn: sqlite3.Connection) -> bool:
        """Validate transaction state before commit."""
        try:
            # Check referential integrity
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM working_memory_items
                WHERE session_id NOT IN (SELECT session_id FROM working_memory_sessions)
            """
            )
            orphaned_items = cursor.fetchone()[0]

            if orphaned_items > 0:
                logger.warning(f"Found {orphaned_items} orphaned working memory items")
                return False

            return True
        except Exception as e:
            logger.error(f"Transaction validation failed: {e}")
            return False

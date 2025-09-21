"""
Outbox Pattern Implementation for Reliable Event Publishing

This module implements the Outbox pattern to ensure reliable event publishing
with transactional guarantees. Events are written to the outbox table within
the same transaction as the business operation, then asynchronously processed
by a background worker.

The pattern provides:
- Transactional guarantee that events are written atomically
- At-least-once delivery semantics
- Retry logic with exponential backoff
- Poison message handling
- Monitoring and observability
"""

import json
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore


class OutboxEventStatus(Enum):
    """Status enumeration for outbox events."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    POISONED = "poisoned"


@dataclass
class OutboxEvent:
    """
    Represents an event in the outbox queue.

    Attributes:
        id: Unique identifier for the event
        aggregate_id: ID of the aggregate that generated the event
        event_type: Type/name of the event
        payload: Event data as JSON string
        created_at: Unix timestamp when event was created
        processed_at: Unix timestamp when event was processed (None if pending)
        retry_count: Number of processing attempts
        status: Current status of the event
        last_error: Last error message if processing failed
        next_retry: Unix timestamp for next retry attempt
    """

    id: str
    aggregate_id: str
    event_type: str
    payload: str
    created_at: int
    processed_at: Optional[int] = None
    retry_count: int = 0
    status: str = OutboxEventStatus.PENDING.value
    last_error: Optional[str] = None
    next_retry: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OutboxEvent":
        """Create from dictionary."""
        return cls(**data)

    def mark_processing(self) -> None:
        """Mark event as currently being processed."""
        self.status = OutboxEventStatus.PROCESSING.value

    def mark_processed(self) -> None:
        """Mark event as successfully processed."""
        self.status = OutboxEventStatus.PROCESSED.value
        self.processed_at = int(time.time())

    def mark_failed(self, error: str, next_retry_delay: int = 60) -> None:
        """Mark event as failed with retry scheduling."""
        self.status = OutboxEventStatus.FAILED.value
        self.retry_count += 1
        self.last_error = error
        self.next_retry = int(time.time()) + next_retry_delay

    def mark_poisoned(self, error: str) -> None:
        """Mark event as poisoned (no more retries)."""
        self.status = OutboxEventStatus.POISONED.value
        self.last_error = error


class OutboxStore(BaseStore):
    """
    Storage implementation for the Outbox pattern.

    Provides transactional event storage with support for:
    - Atomic event writing within business transactions
    - Event retrieval for background processing
    - Status tracking and retry management
    - Cleanup of processed events
    """

    def __init__(self):
        super().__init__()
        self._table_name = "outbox_events"

    def get_store_name(self) -> str:
        """Return the store name for registration."""
        return "outbox"

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for outbox events."""
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "aggregate_id": {"type": "string"},
                "event_type": {"type": "string"},
                "payload": {"type": "string"},
                "created_at": {"type": "integer"},
                "processed_at": {"type": ["integer", "null"]},
                "retry_count": {"type": "integer", "minimum": 0},
                "status": {
                    "type": "string",
                    "enum": [
                        "pending",
                        "processing",
                        "processed",
                        "failed",
                        "poisoned",
                    ],
                },
                "last_error": {"type": ["string", "null"]},
                "next_retry": {"type": ["integer", "null"]},
            },
            "required": ["id", "aggregate_id", "event_type", "payload", "created_at"],
            "additionalProperties": False,
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema and tables."""
        schema_sql = self._get_schema_sql()
        for statement in schema_sql.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(statement)

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new outbox event record."""
        # Convert to OutboxEvent for validation
        event = OutboxEvent(
            id=data.get("id", str(uuid.uuid4())),
            aggregate_id=data["aggregate_id"],
            event_type=data["event_type"],
            payload=(
                data["payload"]
                if isinstance(data["payload"], str)
                else json.dumps(data["payload"])
            ),
            created_at=data.get("created_at", int(time.time())),
            processed_at=data.get("processed_at"),
            retry_count=data.get("retry_count", 0),
            status=data.get("status", OutboxEventStatus.PENDING.value),
            last_error=data.get("last_error"),
            next_retry=data.get("next_retry"),
        )

        # Use the existing add_event method
        created_event = self.add_event(
            aggregate_id=event.aggregate_id,
            event_type=event.event_type,
            payload=(
                json.loads(event.payload)
                if isinstance(event.payload, str)
                else event.payload
            ),
            event_id=event.id,
        )

        return created_event.to_dict()

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read an outbox event by ID."""
        event = self.get_event_by_id(record_id)
        return event.to_dict() if event else None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing outbox event."""
        # Get existing event
        event = self.get_event_by_id(record_id)
        if not event:
            raise RuntimeError(f"Event {record_id} not found")

        # Update fields
        if "processed_at" in data:
            event.processed_at = data["processed_at"]
        if "retry_count" in data:
            event.retry_count = data["retry_count"]
        if "status" in data:
            event.status = data["status"]
        if "last_error" in data:
            event.last_error = data["last_error"]
        if "next_retry" in data:
            event.next_retry = data["next_retry"]

        # Update in database
        self.update_event_status(event)
        return event.to_dict()

    def _delete_record(self, record_id: str) -> bool:
        """Delete an outbox event by ID."""
        if not self._connection:
            raise RuntimeError("Store not in transaction - cannot delete event")

        try:
            cursor = self._connection.execute(
                "DELETE FROM outbox_events WHERE id = ?", (record_id,)
            )
            return cursor.rowcount > 0

        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to delete event: {e}") from e

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List outbox events with optional filtering and pagination."""
        if not self._connection:
            raise RuntimeError("Store not in transaction - cannot list events")

        try:
            # Build query with filters
            where_conditions = []
            params = []

            if filters:
                if "status" in filters:
                    where_conditions.append("status = ?")
                    params.append(filters["status"])
                if "event_type" in filters:
                    where_conditions.append("event_type = ?")
                    params.append(filters["event_type"])
                if "aggregate_id" in filters:
                    where_conditions.append("aggregate_id = ?")
                    params.append(filters["aggregate_id"])

            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)

            # Build full query
            query = f"""
                SELECT id, aggregate_id, event_type, payload, created_at,
                       processed_at, retry_count, status, last_error, next_retry
                FROM outbox_events
                {where_clause}
                ORDER BY created_at ASC
            """

            if limit:
                query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"

            cursor = self._connection.execute(query, params)

            events = []
            for row in cursor.fetchall():
                event = OutboxEvent(
                    id=row[0],
                    aggregate_id=row[1],
                    event_type=row[2],
                    payload=row[3],
                    created_at=row[4],
                    processed_at=row[5],
                    retry_count=row[6],
                    status=row[7],
                    last_error=row[8],
                    next_retry=row[9],
                )
                events.append(event.to_dict())

            return events

        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to list events: {e}") from e

    def _get_schema_sql(self) -> str:
        """
        Return the SQL schema for the outbox events table.

        Schema includes:
        - Primary key on id
        - Indexes for efficient querying by status and retry time
        - Support for event payload and metadata
        """
        return """
        CREATE TABLE IF NOT EXISTS outbox_events (
            id TEXT PRIMARY KEY,
            aggregate_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            processed_at INTEGER,
            retry_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            last_error TEXT,
            next_retry INTEGER,

            -- Constraints
            CHECK (retry_count >= 0),
            CHECK (status IN ('pending', 'processing', 'processed', 'failed', 'poisoned'))
        );

        -- Indexes for efficient querying
        CREATE INDEX IF NOT EXISTS idx_outbox_status
            ON outbox_events(status, created_at);

        CREATE INDEX IF NOT EXISTS idx_outbox_retry
            ON outbox_events(next_retry, status)
            WHERE status = 'failed';

        CREATE INDEX IF NOT EXISTS idx_outbox_aggregate
            ON outbox_events(aggregate_id, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_outbox_event_type
            ON outbox_events(event_type, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_outbox_processed
            ON outbox_events(processed_at)
            WHERE status = 'processed';
        """

    def add_event(
        self,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
        event_id: Optional[str] = None,
    ) -> OutboxEvent:
        """
        Add a new event to the outbox.

        Args:
            aggregate_id: ID of the aggregate that generated the event
            event_type: Type/name of the event
            payload: Event data (will be JSON serialized)
            event_id: Optional custom event ID (UUID generated if not provided)

        Returns:
            The created OutboxEvent

        Raises:
            RuntimeError: If not in a transaction
            ValueError: If payload cannot be serialized
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction - cannot add outbox event")

        try:
            # Generate ID if not provided
            if event_id is None:
                event_id = str(uuid.uuid4())

            # Serialize payload
            payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)

            # Create event
            event = OutboxEvent(
                id=event_id,
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=payload_json,
                created_at=int(time.time()),
            )

            # Insert into database
            self._connection.execute(
                """
                INSERT INTO outbox_events (
                    id, aggregate_id, event_type, payload, created_at,
                    processed_at, retry_count, status, last_error, next_retry
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event.id,
                    event.aggregate_id,
                    event.event_type,
                    event.payload,
                    event.created_at,
                    event.processed_at,
                    event.retry_count,
                    event.status,
                    event.last_error,
                    event.next_retry,
                ),
            )

            return event

        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to add outbox event: {e}") from e
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to serialize payload: {e}") from e

    def get_pending_events(self, limit: int = 100) -> List[OutboxEvent]:
        """
        Get pending events ready for processing.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of pending OutboxEvent objects

        Raises:
            RuntimeError: If not in a transaction
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction - cannot get pending events")

        try:
            cursor = self._connection.execute(
                """
                SELECT id, aggregate_id, event_type, payload, created_at,
                       processed_at, retry_count, status, last_error, next_retry
                FROM outbox_events
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT ?
            """,
                (limit,),
            )

            events = []
            for row in cursor.fetchall():
                event = OutboxEvent(
                    id=row[0],
                    aggregate_id=row[1],
                    event_type=row[2],
                    payload=row[3],
                    created_at=row[4],
                    processed_at=row[5],
                    retry_count=row[6],
                    status=row[7],
                    last_error=row[8],
                    next_retry=row[9],
                )
                events.append(event)

            return events

        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to get pending events: {e}") from e

    def get_retry_events(self, limit: int = 100) -> List[OutboxEvent]:
        """
        Get failed events ready for retry.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of failed OutboxEvent objects ready for retry

        Raises:
            RuntimeError: If not in a transaction
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction - cannot get retry events")

        try:
            current_time = int(time.time())
            cursor = self._connection.execute(
                """
                SELECT id, aggregate_id, event_type, payload, created_at,
                       processed_at, retry_count, status, last_error, next_retry
                FROM outbox_events
                WHERE status = 'failed'
                  AND (next_retry IS NULL OR next_retry <= ?)
                ORDER BY next_retry ASC, created_at ASC
                LIMIT ?
            """,
                (current_time, limit),
            )

            events = []
            for row in cursor.fetchall():
                event = OutboxEvent(
                    id=row[0],
                    aggregate_id=row[1],
                    event_type=row[2],
                    payload=row[3],
                    created_at=row[4],
                    processed_at=row[5],
                    retry_count=row[6],
                    status=row[7],
                    last_error=row[8],
                    next_retry=row[9],
                )
                events.append(event)

            return events

        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to get retry events: {e}") from e

    def update_event_status(self, event: OutboxEvent) -> None:
        """
        Update the status of an event.

        Args:
            event: OutboxEvent with updated status

        Raises:
            RuntimeError: If not in a transaction or update fails
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction - cannot update event status")

        try:
            cursor = self._connection.execute(
                """
                UPDATE outbox_events
                SET processed_at = ?, retry_count = ?, status = ?,
                    last_error = ?, next_retry = ?
                WHERE id = ?
            """,
                (
                    event.processed_at,
                    event.retry_count,
                    event.status,
                    event.last_error,
                    event.next_retry,
                    event.id,
                ),
            )

            if cursor.rowcount == 0:
                raise RuntimeError(f"Event {event.id} not found")

        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to update event status: {e}") from e

    def get_event_by_id(self, event_id: str) -> Optional[OutboxEvent]:
        """
        Get a specific event by ID.

        Args:
            event_id: ID of the event to retrieve

        Returns:
            OutboxEvent if found, None otherwise

        Raises:
            RuntimeError: If not in a transaction
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction - cannot get event")

        try:
            cursor = self._connection.execute(
                """
                SELECT id, aggregate_id, event_type, payload, created_at,
                       processed_at, retry_count, status, last_error, next_retry
                FROM outbox_events
                WHERE id = ?
            """,
                (event_id,),
            )

            row = cursor.fetchone()
            if row is None:
                return None

            return OutboxEvent(
                id=row[0],
                aggregate_id=row[1],
                event_type=row[2],
                payload=row[3],
                created_at=row[4],
                processed_at=row[5],
                retry_count=row[6],
                status=row[7],
                last_error=row[8],
                next_retry=row[9],
            )

        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to get event: {e}") from e

    def cleanup_processed_events(self, older_than_seconds: int = 86400) -> int:
        """
        Clean up processed events older than specified time.

        Args:
            older_than_seconds: Remove events processed longer than this (default 24h)

        Returns:
            Number of events removed

        Raises:
            RuntimeError: If not in a transaction
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction - cannot cleanup events")

        try:
            cutoff_time = int(time.time()) - older_than_seconds
            cursor = self._connection.execute(
                """
                DELETE FROM outbox_events
                WHERE status = 'processed'
                  AND processed_at IS NOT NULL
                  AND processed_at < ?
            """,
                (cutoff_time,),
            )

            return cursor.rowcount

        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to cleanup events: {e}") from e

    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about events in the outbox.

        Returns:
            Dictionary with counts by status

        Raises:
            RuntimeError: If not in a transaction
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction - cannot get statistics")

        try:
            cursor = self._connection.execute(
                """
                SELECT status, COUNT(*)
                FROM outbox_events
                GROUP BY status
            """
            )

            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = row[1]

            # Ensure all statuses are represented
            for status in OutboxEventStatus:
                if status.value not in stats:
                    stats[status.value] = 0

            # Add total count
            stats["total"] = sum(stats.values())

            return stats

        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to get statistics: {e}") from e

"""
Semantic Store Implementation for MemoryOS

This module provides semantic knowledge storage with structured types and metadata.
Supports various semantic item types (notes, tasks, contacts, events, facts, triples, entities)
with flexible key-value payload structure and band-based access control.

Contract: semantic_item.schema.json
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


# Type definitions from semantic_item.schema.json contract
SemanticType = Literal["note", "task", "contact", "event", "fact", "triple", "entity"]


@dataclass
class SemanticItem:
    """
    Semantic Item data structure following semantic_item.schema.json contract.

    Required fields:
    - id: ULID identifier
    - space_id: Space identifier (e.g., personal:alice, shared:household)
    - ts: ISO 8601 timestamp
    - type: Semantic type (note, task, contact, event, fact, triple, entity)
    - keys: Object with arbitrary keys for structured data

    Optional fields:
    - payload: Additional arbitrary data
    - band: Security band (GREEN, AMBER, RED, BLACK)
    - ttl: ISO 8601 duration for expiry (e.g., P30D)
    """

    id: str
    space_id: str
    ts: str
    type: SemanticType
    keys: Dict[str, Any]
    payload: Optional[Dict[str, Any]] = None
    band: Optional[str] = None
    ttl: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "space_id": self.space_id,
            "ts": self.ts,
            "type": self.type,
            "keys": self.keys,
        }
        if self.payload is not None:
            result["payload"] = self.payload
        if self.band is not None:
            result["band"] = self.band
        if self.ttl is not None:
            result["ttl"] = self.ttl
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SemanticItem":
        """Create SemanticItem from dictionary."""
        return cls(
            id=data["id"],
            space_id=data["space_id"],
            ts=data["ts"],
            type=data["type"],
            keys=data["keys"],
            payload=data.get("payload"),
            band=data.get("band"),
            ttl=data.get("ttl"),
        )


class SemanticStore(BaseStore):
    """
    Semantic knowledge store implementation following BaseStore pattern.

    Provides CRUD operations for semantic items with:
    - Type-based organization (notes, tasks, contacts, events, facts, triples, entities)
    - Key-based search and filtering
    - Space-scoped access control
    - Band-based security levels
    - TTL-based expiration
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        """Initialize the semantic store."""
        super().__init__(config)
        self._ensure_initialized()
        logger.info("SemanticStore initialized")

    def _ensure_initialized(self):
        """Ensure the database schema is properly initialized."""
        with sqlite3.connect(self.config.db_path) as conn:
            self._initialize_schema(conn)
            conn.commit()

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for this store's data."""
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "space_id": {"type": "string"},
                "ts": {"type": "string"},
                "type": {
                    "type": "string",
                    "enum": [
                        "note",
                        "task",
                        "contact",
                        "event",
                        "fact",
                        "triple",
                        "entity",
                    ],
                },
                "keys": {"type": "object"},
                "payload": {"type": "object"},
                "band": {"type": "string"},
                "ttl": {"type": "integer"},
            },
            "required": ["id", "space_id", "ts", "type", "keys"],
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize the database schema."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS semantic_items (
            id TEXT PRIMARY KEY,
            space_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            type TEXT NOT NULL,
            keys TEXT NOT NULL,
            payload TEXT,
            band TEXT,
            ttl INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_semantic_space_id ON semantic_items(space_id);
        CREATE INDEX IF NOT EXISTS idx_semantic_type ON semantic_items(type);
        CREATE INDEX IF NOT EXISTS idx_semantic_ts ON semantic_items(ts);
        CREATE INDEX IF NOT EXISTS idx_semantic_band ON semantic_items(band);
        """
        conn.executescript(schema_sql)

    def _create_record(self, item: SemanticItem) -> str:
        """Create a new semantic item record."""
        ts_unix = int(
            datetime.fromisoformat(item.ts.replace("Z", "+00:00")).timestamp()
        )

        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute(
                """
                INSERT INTO semantic_items
                (id, space_id, ts, ts_iso, type, keys, payload, band, ttl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    item.space_id,
                    ts_unix,
                    item.ts,
                    item.type,
                    json.dumps(item.keys),
                    json.dumps(item.payload) if item.payload else None,
                    item.band,
                    item.ttl,
                ),
            )
            conn.commit()

        logger.info(
            f"Created semantic item {item.id} of type {item.type} in space {item.space_id}"
        )
        return item.id

    def _read_record(self, record_id: str) -> Optional[SemanticItem]:
        """Read a semantic item by ID."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, space_id, ts_iso, type, keys, payload, band, ttl
                FROM semantic_items
                WHERE id = ?
                """,
                (record_id,),
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_semantic_item(row)
        return None

    def _update_record(self, record_id: str, item: SemanticItem) -> bool:
        """Update an existing semantic item."""
        ts_unix = int(
            datetime.fromisoformat(item.ts.replace("Z", "+00:00")).timestamp()
        )

        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE semantic_items
                SET space_id = ?, ts = ?, ts_iso = ?, type = ?, keys = ?,
                    payload = ?, band = ?, ttl = ?
                WHERE id = ?
                """,
                (
                    item.space_id,
                    ts_unix,
                    item.ts,
                    item.type,
                    json.dumps(item.keys),
                    json.dumps(item.payload) if item.payload else None,
                    item.band,
                    item.ttl,
                    record_id,
                ),
            )
            conn.commit()
            updated = cursor.rowcount > 0

        if updated:
            logger.info(f"Updated semantic item {record_id}")
        else:
            logger.warning(f"Semantic item {record_id} not found for update")

        return updated

    def _delete_record(self, record_id: str) -> bool:
        """Delete a semantic item by ID."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM semantic_items WHERE id = ?", (record_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(f"Deleted semantic item {record_id}")
        else:
            logger.warning(f"Semantic item {record_id} not found for deletion")

        return deleted

    def _list_records(
        self,
        space_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[SemanticItem]:
        """List semantic items with optional filtering."""
        query = "SELECT id, space_id, ts_iso, type, keys, payload, band, ttl FROM semantic_items"
        params = []

        if space_id:
            query += " WHERE space_id = ?"
            params.append(space_id)

        query += " ORDER BY ts DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        if offset:
            query += " OFFSET ?"
            params.append(offset)

        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_semantic_item(row) for row in cursor.fetchall()]

    def _row_to_semantic_item(self, row: sqlite3.Row) -> SemanticItem:
        """Convert database row to SemanticItem."""
        return SemanticItem(
            id=row["id"],
            space_id=row["space_id"],
            ts=row["ts_iso"],
            type=row["type"],
            keys=json.loads(row["keys"]),
            payload=json.loads(row["payload"]) if row["payload"] else None,
            band=row["band"],
            ttl=row["ttl"],
        )

    # Specialized semantic store methods

    def store_item(self, item: SemanticItem) -> str:
        """Store a semantic item."""
        return self._create_record(item)

    def get_item(self, item_id: str) -> Optional[SemanticItem]:
        """Get a semantic item by ID."""
        return self._read_record(item_id)

    def update_item(self, item_id: str, item: SemanticItem) -> bool:
        """Update a semantic item."""
        return self._update_record(item_id, item)

    def delete_item(self, item_id: str) -> bool:
        """Delete a semantic item."""
        return self._delete_record(item_id)

    def list_items(
        self,
        space_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[SemanticItem]:
        """List semantic items."""
        return self._list_records(space_id, limit, offset)

    def get_items_by_type(
        self,
        semantic_type: SemanticType,
        space_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[SemanticItem]:
        """Get semantic items by type."""
        query = "SELECT id, space_id, ts_iso, type, keys, payload, band, ttl FROM semantic_items WHERE type = ?"
        params = [semantic_type]

        if space_id:
            query += " AND space_id = ?"
            params.append(space_id)

        query += " ORDER BY ts DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_semantic_item(row) for row in cursor.fetchall()]

    def search_by_keys(
        self,
        key_filters: Dict[str, Any],
        space_id: Optional[str] = None,
        semantic_type: Optional[SemanticType] = None,
        limit: Optional[int] = None,
    ) -> List[SemanticItem]:
        """
        Search semantic items by key-value pairs.

        Note: This is a basic implementation that searches for exact matches
        in the JSON keys field. For production use, consider implementing
        proper JSON query capabilities or using SQLite's JSON1 extension.
        """
        items = self.list_items(space_id=space_id, limit=None)

        filtered_items = []
        for item in items:
            if semantic_type and item.type != semantic_type:
                continue

            # Check if all key filters match
            matches = True
            for key, value in key_filters.items():
                if key not in item.keys or item.keys[key] != value:
                    matches = False
                    break

            if matches:
                filtered_items.append(item)

        # Apply limit after filtering
        if limit:
            filtered_items = filtered_items[:limit]

        return filtered_items

    def get_items_by_band(
        self,
        band: str,
        space_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[SemanticItem]:
        """Get semantic items by security band."""
        query = "SELECT id, space_id, ts_iso, type, keys, payload, band, ttl FROM semantic_items WHERE band = ?"
        params = [band]

        if space_id:
            query += " AND space_id = ?"
            params.append(space_id)

        query += " ORDER BY ts DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_semantic_item(row) for row in cursor.fetchall()]

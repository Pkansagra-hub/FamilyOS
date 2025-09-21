"""
Episodic Store - Time-ordered storage for episodic memories

This implementation follows the contracts exactly:
- episodic_record.schema.json
- episodic_sequence.schema.json

Features:
- Contract-compliant storage for episodic records and sequences
- High-performance temporal indexing
- BaseStore abstract interface implementation
- Hippocampus consolidation integration
- ULID-based identifiers as per contracts
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


@dataclass
class EpisodicRecord:
    """
    Episodic memory record following episodic_record.schema.json contract.

    All fields match the contract specification exactly.
    """

    id: str  # ULID
    envelope_id: str  # EnvelopeId (UUID or ULID)
    space_id: (
        str  # SpaceId pattern: (personal|selective|shared|extended|interfamily):...
    )
    ts: datetime  # Timestamp (ISO format)
    band: str  # Band enum: GREEN|AMBER|RED|BLACK
    author: str  # ActorRef
    content: Dict[str, Any]  # Content object with text, lang, attachments
    features: Dict[str, Any]  # Features with keywords, simhash, etc.
    mls_group: str  # MLSGroup
    device: Optional[str] = None  # DeviceRef (optional in contract)
    links: Optional[Dict[str, Any]] = (
        None  # Links with sequence_id, parent_id, link_group_id
    )
    meta: Optional[Dict[str, Any]] = None  # Meta object (additional properties allowed)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary following contract schema."""
        data: Dict[str, Any] = {
            "id": self.id,
            "envelope_id": self.envelope_id,
            "space_id": self.space_id,
            "ts": self.ts.isoformat(),
            "band": self.band,
            "author": self.author,
            "content": self.content,
            "features": self.features,
            "mls_group": self.mls_group,
        }

        if self.device is not None:
            data["device"] = self.device
        if self.links is not None:
            data["links"] = self.links
        if self.meta is not None:
            data["meta"] = self.meta

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EpisodicRecord:
        """Create from dictionary following contract schema."""
        ts = data["ts"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

        return cls(
            id=data["id"],
            envelope_id=data["envelope_id"],
            space_id=data["space_id"],
            ts=ts,
            band=data["band"],
            author=data["author"],
            content=data["content"],
            features=data["features"],
            mls_group=data["mls_group"],
            device=data.get("device"),
            links=data.get("links"),
            meta=data.get("meta"),
        )


@dataclass
class EpisodicSequence:
    """
    Episodic sequence following episodic_sequence.schema.json contract.

    All fields match the contract specification exactly.
    """

    sequence_id: str  # ULID
    space_id: str  # SpaceId
    items: List[Dict[str, Any]]  # Array of items with id, ts, optional weight
    ts: datetime  # Timestamp
    label: Optional[str] = None  # Optional label
    closed: bool = False  # Default false as per contract

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary following contract schema."""
        data: Dict[str, Any] = {
            "sequence_id": self.sequence_id,
            "space_id": self.space_id,
            "items": self.items,
            "ts": self.ts.isoformat(),
            "closed": self.closed,
        }

        if self.label is not None:
            data["label"] = self.label

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EpisodicSequence:
        """Create from dictionary following contract schema."""
        ts = data["ts"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

        return cls(
            sequence_id=data["sequence_id"],
            space_id=data["space_id"],
            items=data["items"],
            ts=ts,
            label=data.get("label"),
            closed=data.get("closed", False),
        )


@dataclass
class TemporalQuery:
    """Query parameters for temporal search of episodic records."""

    space_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    author: Optional[str] = None
    band_filter: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    sequence_id: Optional[str] = None
    limit: int = 100
    offset: int = 0
    order_desc: bool = True  # Most recent first by default


class EpisodicStore(BaseStore):
    """
    Episodic Store - Time-ordered storage following contracts exactly.

    Implements BaseStore abstract interface and provides specialized
    functionality for episodic records and sequences.
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)

    # BaseStore abstract method implementations

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for episodic records (contract-compliant)."""
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://familyos.local/contracts/storage/episodic_record.schema.json",
            "title": "Episodic Memory Record",
            "type": "object",
            "additionalProperties": False,
            "required": [
                "id",
                "envelope_id",
                "space_id",
                "ts",
                "band",
                "author",
                "content",
                "features",
                "mls_group",
            ],
            "properties": {
                "id": {"type": "string", "pattern": "^[0-7][0-9A-HJKMNP-TV-Z]{25}$"},
                "envelope_id": {"type": "string"},
                "space_id": {
                    "type": "string",
                    "pattern": "^(personal|selective|shared|extended|interfamily):[A-Za-z0-9_\\-\\.]+$",
                },
                "ts": {"type": "string", "format": "date-time"},
                "band": {"type": "string", "enum": ["GREEN", "AMBER", "RED", "BLACK"]},
                "author": {"type": "string"},
                "device": {"type": "string"},
                "content": {"type": "object"},
                "features": {"type": "object"},
                "mls_group": {"type": "string"},
                "links": {"type": "object"},
                "meta": {"type": "object"},
            },
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema for episodic storage."""
        # Episodic records table - follows contract exactly
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS episodic_records (
                id TEXT PRIMARY KEY,
                envelope_id TEXT NOT NULL,
                space_id TEXT NOT NULL,
                ts INTEGER NOT NULL,
                ts_iso TEXT NOT NULL,
                band TEXT NOT NULL CHECK (band IN ('GREEN', 'AMBER', 'RED', 'BLACK')),
                author TEXT NOT NULL,
                device TEXT,
                content_json TEXT NOT NULL,
                features_json TEXT NOT NULL,
                mls_group TEXT NOT NULL,
                links_json TEXT,
                meta_json TEXT,
                created_at INTEGER DEFAULT (unixepoch()),
                updated_at INTEGER DEFAULT (unixepoch())
            )
        """
        )

        # Episodic sequences table - follows contract exactly
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS episodic_sequences (
                sequence_id TEXT PRIMARY KEY,
                space_id TEXT NOT NULL,
                ts INTEGER NOT NULL,
                ts_iso TEXT NOT NULL,
                label TEXT,
                items_json TEXT NOT NULL,
                closed INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER DEFAULT (unixepoch()),
                updated_at INTEGER DEFAULT (unixepoch())
            )
        """
        )

        # Performance indexes for temporal queries
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_episodic_records_space_time
            ON episodic_records(space_id, ts DESC)
        """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_episodic_records_author
            ON episodic_records(author)
        """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_episodic_records_band
            ON episodic_records(band)
        """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_episodic_sequences_space
            ON episodic_sequences(space_id, ts DESC)
        """
        )

        logger.info("Episodic store schema initialized")

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new episodic record (BaseStore interface)."""
        record = EpisodicRecord.from_dict(data)
        self.store_record(record)
        return record.to_dict()

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record by ID (BaseStore interface - no space context)."""
        if not self._connection:
            return None

        try:
            cursor = self._connection.execute(
                """
                SELECT id, envelope_id, space_id, ts_iso, band, author,
                       device, content_json, features_json, mls_group,
                       links_json, meta_json
                FROM episodic_records
                WHERE id = ?
                LIMIT 1
            """,
                (record_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            # Convert to EpisodicRecord and return as dict
            record_data = {
                "id": row[0],
                "envelope_id": row[1],
                "space_id": row[2],
                "ts": row[3],
                "band": row[4],
                "author": row[5],
                "content": json.loads(row[7]),
                "features": json.loads(row[8]),
                "mls_group": row[9],
            }

            if row[6]:  # device
                record_data["device"] = row[6]
            if row[10]:  # links_json
                record_data["links"] = json.loads(row[10])
            if row[11]:  # meta_json
                record_data["meta"] = json.loads(row[11])

            return record_data

        except Exception as e:
            logger.error(
                "Failed to read episodic record",
                extra={"record_id": record_id, "error": str(e)},
            )
            return None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record (BaseStore interface)."""
        if not self._connection or not self._in_transaction:
            raise RuntimeError("Store not in transaction")

        # Get existing record
        existing = self._read_record(record_id)
        if not existing:
            raise ValueError(f"Record {record_id} not found")

        # Merge updates
        updated_data = {**existing, **data}
        record = EpisodicRecord.from_dict(updated_data)

        # Update in database
        ts_unix = int(record.ts.timestamp())
        self._connection.execute(
            """
            UPDATE episodic_records
            SET envelope_id=?, space_id=?, ts=?, ts_iso=?, band=?, author=?,
                device=?, content_json=?, features_json=?, mls_group=?,
                links_json=?, meta_json=?, updated_at=unixepoch()
            WHERE id=?
        """,
            (
                record.envelope_id,
                record.space_id,
                ts_unix,
                record.ts.isoformat(),
                record.band,
                record.author,
                record.device,
                json.dumps(record.content),
                json.dumps(record.features),
                record.mls_group,
                json.dumps(record.links) if record.links else None,
                json.dumps(record.meta) if record.meta else None,
                record_id,
            ),
        )

        return record.to_dict()

    def _delete_record(self, record_id: str) -> bool:
        """Delete a record by ID (BaseStore interface)."""
        if not self._connection or not self._in_transaction:
            return False

        try:
            cursor = self._connection.execute(
                """
                DELETE FROM episodic_records WHERE id = ?
            """,
                (record_id,),
            )
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(
                "Failed to delete episodic record",
                extra={"record_id": record_id, "error": str(e)},
            )
            return False

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List records with filtering (BaseStore interface)."""
        if not self._connection:
            return []

        where_clauses: List[str] = []
        params: List[Any] = []

        if filters:
            if "space_id" in filters:
                where_clauses.append("space_id = ?")
                params.append(filters["space_id"])
            if "author" in filters:
                where_clauses.append("author = ?")
                params.append(filters["author"])
            if "band" in filters:
                where_clauses.append("band = ?")
                params.append(filters["band"])

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        sql = f"""
            SELECT id, envelope_id, space_id, ts_iso, band, author,
                   device, content_json, features_json, mls_group,
                   links_json, meta_json
            FROM episodic_records
            WHERE {where_clause}
            ORDER BY ts DESC
        """

        if limit:
            sql += f" LIMIT {limit}"
        if offset:
            sql += f" OFFSET {offset}"

        try:
            cursor = self._connection.execute(sql, params)

            records: List[Dict[str, Any]] = []
            for row in cursor:
                record_data: Dict[str, Any] = {
                    "id": row[0],
                    "envelope_id": row[1],
                    "space_id": row[2],
                    "ts": row[3],
                    "band": row[4],
                    "author": row[5],
                    "content": json.loads(row[7]),
                    "features": json.loads(row[8]),
                    "mls_group": row[9],
                }

                if row[6]:  # device
                    record_data["device"] = row[6]
                if row[10]:  # links_json
                    record_data["links"] = json.loads(row[10])
                if row[11]:  # meta_json
                    record_data["meta"] = json.loads(row[11])

                records.append(record_data)

            return records

        except Exception as e:
            logger.error(
                "Failed to list episodic records",
                extra={"filters": filters, "error": str(e)},
            )
            return []

    # Specialized episodic store methods

    def store_record(self, record: EpisodicRecord) -> str:
        """Store an episodic record (specialized method)."""
        if not self._connection or not self._in_transaction:
            raise RuntimeError("Store not in transaction")

        try:
            ts_unix = int(record.ts.timestamp())

            self._connection.execute(
                """
                INSERT OR REPLACE INTO episodic_records (
                    id, envelope_id, space_id, ts, ts_iso, band, author,
                    device, content_json, features_json, mls_group,
                    links_json, meta_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record.id,
                    record.envelope_id,
                    record.space_id,
                    ts_unix,
                    record.ts.isoformat(),
                    record.band,
                    record.author,
                    record.device,
                    json.dumps(record.content),
                    json.dumps(record.features),
                    record.mls_group,
                    json.dumps(record.links) if record.links else None,
                    json.dumps(record.meta) if record.meta else None,
                ),
            )

            logger.debug(
                "Episodic record stored",
                extra={
                    "record_id": record.id,
                    "space_id": record.space_id,
                    "author": record.author,
                },
            )

            return record.id

        except Exception as e:
            logger.error(
                "Failed to store episodic record",
                extra={"record_id": record.id, "error": str(e)},
            )
            raise

    def get_record(self, record_id: str, space_id: str) -> Optional[EpisodicRecord]:
        """Get episodic record by ID and space (with space context)."""
        if not self._connection:
            return None

        try:
            cursor = self._connection.execute(
                """
                SELECT id, envelope_id, space_id, ts_iso, band, author,
                       device, content_json, features_json, mls_group,
                       links_json, meta_json
                FROM episodic_records
                WHERE id = ? AND space_id = ?
                LIMIT 1
            """,
                (record_id, space_id),
            )

            row = cursor.fetchone()
            if not row:
                return None

            record_data = {
                "id": row[0],
                "envelope_id": row[1],
                "space_id": row[2],
                "ts": row[3],
                "band": row[4],
                "author": row[5],
                "content": json.loads(row[7]),
                "features": json.loads(row[8]),
                "mls_group": row[9],
            }

            if row[6]:  # device
                record_data["device"] = row[6]
            if row[10]:  # links_json
                record_data["links"] = json.loads(row[10])
            if row[11]:  # meta_json
                record_data["meta"] = json.loads(row[11])

            return EpisodicRecord.from_dict(record_data)

        except Exception as e:
            logger.error(
                "Failed to get episodic record",
                extra={"record_id": record_id, "space_id": space_id, "error": str(e)},
            )
            return None

    def query_temporal(self, query: TemporalQuery) -> List[EpisodicRecord]:
        """Execute temporal query against episodic records."""
        if not self._connection:
            return []

        try:
            where_clauses: List[str] = ["space_id = ?"]
            params: List[Any] = [query.space_id]

            if query.start_time:
                where_clauses.append("ts >= ?")
                params.append(int(query.start_time.timestamp()))

            if query.end_time:
                where_clauses.append("ts <= ?")
                params.append(int(query.end_time.timestamp()))

            if query.author:
                where_clauses.append("author = ?")
                params.append(query.author)

            if query.band_filter:
                placeholders = ",".join("?" * len(query.band_filter))
                where_clauses.append(f"band IN ({placeholders})")
                params.extend(query.band_filter)

            if query.sequence_id:
                where_clauses.append("json_extract(links_json, '$.sequence_id') = ?")
                params.append(query.sequence_id)

            # Basic keyword search in content
            if query.keywords:
                keyword_conditions: List[str] = []
                for keyword in query.keywords:
                    keyword_conditions.append(
                        "(content_json LIKE ? OR features_json LIKE ?)"
                    )
                    params.extend([f"%{keyword}%", f"%{keyword}%"])
                where_clauses.append(f"({' OR '.join(keyword_conditions)})")

            where_clause = " AND ".join(where_clauses)
            order_clause = "ORDER BY ts DESC" if query.order_desc else "ORDER BY ts ASC"

            sql = f"""
                SELECT id, envelope_id, space_id, ts_iso, band, author,
                       device, content_json, features_json, mls_group,
                       links_json, meta_json
                FROM episodic_records
                WHERE {where_clause}
                {order_clause}
                LIMIT ? OFFSET ?
            """
            params.extend([query.limit, query.offset])

            cursor = self._connection.execute(sql, params)

            records: List[EpisodicRecord] = []
            for row in cursor:
                record_data = {
                    "id": row[0],
                    "envelope_id": row[1],
                    "space_id": row[2],
                    "ts": row[3],
                    "band": row[4],
                    "author": row[5],
                    "content": json.loads(row[7]),
                    "features": json.loads(row[8]),
                    "mls_group": row[9],
                }

                if row[6]:  # device
                    record_data["device"] = row[6]
                if row[10]:  # links_json
                    record_data["links"] = json.loads(row[10])
                if row[11]:  # meta_json
                    record_data["meta"] = json.loads(row[11])

                records.append(EpisodicRecord.from_dict(record_data))

            return records

        except Exception as e:
            logger.error(
                "Temporal query failed",
                extra={"space_id": query.space_id, "error": str(e)},
            )
            return []

    # === Sequence Management Methods (Issue 2.1.2) ===

    def create_sequence(self, sequence: EpisodicSequence) -> str:
        """
        Create a new episodic sequence.

        Args:
            sequence: EpisodicSequence to create

        Returns:
            The sequence_id of the created sequence
        """
        if not self._connection or not self._in_transaction:
            raise RuntimeError("Cannot create sequence: no active transaction")

        sequence_data = sequence.to_dict()
        ts_unix = int(sequence.ts.timestamp())

        sql = """
            INSERT INTO episodic_sequences
            (sequence_id, space_id, ts, ts_iso, label, items_json, closed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        self._connection.execute(
            sql,
            (
                sequence_data["sequence_id"],
                sequence_data["space_id"],
                ts_unix,
                sequence.ts.isoformat(),
                sequence_data.get("label"),
                json.dumps(sequence_data["items"]),
                sequence_data.get("closed", False),
            ),
        )

        return sequence.sequence_id

    def get_sequence(self, sequence_id: str) -> Optional[EpisodicSequence]:
        """
        Retrieve an episodic sequence by ID.

        Args:
            sequence_id: The sequence ID to retrieve

        Returns:
            EpisodicSequence if found, None otherwise
        """
        if not self._connection:
            return None

        cursor = self._connection.execute(
            "SELECT * FROM episodic_sequences WHERE sequence_id = ?", (sequence_id,)
        )
        row = cursor.fetchone()

        if row:
            return self._row_to_sequence(row)
        return None

    def update_sequence(self, sequence: EpisodicSequence) -> bool:
        """
        Update an existing episodic sequence.

        Args:
            sequence: Updated EpisodicSequence

        Returns:
            True if sequence was updated, False if not found
        """
        if not self._connection or not self._in_transaction:
            return False

        sequence_data = sequence.to_dict()
        ts_unix = int(sequence.ts.timestamp())

        sql = """
            UPDATE episodic_sequences
            SET space_id = ?, ts = ?, ts_iso = ?, label = ?, items_json = ?, closed = ?
            WHERE sequence_id = ?
        """

        cursor = self._connection.execute(
            sql,
            (
                sequence_data["space_id"],
                ts_unix,
                sequence.ts.isoformat(),
                sequence_data.get("label"),
                json.dumps(sequence_data["items"]),
                sequence_data.get("closed", False),
                sequence_data["sequence_id"],
            ),
        )

        return cursor.rowcount > 0

    def delete_sequence(self, sequence_id: str) -> bool:
        """
        Delete an episodic sequence.

        Args:
            sequence_id: The sequence ID to delete

        Returns:
            True if sequence was deleted, False if not found
        """
        if not self._connection or not self._in_transaction:
            return False

        cursor = self._connection.execute(
            "DELETE FROM episodic_sequences WHERE sequence_id = ?", (sequence_id,)
        )
        return cursor.rowcount > 0

    def list_sequences(
        self,
        space_id: str,
        closed: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[EpisodicSequence]:
        """
        List episodic sequences for a space.

        Args:
            space_id: Space ID to filter by
            closed: If specified, filter by closed status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of EpisodicSequence objects
        """
        if not self._connection:
            return []

        where_clauses = ["space_id = ?"]
        parameters: List[Any] = [space_id]

        if closed is not None:
            where_clauses.append("closed = ?")
            parameters.append(closed)

        sql = f"""
            SELECT * FROM episodic_sequences
            WHERE {' AND '.join(where_clauses)}
            ORDER BY ts DESC
        """

        if limit:
            sql += " LIMIT ?"
            parameters.append(limit)

        if offset:
            sql += " OFFSET ?"
            parameters.append(offset)

        cursor = self._connection.execute(sql, parameters)
        rows = cursor.fetchall()

        return [self._row_to_sequence(row) for row in rows]

    def add_to_sequence(
        self,
        sequence_id: str,
        record_id: str,
        space_id: str,
        weight: Optional[float] = None,
    ) -> bool:
        """
        Add a record to an existing sequence.

        Args:
            sequence_id: The sequence to add to
            record_id: The record ID to add
            space_id: The space ID for the record lookup
            weight: Optional weight for the item

        Returns:
            True if successfully added, False if sequence not found
        """
        # Get the sequence
        sequence = self.get_sequence(sequence_id)
        if not sequence:
            return False

        # Get the record to get its timestamp
        record = self.get_record(record_id, space_id)
        if not record:
            return False

        # Add the new item
        new_item: Dict[str, Any] = {"id": record_id, "ts": record.ts}
        if weight is not None:
            new_item["weight"] = weight

        sequence.items.append(new_item)

        # Update the sequence
        return self.update_sequence(sequence)

    def remove_from_sequence(self, sequence_id: str, record_id: str) -> bool:
        """
        Remove a record from a sequence.

        Args:
            sequence_id: The sequence to remove from
            record_id: The record ID to remove

        Returns:
            True if successfully removed, False if sequence or record not found
        """
        # Get the sequence
        sequence = self.get_sequence(sequence_id)
        if not sequence:
            return False

        # Remove the item
        original_length = len(sequence.items)
        sequence.items = [item for item in sequence.items if item["id"] != record_id]

        if len(sequence.items) == original_length:
            return False  # Item not found

        # Update the sequence
        return self.update_sequence(sequence)

    def get_sequence_records(self, sequence_id: str) -> List[EpisodicRecord]:
        """
        Get all records in a sequence, ordered by their position in the sequence.

        Args:
            sequence_id: The sequence ID

        Returns:
            List of EpisodicRecord objects in sequence order
        """
        if not self._connection:
            return []

        sequence = self.get_sequence(sequence_id)
        if not sequence:
            return []

        # Get all record IDs from the sequence
        record_ids = [item["id"] for item in sequence.items]
        if not record_ids:
            return []

        # Build a query to get all records
        placeholders = ",".join("?" * len(record_ids))
        sql = f"SELECT * FROM episodic_records WHERE id IN ({placeholders})"

        cursor = self._connection.execute(sql, record_ids)
        rows = cursor.fetchall()

        # Convert rows to records and create a lookup
        records_by_id: Dict[str, EpisodicRecord] = {}
        for row in rows:
            record_data: Dict[str, Any] = {
                "id": row[0],
                "envelope_id": row[1],
                "space_id": row[2],
                "ts": row[3],
                "band": row[4],
                "author": row[5],
                "content": json.loads(row[7]),
                "features": json.loads(row[8]),
                "mls_group": row[9],
            }

            if row[6]:  # device
                record_data["device"] = row[6]
            if row[10]:  # links_json
                record_data["links"] = json.loads(row[10])
            if row[11]:  # meta_json
                record_data["meta"] = json.loads(row[11])

            records_by_id[row[0]] = EpisodicRecord.from_dict(record_data)

        # Return records in sequence order
        return [
            records_by_id[item["id"]]
            for item in sequence.items
            if item["id"] in records_by_id
        ]

    def _row_to_sequence(self, row: Any) -> EpisodicSequence:
        """Convert a database row to an EpisodicSequence object."""
        # Use ts_iso if available, otherwise convert from unix timestamp
        ts_iso = row[3] if len(row) > 3 and row[3] else None
        if ts_iso:
            ts = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
        else:
            # Fallback to unix timestamp conversion
            ts = datetime.fromtimestamp(row[2])

        return EpisodicSequence.from_dict(
            {
                "sequence_id": row[0],
                "space_id": row[1],
                "ts": ts.isoformat(),
                "label": row[4] if len(row) > 4 else None,
                "items": json.loads(row[5]) if len(row) > 5 and row[5] else [],
                "closed": bool(row[6]) if len(row) > 6 else False,
            }
        )
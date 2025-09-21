"""
MetacogStore - Metacognition report storage for MemoryOS.

Stores and manages metacognition reports including confidence scores,
error signals, reflection outcomes, and performance patterns.
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig


def _default_dict() -> Dict[str, float]:
    """Return empty dict for signal defaults."""
    return {}


def _default_list() -> List[str]:
    """Return empty list for flags defaults."""
    return []


def _default_suggestions() -> List[Dict[str, Any]]:
    """Return empty list for suggestions defaults."""
    return []


@dataclass
class MetacogReport:
    """Metacognition report with confidence and signals."""

    id: str
    timestamp: datetime
    space_id: str
    person_id: Optional[str] = None

    # Core metacognitive data
    confidence: float = 0.0  # Fused confidence [0-1]
    signals: Dict[str, float] = field(default_factory=_default_dict)  # Error signals
    flags: List[str] = field(default_factory=_default_list)  # Warning flags
    suggestions: List[Dict[str, Any]] = field(
        default_factory=_default_suggestions
    )  # Improvement tasks

    # Component confidences
    confidences: Dict[str, float] = field(default_factory=_default_dict)  # Per-module

    # Metadata
    model_version: str = "metacog:2025-09-06"
    notes: Optional[str] = None


class MetacogStore(BaseStore):
    """Storage for metacognition reports and confidence tracking."""

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for this store's data."""
        return {
            "metacog_report": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "ts": {"type": "string"},
                    "space_id": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "signals": {"type": "object"},
                    "notes": {"type": "string"},
                },
                "required": ["id", "ts", "space_id", "confidence", "signals"],
            }
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema."""
        conn.executescript(
            """
        CREATE TABLE IF NOT EXISTS metacog_reports (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            space_id TEXT NOT NULL,
            person_id TEXT,
            confidence REAL NOT NULL,
            signals TEXT NOT NULL,        -- JSON object of error signals
            flags TEXT,                   -- JSON array of warning flags
            suggestions TEXT,             -- JSON array of improvement suggestions
            confidences TEXT,             -- JSON object of per-module confidences
            model_version TEXT DEFAULT 'metacog:2025-09-06',
            notes TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_metacog_reports_space
        ON metacog_reports (space_id);

        CREATE INDEX IF NOT EXISTS idx_metacog_reports_timestamp
        ON metacog_reports (timestamp DESC);

        CREATE INDEX IF NOT EXISTS idx_metacog_reports_confidence
        ON metacog_reports (confidence);
        """
        )

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new metacognition report record."""
        # Generate ID if not provided
        if "id" not in data:
            data["id"] = f"metacog-{uuid.uuid4().hex}"

        # Handle timestamp
        if "timestamp" in data:
            if isinstance(data["timestamp"], str):
                timestamp = datetime.fromisoformat(
                    data["timestamp"].replace("Z", "+00:00")
                )
            else:
                timestamp = data["timestamp"]
        else:
            timestamp = datetime.now(timezone.utc)

        metacog_report = MetacogReport(
            id=data["id"],
            timestamp=timestamp,
            space_id=data.get("space_id", "default"),
            person_id=data.get("person_id"),
            confidence=data.get("confidence", 0.0),
            signals=data.get("signals", {}),
            flags=data.get("flags", []),
            suggestions=data.get("suggestions", []),
            confidences=data.get("confidences", {}),
            model_version=data.get("model_version", "metacog:2025-09-06"),
            notes=data.get("notes"),
        )

        if not self._connection:
            raise RuntimeError("No database connection")

        self._connection.execute(
            """
            INSERT INTO metacog_reports
            (id, timestamp, space_id, person_id, confidence, signals, flags,
             suggestions, confidences, model_version, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                metacog_report.id,
                metacog_report.timestamp.isoformat(),
                metacog_report.space_id,
                metacog_report.person_id,
                metacog_report.confidence,
                json.dumps(metacog_report.signals),
                json.dumps(metacog_report.flags),
                json.dumps(metacog_report.suggestions),
                json.dumps(metacog_report.confidences),
                metacog_report.model_version,
                metacog_report.notes,
            ),
        )

        return {
            "record_id": metacog_report.id,
            "id": metacog_report.id,
            "ts": metacog_report.timestamp.isoformat(),
            "space_id": metacog_report.space_id,
            "person_id": metacog_report.person_id,
            "confidence": metacog_report.confidence,
            "signals": metacog_report.signals,
            "flags": metacog_report.flags,
            "suggestions": metacog_report.suggestions,
            "confidences": metacog_report.confidences,
            "model_version": metacog_report.model_version,
            "notes": metacog_report.notes,
        }

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a metacognition report record by ID."""
        if not self._connection:
            raise RuntimeError("No database connection")

        cursor = self._connection.execute(
            "SELECT * FROM metacog_reports WHERE id = ?", (record_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "ts": row[1],
            "space_id": row[2],
            "person_id": row[3],
            "confidence": row[4],
            "signals": json.loads(row[5] or "{}"),
            "flags": json.loads(row[6] or "[]"),
            "suggestions": json.loads(row[7] or "[]"),
            "confidences": json.loads(row[8] or "{}"),
            "model_version": row[9],
            "notes": row[10],
        }

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing metacognition report record."""
        if not self._connection:
            raise RuntimeError("No database connection")

        # Read current record
        current = self._read_record(record_id)
        if not current:
            raise ValueError(f"Record {record_id} not found")

        # Update fields (most fields shouldn't change, but allow notes/confidence updates)
        if "confidence" in data:
            current["confidence"] = data["confidence"]
        if "signals" in data:
            current["signals"] = data["signals"]
        if "flags" in data:
            current["flags"] = data["flags"]
        if "suggestions" in data:
            current["suggestions"] = data["suggestions"]
        if "confidences" in data:
            current["confidences"] = data["confidences"]
        if "notes" in data:
            current["notes"] = data["notes"]

        self._connection.execute(
            """
            UPDATE metacog_reports
            SET confidence = ?, signals = ?, flags = ?, suggestions = ?,
                confidences = ?, notes = ?
            WHERE id = ?
        """,
            (
                current["confidence"],
                json.dumps(current["signals"]),
                json.dumps(current["flags"]),
                json.dumps(current["suggestions"]),
                json.dumps(current["confidences"]),
                current["notes"],
                record_id,
            ),
        )

        return current

    def _delete_record(self, record_id: str) -> bool:
        """Delete a metacognition report record."""
        if not self._connection:
            raise RuntimeError("No database connection")

        cursor = self._connection.execute(
            "DELETE FROM metacog_reports WHERE id = ?", (record_id,)
        )
        return cursor.rowcount > 0

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List metacognition report records with optional filtering and pagination."""
        if not self._connection:
            raise RuntimeError("No database connection")

        query = "SELECT * FROM metacog_reports"
        params: List[Any] = []

        if filters:
            conditions: List[str] = []
            if "space_id" in filters:
                conditions.append("space_id = ?")
                params.append(filters["space_id"])
            if "person_id" in filters:
                conditions.append("person_id = ?")
                params.append(filters["person_id"])
            if "min_confidence" in filters:
                conditions.append("confidence >= ?")
                params.append(filters["min_confidence"])
            if "max_confidence" in filters:
                conditions.append("confidence <= ?")
                params.append(filters["max_confidence"])

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
        results: List[Dict[str, Any]] = []

        for row in cursor.fetchall():
            results.append(
                {
                    "id": row[0],
                    "ts": row[1],
                    "space_id": row[2],
                    "person_id": row[3],
                    "confidence": row[4],
                    "signals": json.loads(row[5] or "{}"),
                    "flags": json.loads(row[6] or "[]"),
                    "suggestions": json.loads(row[7] or "[]"),
                    "confidences": json.loads(row[8] or "{}"),
                    "model_version": row[9],
                    "notes": row[10],
                }
            )

        return results

    # High-level API methods

    def get_latest_confidence(
        self, space_id: str, person_id: Optional[str] = None
    ) -> float:
        """Get the latest fused confidence for a space/person."""
        filters = {"space_id": space_id}
        if person_id:
            filters["person_id"] = person_id

        records = self._list_records(filters=filters, limit=1)
        return records[0]["confidence"] if records else 0.0

    def get_recent_flags(self, space_id: str, hours: int = 24) -> List[str]:
        """Get recent warning flags for a space."""
        from datetime import timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        # Get recent records
        records = self._list_records(filters={"space_id": space_id}, limit=100)

        all_flags: List[str] = []
        for record in records:
            if record["ts"] >= cutoff:
                flags = record.get("flags", [])
                if isinstance(flags, list):
                    all_flags.extend(flags)

        return list(set(all_flags))  # Deduplicate

    def get_confidence_trend(
        self, space_id: str, person_id: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get confidence trend over time."""
        filters = {"space_id": space_id}
        if person_id:
            filters["person_id"] = person_id

        records = self._list_records(filters=filters, limit=limit)

        return [
            {
                "timestamp": record["ts"],
                "confidence": record["confidence"],
                "signals": record["signals"],
            }
            for record in records
        ]

    def store_metacog_report(self, metacog_data: Dict[str, Any]) -> Dict[str, Any]:
        """High-level method to store a metacognition report."""
        return self.create(metacog_data)

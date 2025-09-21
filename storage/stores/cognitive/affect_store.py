"""Affect Store - Storage for emotional states and affect annotations."""

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from storage.core.base_store import BaseStore, StoreConfig, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class AffectState:
    """Current affect state for a person in a space."""

    person_id: str
    space_id: str
    v_ema: float = 0.0  # Valence exponential moving average
    a_ema: float = 0.0  # Arousal exponential moving average
    confidence: float = 0.0
    model_version: str = "affect-mvp"
    updated_at: float = field(default_factory=time.time)

    # Behavior baselines for z-score normalization
    baselines_json: Optional[str] = None  # JSON-serialized BehaviorBaselines


@dataclass
class AffectAnnotation:
    """Individual affect annotation for an event."""

    id: Optional[str] = None
    event_id: str = ""
    person_id: str = ""
    space_id: str = ""
    valence: float = 0.0
    arousal: float = 0.0
    dominance: Optional[float] = None  # Optional third dimension
    tags: List[str] = field(default_factory=list)  # type: ignore
    confidence: float = 0.0
    model_version: str = "affect-mvp"
    created_at: float = field(default_factory=time.time)

    # Context information
    context_json: Optional[str] = None  # JSON-serialized context data


class AffectStore(BaseStore):
    """Storage for affect states and annotations with VAD tracking."""

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize the affect storage schema."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            # Affect states table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS affect_states (
                    person_id TEXT NOT NULL,
                    space_id TEXT NOT NULL,
                    v_ema REAL NOT NULL DEFAULT 0.0,
                    a_ema REAL NOT NULL DEFAULT 0.0,
                    confidence REAL NOT NULL DEFAULT 0.0,
                    model_version TEXT NOT NULL DEFAULT 'affect-mvp',
                    updated_at REAL NOT NULL,
                    baselines_json TEXT,
                    PRIMARY KEY (person_id, space_id)
                )
            """
            )

            # Affect annotations table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS affect_annotations (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    person_id TEXT NOT NULL,
                    space_id TEXT NOT NULL,
                    valence REAL NOT NULL,
                    arousal REAL NOT NULL,
                    dominance REAL,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 0.0,
                    model_version TEXT NOT NULL DEFAULT 'affect-mvp',
                    created_at REAL NOT NULL,
                    context_json TEXT,
                    UNIQUE(event_id, person_id, space_id)
                )
            """
            )

            # Indexes for efficient queries
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_affect_annotations_person_space_time
                ON affect_annotations(person_id, space_id, created_at DESC)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_affect_annotations_event
                ON affect_annotations(event_id)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_affect_annotations_valence_arousal
                ON affect_annotations(valence, arousal)
            """
            )

            conn.commit()
            logger.info("Affect store schema initialized")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to initialize affect store schema: {e}")
            raise
        finally:
            conn.close()

    def get_state(self, person_id: str, space_id: str) -> AffectState:
        """Get current affect state for a person in a space."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT person_id, space_id, v_ema, a_ema, confidence,
                       model_version, updated_at, baselines_json
                FROM affect_states
                WHERE person_id = ? AND space_id = ?
            """,
                (person_id, space_id),
            )

            row = cursor.fetchone()
            if row:
                return AffectState(
                    person_id=str(row[0]),
                    space_id=str(row[1]),
                    v_ema=float(row[2]),
                    a_ema=float(row[3]),
                    confidence=float(row[4]),
                    model_version=str(row[5]),
                    updated_at=float(row[6]),
                    baselines_json=row[7] if row[7] else None,
                )
            else:
                # Return default state
                return AffectState(person_id=person_id, space_id=space_id)

        finally:
            conn.close()

    def put_state(self, state: AffectState) -> None:
        """Update affect state for a person in a space."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO affect_states
                (person_id, space_id, v_ema, a_ema, confidence,
                 model_version, updated_at, baselines_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    state.person_id,
                    state.space_id,
                    state.v_ema,
                    state.a_ema,
                    state.confidence,
                    state.model_version,
                    state.updated_at,
                    state.baselines_json,
                ),
            )
            conn.commit()
            logger.debug(
                f"Updated affect state for {state.person_id} in {state.space_id}"
            )

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update affect state: {e}")
            raise
        finally:
            conn.close()

    def append_annotation(self, annotation: AffectAnnotation) -> str:
        """Add an affect annotation and return its ID."""
        if not annotation.id:
            # Generate ID if not provided
            from uuid import uuid4

            annotation.id = f"aff-{uuid4().hex[:16]}"

        conn = sqlite3.connect(self.config.db_path)
        try:
            tags_json = json.dumps(annotation.tags)

            conn.execute(
                """
                INSERT OR REPLACE INTO affect_annotations
                (id, event_id, person_id, space_id, valence, arousal, dominance,
                 tags_json, confidence, model_version, created_at, context_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    annotation.id,
                    annotation.event_id,
                    annotation.person_id,
                    annotation.space_id,
                    annotation.valence,
                    annotation.arousal,
                    annotation.dominance,
                    tags_json,
                    annotation.confidence,
                    annotation.model_version,
                    annotation.created_at,
                    annotation.context_json,
                ),
            )
            conn.commit()
            logger.debug(f"Added affect annotation {annotation.id}")
            return annotation.id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add affect annotation: {e}")
            raise
        finally:
            conn.close()

    def list_annotations(
        self,
        person_id: str,
        space_id: str,
        limit: int = 2000,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> List[AffectAnnotation]:
        """List affect annotations for a person in a space."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            query = """
                SELECT id, event_id, person_id, space_id, valence, arousal, dominance,
                       tags_json, confidence, model_version, created_at, context_json
                FROM affect_annotations
                WHERE person_id = ? AND space_id = ?
            """
            params = [person_id, space_id]

            if start_time is not None:
                query += " AND created_at >= ?"
                params.append(start_time)

            if end_time is not None:
                query += " AND created_at <= ?"
                params.append(end_time)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            annotations = []

            for row in cursor.fetchall():
                tags = json.loads(row[7]) if row[7] else []
                annotations.append(
                    AffectAnnotation(
                        id=str(row[0]),
                        event_id=str(row[1]),
                        person_id=str(row[2]),
                        space_id=str(row[3]),
                        valence=float(row[4]),
                        arousal=float(row[5]),
                        dominance=float(row[6]) if row[6] is not None else None,
                        tags=tags,  # type: ignore
                        confidence=float(row[8]),
                        model_version=str(row[9]),
                        created_at=float(row[10]),
                        context_json=str(row[11]) if row[11] else None,
                    )
                )

            return annotations

        finally:
            conn.close()

    def get_annotation_by_event(self, event_id: str) -> Optional[AffectAnnotation]:
        """Get affect annotation by event ID."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT id, event_id, person_id, space_id, valence, arousal, dominance,
                       tags_json, confidence, model_version, created_at, context_json
                FROM affect_annotations
                WHERE event_id = ?
            """,
                (event_id,),
            )

            row = cursor.fetchone()
            if row:
                tags = json.loads(row[7]) if row[7] else []
                return AffectAnnotation(
                    id=str(row[0]),
                    event_id=str(row[1]),
                    person_id=str(row[2]),
                    space_id=str(row[3]),
                    valence=float(row[4]),
                    arousal=float(row[5]),
                    dominance=float(row[6]) if row[6] is not None else None,
                    tags=tags,  # type: ignore
                    confidence=float(row[8]),
                    model_version=str(row[9]),
                    created_at=float(row[10]),
                    context_json=str(row[11]) if row[11] else None,
                )
            return None

        finally:
            conn.close()

    def get_valence_arousal_history(
        self, person_id: str, space_id: str, hours: int = 24
    ) -> List[Tuple[float, float, float]]:
        """Get valence/arousal history as (timestamp, valence, arousal) tuples."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            start_time = time.time() - (hours * 3600)
            cursor = conn.execute(
                """
                SELECT created_at, valence, arousal
                FROM affect_annotations
                WHERE person_id = ? AND space_id = ? AND created_at >= ?
                ORDER BY created_at ASC
            """,
                (person_id, space_id, start_time),
            )

            return [(row[0], row[1], row[2]) for row in cursor.fetchall()]

        finally:
            conn.close()

    def update_ema_from_annotation(
        self, annotation: AffectAnnotation, alpha: float = 0.1
    ) -> AffectState:
        """Update EMA state from a new annotation."""
        current_state = self.get_state(annotation.person_id, annotation.space_id)

        # Update EMAs with new values
        current_state.v_ema = (
            1 - alpha
        ) * current_state.v_ema + alpha * annotation.valence
        current_state.a_ema = (
            1 - alpha
        ) * current_state.a_ema + alpha * annotation.arousal
        current_state.confidence = annotation.confidence
        current_state.model_version = annotation.model_version
        current_state.updated_at = annotation.created_at

        # Save updated state
        self.put_state(current_state)
        return current_state

    def validate_schema(self) -> ValidationResult:
        """Validate the affect store schema."""
        errors = []
        warnings = []

        conn = sqlite3.connect(self.config.db_path)
        try:
            # Check if required tables exist
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('affect_states', 'affect_annotations')
            """
            )
            tables = {row[0] for row in cursor.fetchall()}

            if "affect_states" not in tables:
                errors.append("affect_states table missing")

            if "affect_annotations" not in tables:
                errors.append("affect_annotations table missing")

            # Check indexes exist
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='index' AND name LIKE 'idx_affect_%'
            """
            )
            indexes = {row[0] for row in cursor.fetchall()}

            expected_indexes = {
                "idx_affect_annotations_person_space_time",
                "idx_affect_annotations_event",
                "idx_affect_annotations_valence_arousal",
            }

            missing_indexes = expected_indexes - indexes
            if missing_indexes:
                warnings.extend([f"Missing index: {idx}" for idx in missing_indexes])

        finally:
            conn.close()

        return ValidationResult(
            is_valid=(len(errors) == 0), errors=errors, warnings=warnings
        )

    # BaseStore abstract method implementations

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for affect store data."""
        return {
            "type": "object",
            "properties": {
                "affect_states": {
                    "type": "object",
                    "properties": {
                        "person_id": {"type": "string"},
                        "space_id": {"type": "string"},
                        "v_ema": {"type": "number"},
                        "a_ema": {"type": "number"},
                        "confidence": {"type": "number"},
                    },
                },
                "affect_annotations": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "event_id": {"type": "string"},
                        "person_id": {"type": "string"},
                        "space_id": {"type": "string"},
                        "valence": {"type": "number"},
                        "arousal": {"type": "number"},
                    },
                },
            },
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema and tables using provided connection."""
        # Use the same logic as _init_schema but with provided connection
        try:
            # Affect states table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS affect_states (
                    person_id TEXT NOT NULL,
                    space_id TEXT NOT NULL,
                    v_ema REAL NOT NULL DEFAULT 0.0,
                    a_ema REAL NOT NULL DEFAULT 0.0,
                    confidence REAL NOT NULL DEFAULT 0.0,
                    model_version TEXT NOT NULL DEFAULT 'affect-mvp',
                    updated_at REAL NOT NULL,
                    baselines_json TEXT,
                    PRIMARY KEY (person_id, space_id)
                )
            """
            )

            # Affect annotations table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS affect_annotations (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    person_id TEXT NOT NULL,
                    space_id TEXT NOT NULL,
                    valence REAL NOT NULL,
                    arousal REAL NOT NULL,
                    dominance REAL,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 0.0,
                    model_version TEXT NOT NULL DEFAULT 'affect-mvp',
                    created_at REAL NOT NULL,
                    context_json TEXT,
                    UNIQUE(event_id, person_id, space_id)
                )
            """
            )

            # Indexes for efficient queries
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_affect_annotations_person_space_time
                ON affect_annotations(person_id, space_id, created_at DESC)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_affect_annotations_event
                ON affect_annotations(event_id)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_affect_annotations_valence_arousal
                ON affect_annotations(valence, arousal)
            """
            )

            logger.info("Affect store schema initialized via BaseStore")

        except Exception as e:
            logger.error(f"Failed to initialize affect store schema via BaseStore: {e}")
            raise

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record in the store."""
        # This is a simplified implementation for BaseStore compatibility
        record_type = data.get("type", "annotation")

        if record_type == "state":
            state = AffectState(**data["state_data"])
            self.put_state(state)
            return {"id": f"{state.person_id}:{state.space_id}", "type": "state"}

        elif record_type == "annotation":
            annotation = AffectAnnotation(**data["annotation_data"])
            ann_id = self.append_annotation(annotation)
            return {"id": ann_id, "type": "annotation"}

        else:
            raise ValueError(f"Unknown record type: {record_type}")

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record by ID."""
        # Handle both state and annotation IDs
        if ":" in record_id:
            # State ID format: "person_id:space_id"
            person_id, space_id = record_id.split(":", 1)
            state = self.get_state(person_id, space_id)
            return {
                "id": record_id,
                "type": "state",
                "data": {
                    "person_id": state.person_id,
                    "space_id": state.space_id,
                    "v_ema": state.v_ema,
                    "a_ema": state.a_ema,
                    "confidence": state.confidence,
                },
            }
        else:
            # Annotation ID
            conn = sqlite3.connect(self.config.db_path)
            try:
                cursor = conn.execute(
                    "SELECT * FROM affect_annotations WHERE id = ?", (record_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "id": record_id,
                        "type": "annotation",
                        "data": {
                            "event_id": row[1],
                            "person_id": row[2],
                            "space_id": row[3],
                            "valence": row[4],
                            "arousal": row[5],
                        },
                    }
                return None
            finally:
                conn.close()

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record."""
        if ":" in record_id:
            # State update
            person_id, space_id = record_id.split(":", 1)
            state = self.get_state(person_id, space_id)

            # Update fields from data
            if "v_ema" in data:
                state.v_ema = data["v_ema"]
            if "a_ema" in data:
                state.a_ema = data["a_ema"]
            if "confidence" in data:
                state.confidence = data["confidence"]

            state.updated_at = time.time()
            self.put_state(state)

            return {"id": record_id, "type": "state", "updated": True}

        else:
            # Annotation updates are not typically allowed
            raise ValueError("Annotations are immutable records")

    def _delete_record(self, record_id: str) -> bool:
        """Delete a record."""
        if ":" in record_id:
            # Cannot delete state records (they reset to defaults)
            return False
        else:
            # Delete annotation
            conn = sqlite3.connect(self.config.db_path)
            try:
                cursor = conn.execute(
                    "DELETE FROM affect_annotations WHERE id = ?", (record_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List records with optional filtering and pagination."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            # Simple implementation - list annotations by default
            query = """
                SELECT id, event_id, person_id, space_id, valence, arousal, dominance,
                       tags_json, confidence, model_version, created_at, context_json
                FROM affect_annotations
            """
            params = []

            # Apply filters
            if filters:
                conditions = []
                if "person_id" in filters:
                    conditions.append("person_id = ?")
                    params.append(filters["person_id"])
                if "space_id" in filters:
                    conditions.append("space_id = ?")
                    params.append(filters["space_id"])
                if "event_id" in filters:
                    conditions.append("event_id = ?")
                    params.append(filters["event_id"])

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            if offset:
                query += " OFFSET ?"
                params.append(offset)

            cursor = conn.execute(query, params)
            records = []

            for row in cursor.fetchall():
                tags = json.loads(row[7]) if row[7] else []
                records.append(
                    {
                        "id": str(row[0]),
                        "type": "annotation",
                        "data": {
                            "event_id": str(row[1]),
                            "person_id": str(row[2]),
                            "space_id": str(row[3]),
                            "valence": float(row[4]),
                            "arousal": float(row[5]),
                            "dominance": float(row[6]) if row[6] is not None else None,
                            "tags": tags,
                            "confidence": float(row[8]),
                            "model_version": str(row[9]),
                            "created_at": float(row[10]),
                            "context_json": str(row[11]) if row[11] else None,
                        },
                    }
                )

            return records

        finally:
            conn.close()

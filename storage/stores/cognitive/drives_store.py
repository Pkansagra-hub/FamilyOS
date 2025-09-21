"""Drives Storage - Drive states, needs, and satisfaction tracking."""

import json
import logging
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from storage.core.base_store import BaseStore, StoreConfig, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class DriveNeed:
    """Individual drive need state with homeostatic tracking."""

    # Current level (0.0 to range)
    x: float = 0.0

    # Desired setpoint (homeostatic target)
    setpoint: float = 0.5

    # Feasible range for normalization
    range: float = 1.0

    # Integrator term for debt accumulation
    i_term: float = 0.0

    # Last satisfaction event timestamp
    last_satisfied: Optional[float] = None

    # Satisfaction history (timestamp, delta_x)
    satisfaction_history: List[Tuple[float, float]] = field(default_factory=list)

    def get_error(self) -> float:
        """Get normalized error (positive = need more)."""
        return (self.setpoint - self.x) / self.range if self.range > 0 else 0.0

    def get_need_activation(self, kappa: float = 3.0, theta: float = 0.1) -> float:
        """Get need activation via logistic function."""
        import math

        error = self.get_error()
        return 1.0 / (1.0 + math.exp(-kappa * (error - theta)))

    def update_integrator(self, decay: float = 0.9) -> None:
        """Update integrator term for debt accumulation."""
        error = self.get_error()
        self.i_term = decay * self.i_term + (1.0 - decay) * error

    def satisfy(self, delta_x: float, timestamp: Optional[float] = None) -> None:
        """Record satisfaction event."""
        if timestamp is None:
            timestamp = time.time()

        # Update current level
        self.x = max(0.0, min(self.range, self.x + delta_x))

        # Record satisfaction
        self.last_satisfied = timestamp
        self.satisfaction_history.append((timestamp, delta_x))

        # Keep only recent history (last 100 entries)
        if len(self.satisfaction_history) > 100:
            self.satisfaction_history = self.satisfaction_history[-100:]


@dataclass
class DriveState:
    """Complete drive state for a person in a space."""

    person_id: str
    space_id: str

    # Core needs tracking
    needs: Dict[str, DriveNeed] = field(default_factory=dict)

    # State metadata
    last_update: float = field(default_factory=time.time)
    version: str = "drives-mvp"

    # Drive configuration
    drive_config: Dict[str, Any] = field(default_factory=dict)

    def get_need(self, drive_name: str) -> DriveNeed:
        """Get or create a drive need."""
        if drive_name not in self.needs:
            # Default drive configurations
            defaults = {
                "sleep": {"setpoint": 0.2, "range": 8.0},
                "social": {"setpoint": 0.6, "range": 1.0},
                "chores": {"setpoint": 0.4, "range": 1.0},
                "planning": {"setpoint": 0.2, "range": 1.0},
                "achievement": {"setpoint": 0.5, "range": 1.0},
                "hunger": {"setpoint": 0.3, "range": 1.0},
                "exercise": {"setpoint": 0.4, "range": 1.0},
                "creativity": {"setpoint": 0.3, "range": 1.0},
            }

            config = defaults.get(drive_name, {"setpoint": 0.5, "range": 1.0})
            self.needs[drive_name] = DriveNeed(
                setpoint=config["setpoint"], range=config["range"]
            )

        return self.needs[drive_name]

    def update_need(
        self,
        drive_name: str,
        delta_x: Optional[float] = None,
        new_x: Optional[float] = None,
    ) -> None:
        """Update a drive need level."""
        need = self.get_need(drive_name)

        if new_x is not None:
            need.x = max(0.0, min(need.range, new_x))
        elif delta_x is not None:
            need.satisfy(delta_x)

        need.update_integrator()
        self.last_update = time.time()

    def get_priorities(self) -> Dict[str, float]:
        """Get current need priorities for all drives."""
        priorities = {}
        for drive_name, need in self.needs.items():
            priorities[drive_name] = need.get_need_activation()
        return priorities

    def apply_temporal_modulation(
        self,
        affect_arousal: float = 0.0,
        time_of_day_sin: float = 0.0,
        day_of_week_sin: float = 0.0,
        is_urgent: bool = False,
    ) -> Dict[str, float]:
        """Apply contextual modulation to drive priorities."""
        base_priorities = self.get_priorities()
        modulated = {}

        # Temporal modulation coefficients
        alpha_a = 0.3  # arousal coefficient
        alpha_u = 0.5  # urgency coefficient
        beta_t = 0.2  # time of day coefficient
        beta_w = 0.1  # day of week coefficient

        for drive_name, base_priority in base_priorities.items():
            # Arousal and urgency modulation
            arousal_mod = 1.0 + alpha_a * affect_arousal
            if is_urgent:
                arousal_mod += alpha_u

            # Temporal modulation (simplified)
            temporal_mod = 1.0 + beta_t * time_of_day_sin + beta_w * day_of_week_sin

            # Apply modulation
            modulated[drive_name] = base_priority * arousal_mod * temporal_mod

        return modulated


@dataclass
class DriveEvent:
    """Drive satisfaction or frustration event."""

    event_id: str
    person_id: str
    space_id: str

    # Drive affected
    drive_name: str

    # Change in drive level
    delta_x: float

    # Event metadata
    event_type: str = "satisfaction"  # "satisfaction", "frustration", "decay"
    source: str = "manual"  # "manual", "action", "temporal"

    # Context
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    context_json: Optional[str] = None

    # Timing
    created_at: float = field(default_factory=time.time)


class DrivesStore(BaseStore):
    """Storage for drive states and satisfaction events."""

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self.default_drives = [
            "sleep",
            "social",
            "chores",
            "planning",
            "achievement",
            "hunger",
            "exercise",
            "creativity",
        ]

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for drives storage."""
        return {
            "type": "object",
            "properties": {
                "drive_states": {
                    "type": "object",
                    "description": "Drive states storage schema",
                },
                "drive_events": {
                    "type": "object",
                    "description": "Drive events storage schema",
                },
            },
        }

    def _get_sql_schema(self) -> str:
        """Get database schema SQL for drives storage."""
        return """
        CREATE TABLE IF NOT EXISTS drive_states (
            person_id TEXT NOT NULL,
            space_id TEXT NOT NULL,
            needs_json TEXT NOT NULL,
            last_update REAL NOT NULL,
            version TEXT NOT NULL,
            drive_config_json TEXT,
            created_at REAL NOT NULL DEFAULT (unixepoch()),
            updated_at REAL NOT NULL DEFAULT (unixepoch()),
            PRIMARY KEY (person_id, space_id)
        );

        CREATE TABLE IF NOT EXISTS drive_events (
            event_id TEXT PRIMARY KEY,
            person_id TEXT NOT NULL,
            space_id TEXT NOT NULL,
            drive_name TEXT NOT NULL,
            delta_x REAL NOT NULL,
            event_type TEXT NOT NULL,
            source TEXT NOT NULL,
            tags_json TEXT,
            confidence REAL NOT NULL,
            context_json TEXT,
            created_at REAL NOT NULL,
            FOREIGN KEY (person_id, space_id) REFERENCES drive_states(person_id, space_id)
        );

        CREATE INDEX IF NOT EXISTS idx_drive_states_person_space
            ON drive_states(person_id, space_id);
        CREATE INDEX IF NOT EXISTS idx_drive_events_person_space
            ON drive_events(person_id, space_id);
        CREATE INDEX IF NOT EXISTS idx_drive_events_drive_name
            ON drive_events(drive_name);
        CREATE INDEX IF NOT EXISTS idx_drive_events_created_at
            ON drive_events(created_at);
        """

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema."""
        conn.executescript(self._get_sql_schema())

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record."""
        # Determine if this is a drive state or event based on data structure
        if "needs" in data and "person_id" in data and "space_id" in data:
            record_id = self._create_drive_state(data)
            return {"record_id": record_id, **data}
        elif "drive_name" in data and "delta_x" in data:
            record_id = self._create_drive_event(data)
            return {"record_id": record_id, **data}
        else:
            raise ValueError("Unknown record type for drives store")

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record by ID."""
        # Try to read as drive state first (format: "person_id:space_id")
        if ":" in record_id:
            parts = record_id.split(":", 1)
            if len(parts) == 2:
                return self._read_drive_state(parts[0], parts[1])

        # Try to read as drive event
        return self._read_drive_event(record_id)

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record."""
        # Only drive states can be updated (events are immutable)
        if ":" in record_id:
            parts = record_id.split(":", 1)
            if len(parts) == 2:
                success = self._update_drive_state(parts[0], parts[1], data)
                if success:
                    return {"record_id": record_id, **data}

        raise ValueError(f"Cannot update record {record_id}")

    def _delete_record(self, record_id: str) -> bool:
        """Delete a record."""
        # Try to delete as drive state first
        if ":" in record_id:
            parts = record_id.split(":", 1)
            if len(parts) == 2:
                return self._delete_drive_state(parts[0], parts[1])

        # Try to delete as drive event
        return self._delete_drive_event(record_id)

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List records with optional filtering and pagination."""
        # Default to listing drive states
        return self._list_drive_states(limit, offset)

    def _create_drive_state(self, data: Dict[str, Any]) -> str:
        """Create a drive state record."""
        drive_state = DriveState(**data)

        # Serialize needs manually to handle nested structures
        needs_dict = {}
        for k, v in drive_state.needs.items():
            needs_dict[k] = {
                "x": v.x,
                "setpoint": v.setpoint,
                "range": v.range,
                "i_term": v.i_term,
                "last_satisfied": v.last_satisfied,
                "satisfaction_history": v.satisfaction_history,
            }

        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO drive_states
                (person_id, space_id, needs_json, last_update, version, drive_config_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    drive_state.person_id,
                    drive_state.space_id,
                    json.dumps(needs_dict),
                    drive_state.last_update,
                    drive_state.version,
                    json.dumps(drive_state.drive_config),
                    time.time(),
                ),
            )

        return f"{drive_state.person_id}:{drive_state.space_id}"

    def _read_drive_state(
        self, person_id: str, space_id: str
    ) -> Optional[Dict[str, Any]]:
        """Read a drive state."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM drive_states
                WHERE person_id = ? AND space_id = ?
            """,
                (person_id, space_id),
            )

            row = cursor.fetchone()
            if not row:
                return None

            needs_data = json.loads(row["needs_json"])
            needs = {k: DriveNeed(**v) for k, v in needs_data.items()}

            return {
                "person_id": row["person_id"],
                "space_id": row["space_id"],
                "needs": needs,
                "last_update": row["last_update"],
                "version": row["version"],
                "drive_config": json.loads(row["drive_config_json"] or "{}"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

    def _update_drive_state(
        self, person_id: str, space_id: str, data: Dict[str, Any]
    ) -> bool:
        """Update a drive state."""
        try:
            with sqlite3.connect(self.config.db_path) as conn:
                # Serialize needs manually if they're DriveNeed objects
                if "needs" in data:
                    needs_dict = {}
                    for k, v in data["needs"].items():
                        if hasattr(v, "x"):  # DriveNeed object
                            needs_dict[k] = {
                                "x": v.x,
                                "setpoint": v.setpoint,
                                "range": v.range,
                                "i_term": v.i_term,
                                "last_satisfied": v.last_satisfied,
                                "satisfaction_history": v.satisfaction_history,
                            }
                        else:  # Already a dict
                            needs_dict[k] = v
                    needs_json = json.dumps(needs_dict)
                else:
                    needs_json = json.dumps({})

                cursor = conn.execute(
                    """
                    UPDATE drive_states
                    SET needs_json = ?, last_update = ?, version = ?,
                        drive_config_json = ?, updated_at = ?
                    WHERE person_id = ? AND space_id = ?
                """,
                    (
                        needs_json,
                        data.get("last_update", time.time()),
                        data.get("version", "drives-mvp"),
                        json.dumps(data.get("drive_config", {})),
                        time.time(),
                        person_id,
                        space_id,
                    ),
                )

                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update drive state: {e}")
            return False

    def _delete_drive_state(self, person_id: str, space_id: str) -> bool:
        """Delete a drive state."""
        try:
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM drive_states
                    WHERE person_id = ? AND space_id = ?
                """,
                    (person_id, space_id),
                )

                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete drive state: {e}")
            return False

    def _list_drive_states(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List drive states."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM drive_states ORDER BY updated_at DESC"
            params = []

            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)

            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                needs_data = json.loads(row["needs_json"])
                needs = {k: DriveNeed(**v) for k, v in needs_data.items()}

                results.append(
                    {
                        "person_id": row["person_id"],
                        "space_id": row["space_id"],
                        "needs": needs,
                        "last_update": row["last_update"],
                        "version": row["version"],
                        "drive_config": json.loads(row["drive_config_json"] or "{}"),
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                )

            return results

    def _create_drive_event(self, data: Dict[str, Any]) -> str:
        """Create a drive event record."""
        drive_event = DriveEvent(**data)

        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute(
                """
                INSERT INTO drive_events
                (event_id, person_id, space_id, drive_name, delta_x, event_type,
                 source, tags_json, confidence, context_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    drive_event.event_id,
                    drive_event.person_id,
                    drive_event.space_id,
                    drive_event.drive_name,
                    drive_event.delta_x,
                    drive_event.event_type,
                    drive_event.source,
                    json.dumps(drive_event.tags),
                    drive_event.confidence,
                    drive_event.context_json,
                    drive_event.created_at,
                ),
            )

        return drive_event.event_id

    def _read_drive_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Read a drive event."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM drive_events WHERE event_id = ?
            """,
                (event_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            return {
                "event_id": row["event_id"],
                "person_id": row["person_id"],
                "space_id": row["space_id"],
                "drive_name": row["drive_name"],
                "delta_x": row["delta_x"],
                "event_type": row["event_type"],
                "source": row["source"],
                "tags": json.loads(row["tags_json"] or "[]"),
                "confidence": row["confidence"],
                "context_json": row["context_json"],
                "created_at": row["created_at"],
            }

    def _delete_drive_event(self, event_id: str) -> bool:
        """Delete a drive event."""
        try:
            with sqlite3.connect(self.config.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM drive_events WHERE event_id = ?
                """,
                    (event_id,),
                )

                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete drive event: {e}")
            return False

    def _list_drive_events(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List drive events."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM drive_events ORDER BY created_at DESC"
            params = []

            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)

            if offset is not None:
                query += " OFFSET ?"
                params.append(offset)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "event_id": row["event_id"],
                        "person_id": row["person_id"],
                        "space_id": row["space_id"],
                        "drive_name": row["drive_name"],
                        "delta_x": row["delta_x"],
                        "event_type": row["event_type"],
                        "source": row["source"],
                        "tags": json.loads(row["tags_json"] or "[]"),
                        "confidence": row["confidence"],
                        "context_json": row["context_json"],
                        "created_at": row["created_at"],
                    }
                )

            return results

    # High-level API methods

    def get_drive_state(self, person_id: str, space_id: str) -> DriveState:
        """Get or create drive state for person in space."""
        data = self._read_drive_state(person_id, space_id)

        if data:
            return DriveState(
                person_id=data["person_id"],
                space_id=data["space_id"],
                needs=data["needs"],
                last_update=data["last_update"],
                version=data["version"],
                drive_config=data["drive_config"],
            )
        else:
            # Create default drive state
            drive_state = DriveState(person_id=person_id, space_id=space_id)

            # Initialize default drives
            for drive_name in self.default_drives:
                drive_state.get_need(drive_name)  # Creates with defaults

            # Save to database - convert manually to avoid asdict issues
            data_to_save = {
                "person_id": drive_state.person_id,
                "space_id": drive_state.space_id,
                "needs": drive_state.needs,
                "last_update": drive_state.last_update,
                "version": drive_state.version,
                "drive_config": drive_state.drive_config,
            }

            self._create_drive_state(data_to_save)

            return drive_state

    def update_drive_state(self, drive_state: DriveState) -> None:
        """Update drive state in storage."""
        # Convert to dict manually to handle the nested DriveNeed objects
        data = {
            "person_id": drive_state.person_id,
            "space_id": drive_state.space_id,
            "needs": drive_state.needs,  # Will be handled in _update_drive_state
            "last_update": drive_state.last_update,
            "version": drive_state.version,
            "drive_config": drive_state.drive_config,
        }

        self._update_drive_state(drive_state.person_id, drive_state.space_id, data)

    def record_drive_event(self, drive_event: DriveEvent) -> str:
        """Record a drive satisfaction/frustration event."""
        return self._create_drive_event(asdict(drive_event))

    def get_drive_events(
        self,
        person_id: str,
        space_id: str,
        drive_name: Optional[str] = None,
        hours: int = 24,
        limit: Optional[int] = None,
    ) -> List[DriveEvent]:
        """Get drive events for person in space."""
        cutoff_time = time.time() - (hours * 3600)

        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if drive_name:
                query = """
                    SELECT * FROM drive_events
                    WHERE person_id = ? AND space_id = ? AND drive_name = ?
                          AND created_at > ?
                    ORDER BY created_at DESC
                """
                params = [person_id, space_id, drive_name, cutoff_time]
            else:
                query = """
                    SELECT * FROM drive_events
                    WHERE person_id = ? AND space_id = ? AND created_at > ?
                    ORDER BY created_at DESC
                """
                params = [person_id, space_id, cutoff_time]

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            events = []
            for row in rows:
                events.append(
                    DriveEvent(
                        event_id=row["event_id"],
                        person_id=row["person_id"],
                        space_id=row["space_id"],
                        drive_name=row["drive_name"],
                        delta_x=row["delta_x"],
                        event_type=row["event_type"],
                        source=row["source"],
                        tags=json.loads(row["tags_json"] or "[]"),
                        confidence=row["confidence"],
                        context_json=row["context_json"],
                        created_at=row["created_at"],
                    )
                )

            return events

    def satisfy_drive(
        self,
        person_id: str,
        space_id: str,
        drive_name: str,
        delta_x: float,
        event_id: Optional[str] = None,
        source: str = "manual",
        tags: Optional[List[str]] = None,
    ) -> str:
        """Record drive satisfaction and update state."""
        import uuid

        if event_id is None:
            event_id = f"drv-{uuid.uuid4().hex[:12]}"

        # Record event
        drive_event = DriveEvent(
            event_id=event_id,
            person_id=person_id,
            space_id=space_id,
            drive_name=drive_name,
            delta_x=delta_x,
            event_type="satisfaction" if delta_x > 0 else "frustration",
            source=source,
            tags=tags or [],
        )

        self.record_drive_event(drive_event)

        # Update drive state
        drive_state = self.get_drive_state(person_id, space_id)
        drive_state.update_need(drive_name, delta_x=delta_x)
        self.update_drive_state(drive_state)

        return event_id

    def get_drive_priorities(
        self,
        person_id: str,
        space_id: str,
        affect_arousal: float = 0.0,
        time_of_day_sin: float = 0.0,
        day_of_week_sin: float = 0.0,
        is_urgent: bool = False,
    ) -> Dict[str, float]:
        """Get current drive priorities with temporal modulation."""
        drive_state = self.get_drive_state(person_id, space_id)
        return drive_state.apply_temporal_modulation(
            affect_arousal, time_of_day_sin, day_of_week_sin, is_urgent
        )

    def validate_schema(self) -> ValidationResult:
        """Validate the drives storage schema."""
        try:
            with sqlite3.connect(self.config.db_path) as conn:
                # Check if required tables exist
                cursor = conn.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name IN ('drive_states', 'drive_events')
                """
                )
                tables = {row[0] for row in cursor.fetchall()}

                errors = []
                warnings = []

                if "drive_states" not in tables:
                    errors.append("Missing drive_states table")

                if "drive_events" not in tables:
                    errors.append("Missing drive_events table")

                if not errors:
                    # Check for required columns
                    cursor = conn.execute("PRAGMA table_info(drive_states)")
                    state_columns = {row[1] for row in cursor.fetchall()}

                    required_state_columns = {
                        "person_id",
                        "space_id",
                        "needs_json",
                        "last_update",
                        "version",
                    }
                    missing = required_state_columns - state_columns
                    if missing:
                        errors.append(f"Missing drive_states columns: {missing}")

                    cursor = conn.execute("PRAGMA table_info(drive_events)")
                    event_columns = {row[1] for row in cursor.fetchall()}

                    required_event_columns = {
                        "event_id",
                        "person_id",
                        "space_id",
                        "drive_name",
                        "delta_x",
                        "event_type",
                        "source",
                        "created_at",
                    }
                    missing = required_event_columns - event_columns
                    if missing:
                        errors.append(f"Missing drive_events columns: {missing}")

                return ValidationResult(
                    is_valid=len(errors) == 0, errors=errors, warnings=warnings
                )

        except Exception as e:
            return ValidationResult(
                is_valid=False, errors=[f"Schema validation failed: {e}"], warnings=[]
            )

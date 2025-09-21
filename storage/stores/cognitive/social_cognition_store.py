"""Social Cognition Store - Theory of Mind (ToM) mental state tracking and inference storage."""

import json
import logging
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

from storage.core.base_store import BaseStore, StoreConfig, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class Belief:
    """Individual belief with truth probability and confidence."""

    truth_prob: float
    confidence: float
    source: str
    updated_at: float = field(default_factory=time.time)


@dataclass
class Desire:
    """Goal or desire with strength rating."""

    strength: float
    source: str
    updated_at: float = field(default_factory=time.time)


@dataclass
class Intention:
    """Intended plan with commitment level."""

    commitment: float
    source: str
    deadline: Optional[float] = None
    updated_at: float = field(default_factory=time.time)


@dataclass
class AffectHint:
    """Optional affect state hint for mental state context."""

    valence: float  # -1.0 to 1.0
    arousal: float  # 0.0 to 1.0


@dataclass
class MentalState:
    """Complete mental state for a person in a space."""

    person_id: str
    space_id: str
    beliefs: Dict[str, Belief] = field(default_factory=dict)
    desires: Dict[str, Desire] = field(default_factory=dict)
    intentions: Dict[str, Intention] = field(default_factory=dict)
    affect_hint: Optional[AffectHint] = None
    visibility: List[str] = field(default_factory=list)  # observed event_ids
    model_version: str = "tom-mvp"
    updated_at: float = field(default_factory=time.time)


@dataclass
class NormJudgment:
    """Social norm assessment."""

    tag: str
    pressure: float  # -1.0 to 1.0 (negative = violation, positive = compliance)
    confidence: float  # 0.0 to 1.0


@dataclass
class IntentionRecord:
    """Detected intention with commitment level."""

    plan: str
    commitment: float


@dataclass
class ToMReport:
    """Theory of Mind inference report."""

    id: str
    event_id: str
    person_id: str
    space_id: str
    inferred_beliefs: Dict[str, float]  # belief -> truth_prob
    intentions: List[IntentionRecord]
    norm_judgments: List[NormJudgment]
    confidence: float
    false_belief_risk: Optional[float] = None
    notes: List[str] = field(default_factory=list)
    model_version: str = "tom-mvp"
    created_at: float = field(default_factory=time.time)


class SocialCognitionStore(BaseStore):
    """Storage for Theory of Mind mental states and inference reports."""

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._init_schema()

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for social cognition data."""
        return {
            "mental_state": {
                "type": "object",
                "properties": {
                    "person_id": {"type": "string"},
                    "space_id": {"type": "string"},
                    "beliefs": {"type": "object"},
                    "desires": {"type": "object"},
                    "intentions": {"type": "object"},
                    "affect_hint": {"type": ["object", "null"]},
                    "visibility": {"type": "array", "items": {"type": "string"}},
                    "model_version": {"type": "string"},
                    "updated_at": {"type": "number"},
                },
                "required": ["person_id", "space_id", "model_version", "updated_at"],
            },
            "tom_report": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "event_id": {"type": "string"},
                    "person_id": {"type": "string"},
                    "space_id": {"type": "string"},
                    "inferred_beliefs": {"type": "object"},
                    "intentions": {"type": "array"},
                    "norm_judgments": {"type": "array"},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "false_belief_risk": {"type": ["number", "null"]},
                    "notes": {"type": "array", "items": {"type": "string"}},
                    "model_version": {"type": "string"},
                    "created_at": {"type": "number"},
                },
                "required": [
                    "id",
                    "event_id",
                    "person_id",
                    "space_id",
                    "confidence",
                    "model_version",
                    "created_at",
                ],
            },
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema and tables."""
        self._init_schema()  # Reuse existing initialization

    def _init_schema(self) -> None:
        """Initialize the social cognition storage schema."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            # Mental states table - per person per space
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mental_states (
                    person_id TEXT NOT NULL,
                    space_id TEXT NOT NULL,
                    beliefs_json TEXT NOT NULL DEFAULT '{}',
                    desires_json TEXT NOT NULL DEFAULT '{}',
                    intentions_json TEXT NOT NULL DEFAULT '{}',
                    affect_hint_json TEXT,
                    visibility_json TEXT NOT NULL DEFAULT '[]',
                    model_version TEXT NOT NULL DEFAULT 'tom-mvp',
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (person_id, space_id)
                )
            """
            )

            # ToM reports table - inference outputs
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tom_reports (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    person_id TEXT NOT NULL,
                    space_id TEXT NOT NULL,
                    inferred_beliefs_json TEXT NOT NULL DEFAULT '{}',
                    intentions_json TEXT NOT NULL DEFAULT '[]',
                    norm_judgments_json TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 0.0,
                    false_belief_risk REAL,
                    notes_json TEXT NOT NULL DEFAULT '[]',
                    model_version TEXT NOT NULL DEFAULT 'tom-mvp',
                    created_at REAL NOT NULL
                )
            """
            )

            # Indexes for efficient queries
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mental_states_person_space "
                "ON mental_states(person_id, space_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mental_states_updated "
                "ON mental_states(updated_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tom_reports_event "
                "ON tom_reports(event_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tom_reports_person_space "
                "ON tom_reports(person_id, space_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tom_reports_created "
                "ON tom_reports(created_at DESC)"
            )

            conn.commit()
        finally:
            conn.close()

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new social cognition record (mental state or ToM report)."""
        # Determine record type based on data structure
        if "inferred_beliefs" in data:
            return self._create_tom_report(data)
        else:
            return self._create_mental_state(data)

    def _create_mental_state(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a mental state record."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            # Convert complex fields to JSON
            beliefs_json = json.dumps(data.get("beliefs", {}))
            desires_json = json.dumps(data.get("desires", {}))
            intentions_json = json.dumps(data.get("intentions", {}))
            affect_hint_json = (
                json.dumps(data.get("affect_hint")) if data.get("affect_hint") else None
            )
            visibility_json = json.dumps(data.get("visibility", []))

            # Insert or replace mental state
            conn.execute(
                """
                INSERT OR REPLACE INTO mental_states
                (person_id, space_id, beliefs_json, desires_json, intentions_json,
                 affect_hint_json, visibility_json, model_version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["person_id"],
                    data["space_id"],
                    beliefs_json,
                    desires_json,
                    intentions_json,
                    affect_hint_json,
                    visibility_json,
                    data.get("model_version", "tom-mvp"),
                    data.get("updated_at", time.time()),
                ),
            )

            conn.commit()
            return data
        finally:
            conn.close()

    def _create_tom_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a ToM report record."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            report_id = data.get("id", f"tom-rpt-{uuid4().hex[:12]}")

            # Convert complex fields to JSON
            inferred_beliefs_json = json.dumps(data.get("inferred_beliefs", {}))
            intentions_json = json.dumps(data.get("intentions", []))
            norm_judgments_json = json.dumps(data.get("norm_judgments", []))
            notes_json = json.dumps(data.get("notes", []))

            conn.execute(
                """
                INSERT INTO tom_reports
                (id, event_id, person_id, space_id, inferred_beliefs_json,
                 intentions_json, norm_judgments_json, confidence, false_belief_risk,
                 notes_json, model_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    data["event_id"],
                    data["person_id"],
                    data["space_id"],
                    inferred_beliefs_json,
                    intentions_json,
                    norm_judgments_json,
                    data.get("confidence", 0.0),
                    data.get("false_belief_risk"),
                    notes_json,
                    data.get("model_version", "tom-mvp"),
                    data.get("created_at", time.time()),
                ),
            )

            conn.commit()
            result = data.copy()
            result["id"] = report_id
            return result
        finally:
            conn.close()

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record by ID (mental state key or ToM report ID)."""
        # Try to parse as mental state key (person_id:space_id)
        if ":" in record_id:
            parts = record_id.split(":", 1)
            if len(parts) == 2:
                person_id, space_id = parts
                return self.get_mental_state(person_id, space_id)

        # Try as ToM report ID
        return self.get_tom_report(record_id)

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a record."""
        if ":" in record_id:
            # Mental state update
            parts = record_id.split(":", 1)
            if len(parts) == 2:
                person_id, space_id = parts
                data["person_id"] = person_id
                data["space_id"] = space_id
                return self._create_mental_state(data)

        raise ValueError(f"Cannot update ToM reports or invalid record_id: {record_id}")

    def _delete_record(self, record_id: str) -> bool:
        """Delete a record."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            if ":" in record_id:
                # Delete mental state
                parts = record_id.split(":", 1)
                if len(parts) == 2:
                    person_id, space_id = parts
                    cursor = conn.execute(
                        "DELETE FROM mental_states WHERE person_id = ? AND space_id = ?",
                        (person_id, space_id),
                    )
                    conn.commit()
                    return cursor.rowcount > 0
            else:
                # Delete ToM report
                cursor = conn.execute(
                    "DELETE FROM tom_reports WHERE id = ?", (record_id,)
                )
                conn.commit()
                return cursor.rowcount > 0

            return False
        finally:
            conn.close()

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List all records (mental states and ToM reports)."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            records: List[Dict[str, Any]] = []

            # Get mental states
            query = "SELECT * FROM mental_states ORDER BY updated_at DESC"
            if limit:
                query += f" LIMIT {limit}"
                if offset:
                    query += f" OFFSET {offset}"

            cursor = conn.execute(query)
            for row in cursor.fetchall():
                record: Dict[str, Any] = {
                    "type": "mental_state",
                    "person_id": row[0],
                    "space_id": row[1],
                    "beliefs": json.loads(row[2]),
                    "desires": json.loads(row[3]),
                    "intentions": json.loads(row[4]),
                    "affect_hint": json.loads(row[5]) if row[5] else None,
                    "visibility": json.loads(row[6]),
                    "model_version": row[7],
                    "updated_at": row[8],
                }
                records.append(record)

            # Get ToM reports (remaining limit)
            remaining_limit = limit - len(records) if limit else None
            if remaining_limit is None or remaining_limit > 0:
                query = "SELECT * FROM tom_reports ORDER BY created_at DESC"
                if remaining_limit:
                    query += f" LIMIT {remaining_limit}"

                cursor = conn.execute(query)
                for row in cursor.fetchall():
                    record = {
                        "type": "tom_report",
                        "id": row[0],
                        "event_id": row[1],
                        "person_id": row[2],
                        "space_id": row[3],
                        "inferred_beliefs": json.loads(row[4]),
                        "intentions": json.loads(row[5]),
                        "norm_judgments": json.loads(row[6]),
                        "confidence": row[7],
                        "false_belief_risk": row[8],
                        "notes": json.loads(row[9]),
                        "model_version": row[10],
                        "created_at": row[11],
                    }
                    records.append(record)

            return records
        finally:
            conn.close()

    def _count_records(self) -> int:
        """Count total records (mental states + ToM reports)."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM mental_states")
            mental_count = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM tom_reports")
            report_count = cursor.fetchone()[0]

            return mental_count + report_count
        finally:
            conn.close()

    def _validate_data(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate social cognition data."""
        errors: List[str] = []

        # Common required fields
        if not data.get("person_id"):
            errors.append("person_id is required")
        if not data.get("space_id"):
            errors.append("space_id is required")

        # Validate based on record type
        if "inferred_beliefs" in data:
            # ToM report validation
            if not data.get("event_id"):
                errors.append("event_id is required for ToM reports")

            confidence = data.get("confidence", 0.0)
            if not (0.0 <= confidence <= 1.0):
                errors.append("confidence must be between 0.0 and 1.0")

            false_belief_risk = data.get("false_belief_risk")
            if false_belief_risk is not None and not (0.0 <= false_belief_risk <= 1.0):
                errors.append("false_belief_risk must be between 0.0 and 1.0")
        else:
            # Mental state validation
            affect_hint = data.get("affect_hint")
            if affect_hint:
                valence = affect_hint.get("valence", 0.0)
                if not (-1.0 <= valence <= 1.0):
                    errors.append("affect_hint.valence must be between -1.0 and 1.0")

                arousal = affect_hint.get("arousal", 0.0)
                if not (0.0 <= arousal <= 1.0):
                    errors.append("affect_hint.arousal must be between 0.0 and 1.0")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    # High-level API methods

    def store_mental_state(self, mental_state: MentalState) -> Dict[str, Any]:
        """Store or update a mental state."""
        data = asdict(mental_state)
        # Convert nested dataclasses to dicts
        for beliefs_key, belief in data.get("beliefs", {}).items():
            if hasattr(belief, "__dict__"):
                data["beliefs"][beliefs_key] = asdict(belief)
        for desires_key, desire in data.get("desires", {}).items():
            if hasattr(desire, "__dict__"):
                data["desires"][desires_key] = asdict(desire)
        for intentions_key, intention in data.get("intentions", {}).items():
            if hasattr(intention, "__dict__"):
                data["intentions"][intentions_key] = asdict(intention)
        if data.get("affect_hint") and hasattr(data["affect_hint"], "__dict__"):
            data["affect_hint"] = asdict(data["affect_hint"])

        return self._create_mental_state(data)

    def get_mental_state(
        self, person_id: str, space_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get mental state for a person in a space."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT person_id, space_id, beliefs_json, desires_json, intentions_json,
                       affect_hint_json, visibility_json, model_version, updated_at
                FROM mental_states
                WHERE person_id = ? AND space_id = ?
                """,
                (person_id, space_id),
            )
            row = cursor.fetchone()
            if not row:
                return None

            return {
                "person_id": row[0],
                "space_id": row[1],
                "beliefs": json.loads(row[2]),
                "desires": json.loads(row[3]),
                "intentions": json.loads(row[4]),
                "affect_hint": json.loads(row[5]) if row[5] else None,
                "visibility": json.loads(row[6]),
                "model_version": row[7],
                "updated_at": row[8],
            }
        finally:
            conn.close()

    def update_mental_state(
        self,
        person_id: str,
        space_id: str,
        beliefs: Optional[Dict[str, Belief]] = None,
        desires: Optional[Dict[str, Desire]] = None,
        intentions: Optional[Dict[str, Intention]] = None,
        affect_hint: Optional[AffectHint] = None,
        new_visibility: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update specific parts of a mental state."""
        # Get current state or create new
        current = self.get_mental_state(person_id, space_id)
        if not current:
            current = {
                "person_id": person_id,
                "space_id": space_id,
                "beliefs": {},
                "desires": {},
                "intentions": {},
                "affect_hint": None,
                "visibility": [],
                "model_version": "tom-mvp",
                "updated_at": time.time(),
            }

        # Update fields if provided
        if beliefs is not None:
            current["beliefs"].update(
                {
                    k: asdict(v) if hasattr(v, "__dict__") else v
                    for k, v in beliefs.items()
                }
            )
        if desires is not None:
            current["desires"].update(
                {
                    k: asdict(v) if hasattr(v, "__dict__") else v
                    for k, v in desires.items()
                }
            )
        if intentions is not None:
            current["intentions"].update(
                {
                    k: asdict(v) if hasattr(v, "__dict__") else v
                    for k, v in intentions.items()
                }
            )
        if affect_hint is not None:
            current["affect_hint"] = (
                asdict(affect_hint) if hasattr(affect_hint, "__dict__") else affect_hint
            )
        if new_visibility is not None:
            # Add new event IDs to visibility list
            current_visibility = set(current["visibility"])
            current_visibility.update(new_visibility)
            current["visibility"] = list(current_visibility)

        current["updated_at"] = time.time()

        return self._create_mental_state(current)

    def store_tom_report(self, report: ToMReport) -> Dict[str, Any]:
        """Store a ToM inference report."""
        data = asdict(report)
        # Convert nested dataclasses to dicts
        if data.get("intentions"):
            data["intentions"] = [
                asdict(intention) if hasattr(intention, "__dict__") else intention
                for intention in data["intentions"]
            ]
        if data.get("norm_judgments"):
            data["norm_judgments"] = [
                asdict(judgment) if hasattr(judgment, "__dict__") else judgment
                for judgment in data["norm_judgments"]
            ]

        return self._create_tom_report(data)

    def get_tom_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a ToM report by ID."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT id, event_id, person_id, space_id, inferred_beliefs_json,
                       intentions_json, norm_judgments_json, confidence, false_belief_risk,
                       notes_json, model_version, created_at
                FROM tom_reports
                WHERE id = ?
                """,
                (report_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            return {
                "id": row[0],
                "event_id": row[1],
                "person_id": row[2],
                "space_id": row[3],
                "inferred_beliefs": json.loads(row[4]),
                "intentions": json.loads(row[5]),
                "norm_judgments": json.loads(row[6]),
                "confidence": row[7],
                "false_belief_risk": row[8],
                "notes": json.loads(row[9]),
                "model_version": row[10],
                "created_at": row[11],
            }
        finally:
            conn.close()

    def get_reports_for_person(
        self, person_id: str, space_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent ToM reports for a person (optionally in specific space)."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            if space_id:
                query = """
                    SELECT id, event_id, person_id, space_id, inferred_beliefs_json,
                           intentions_json, norm_judgments_json, confidence, false_belief_risk,
                           notes_json, model_version, created_at
                    FROM tom_reports
                    WHERE person_id = ? AND space_id = ?
                    ORDER BY created_at DESC LIMIT ?
                """
                params = (person_id, space_id, limit)
            else:
                query = """
                    SELECT id, event_id, person_id, space_id, inferred_beliefs_json,
                           intentions_json, norm_judgments_json, confidence, false_belief_risk,
                           notes_json, model_version, created_at
                    FROM tom_reports
                    WHERE person_id = ?
                    ORDER BY created_at DESC LIMIT ?
                """
                params = (person_id, limit)

            cursor = conn.execute(query, params)
            reports: List[Dict[str, Any]] = []
            for row in cursor.fetchall():
                reports.append(
                    {
                        "id": row[0],
                        "event_id": row[1],
                        "person_id": row[2],
                        "space_id": row[3],
                        "inferred_beliefs": json.loads(row[4]),
                        "intentions": json.loads(row[5]),
                        "norm_judgments": json.loads(row[6]),
                        "confidence": row[7],
                        "false_belief_risk": row[8],
                        "notes": json.loads(row[9]),
                        "model_version": row[10],
                        "created_at": row[11],
                    }
                )

            return reports
        finally:
            conn.close()

    def get_recent_intentions(
        self, person_id: str, space_id: str, min_commitment: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Get recent high-commitment intentions for a person."""
        mental_state = self.get_mental_state(person_id, space_id)
        if not mental_state:
            return []

        intentions: List[Dict[str, Any]] = []
        for plan, intention_data in mental_state.get("intentions", {}).items():
            commitment = intention_data.get("commitment", 0.0)
            if commitment >= min_commitment:
                intentions.append(
                    {
                        "plan": plan,
                        "commitment": commitment,
                        "deadline": intention_data.get("deadline"),
                        "source": intention_data.get("source"),
                        "updated_at": intention_data.get("updated_at"),
                    }
                )

        # Sort by commitment descending
        intentions.sort(key=lambda x: x["commitment"], reverse=True)
        return intentions

    def get_belief_confidence(
        self, person_id: str, space_id: str, belief: str
    ) -> Optional[float]:
        """Get confidence for a specific belief."""
        mental_state = self.get_mental_state(person_id, space_id)
        if not mental_state:
            return None

        belief_data = mental_state.get("beliefs", {}).get(belief)
        if not belief_data:
            return None

        return belief_data.get("confidence", 0.0)

    def add_observed_events(
        self, person_id: str, space_id: str, event_ids: List[str]
    ) -> None:
        """Add new observed events to a person's visibility."""
        self.update_mental_state(person_id, space_id, new_visibility=event_ids)

    def check_false_belief_risk(
        self,
        person_id: str,
        space_id: str,
        ground_truth_beliefs: Dict[str, float],
        threshold: float = 0.3,
    ) -> Optional[float]:
        """Check for false belief risk by comparing with ground truth."""
        mental_state = self.get_mental_state(person_id, space_id)
        if not mental_state:
            return None

        person_beliefs = mental_state.get("beliefs", {})
        divergences: List[float] = []

        for belief, truth_prob in ground_truth_beliefs.items():
            person_belief_data = person_beliefs.get(belief)
            if person_belief_data:
                person_prob = person_belief_data.get("truth_prob", 0.5)
                divergence = abs(truth_prob - person_prob)
                divergences.append(divergence)

        if not divergences:
            return None

        max_divergence = max(divergences)
        return max_divergence if max_divergence > threshold else None

    def get_social_norm_patterns(
        self, space_id: str, limit: int = 100
    ) -> Dict[str, Dict[str, Any]]:
        """Get patterns of social norm judgments in a space."""
        conn = sqlite3.connect(self.config.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT norm_judgments_json, confidence, created_at
                FROM tom_reports
                WHERE space_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (space_id, limit),
            )

            norm_stats = {}

            for row in cursor.fetchall():
                norm_judgments = json.loads(row[0])
                row[1]

                for judgment in norm_judgments:
                    tag = judgment.get("tag")
                    pressure = judgment.get("pressure", 0.0)
                    confidence = judgment.get("confidence", 0.0)

                    if tag not in norm_stats:
                        norm_stats[tag] = {
                            "count": 0,
                            "avg_pressure": 0.0,
                            "avg_confidence": 0.0,
                            "total_pressure": 0.0,
                            "total_confidence": 0.0,
                        }

                    stats = norm_stats[tag]
                    stats["count"] += 1
                    stats["total_pressure"] += pressure
                    stats["total_confidence"] += confidence
                    stats["avg_pressure"] = stats["total_pressure"] / stats["count"]
                    stats["avg_confidence"] = stats["total_confidence"] / stats["count"]

            return norm_stats
        finally:
            conn.close()

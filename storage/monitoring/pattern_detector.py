"""
Pattern Detector Store - Storage for detected patterns and their evidence.

This module implements storage for pattern detection results following the
pattern_detection.schema.json contract. Stores detected patterns with confidence
scores and evidence links for analysis and learning.

Key Features:
- Pattern detection result storage with confidence scoring
- Evidence tracking via ULID references
- Space-scoped access control for family contexts
- Pattern search and filtering capabilities
- BaseStore compliance for transaction management
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


@dataclass
class PatternDetection:
    """
    Pattern detection record following pattern_detection.schema.json contract.

    Represents a detected pattern with confidence score and supporting evidence.
    """

    id: str  # ULID
    space_id: str  # Space ID
    ts: str  # Timestamp
    pattern: str  # Pattern description/identifier
    score: float  # Confidence score (0.0-1.0)
    evidence: Optional[List[str]] = None  # List of evidence ULIDs


class PatternDetector(BaseStore):
    """
    Pattern detection storage for learning and analysis.

    Provides pattern management with:
    - Pattern detection result storage with confidence scoring
    - Evidence tracking and linking via ULIDs
    - Space-scoped access controls
    - Pattern search and filtering capabilities
    - Score-based ranking and analysis

    Storage Model:
    - pattern_detections table: Pattern metadata with evidence links
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        """Initialize pattern detector store with detections table schema."""
        super().__init__(config)
        logger.info("PatternDetector initialized for pattern detection storage")

    def _get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for pattern detection validation."""
        return {
            "type": "object",
            "required": ["id", "space_id", "ts", "pattern", "score"],
            "properties": {
                "id": {"type": "string"},
                "space_id": {"type": "string"},
                "ts": {"type": "string", "format": "date-time"},
                "pattern": {"type": "string"},
                "score": {"type": "number"},
                "evidence": {"type": "array", "items": {"type": "string"}},
            },
        }

    def _initialize_schema(self, conn: Any) -> None:
        """Initialize pattern detections database schema."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS pattern_detections (
            id TEXT PRIMARY KEY,
            space_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            pattern TEXT NOT NULL,
            score REAL NOT NULL,
            evidence TEXT,  -- JSON array of ULIDs
            created_ts TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_ts TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_pattern_detections_space_id ON pattern_detections(space_id);
        CREATE INDEX IF NOT EXISTS idx_pattern_detections_ts ON pattern_detections(ts);
        CREATE INDEX IF NOT EXISTS idx_pattern_detections_pattern ON pattern_detections(pattern);
        CREATE INDEX IF NOT EXISTS idx_pattern_detections_score ON pattern_detections(score);
        CREATE INDEX IF NOT EXISTS idx_pattern_detections_space_pattern
            ON pattern_detections(space_id, pattern);
        CREATE INDEX IF NOT EXISTS idx_pattern_detections_space_score
            ON pattern_detections(space_id, score);
        """

        conn.executescript(schema_sql)
        logger.info("Pattern detector schema initialized with pattern_detections table")

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a generic record (converts to PatternDetection and calls store_detection)."""
        pattern_detection = PatternDetection(
            id=data["id"],
            space_id=data["space_id"],
            ts=data["ts"],
            pattern=data["pattern"],
            score=data["score"],
            evidence=data.get("evidence"),
        )
        self.store_detection(pattern_detection)
        return asdict(pattern_detection)

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a generic record (calls get_detection and converts to dict)."""
        detection = self.get_detection(record_id)
        return asdict(detection) if detection else None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a generic record (calls update_detection and returns updated record)."""
        self.update_detection(record_id, data)
        updated_detection = self.get_detection(record_id)
        if not updated_detection:
            raise ValueError(f"Failed to update pattern detection {record_id}")
        return asdict(updated_detection)

    def _delete_record(self, record_id: str) -> bool:
        """Delete a generic record (calls delete_detection)."""
        try:
            self.delete_detection(record_id)
            return True
        except Exception:
            return False

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List generic records (returns pattern detections as dicts)."""
        space_id = filters.get("space_id") if filters else None
        pattern = filters.get("pattern") if filters else None
        min_score = filters.get("min_score") if filters else None

        detections = self.list_detections(space_id, pattern, min_score, limit)

        # Apply offset if specified
        if offset and offset > 0:
            detections = detections[offset:]

        return [asdict(detection) for detection in detections]

    # Pattern Detection Management
    def store_detection(self, detection: PatternDetection) -> str:
        """
        Store a pattern detection result.

        Args:
            detection: PatternDetection instance to store

        Returns:
            detection_id: The ID of the stored detection
        """
        if not self._connection:
            raise RuntimeError("PatternDetector not in transaction")

        evidence_json = json.dumps(detection.evidence) if detection.evidence else None

        self._connection.execute(
            """
            INSERT INTO pattern_detections (id, space_id, ts, pattern, score, evidence)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                detection.id,
                detection.space_id,
                detection.ts,
                detection.pattern,
                detection.score,
                evidence_json,
            ),
        )

        logger.info(
            f"Stored pattern detection {detection.id} ({detection.pattern}) "
            f"with score {detection.score:.3f} in space {detection.space_id}"
        )
        return detection.id

    def get_detection(self, detection_id: str) -> Optional[PatternDetection]:
        """
        Retrieve a pattern detection by ID.

        Args:
            detection_id: The detection ID to retrieve

        Returns:
            PatternDetection instance or None if not found
        """
        if not self._connection:
            raise RuntimeError("PatternDetector not in transaction")

        cursor = self._connection.execute(
            """
            SELECT id, space_id, ts, pattern, score, evidence
            FROM pattern_detections WHERE id = ?
        """,
            (detection_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        evidence = json.loads(row[5]) if row[5] else None

        return PatternDetection(
            id=row[0],
            space_id=row[1],
            ts=row[2],
            pattern=row[3],
            score=row[4],
            evidence=evidence,
        )

    def update_detection(self, detection_id: str, updates: Dict[str, Any]) -> None:
        """
        Update a pattern detection.

        Args:
            detection_id: The detection ID to update
            updates: Dictionary of fields to update
        """
        if not self._connection:
            raise RuntimeError("PatternDetector not in transaction")

        # Build dynamic update query
        update_fields: List[str] = []
        values: List[Any] = []

        if "pattern" in updates:
            update_fields.append("pattern = ?")
            values.append(updates["pattern"])

        if "score" in updates:
            update_fields.append("score = ?")
            values.append(updates["score"])

        if "evidence" in updates:
            update_fields.append("evidence = ?")
            values.append(
                json.dumps(updates["evidence"]) if updates["evidence"] else None
            )

        if not update_fields:
            return

        update_fields.append("updated_ts = CURRENT_TIMESTAMP")
        values.append(detection_id)

        self._connection.execute(
            f"""
            UPDATE pattern_detections SET {', '.join(update_fields)}
            WHERE id = ?
        """,
            values,
        )

        logger.info(f"Updated pattern detection {detection_id}")

    def delete_detection(self, detection_id: str) -> None:
        """
        Delete a pattern detection.

        Args:
            detection_id: The detection ID to delete
        """
        if not self._connection:
            raise RuntimeError("PatternDetector not in transaction")

        self._connection.execute(
            "DELETE FROM pattern_detections WHERE id = ?", (detection_id,)
        )

        logger.info(f"Deleted pattern detection {detection_id}")

    def list_detections(
        self,
        space_id: Optional[str] = None,
        pattern: Optional[str] = None,
        min_score: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[PatternDetection]:
        """
        List pattern detections with optional filtering.

        Args:
            space_id: Optional space filter
            pattern: Optional pattern filter
            min_score: Optional minimum score threshold
            limit: Optional result limit

        Returns:
            List of PatternDetection instances
        """
        if not self._connection:
            raise RuntimeError("PatternDetector not in transaction")

        # Build dynamic query
        where_clauses: List[str] = []
        params: List[Any] = []

        if space_id:
            where_clauses.append("space_id = ?")
            params.append(space_id)

        if pattern:
            where_clauses.append("pattern = ?")
            params.append(pattern)

        if min_score is not None:
            where_clauses.append("score >= ?")
            params.append(min_score)

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            SELECT id, space_id, ts, pattern, score, evidence
            FROM pattern_detections WHERE {where_clause}
            ORDER BY score DESC, ts DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor = self._connection.execute(query, params)
        rows = cursor.fetchall()

        detections = []
        for row in rows:
            evidence = json.loads(row[5]) if row[5] else None
            detection = PatternDetection(
                id=row[0],
                space_id=row[1],
                ts=row[2],
                pattern=row[3],
                score=row[4],
                evidence=evidence,
            )
            detections.append(detection)

        return detections

    def list_patterns_by_score(
        self,
        min_score: float,
        space_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[PatternDetection]:
        """
        List pattern detections above a score threshold.

        Args:
            min_score: Minimum score threshold
            space_id: Optional space filter
            limit: Optional result limit

        Returns:
            List of PatternDetection instances sorted by score descending
        """
        return self.list_detections(space_id, None, min_score, limit)

    def get_top_patterns(
        self,
        space_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[PatternDetection]:
        """
        Get top-scoring pattern detections.

        Args:
            space_id: Optional space filter
            limit: Maximum number of results (default 10)

        Returns:
            List of top PatternDetection instances sorted by score
        """
        return self.list_detections(space_id, None, None, limit)

    def get_pattern_stats(self, space_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get pattern detection statistics.

        Args:
            space_id: Optional space filter

        Returns:
            Dictionary with pattern counts and score statistics
        """
        if not self._connection:
            raise RuntimeError("PatternDetector not in transaction")

        # Build base query
        if space_id:
            base_where = "WHERE space_id = ?"
            params = (space_id,)
        else:
            base_where = ""
            params = ()

        # Get total count
        cursor = self._connection.execute(
            f"SELECT COUNT(*) FROM pattern_detections {base_where}", params
        )
        total_detections = cursor.fetchone()[0]

        # Get unique pattern count
        cursor = self._connection.execute(
            f"SELECT COUNT(DISTINCT pattern) FROM pattern_detections {base_where}",
            params,
        )
        unique_patterns = cursor.fetchone()[0]

        # Get score statistics
        cursor = self._connection.execute(
            f"""
            SELECT AVG(score), MIN(score), MAX(score)
            FROM pattern_detections {base_where}
        """,
            params,
        )
        score_row = cursor.fetchone()
        avg_score = score_row[0] if score_row[0] is not None else 0.0
        min_score = score_row[1] if score_row[1] is not None else 0.0
        max_score = score_row[2] if score_row[2] is not None else 0.0

        # Get pattern breakdown
        cursor = self._connection.execute(
            f"""
            SELECT pattern, COUNT(*), AVG(score)
            FROM pattern_detections {base_where}
            GROUP BY pattern ORDER BY COUNT(*) DESC
        """,
            params,
        )

        pattern_stats = []
        for row in cursor.fetchall():
            pattern_stats.append(
                {
                    "pattern": row[0],
                    "count": row[1],
                    "avg_score": row[2],
                }
            )

        return {
            "total_detections": total_detections,
            "unique_patterns": unique_patterns,
            "score_stats": {
                "avg": avg_score,
                "min": min_score,
                "max": max_score,
            },
            "pattern_breakdown": pattern_stats,
        }

    def cleanup_low_confidence_detections(
        self,
        score_threshold: float,
        older_than_days: Optional[int] = None,
        space_id: Optional[str] = None,
    ) -> int:
        """
        Clean up low-confidence pattern detections.

        Args:
            score_threshold: Delete detections below this score
            older_than_days: Optional additional age filter
            space_id: Optional space filter

        Returns:
            Number of detections deleted
        """
        if not self._connection:
            raise RuntimeError("PatternDetector not in transaction")

        # Build dynamic query
        where_clauses = ["score < ?"]
        params: List[Any] = [score_threshold]

        if space_id:
            where_clauses.append("space_id = ?")
            params.append(space_id)

        if older_than_days:
            cutoff_ts = datetime.now(timezone.utc).timestamp() - (
                older_than_days * 24 * 60 * 60
            )
            cutoff_iso = datetime.fromtimestamp(cutoff_ts, timezone.utc).isoformat()
            where_clauses.append("ts < ?")
            params.append(cutoff_iso)

        where_clause = " AND ".join(where_clauses)

        # First count what we'll delete
        cursor = self._connection.execute(
            f"SELECT COUNT(*) FROM pattern_detections WHERE {where_clause}", params
        )
        delete_count = cursor.fetchone()[0]

        # Then delete
        if delete_count > 0:
            self._connection.execute(
                f"DELETE FROM pattern_detections WHERE {where_clause}", params
            )
            logger.info(
                f"Cleaned up {delete_count} low-confidence pattern detections "
                f"(score < {score_threshold})"
            )

        return delete_count

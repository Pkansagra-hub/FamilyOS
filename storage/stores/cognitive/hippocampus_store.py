"""Hippocampus Store - Brain-inspired memory pattern storage

Implements contract-compliant storage for hippocampus traces following the
DG (Dentate Gyrus) pattern separation encoding from the hippocampus module.

Storage Schema:
- id: ULID trace identifier
- space_id: Space scope for privacy/policy enforcement
- ts: ISO timestamp of encoding
- simhash_hex: 512-bit SimHash as hex string for pattern matching
- minhash32: Array of 32-bit MinHash values for Jaccard similarity
- novelty: Computed novelty score (0.0-1.0)
- meta: Optional metadata (author, mentions, etc.)

Integration:
- Extends BaseStore for transaction management and validation
- Space-scoped queries for privacy enforcement
- Optimized indexing for pattern matching and temporal queries
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


class HippocampusStore(BaseStore):
    """
    Storage for hippocampus traces with pattern matching capabilities.

    Implements brain-inspired storage following DG (Dentate Gyrus)
    pattern separation encoding with SimHash/MinHash for similarity.
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._store_name = "hippocampus"

    def _get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for hippocampus trace validation."""
        return {
            "type": "object",
            "required": ["id", "space_id", "ts", "simhash_hex", "minhash32", "novelty"],
            "properties": {
                "id": {
                    "type": "string",
                    "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$",  # ULID format
                    "description": "ULID trace identifier",
                },
                "space_id": {
                    "type": "string",
                    "pattern": "^[a-zA-Z0-9_:-]+$",
                    "description": "Space scope for privacy enforcement",
                },
                "ts": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO timestamp of encoding",
                },
                "simhash_hex": {
                    "type": "string",
                    "pattern": "^[0-9a-fA-F]{128}$",  # 512 bits = 128 hex chars
                    "description": "512-bit SimHash as hex string",
                },
                "minhash32": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0, "maximum": 4294967295},
                    "minItems": 32,
                    "maxItems": 64,
                    "description": "Array of 32-bit MinHash values",
                },
                "novelty": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Computed novelty score",
                },
                "meta": {
                    "type": "object",
                    "description": "Optional metadata (author, mentions, etc.)",
                    "additionalProperties": True,
                },
            },
            "additionalProperties": False,
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize hippocampus traces table with optimized indexes."""

        # Main traces table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hippocampus_traces (
                id TEXT PRIMARY KEY,
                space_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                simhash_hex TEXT NOT NULL,
                minhash32 TEXT NOT NULL,  -- JSON array
                novelty REAL NOT NULL,
                meta TEXT,  -- JSON object
                created_at TEXT NOT NULL DEFAULT (datetime('now')),

                CHECK (length(id) = 26),
                CHECK (length(simhash_hex) = 128),
                CHECK (novelty >= 0.0 AND novelty <= 1.0)
            )
        """
        )

        # Indexes for pattern matching and temporal queries
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_hippocampus_space_ts
            ON hippocampus_traces(space_id, ts DESC)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_hippocampus_novelty
            ON hippocampus_traces(space_id, novelty DESC)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_hippocampus_simhash
            ON hippocampus_traces(space_id, simhash_hex)
        """
        )

        logger.info("Hippocampus store schema initialized")

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new hippocampus trace record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Serialize complex fields
        minhash32_json = json.dumps(data["minhash32"])
        meta_json = json.dumps(data.get("meta", {}))
        created_at = datetime.now(timezone.utc).isoformat()

        self._connection.execute(
            """
            INSERT INTO hippocampus_traces
            (id, space_id, ts, simhash_hex, minhash32, novelty, meta, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                data["id"],
                data["space_id"],
                data["ts"],
                data["simhash_hex"],
                minhash32_json,
                data["novelty"],
                meta_json,
                created_at,
            ),
        )

        # Return the created record
        result = self._read_record(data["id"])
        if result is None:
            raise RuntimeError(f"Failed to create record {data['id']}")
        return result

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a hippocampus trace by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            """
            SELECT id, space_id, ts, simhash_hex, minhash32, novelty, meta, created_at
            FROM hippocampus_traces
            WHERE id = ?
        """,
            (record_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_dict(row)

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing hippocampus trace record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Build dynamic update query for provided fields
        update_fields: List[str] = []
        values: List[Any] = []

        for field in ["space_id", "ts", "simhash_hex", "novelty"]:
            if field in data:
                update_fields.append(f"{field} = ?")
                values.append(data[field])

        if "minhash32" in data:
            update_fields.append("minhash32 = ?")
            values.append(json.dumps(data["minhash32"]))

        if "meta" in data:
            update_fields.append("meta = ?")
            values.append(json.dumps(data["meta"]))

        if not update_fields:
            raise ValueError("No valid fields to update")

        values.append(record_id)

        cursor = self._connection.execute(
            f"""
            UPDATE hippocampus_traces
            SET {', '.join(update_fields)}
            WHERE id = ?
        """,
            values,
        )

        if cursor.rowcount == 0:
            raise ValueError(f"Record {record_id} not found")

        result = self._read_record(record_id)
        if result is None:
            raise RuntimeError(f"Failed to read updated record {record_id}")
        return result

    def _delete_record(self, record_id: str) -> bool:
        """Delete a hippocampus trace by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            """
            DELETE FROM hippocampus_traces WHERE id = ?
        """,
            (record_id,),
        )

        return cursor.rowcount > 0

    def get_encoding(self, event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get hippocampal encoding by event ID.

        This is the public interface method called by HippocampusAPI.
        Returns the raw record dict that can be converted to HippocampalEncoding.
        """
        return self._read_record(event_id)

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List hippocampus traces with optional filtering and pagination."""
        if not self._connection:
            raise RuntimeError("No active connection")

        where_clauses: List[str] = []
        values: List[Any] = []

        if filters:
            if "space_id" in filters:
                where_clauses.append("space_id = ?")
                values.append(filters["space_id"])

            if "min_novelty" in filters:
                where_clauses.append("novelty >= ?")
                values.append(filters["min_novelty"])

            if "max_novelty" in filters:
                where_clauses.append("novelty <= ?")
                values.append(filters["max_novelty"])

            if "since_ts" in filters:
                where_clauses.append("ts >= ?")
                values.append(filters["since_ts"])

            if "until_ts" in filters:
                where_clauses.append("ts <= ?")
                values.append(filters["until_ts"])

        query = """
            SELECT id, space_id, ts, simhash_hex, minhash32, novelty, meta, created_at
            FROM hippocampus_traces
        """

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY ts DESC"

        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"

        cursor = self._connection.execute(query, values)
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to dictionary with JSON deserialization."""
        return {
            "id": str(row[0]),
            "space_id": str(row[1]),
            "ts": str(row[2]),
            "simhash_hex": str(row[3]),
            "minhash32": json.loads(str(row[4])),
            "novelty": float(row[5]),
            "meta": json.loads(str(row[6])) if row[6] else {},
            "created_at": str(row[7]),
        }

    # Specialized query methods for pattern matching

    def find_by_space(
        self, space_id: str, limit: int = 100, min_novelty: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Find traces by space with optional novelty filtering."""
        filters = {"space_id": space_id}
        if min_novelty is not None:
            filters["min_novelty"] = min_novelty

        return self.list(filters=filters, limit=limit)

    def find_codes_in_space(
        self, space_id: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Find all stored SDR codes within a space for CA3 pattern completion.

        Returns only the essential fields needed for pattern matching:
        - id: trace identifier
        - simhash_hex: 512-bit SimHash for Hamming distance calculation
        - minhash32: MinHash values for Jaccard similarity
        - novelty: novelty score for ranking
        """
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            """
            SELECT id, simhash_hex, minhash32, novelty
            FROM hippocampus_traces
            WHERE space_id = ?
            ORDER BY novelty DESC, ts DESC
            LIMIT ?
            """,
            (space_id, limit),
        )

        codes = []
        for row in cursor.fetchall():
            # Parse minhash32 from JSON
            minhash32 = json.loads(row[2]) if row[2] else []

            codes.append(
                {
                    "id": row[0],
                    "simhash_hex": row[1],
                    "minhash32": minhash32,
                    "novelty": row[3],
                }
            )

        logger.info(
            "Found codes in space",
            extra={
                "space_id": space_id,
                "count": len(codes),
                "limit": limit,
            },
        )

        return codes

    def find_similar_by_simhash(
        self,
        space_id: str,
        target_simhash: str,
        max_hamming_distance: int = 64,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Find traces with similar SimHash within Hamming distance threshold.

        Note: This is a simplified implementation. For production, consider
        using specialized similarity search with LSH or approximate methods.
        """
        if not self._connection:
            raise RuntimeError("No active connection")

        # For now, fetch all traces in space and compute Hamming distance
        # TODO: Implement LSH indexing for efficient similarity search

        all_traces = self.find_by_space(space_id, limit=1000)
        similar_traces = []

        target_bits = int(target_simhash, 16)

        for trace in all_traces:
            trace_bits = int(trace["simhash_hex"], 16)
            hamming_dist = bin(target_bits ^ trace_bits).count("1")

            if hamming_dist <= max_hamming_distance:
                trace["hamming_distance"] = hamming_dist
                similar_traces.append(trace)

        # Sort by similarity (lower Hamming distance = more similar)
        similar_traces.sort(key=lambda x: x["hamming_distance"])
        return similar_traces[:limit]

    def get_recent_traces(
        self, space_id: str, hours: int = 24, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent traces within specified time window."""
        from datetime import datetime, timedelta

        since_ts = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        return self.list(
            filters={"space_id": space_id, "since_ts": since_ts}, limit=limit
        )

    def get_novelty_distribution(self, space_id: str) -> Dict[str, Any]:
        """Get novelty score distribution for analytics."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            """
            SELECT
                COUNT(*) as total_traces,
                AVG(novelty) as avg_novelty,
                MIN(novelty) as min_novelty,
                MAX(novelty) as max_novelty,
                COUNT(CASE WHEN novelty >= 0.8 THEN 1 END) as high_novelty_count,
                COUNT(CASE WHEN novelty <= 0.2 THEN 1 END) as low_novelty_count
            FROM hippocampus_traces
            WHERE space_id = ?
        """,
            (space_id,),
        )

        row = cursor.fetchone()
        return {
            "total_traces": row[0],
            "avg_novelty": row[1],
            "min_novelty": row[2],
            "max_novelty": row[3],
            "high_novelty_count": row[4],  # >= 0.8
            "low_novelty_count": row[5],  # <= 0.2
        }

    # ============================================================================
    # SEQUENCE INTEGRATION (Sub-issue 4.1.1.2)
    # ============================================================================

    def create_temporal_sequence(
        self, space_id: str, trace_ids: List[str], label: Optional[str] = None
    ) -> str:
        """
        Create a temporal sequence from hippocampus traces.

        Integrates with episodic sequence store to create temporal relationships
        between hippocampus traces for consolidation and retrieval.

        Args:
            space_id: Space scope for the sequence
            trace_ids: List of hippocampus trace IDs to sequence
            label: Optional label for the sequence

        Returns:
            sequence_id: ULID of created sequence
        """
        import random
        import time

        from storage.stores.memory.episodic_store import EpisodicSequence, EpisodicStore

        # Generate a ULID-like identifier (timestamp + randomness)
        def generate_ulid() -> str:
            """Generate a ULID-like identifier for sequence IDs."""
            # Use current timestamp in base32
            ts = int(time.time() * 1000)  # milliseconds
            # Convert to base32-like encoding
            chars = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
            ts_part = ""
            for _ in range(10):
                ts_part = chars[ts % len(chars)] + ts_part
                ts //= len(chars)

            # Add 16 random characters
            random_part = "".join(random.choices(chars, k=16))
            return ts_part + random_part

        # Validate all traces exist and are in the same space
        if not self._connection:
            raise RuntimeError("No active connection")

        trace_items: List[Dict[str, Any]] = []
        for trace_id in trace_ids:
            cursor = self._connection.execute(
                "SELECT id, ts FROM hippocampus_traces WHERE id = ? AND space_id = ?",
                (trace_id, space_id),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Trace {trace_id} not found in space {space_id}")

            trace_items.append(
                {
                    "id": row[0],
                    "ts": datetime.fromisoformat(row[1]),
                    "weight": 1.0,  # Default weight for hippocampus traces
                }
            )

        # Sort by timestamp for temporal ordering
        trace_items.sort(key=lambda x: x["ts"])

        # Create sequence using episodic store
        episodic_store = EpisodicStore(self.config)

        sequence = EpisodicSequence(
            sequence_id=generate_ulid(),
            space_id=space_id,
            ts=datetime.now(timezone.utc),
            items=trace_items,
            label=label or f"hippocampus_sequence_{len(trace_items)}_traces",
            closed=False,
        )

        return episodic_store.create_sequence(sequence)

    def get_temporal_sequences(self, space_id: str) -> List[Dict[str, Any]]:
        """
        Get all temporal sequences containing hippocampus traces in a space.

        Args:
            space_id: Space to query sequences for

        Returns:
            List of sequence metadata with hippocampus trace counts
        """
        from storage.stores.memory.episodic_store import EpisodicStore

        episodic_store = EpisodicStore(self.config)
        sequences = episodic_store.list_sequences(space_id=space_id)

        # Filter to sequences that contain hippocampus traces
        hippocampus_sequences: List[Dict[str, Any]] = []
        for seq in sequences:
            if not self._connection:
                continue

            # Check if sequence contains any hippocampus traces
            hippocampus_count = 0
            for item in seq.items:
                cursor = self._connection.execute(
                    "SELECT COUNT(*) FROM hippocampus_traces WHERE id = ?",
                    (item["id"],),
                )
                row = cursor.fetchone()
                if row and row[0] > 0:
                    hippocampus_count += 1

            if hippocampus_count > 0:
                seq_dict = seq.to_dict()
                seq_dict["hippocampus_trace_count"] = hippocampus_count
                hippocampus_sequences.append(seq_dict)

        return hippocampus_sequences

    def get_traces_in_sequence(self, sequence_id: str) -> List[Dict[str, Any]]:
        """
        Get hippocampus traces that are part of a temporal sequence.

        Args:
            sequence_id: ULID of the sequence

        Returns:
            List of hippocampus traces in sequence order
        """
        from storage.stores.memory.episodic_store import EpisodicStore

        episodic_store = EpisodicStore(self.config)
        sequence = episodic_store.get_sequence(sequence_id)
        if not sequence:
            return []

        # Get hippocampus traces for each sequence item
        traces: List[Dict[str, Any]] = []
        if self._connection:
            for item in sequence.items:
                cursor = self._connection.execute(
                    "SELECT * FROM hippocampus_traces WHERE id = ?", (item["id"],)
                )
                row = cursor.fetchone()
                if row:
                    trace_dict = {
                        "id": row[0],
                        "space_id": row[1],
                        "ts": row[2],
                        "simhash_hex": row[3],
                        "minhash32": json.loads(row[4]),
                        "novelty": row[5],
                        "meta": json.loads(row[6]) if row[6] else {},
                    }
                    trace_dict["sequence_weight"] = item.get("weight", 1.0)
                    traces.append(trace_dict)

        return traces

    def find_traces_by_temporal_pattern(
        self,
        space_id: str,
        time_window_hours: int = 24,
        min_novelty: float = 0.5,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Find hippocampus traces that follow temporal patterns suitable for sequencing.

        Identifies traces with temporal proximity and moderate-to-high novelty
        that are good candidates for sequence creation.

        Args:
            space_id: Space to search in
            time_window_hours: Time window for pattern detection
            min_novelty: Minimum novelty threshold
            limit: Maximum number of traces to return

        Returns:
            List of traces grouped by temporal patterns
        """
        if not self._connection:
            return []

        from datetime import timedelta

        # Find traces in time window with sufficient novelty
        since_ts = (
            datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        ).isoformat()

        cursor = self._connection.execute(
            """
            SELECT id, space_id, ts, simhash_hex, minhash32, novelty, meta
            FROM hippocampus_traces
            WHERE space_id = ?
            AND ts > ?
            AND novelty >= ?
            ORDER BY ts DESC
            LIMIT ?
        """,
            (space_id, since_ts, min_novelty, limit),
        )

        traces = []
        for row in cursor:
            trace_dict = {
                "id": row[0],
                "space_id": row[1],
                "ts": row[2],
                "simhash_hex": row[3],
                "minhash32": json.loads(row[4]),
                "novelty": row[5],
                "meta": json.loads(row[6]) if row[6] else {},
            }
            traces.append(trace_dict)

        return traces

    def get_temporal_index_entry(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get temporal index entry for a hippocampus trace.

        Creates time index entry compatible with temporal indexing system
        for integration with retrieval and consolidation pipelines.

        Args:
            trace_id: ULID of the trace

        Returns:
            Temporal index entry dict or None if trace not found
        """
        if not self._connection:
            return None

        cursor = self._connection.execute(
            "SELECT id, space_id, ts, simhash_hex, novelty FROM hippocampus_traces WHERE id = ?",
            (trace_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        ts = datetime.fromisoformat(row[2])

        # Create temporal index entries for different granularities
        temporal_entries = []

        # Minute granularity
        minute_bucket = ts.replace(second=0, microsecond=0).isoformat()
        temporal_entries.append(
            {
                "space_id": row[1],
                "g": "minute",
                "time_bucket": minute_bucket,
                "doc_id": row[0],
                "ts": row[2],
                "hash": row[3][:16],  # Use first 16 chars of simhash as content hash
                "attributes": {"type": "hippocampus_trace", "novelty": row[4]},
            }
        )

        # Hour granularity
        hour_bucket = ts.replace(minute=0, second=0, microsecond=0).isoformat()
        temporal_entries.append(
            {
                "space_id": row[1],
                "g": "hour",
                "time_bucket": hour_bucket,
                "doc_id": row[0],
                "ts": row[2],
                "hash": row[3][:16],
                "attributes": {"type": "hippocampus_trace", "novelty": row[4]},
            }
        )

        return {"trace_id": row[0], "temporal_entries": temporal_entries}

    # ============================================================================
    # POLICY ENFORCEMENT (Sub-issue 4.1.1.3)
    # ============================================================================

    def _enforce_read_policy(
        self, space_id: str, actor_id: str, trace_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enforce read policy for hippocampus traces with RBAC/ABAC controls.

        Args:
            space_id: Space scope for policy evaluation
            actor_id: Actor requesting access
            trace_data: Raw trace data from database

        Returns:
            Policy-compliant trace data with redactions applied
        """
        try:
            from policy import PolicyDecisionEngine, PolicyRequest

            # Use the default policy engine (creates temp storage)
            engine = PolicyDecisionEngine.create_default()

            # Create policy request
            policy_request = PolicyRequest(
                actor_id=actor_id,
                operation="hippocampus.read",
                resource=trace_data.get("id", "unknown"),
                space_id=space_id,
                band="GREEN",  # Default band for hippocampus traces
                tags=["hippocampus", "memory"],
            )

            # Get policy decision
            decision = engine.evaluate_access(policy_request)

            if decision.decision == "DENY":
                raise PermissionError(
                    f"Access denied to hippocampus trace: {decision.reasons}"
                )

            # Apply redactions if required
            if decision.decision == "ALLOW_REDACTED" or decision.obligations.redact:
                trace_data = self._apply_redactions(
                    trace_data, decision.obligations.redact
                )

            return trace_data

        except ImportError:
            # Policy layer not available, allow access (dev mode)
            logger.warning("Policy layer not available, allowing unrestricted access")
            return trace_data
        except Exception as e:
            logger.error(f"Policy enforcement error: {e}")
            # In production, deny on policy failure; in dev, log and allow
            return trace_data

    def _enforce_write_policy(
        self, space_id: str, actor_id: str, trace_data: Dict[str, Any]
    ) -> bool:
        """
        Enforce write policy for hippocampus traces.

        Args:
            space_id: Space scope for policy evaluation
            actor_id: Actor requesting write access
            trace_data: Trace data to be written

        Returns:
            True if write is allowed, False otherwise
        """
        try:
            from policy import PolicyDecisionEngine, PolicyRequest

            # Use the default policy engine
            engine = PolicyDecisionEngine.create_default()

            # Create policy request for write
            policy_request = PolicyRequest(
                actor_id=actor_id,
                operation="hippocampus.write",
                resource=trace_data.get("id", "unknown"),
                space_id=space_id,
                band="GREEN",
                tags=["hippocampus", "memory"],
            )

            # Get policy decision
            decision = engine.evaluate_access(policy_request)

            return decision.decision in ["ALLOW", "ALLOW_REDACTED"]

        except ImportError:
            # Policy layer not available, allow access (dev mode)
            logger.warning(
                "Policy layer not available, allowing unrestricted write access"
            )
            return True
        except Exception as e:
            logger.error(f"Write policy enforcement error: {e}")
            return False

    def _apply_redactions(
        self, trace_data: Dict[str, Any], redact_categories: List[str]
    ) -> Dict[str, Any]:
        """
        Apply redactions to hippocampus trace data based on policy requirements.

        Args:
            trace_data: Original trace data
            redact_categories: List of categories to redact

        Returns:
            Redacted trace data
        """
        try:
            from policy import Redactor

            redactor = Redactor(categories=redact_categories)
            redacted_data = trace_data.copy()

            # Redact metadata if present
            if "meta" in redacted_data and redacted_data["meta"]:
                meta_str = json.dumps(redacted_data["meta"])
                redacted_meta = redactor.redact_text(meta_str)
                redacted_data["meta"] = {"redacted": True, "text": redacted_meta.text}

            # Redact SimHash if sensitive pattern detection is requested
            if "pattern.similarity" in redact_categories:
                redacted_data["simhash_hex"] = "0" * 128  # Zero out SimHash
                redacted_data["minhash32"] = [0] * 32  # Zero out MinHash

            # Mark as redacted
            redacted_data["_redacted"] = True
            redacted_data["_redaction_categories"] = redact_categories

            return redacted_data

        except ImportError:
            logger.warning("Policy redactor not available")
            return trace_data
        except Exception as e:
            logger.error(f"Redaction error: {e}")
            return trace_data

    def read_with_policy(
        self, trace_id: str, actor_id: str, space_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Read a hippocampus trace with policy enforcement.

        Args:
            trace_id: ULID of the trace to read
            actor_id: Actor requesting access
            space_id: Optional space scope (if known)

        Returns:
            Policy-compliant trace data or None if access denied
        """
        # First get the raw trace
        raw_trace = self._read_record(trace_id)
        if not raw_trace:
            return None

        # Use provided space_id or extract from trace
        effective_space_id = space_id or raw_trace.get("space_id", "unknown")

        # Enforce read policy
        return self._enforce_read_policy(effective_space_id, actor_id, raw_trace)

    def create_with_policy(self, data: Dict[str, Any], actor_id: str) -> Dict[str, Any]:
        """
        Create a hippocampus trace with policy enforcement.

        Args:
            data: Trace data to create
            actor_id: Actor requesting write access

        Returns:
            Created trace data

        Raises:
            PermissionError: If write access is denied
        """
        space_id = data.get("space_id", "unknown")

        # Enforce write policy
        if not self._enforce_write_policy(space_id, actor_id, data):
            raise PermissionError(
                f"Write access denied for actor {actor_id} in space {space_id}"
            )

        # Create the trace
        return self.create(data)

    def list_with_policy(
        self,
        actor_id: str,
        space_id: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List hippocampus traces with policy enforcement.

        Args:
            actor_id: Actor requesting access
            space_id: Space to list traces from
            filters: Optional filters for the query
            limit: Maximum number of traces to return

        Returns:
            List of policy-compliant traces
        """
        # Get raw traces
        raw_traces = self.list(
            filters={"space_id": space_id, **(filters or {})}, limit=limit
        )

        # Apply policy to each trace
        policy_compliant_traces = []
        for trace in raw_traces:
            try:
                compliant_trace = self._enforce_read_policy(space_id, actor_id, trace)
                policy_compliant_traces.append(compliant_trace)
            except PermissionError:
                # Skip traces that are denied
                continue

        return policy_compliant_traces

    def find_similar_with_policy(
        self,
        simhash_hex: str,
        actor_id: str,
        space_id: str,
        max_hamming_distance: int = 10,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Find similar traces with policy enforcement.

        Args:
            simhash_hex: SimHash to find similar traces for
            actor_id: Actor requesting access
            space_id: Space to search in
            max_hamming_distance: Maximum Hamming distance for similarity
            limit: Maximum number of similar traces to return

        Returns:
            List of policy-compliant similar traces
        """
        # Get raw similar traces
        raw_traces = self.find_similar_by_simhash(
            simhash_hex, space_id, max_hamming_distance, limit
        )

        # Apply policy to each trace
        policy_compliant_traces = []
        for trace in raw_traces:
            try:
                compliant_trace = self._enforce_read_policy(space_id, actor_id, trace)
                policy_compliant_traces.append(compliant_trace)
            except PermissionError:
                # Skip traces that are denied
                continue

        return policy_compliant_traces
        return policy_compliant_traces

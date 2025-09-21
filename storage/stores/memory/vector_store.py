"""
Vector Store Implementation for MemoryOS

This module provides high-performance vector storage for embeddings and similarity search.
Supports various data types (f32, f16, q8, bfloat16) with model-specific organization
and efficient nearest neighbor search capabilities.

Contract: vector_row.schema.json
"""

from __future__ import annotations

import logging
import sqlite3
import struct
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


# Type definitions from vector_row.schema.json contract
VectorDType = Literal["f32", "f16", "q8", "bfloat16"]


@dataclass
class VectorRow:
    """
    Vector Row data structure following vector_row.schema.json contract.

    Required fields:
    - vec_id: ULID identifier for the vector
    - doc_id: ULID identifier for the source document
    - space_id: Space identifier (e.g., personal:alice, shared:household)
    - model_id: Embedding model identifier (e.g., text-embedding-ada-002)
    - dim: Vector dimensions (integer, 1-32768)
    - vector: Array of numbers representing the embedding

    Optional fields:
    - dtype: Data type (f32, f16, q8, bfloat16) - defaults to f32
    - norm: Vector norm for normalized operations
    - index_name: Name of the index this vector belongs to
    - timestamp: ISO 8601 timestamp
    """

    vec_id: str
    doc_id: str
    space_id: str
    model_id: str
    dim: int
    vector: List[float]
    dtype: Optional[VectorDType] = None
    norm: Optional[float] = None
    index_name: Optional[str] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "vec_id": self.vec_id,
            "doc_id": self.doc_id,
            "space_id": self.space_id,
            "model_id": self.model_id,
            "dim": self.dim,
            "vector": self.vector,
            "dtype": self.dtype,
        }
        if self.norm is not None:
            result["norm"] = self.norm
        if self.index_name is not None:
            result["index_name"] = self.index_name
        if self.timestamp is not None:
            result["timestamp"] = self.timestamp
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorRow":
        """Create VectorRow from dictionary."""
        return cls(
            vec_id=data["vec_id"],
            doc_id=data["doc_id"],
            space_id=data["space_id"],
            model_id=data["model_id"],
            dim=data["dim"],
            vector=data["vector"],
            dtype=data.get("dtype"),  # Default to None, consistent with dataclass
            norm=data.get("norm"),
            index_name=data.get("index_name"),
            timestamp=data.get("timestamp"),
        )

    def calculate_norm(self) -> float:
        """Calculate and cache the L2 norm of the vector."""
        if self.norm is None:
            self.norm = sum(x * x for x in self.vector) ** 0.5
        return self.norm or 0.0


class VectorStore(BaseStore):
    """
    Vector store implementation following BaseStore pattern.

    Provides CRUD operations for vector embeddings with:
    - Model-specific organization
    - Multiple data type support (f32, f16, q8, bfloat16)
    - Efficient similarity search
    - Space-scoped access control
    - Index management capabilities
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config or StoreConfig(db_path="data/vector.db"))

    # BaseStore abstract method implementations

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for vector rows (contract-compliant)."""
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://familyos.local/contracts/storage/vector_row.schema.json",
            "title": "Vector Row",
            "type": "object",
            "additionalProperties": False,
            "required": ["vec_id", "doc_id", "space_id", "model_id", "dim", "vector"],
            "properties": {
                "vec_id": {
                    "type": "string",
                    "pattern": "^[0-7][0-9A-HJKMNP-TV-Z]{25}$",
                },
                "doc_id": {
                    "type": "string",
                    "pattern": "^[0-7][0-9A-HJKMNP-TV-Z]{25}$",
                },
                "space_id": {
                    "type": "string",
                    "pattern": "^(personal|selective|shared|extended|interfamily):[A-Za-z0-9_\\-\\.]+$",
                },
                "model_id": {"type": "string", "pattern": "^[A-Za-z0-9._:-]{2,64}$"},
                "dim": {"type": "integer", "minimum": 1, "maximum": 32768},
                "dtype": {
                    "type": "string",
                    "enum": ["f32", "f16", "q8", "bfloat16"],
                    "default": "f32",
                },
                "vector": {"type": "array", "items": {"type": "number"}, "minItems": 8},
                "norm": {"type": "number"},
                "index_name": {"type": "string", "pattern": "^[A-Za-z0-9._:-]{2,64}$"},
                "timestamp": {"type": "string", "format": "date-time"},
            },
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize the database schema."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS vector_rows (
            vec_id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            space_id TEXT NOT NULL,
            model_id TEXT NOT NULL,
            dim INTEGER NOT NULL,
            vector_data BLOB NOT NULL,
            dtype TEXT NOT NULL DEFAULT 'f32',
            norm REAL,
            index_name TEXT,
            timestamp INTEGER,
            timestamp_iso TEXT,
            created_at INTEGER NOT NULL DEFAULT (unixepoch()),
            updated_at INTEGER NOT NULL DEFAULT (unixepoch())
        );

        -- Indexes for efficient queries
        CREATE INDEX IF NOT EXISTS idx_vector_doc_id ON vector_rows(doc_id);
        CREATE INDEX IF NOT EXISTS idx_vector_space_id ON vector_rows(space_id);
        CREATE INDEX IF NOT EXISTS idx_vector_model_id ON vector_rows(model_id);
        CREATE INDEX IF NOT EXISTS idx_vector_space_model ON vector_rows(space_id, model_id);
        CREATE INDEX IF NOT EXISTS idx_vector_index_name ON vector_rows(index_name);
        CREATE INDEX IF NOT EXISTS idx_vector_timestamp ON vector_rows(timestamp);

        -- Update trigger for updated_at
        CREATE TRIGGER IF NOT EXISTS vector_rows_updated_at
        AFTER UPDATE ON vector_rows
        BEGIN
            UPDATE vector_rows SET updated_at = unixepoch() WHERE vec_id = NEW.vec_id;
        END;
        """
        conn.executescript(schema_sql)

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new vector row record."""
        vector_row = VectorRow.from_dict(data)

        # Serialize the vector - use 'f32' if dtype is None
        dtype_to_use = vector_row.dtype if vector_row.dtype is not None else "f32"
        vector_data = self._serialize_vector(vector_row.vector, dtype_to_use)

        # Handle timestamp conversion
        ts_unix = None
        ts_iso = None
        if vector_row.timestamp:
            if isinstance(vector_row.timestamp, str):
                # Parse ISO format
                from datetime import datetime

                dt = datetime.fromisoformat(vector_row.timestamp.replace("Z", "+00:00"))
                ts_unix = int(dt.timestamp())
                ts_iso = vector_row.timestamp
            else:
                # Assume Unix timestamp
                ts_unix = int(vector_row.timestamp)
                from datetime import datetime, timezone

                dt = datetime.fromtimestamp(ts_unix, tz=timezone.utc)
                ts_iso = dt.isoformat()

        with sqlite3.connect(self.config.db_path) as conn:
            conn.execute(
                """
                INSERT INTO vector_rows
                (vec_id, doc_id, space_id, model_id, dim, vector_data, dtype, norm, index_name, timestamp, timestamp_iso)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vector_row.vec_id,
                    vector_row.doc_id,
                    vector_row.space_id,
                    vector_row.model_id,
                    vector_row.dim,
                    vector_data,
                    dtype_to_use,  # Always use a valid dtype value
                    vector_row.norm,
                    vector_row.index_name,
                    ts_unix,
                    ts_iso,
                ),
            )

        # Return the created data
        return vector_row.to_dict()

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a vector row by ID and return as dictionary."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT vec_id, doc_id, space_id, model_id, dim, vector_data, dtype, norm, index_name, timestamp_iso
                FROM vector_rows
                WHERE vec_id = ?
                """,
                (record_id,),
            )
            row = cursor.fetchone()
            if row:
                vector_row = self._row_to_vector_row(row)
                return vector_row.to_dict()
        return None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing vector row from dictionary data."""
        vector_row = VectorRow.from_dict(data)

        # Validate dimensions
        if len(vector_row.vector) != vector_row.dim:
            raise ValueError(
                f"Vector length {len(vector_row.vector)} does not match dim {vector_row.dim}"
            )

        # Serialize vector for storage - use 'f32' if dtype is None
        dtype_to_use = vector_row.dtype if vector_row.dtype is not None else "f32"
        vector_data = self._serialize_vector(vector_row.vector, dtype_to_use)

        # Handle timestamp
        ts_unix = None
        ts_iso = vector_row.timestamp
        if ts_iso:
            ts_unix = int(
                datetime.fromisoformat(ts_iso.replace("Z", "+00:00")).timestamp()
            )

        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE vector_rows
                SET doc_id = ?, space_id = ?, model_id = ?, dim = ?, vector_data = ?,
                    dtype = ?, norm = ?, index_name = ?, timestamp = ?, timestamp_iso = ?
                WHERE vec_id = ?
                """,
                (
                    vector_row.doc_id,
                    vector_row.space_id,
                    vector_row.model_id,
                    vector_row.dim,
                    vector_data,
                    dtype_to_use,  # Always use a valid dtype value
                    vector_row.norm,
                    vector_row.index_name,
                    ts_unix,
                    ts_iso,
                    record_id,
                ),
            )
            conn.commit()
            updated = cursor.rowcount > 0

        if updated:
            logger.info(f"Updated vector row {record_id}")
            return vector_row.to_dict()
        else:
            logger.warning(f"Vector row {record_id} not found for update")
            raise ValueError(f"Vector row {record_id} not found for update")

    def _delete_record(self, record_id: str) -> bool:
        """Delete a vector row by ID."""
        with sqlite3.connect(self.config.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM vector_rows WHERE vec_id = ?", (record_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(f"Deleted vector row {record_id}")
        else:
            logger.warning(f"Vector row {record_id} not found for deletion")

        return deleted

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List vector rows with optional filtering, returning dictionaries."""
        query = "SELECT vec_id, doc_id, space_id, model_id, dim, vector_data, dtype, norm, index_name, timestamp_iso FROM vector_rows"
        params: List[str] = []

        # Handle filters
        if filters:
            where_clauses: List[str] = []
            if "space_id" in filters:
                where_clauses.append("space_id = ?")
                params.append(filters["space_id"])
            if "model_id" in filters:
                where_clauses.append("model_id = ?")
                params.append(filters["model_id"])
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(str(limit))

        if offset:
            query += " OFFSET ?"
            params.append(str(offset))

        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_vector_row(row).to_dict() for row in cursor.fetchall()]

    def _serialize_vector(self, vector: List[float], dtype: VectorDType) -> bytes:
        """Serialize vector to binary format based on dtype."""
        if dtype == "f32":
            return struct.pack(f"{len(vector)}f", *vector)
        elif dtype == "f16":
            # For f16, we'll store as f32 but could be optimized for space
            return struct.pack(f"{len(vector)}f", *vector)
        elif dtype == "q8":
            # For q8 (quantized 8-bit), we'll store as f32 for now
            # In production, implement proper quantization
            return struct.pack(f"{len(vector)}f", *vector)
        elif dtype == "bfloat16":
            # For bfloat16, we'll store as f32 for now
            return struct.pack(f"{len(vector)}f", *vector)
        else:
            raise ValueError(f"Unsupported dtype: {dtype}")

    def _deserialize_vector(
        self, data: bytes, dim: int, dtype: VectorDType
    ) -> List[float]:
        """Deserialize vector from binary format."""
        if dtype in ["f32", "f16", "q8", "bfloat16"]:
            # All stored as f32 for now
            return list(struct.unpack(f"{dim}f", data))
        else:
            raise ValueError(f"Unsupported dtype: {dtype}")

    def _row_to_vector_row(self, row: sqlite3.Row) -> VectorRow:
        """Convert database row to VectorRow."""
        # Deserialize vector data
        vector = self._deserialize_vector(row["vector_data"], row["dim"], row["dtype"])

        return VectorRow(
            vec_id=row["vec_id"],
            doc_id=row["doc_id"],
            space_id=row["space_id"],
            model_id=row["model_id"],
            dim=row["dim"],
            vector=vector,
            dtype=row["dtype"],
            norm=row["norm"],
            index_name=row["index_name"],
            timestamp=row["timestamp_iso"],
        )

    # Specialized vector store methods (working with VectorRow objects)

    def store_vector(self, vector_row: VectorRow) -> str:
        """Store a vector row."""
        result_dict = self._create_record(vector_row.to_dict())
        return result_dict["vec_id"]

    def get_vector(self, vec_id: str) -> Optional[VectorRow]:
        """Get a vector row by ID."""
        result_dict = self._read_record(vec_id)
        if result_dict:
            return VectorRow.from_dict(result_dict)
        return None

    def get_embedding(self, event_id: str) -> Optional[List[float]]:
        """
        Get embedding vector for an event (doc_id in vector storage).

        For hippocampus integration, event_id maps to doc_id in vector storage.
        Returns the first/latest vector for the document if multiple exist.

        Args:
            event_id: Event identifier (maps to doc_id)

        Returns:
            Vector as list of floats, or None if not found
        """
        vectors = self.get_vectors_by_doc_id(event_id)
        if vectors:
            # Return the most recent vector (first in list due to ORDER BY created_at DESC)
            return vectors[0].vector
        return None

    def update_vector(self, vec_id: str, vector_row: VectorRow) -> bool:
        """Update a vector row."""
        try:
            self._update_record(vec_id, vector_row.to_dict())
            return True
        except ValueError:
            return False

    def delete_vector(self, vec_id: str) -> bool:
        """Delete a vector row."""
        return self._delete_record(vec_id)

    def list_vectors(
        self,
        space_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[VectorRow]:
        """List vector rows."""
        filters = {"space_id": space_id} if space_id else None
        result_dicts = self._list_records(filters, limit, offset)
        return [VectorRow.from_dict(d) for d in result_dicts]

    def get_vectors_by_doc_id(self, doc_id: str) -> List[VectorRow]:
        """Get all vectors for a document."""
        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT vec_id, doc_id, space_id, model_id, dim, vector_data, dtype, norm, index_name, timestamp_iso
                FROM vector_rows
                WHERE doc_id = ?
                ORDER BY created_at DESC
                """,
                (doc_id,),
            )
            return [self._row_to_vector_row(row) for row in cursor.fetchall()]

    def get_vectors_by_model(
        self,
        model_id: str,
        space_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[VectorRow]:
        """Get vectors by model ID."""
        query = """
        SELECT vec_id, doc_id, space_id, model_id, dim, vector_data, dtype, norm, index_name, timestamp_iso
        FROM vector_rows
        WHERE model_id = ?
        """
        params: List[str] = [model_id]

        if space_id:
            query += " AND space_id = ?"
            params.append(space_id)

        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(str(limit))

        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_vector_row(row) for row in cursor.fetchall()]

    def cosine_similarity(self, vector_a: List[float], vector_b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vector_a) != len(vector_b):
            raise ValueError("Vectors must have the same dimensions")

        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
        norm1 = sum(a * a for a in vector_a) ** 0.5
        norm2 = sum(b * b for b in vector_b) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def similarity_search(
        self,
        query_vector: List[float],
        model_id: str,
        space_id: Optional[str] = None,
        limit: int = 10,
        min_similarity: float = 0.0,
    ) -> List[Tuple[VectorRow, float]]:
        """
        Find similar vectors using cosine similarity.

        Returns list of (VectorRow, similarity_score) tuples ordered by similarity.
        """
        vectors = self.get_vectors_by_model(model_id, space_id)

        results: List[Tuple[VectorRow, float]] = []
        for vector_row in vectors:
            if len(vector_row.vector) != len(query_vector):
                continue

            similarity = self.cosine_similarity(query_vector, vector_row.vector)
            if similarity >= min_similarity:
                results.append((vector_row, similarity))

        # Sort by similarity (highest first) and apply limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_index_vectors(
        self, index_name: str, space_id: Optional[str] = None
    ) -> List[VectorRow]:
        """Get all vectors belonging to a specific index."""
        query = """
        SELECT vec_id, doc_id, space_id, model_id, dim, vector_data, dtype, norm, index_name, timestamp_iso
        FROM vector_rows
        WHERE index_name = ?
        """
        params: List[str] = [index_name]

        if space_id:
            query += " AND space_id = ?"
            params.append(space_id)

        query += " ORDER BY created_at DESC"

        with sqlite3.connect(self.config.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [self._row_to_vector_row(row) for row in cursor.fetchall()]
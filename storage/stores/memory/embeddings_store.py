"""Embeddings Store Implementation

Provides vector embeddings storage and similarity search with:
- Multiple embedding model support
- Vector similarity search with configurable distance metrics
- Quantization support for memory efficiency
- Performance optimization and caching
- Integration with UnitOfWork and MLS security

Contr        try:
            if not self._connection:
                self._connection = self._get_connection()

            # Validate dimensionscontracts/storage/schemas/embedding_record.schema.json
"""

import hashlib
import json
import logging
import sqlite3
import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import numpy as np

from storage.core.base_store import BaseStore, StoreConfig
from storage.core.sqlite_util import create_optimized_connection

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingRecord:
    """Embedding record structure matching contract schema."""

    embedding_id: str  # ULID format
    doc_id: str  # ULID of source document
    model_id: str  # Embedding model identifier
    dim: int  # Vector dimensions
    sha256: str  # Hash of the vector data
    vector_ref: str  # ULID reference to vector storage
    quantized: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class VectorRow:
    """Vector storage row with the actual embedding data."""

    id: str  # ULID (vector_ref)
    space_id: str
    doc_id: str
    model_id: str
    dim: int
    vector: List[float]
    norm: Optional[float] = None
    privacy_band: str = "GREEN"
    ts: Optional[datetime] = None


@dataclass
class SimilarityQuery:
    """Vector similarity search query parameters."""

    vector: List[float]
    model_id: str
    limit: int = 20
    offset: int = 0
    threshold: float = 0.0  # Minimum similarity score
    space_ids: Optional[List[str]] = None
    bands: Optional[List[str]] = None
    distance_metric: str = "cosine"  # cosine, euclidean, dot_product


@dataclass
class SimilarityResult:
    """Vector similarity search result."""

    embedding_id: str
    doc_id: str
    score: float  # Similarity score (0-1 for cosine, distance for others)
    vector: Optional[List[float]] = None
    metadata: Optional[Dict[str, str]] = field(default_factory=lambda: {})


class EmbeddingsStore(BaseStore):
    """Embeddings store with vector similarity search."""

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._connection: Optional[sqlite3.Connection] = None
        self._initialized = False
        self._model_cache: Dict[str, Dict[str, str]] = {}
        self._stats_cache: Optional[Dict[str, str]] = None

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for embedding records."""
        return {
            "type": "object",
            "required": [
                "embedding_id",
                "doc_id",
                "model_id",
                "dim",
                "sha256",
                "vector_ref",
            ],
            "properties": {
                "embedding_id": {
                    "type": "string",
                    "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$",
                },
                "doc_id": {"type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$"},
                "model_id": {"type": "string", "pattern": "^[A-Za-z0-9._:-]{2,64}$"},
                "dim": {"type": "integer", "minimum": 1, "maximum": 32768},
                "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                "vector_ref": {"type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$"},
                "quantized": {"type": "boolean"},
                "metadata": {
                    "anyOf": [
                        {"type": "object", "additionalProperties": True},
                        {"type": "null"},
                    ]
                },
            },
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize embeddings schema and tables."""
        # Embedding records table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embedding_records (
                embedding_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                dim INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                vector_ref TEXT NOT NULL,
                quantized BOOLEAN DEFAULT FALSE,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(doc_id, model_id)
            )
        """
        )

        # Vector storage table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vector_rows (
                id TEXT PRIMARY KEY,
                space_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                dim INTEGER NOT NULL,
                vector BLOB NOT NULL,
                norm REAL,
                privacy_band TEXT DEFAULT 'GREEN',
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Model metadata table for tracking models
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embedding_models (
                model_id TEXT PRIMARY KEY,
                dim INTEGER NOT NULL,
                distance_metric TEXT DEFAULT 'cosine',
                quantization_type TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Indexes for efficient searches
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_embedding_records_doc_model
            ON embedding_records(doc_id, model_id)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_vector_rows_space_model
            ON vector_rows(space_id, model_id)
        """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_vector_rows_model_band
            ON vector_rows(model_id, privacy_band)
        """
        )

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new embedding record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        embedding_id = data["embedding_id"]

        # Insert embedding record
        self._connection.execute(
            """
            INSERT INTO embedding_records (embedding_id, doc_id, model_id, dim, sha256, vector_ref, quantized, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                embedding_id,
                data["doc_id"],
                data["model_id"],
                data["dim"],
                data["sha256"],
                data["vector_ref"],
                data.get("quantized", False),
                json.dumps(data.get("metadata")) if data.get("metadata") else None,
            ),
        )

        return data

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read an embedding record by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            """
            SELECT embedding_id, doc_id, model_id, dim, sha256, vector_ref, quantized, metadata
            FROM embedding_records
            WHERE embedding_id = ?
        """,
            (record_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "embedding_id": row[0],
            "doc_id": row[1],
            "model_id": row[2],
            "dim": row[3],
            "sha256": row[4],
            "vector_ref": row[5],
            "quantized": bool(row[6]),
            "metadata": json.loads(row[7]) if row[7] else None,
        }

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing embedding record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Build update query
        set_clauses: List[str] = []
        params: List[Any] = []

        for fieldname in [
            "doc_id",
            "model_id",
            "dim",
            "sha256",
            "vector_ref",
            "quantized",
        ]:
            if fieldname in data:
                set_clauses.append(f"{fieldname} = ?")
                params.append(data[fieldname])

        if "metadata" in data:
            set_clauses.append("metadata = ?")
            params.append(json.dumps(data["metadata"]) if data["metadata"] else None)

        if set_clauses:
            params.append(record_id)
            self._connection.execute(
                f"""
                UPDATE embedding_records
                SET {', '.join(set_clauses)}
                WHERE embedding_id = ?
            """,
                params,
            )

        # Return updated record
        return self._read_record(record_id) or data

    def _delete_record(self, record_id: str) -> bool:
        """Delete an embedding record by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Get vector_ref before deletion
        cursor = self._connection.execute(
            """
            SELECT vector_ref FROM embedding_records WHERE embedding_id = ?
        """,
            (record_id,),
        )

        row = cursor.fetchone()
        if not row:
            return False

        vector_ref = row[0]

        # Delete embedding record
        cursor = self._connection.execute(
            """
            DELETE FROM embedding_records WHERE embedding_id = ?
        """,
            (record_id,),
        )

        if cursor.rowcount == 0:
            return False

        # Delete associated vector
        self._connection.execute(
            """
            DELETE FROM vector_rows WHERE id = ?
        """,
            (vector_ref,),
        )

        return True

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List embedding records with optional filtering and pagination."""
        if not self._connection:
            raise RuntimeError("No active connection")

        conditions: List[str] = []
        params: List[Any] = []

        if filters:
            for fieldname, value in filters.items():
                if fieldname in ["doc_id", "model_id", "quantized"]:
                    conditions.append(f"e.{fieldname} = ?")
                    params.append(value)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        limit_clause = f" LIMIT {limit}" if limit else ""
        offset_clause = f" OFFSET {offset}" if offset else ""

        cursor = self._connection.execute(
            f"""
            SELECT e.embedding_id, e.doc_id, e.model_id, e.dim, e.sha256, e.vector_ref, e.quantized, e.metadata
            FROM embedding_records e
            {where_clause}
            ORDER BY e.created_at DESC
            {limit_clause}{offset_clause}
        """,
            params,
        )

        results: List[Dict[str, Any]] = []
        for row in cursor.fetchall():
            results.append(
                {
                    "embedding_id": row[0],
                    "doc_id": row[1],
                    "model_id": row[2],
                    "dim": row[3],
                    "sha256": row[4],
                    "vector_ref": row[5],
                    "quantized": bool(row[6]),
                    "metadata": json.loads(row[7]) if row[7] else None,
                }
            )

        return results

    # Public API methods

    def store_embedding(
        self,
        embedding: EmbeddingRecord,
        vector: List[float],
        space_id: str,
        privacy_band: str = "GREEN",
    ) -> bool:
        """Store an embedding with its vector data."""
        try:
            if not self._connection:
                self._connection = self._get_connection()

            # Validate dimensions
            if len(vector) != embedding.dim:
                raise ValueError(
                    f"Vector dimension {len(vector)} doesn't match record dim {embedding.dim}"
                )

            # Calculate vector hash for verification
            vector_bytes = struct.pack(f"{len(vector)}f", *vector)
            calculated_hash = hashlib.sha256(vector_bytes).hexdigest()

            # Update the embedding hash to match calculated
            embedding.sha256 = calculated_hash

            # Store vector data first
            vector_norm = float(np.linalg.norm(vector)) if vector else None

            self._connection.execute(
                """
                INSERT INTO vector_rows (id, space_id, doc_id, model_id, dim, vector, norm, privacy_band, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    embedding.vector_ref,
                    space_id,
                    embedding.doc_id,
                    embedding.model_id,
                    embedding.dim,
                    vector_bytes,
                    vector_norm,
                    privacy_band,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

            # Store embedding record
            embedding_data: Dict[str, Any] = {
                "embedding_id": embedding.embedding_id,
                "doc_id": embedding.doc_id,
                "model_id": embedding.model_id,
                "dim": embedding.dim,
                "sha256": embedding.sha256,
                "vector_ref": embedding.vector_ref,
                "quantized": embedding.quantized,
                "metadata": embedding.metadata,
            }

            if self.config.schema_validation:
                validation = self.validate_data(embedding_data)
                if not validation.is_valid:
                    raise ValueError(
                        f"Embedding validation failed: {validation.errors}"
                    )

            self.create(embedding_data)

            # Clear caches
            self._stats_cache = None

            return True

        except Exception as e:
            logger.error(f"Failed to store embedding {embedding.embedding_id}: {e}")
            return False

    def get_embedding(
        self,
        embedding_id: str,
        include_vector: bool = False,
        space_filter: Optional[Set[str]] = None,
    ) -> Optional[EmbeddingRecord]:
        """Get an embedding record by ID with optional vector data."""
        try:
            record_data = self.read(embedding_id)
            if not record_data:
                return None

            # Check space filter if vector is requested
            if include_vector or space_filter:
                vector_data = self._get_vector_data(record_data["vector_ref"])
                if not vector_data:
                    return None

                # Apply space filter
                if space_filter and vector_data["space_id"] not in space_filter:
                    return None

            return EmbeddingRecord(
                embedding_id=record_data["embedding_id"],
                doc_id=record_data["doc_id"],
                model_id=record_data["model_id"],
                dim=record_data["dim"],
                sha256=record_data["sha256"],
                vector_ref=record_data["vector_ref"],
                quantized=record_data["quantized"],
                metadata=record_data["metadata"],
            )

        except Exception as e:
            logger.error(f"Failed to get embedding {embedding_id}: {e}")
            return None

    def get_vector_data(self, vector_ref: str) -> Optional[List[float]]:
        """Get vector data by vector reference."""
        try:
            vector_data = self._get_vector_data(vector_ref)
            if not vector_data:
                return None

            # Unpack binary vector data
            vector_bytes = vector_data["vector"]
            dim = vector_data["dim"]
            vector = list(struct.unpack(f"{dim}f", vector_bytes))

            return vector

        except Exception as e:
            logger.error(f"Failed to get vector data {vector_ref}: {e}")
            return None

    def similarity_search(
        self, query: SimilarityQuery, space_filter: Optional[Set[str]] = None
    ) -> List[SimilarityResult]:
        """Perform vector similarity search."""
        try:
            if not self._connection:
                self._connection = self._get_connection()

            # Normalize query vector for cosine similarity
            query_vector = np.array(query.vector)
            if query.distance_metric == "cosine":
                query_norm = np.linalg.norm(query_vector)
                if query_norm > 0:
                    query_vector = query_vector / query_norm

            # Build conditions
            conditions: List[str] = ["v.model_id = ?"]
            params: List[Any] = [query.model_id]

            # Add space filter
            if space_filter:
                space_placeholders = ",".join("?" * len(space_filter))
                conditions.append(f"v.space_id IN ({space_placeholders})")
                params.extend(space_filter)

            # Add band filter
            if query.bands:
                band_placeholders = ",".join("?" * len(query.bands))
                conditions.append(f"v.privacy_band IN ({band_placeholders})")
                params.extend(query.bands)

            where_clause = " AND ".join(conditions)

            # Get candidate vectors
            cursor = self._connection.execute(
                f"""
                SELECT e.embedding_id, e.doc_id, v.vector, v.norm, v.space_id, v.privacy_band
                FROM embedding_records e
                JOIN vector_rows v ON e.vector_ref = v.id
                WHERE {where_clause}
                ORDER BY e.created_at DESC
                LIMIT ?
            """,
                params + [query.limit * 2],
            )  # Get more candidates for better ranking

            results: List[SimilarityResult] = []

            for row in cursor.fetchall():
                try:
                    # Unpack vector
                    vector_bytes = row[2]
                    dim = len(query.vector)
                    candidate_vector = np.array(struct.unpack(f"{dim}f", vector_bytes))

                    # Calculate similarity
                    score = self._calculate_similarity(
                        query_vector, candidate_vector, query.distance_metric, row[3]
                    )

                    # Apply threshold
                    if score >= query.threshold:
                        results.append(
                            SimilarityResult(
                                embedding_id=row[0],
                                doc_id=row[1],
                                score=score,
                                vector=(
                                    candidate_vector.tolist()
                                    if query.distance_metric != "cosine"
                                    else None
                                ),
                                metadata={
                                    "space_id": row[4],
                                    "privacy_band": row[5],
                                    "distance_metric": query.distance_metric,
                                },
                            )
                        )

                except Exception as e:
                    logger.warning(f"Failed to process candidate vector: {e}")
                    continue

            # Sort by score (descending for similarity)
            if query.distance_metric in ["cosine", "dot_product"]:
                results.sort(key=lambda x: x.score, reverse=True)
            else:  # euclidean (distance)
                results.sort(key=lambda x: x.score)

            # Apply pagination
            start_idx = query.offset
            end_idx = query.offset + query.limit
            return results[start_idx:end_idx]

        except Exception as e:
            logger.error(f"Similarity search failed for model {query.model_id}: {e}")
            return []

    def register_model(
        self,
        model_id: str,
        dim: int,
        distance_metric: str = "cosine",
        description: Optional[str] = None,
    ) -> bool:
        """Register a new embedding model."""
        try:
            if not self._connection:
                self._connection = self._get_connection()

            self._connection.execute(
                """
                INSERT OR REPLACE INTO embedding_models (model_id, dim, distance_metric, description)
                VALUES (?, ?, ?, ?)
            """,
                (model_id, dim, distance_metric, description),
            )

            # Update cache
            self._model_cache[model_id] = {
                "dim": str(dim),
                "distance_metric": distance_metric,
                "description": description or "",
            }

            return True

        except Exception as e:
            logger.error(f"Failed to register model {model_id}: {e}")
            return False

    def get_models(self) -> Dict[str, Dict[str, str]]:
        """Get all registered embedding models."""
        try:
            if not self._connection:
                self._connection = self._get_connection()

            cursor = self._connection.execute(
                """
                SELECT model_id, dim, distance_metric, description
                FROM embedding_models
                ORDER BY model_id
            """
            )

            models: Dict[str, Dict[str, str]] = {}
            for row in cursor.fetchall():
                models[row[0]] = {
                    "dim": str(row[1]),
                    "distance_metric": str(row[2]),
                    "description": str(row[3]) if row[3] else "",
                }

            return models

        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return {}

    def get_stats(self) -> Dict[str, str]:
        """Get embeddings store statistics."""
        if self._stats_cache:
            return self._stats_cache

        try:
            if not self._connection:
                self._connection = self._get_connection()

            # Basic counts
            cursor = self._connection.execute(
                """
                SELECT
                    COUNT(*) as total_embeddings,
                    COUNT(DISTINCT model_id) as unique_models,
                    COUNT(DISTINCT doc_id) as unique_documents
                FROM embedding_records
            """
            )
            row = cursor.fetchone()

            # Model distribution
            cursor = self._connection.execute(
                """
                SELECT model_id, COUNT(*)
                FROM embedding_records
                GROUP BY model_id
            """
            )
            model_dist = dict(cursor.fetchall())

            # Quantization distribution
            cursor = self._connection.execute(
                """
                SELECT quantized, COUNT(*)
                FROM embedding_records
                GROUP BY quantized
            """
            )
            quant_dist = dict(cursor.fetchall())

            stats: Dict[str, str] = {
                "total_embeddings": str(row[0]),
                "unique_models": str(row[1]),
                "unique_documents": str(row[2]),
                "model_distribution": str(model_dist),
                "quantization_distribution": str(
                    {str(k): str(v) for k, v in quant_dist.items()}
                ),
                "cache_size": str(len(self._model_cache)),
            }

            self._stats_cache = stats
            return stats

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
        self._model_cache.clear()

    # Private helper methods

    def _get_vector_data(self, vector_ref: str) -> Optional[Dict[str, Any]]:
        """Get vector row data by reference."""
        if not self._connection:
            return None

        cursor = self._connection.execute(
            """
            SELECT space_id, doc_id, model_id, dim, vector, norm, privacy_band, ts
            FROM vector_rows
            WHERE id = ?
        """,
            (vector_ref,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "space_id": row[0],
            "doc_id": row[1],
            "model_id": row[2],
            "dim": row[3],
            "vector": row[4],
            "norm": row[5],
            "privacy_band": row[6],
            "ts": row[7],
        }

    def _calculate_similarity(
        self,
        query_vector: np.ndarray,
        candidate_vector: np.ndarray,
        metric: str,
        candidate_norm: Optional[float] = None,
    ) -> float:
        """Calculate similarity score between vectors."""
        try:
            if metric == "cosine":
                # Use pre-computed norm if available
                if candidate_norm:
                    candidate_vector = candidate_vector / candidate_norm
                else:
                    norm = np.linalg.norm(candidate_vector)
                    if norm > 0:
                        candidate_vector = candidate_vector / norm

                return float(np.dot(query_vector, candidate_vector))

            elif metric == "dot_product":
                return float(np.dot(query_vector, candidate_vector))

            elif metric == "euclidean":
                return float(np.linalg.norm(query_vector - candidate_vector))

            else:
                logger.warning(f"Unknown distance metric: {metric}")
                return 0.0

        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if not self._connection:
            self._connection = create_optimized_connection(self.config.db_path)
            if not self._initialized:
                self._initialize_schema(self._connection)
                self._initialized = True
        return self._connection
        return self._connection

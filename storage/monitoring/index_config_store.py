"""
Index Configuration Store for Index Lifecycle Management.

This module provides configuration management for search indexes, supporting:
- Index configuration CRUD operations
- Lifecycle state management
- Health monitoring integration
- Band-based access control
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from storage.core.base_store import BaseStore

logger = logging.getLogger(__name__)

# Type definitions for index configuration
IndexType = Literal["fts", "embeddings"]
BandLevel = Literal["GREEN", "AMBER", "RED", "BLACK"]
SimilarityMetric = Literal["cosine", "euclidean", "dot_product"]
FTSAnalyzer = Literal["porter", "simple", "email", "unicode61"]


@dataclass
class FTSConfig:
    """FTS-specific configuration."""

    analyzer: FTSAnalyzer = "porter"
    tokenizer: str = "unicode61"
    stemming: bool = True
    languages: List[str] = field(default_factory=lambda: ["en"])


@dataclass
class EmbeddingsConfig:
    """Embeddings-specific configuration."""

    model_id: str
    dimensions: int
    similarity_metric: SimilarityMetric = "cosine"
    quantization: bool = False


@dataclass
class IndexConfig:
    """Represents configuration for a search index."""

    index_name: str  # Must match pattern ^[A-Za-z0-9._:-]{2,64}$
    type: IndexType
    space_id: str  # MemoryOS space scope (e.g., 'shared:household')
    band_min: BandLevel  # Minimum band level for index access
    refresh_interval: int = 60  # Refresh interval in seconds
    max_size_mb: int = 1000  # Maximum index size in MB
    fts_config: Optional[FTSConfig] = None
    embeddings_config: Optional[EmbeddingsConfig] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Validate configuration consistency."""
        if self.type == "fts" and self.fts_config is None:
            raise ValueError("FTS index requires fts_config")
        if self.type == "embeddings" and self.embeddings_config is None:
            raise ValueError("Embeddings index requires embeddings_config")
        if self.type == "fts" and self.embeddings_config is not None:
            raise ValueError("FTS index cannot have embeddings_config")
        if self.type == "embeddings" and self.fts_config is not None:
            raise ValueError("Embeddings index cannot have fts_config")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = {
            "index_name": self.index_name,
            "type": self.type,
            "space_id": self.space_id,
            "band_min": self.band_min,
            "refresh_interval": self.refresh_interval,
            "max_size_mb": self.max_size_mb,
            "metadata": self.metadata,
            "created_ts": self.created_ts.isoformat(),
            "updated_ts": self.updated_ts.isoformat(),
        }

        if self.fts_config:
            data["fts_config"] = {
                "analyzer": self.fts_config.analyzer,
                "tokenizer": self.fts_config.tokenizer,
                "stemming": self.fts_config.stemming,
                "languages": self.fts_config.languages,
            }

        if self.embeddings_config:
            data["embeddings_config"] = {
                "model_id": self.embeddings_config.model_id,
                "dimensions": self.embeddings_config.dimensions,
                "similarity_metric": self.embeddings_config.similarity_metric,
                "quantization": self.embeddings_config.quantization,
            }

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IndexConfig":
        """Create from dictionary."""
        data = data.copy()

        # Parse timestamps
        if "created_ts" in data and isinstance(data["created_ts"], str):
            data["created_ts"] = datetime.fromisoformat(
                data["created_ts"].replace("Z", "+00:00")
            )
        if "updated_ts" in data and isinstance(data["updated_ts"], str):
            data["updated_ts"] = datetime.fromisoformat(
                data["updated_ts"].replace("Z", "+00:00")
            )

        # Parse FTS config
        if "fts_config" in data and data["fts_config"]:
            fts_data = data.pop("fts_config")
            data["fts_config"] = FTSConfig(**fts_data)

        # Parse embeddings config
        if "embeddings_config" in data and data["embeddings_config"]:
            emb_data = data.pop("embeddings_config")
            data["embeddings_config"] = EmbeddingsConfig(**emb_data)

        return cls(**data)


@dataclass
class IndexConfigQuery:
    """Query parameters for finding index configurations."""

    index_name: Optional[str] = None
    type: Optional[IndexType] = None
    space_id: Optional[str] = None
    band_min: Optional[BandLevel] = None
    limit: int = 100


class IndexConfigStore(BaseStore):
    """
    Storage for index configuration management.

    Supports:
    - CRUD operations for index configurations
    - Space and band-based filtering
    - Configuration validation and lifecycle management
    - Health monitoring integration
    """

    def _get_schema_sql(self) -> str:
        """Get the SQL schema for index configuration table."""
        return """
        CREATE TABLE IF NOT EXISTS index_configs (
            index_name TEXT PRIMARY KEY,
            type TEXT NOT NULL CHECK(type IN ('fts', 'embeddings')),
            space_id TEXT NOT NULL,
            band_min TEXT NOT NULL CHECK(band_min IN ('GREEN', 'AMBER', 'RED', 'BLACK')),
            refresh_interval INTEGER NOT NULL DEFAULT 60,
            max_size_mb INTEGER NOT NULL DEFAULT 1000,
            fts_config TEXT,  -- JSON blob for FTS configuration
            embeddings_config TEXT,  -- JSON blob for embeddings configuration
            metadata TEXT NOT NULL DEFAULT '{}',  -- JSON blob for metadata
            created_ts TEXT NOT NULL,
            updated_ts TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_index_configs_space_id ON index_configs(space_id);
        CREATE INDEX IF NOT EXISTS idx_index_configs_type ON index_configs(type);
        CREATE INDEX IF NOT EXISTS idx_index_configs_band_min ON index_configs(band_min);
        """

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize the index_configs table."""
        try:
            conn.executescript(self._get_schema_sql())
            logger.debug("Initialized index_configs schema")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize index_configs schema: {e}")
            raise

    def create_config(self, config: IndexConfig) -> str:
        """
        Create a new index configuration.

        Args:
            config: The index configuration to create

        Returns:
            The index_name of the created configuration

        Raises:
            ValueError: If configuration is invalid
            sqlite3.IntegrityError: If index_name already exists
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction")

        # Validate index name pattern
        import re

        if not re.match(r"^[A-Za-z0-9._:-]{2,64}$", config.index_name):
            raise ValueError(f"Invalid index name pattern: {config.index_name}")

        try:
            data = config.to_dict()

            self._connection.execute(
                """
                INSERT INTO index_configs (
                    index_name, type, space_id, band_min, refresh_interval, max_size_mb,
                    fts_config, embeddings_config, metadata, created_ts, updated_ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["index_name"],
                    data["type"],
                    data["space_id"],
                    data["band_min"],
                    data["refresh_interval"],
                    data["max_size_mb"],
                    (
                        json.dumps(data.get("fts_config"))
                        if data.get("fts_config")
                        else None
                    ),
                    (
                        json.dumps(data.get("embeddings_config"))
                        if data.get("embeddings_config")
                        else None
                    ),
                    json.dumps(data["metadata"]),
                    data["created_ts"],
                    data["updated_ts"],
                ),
            )

            logger.info(f"Created index configuration: {config.index_name}")
            self._operation_count += 1
            return config.index_name

        except sqlite3.Error as e:
            logger.error(
                f"Failed to create index configuration {config.index_name}: {e}"
            )
            self._error_count += 1
            raise

    def get_config(self, index_name: str) -> Optional[IndexConfig]:
        """
        Get an index configuration by name.

        Args:
            index_name: The name of the index configuration

        Returns:
            The index configuration if found, None otherwise
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction")

        try:
            cursor = self._connection.execute(
                """
                SELECT index_name, type, space_id, band_min, refresh_interval, max_size_mb,
                       fts_config, embeddings_config, metadata, created_ts, updated_ts
                FROM index_configs
                WHERE index_name = ?
                """,
                (index_name,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            data = {
                "index_name": row[0],
                "type": row[1],
                "space_id": row[2],
                "band_min": row[3],
                "refresh_interval": row[4],
                "max_size_mb": row[5],
                "metadata": json.loads(row[8]),
                "created_ts": row[9],
                "updated_ts": row[10],
            }

            # Parse config blobs
            if row[6]:  # fts_config
                data["fts_config"] = json.loads(row[6])
            if row[7]:  # embeddings_config
                data["embeddings_config"] = json.loads(row[7])

            return IndexConfig.from_dict(data)

        except sqlite3.Error as e:
            logger.error(f"Failed to get index configuration {index_name}: {e}")
            self._error_count += 1
            raise

    def update_config(self, config: IndexConfig) -> bool:
        """
        Update an existing index configuration.

        Args:
            config: The updated index configuration

        Returns:
            True if updated, False if not found
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction")

        # Update the timestamp
        config.updated_ts = datetime.now(timezone.utc)

        try:
            data = config.to_dict()

            cursor = self._connection.execute(
                """
                UPDATE index_configs SET
                    type = ?, space_id = ?, band_min = ?, refresh_interval = ?, max_size_mb = ?,
                    fts_config = ?, embeddings_config = ?, metadata = ?, updated_ts = ?
                WHERE index_name = ?
                """,
                (
                    data["type"],
                    data["space_id"],
                    data["band_min"],
                    data["refresh_interval"],
                    data["max_size_mb"],
                    (
                        json.dumps(data.get("fts_config"))
                        if data.get("fts_config")
                        else None
                    ),
                    (
                        json.dumps(data.get("embeddings_config"))
                        if data.get("embeddings_config")
                        else None
                    ),
                    json.dumps(data["metadata"]),
                    data["updated_ts"],
                    data["index_name"],
                ),
            )

            updated = cursor.rowcount > 0
            if updated:
                logger.info(f"Updated index configuration: {config.index_name}")
                self._operation_count += 1

            return updated

        except sqlite3.Error as e:
            logger.error(
                f"Failed to update index configuration {config.index_name}: {e}"
            )
            self._error_count += 1
            raise

    def delete_config(self, index_name: str) -> bool:
        """
        Delete an index configuration.

        Args:
            index_name: The name of the index configuration to delete

        Returns:
            True if deleted, False if not found
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction")

        try:
            cursor = self._connection.execute(
                "DELETE FROM index_configs WHERE index_name = ?", (index_name,)
            )

            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted index configuration: {index_name}")
                self._operation_count += 1

            return deleted

        except sqlite3.Error as e:
            logger.error(f"Failed to delete index configuration {index_name}: {e}")
            self._error_count += 1
            raise

    def list_configs(
        self, query: Optional[IndexConfigQuery] = None
    ) -> List[IndexConfig]:
        """
        List index configurations matching the query.

        Args:
            query: Optional query parameters for filtering

        Returns:
            List of matching index configurations
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction")

        query = query or IndexConfigQuery()

        where_clauses = []
        params = []

        if query.index_name:
            where_clauses.append("index_name = ?")
            params.append(query.index_name)

        if query.type:
            where_clauses.append("type = ?")
            params.append(query.type)

        if query.space_id:
            where_clauses.append("space_id = ?")
            params.append(query.space_id)

        if query.band_min:
            where_clauses.append("band_min = ?")
            params.append(query.band_min)

        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        try:
            cursor = self._connection.execute(
                f"""
                SELECT index_name, type, space_id, band_min, refresh_interval, max_size_mb,
                       fts_config, embeddings_config, metadata, created_ts, updated_ts
                FROM index_configs
                {where_sql}
                ORDER BY index_name
                LIMIT ?
                """,
                params + [query.limit],
            )

            configs = []
            for row in cursor.fetchall():
                data = {
                    "index_name": row[0],
                    "type": row[1],
                    "space_id": row[2],
                    "band_min": row[3],
                    "refresh_interval": row[4],
                    "max_size_mb": row[5],
                    "metadata": json.loads(row[8]),
                    "created_ts": row[9],
                    "updated_ts": row[10],
                }

                # Parse config blobs
                if row[6]:  # fts_config
                    data["fts_config"] = json.loads(row[6])
                if row[7]:  # embeddings_config
                    data["embeddings_config"] = json.loads(row[7])

                configs.append(IndexConfig.from_dict(data))

            logger.debug(f"Found {len(configs)} index configurations")
            return configs

        except sqlite3.Error as e:
            logger.error(f"Failed to list index configurations: {e}")
            self._error_count += 1
            raise

    def get_configs_by_space(self, space_id: str) -> List[IndexConfig]:
        """
        Get all index configurations for a specific space.

        Args:
            space_id: The space identifier

        Returns:
            List of index configurations for the space
        """
        return self.list_configs(IndexConfigQuery(space_id=space_id))

    def get_configs_by_type(self, index_type: IndexType) -> List[IndexConfig]:
        """
        Get all index configurations of a specific type.

        Args:
            index_type: The index type ('fts' or 'embeddings')

        Returns:
            List of index configurations of the specified type
        """
        return self.list_configs(IndexConfigQuery(type=index_type))

    def config_exists(self, index_name: str) -> bool:
        """
        Check if an index configuration exists.

        Args:
            index_name: The name of the index configuration

        Returns:
            True if the configuration exists, False otherwise
        """
        if not self._connection:
            raise RuntimeError("Store not in transaction")

        try:
            cursor = self._connection.execute(
                "SELECT 1 FROM index_configs WHERE index_name = ?", (index_name,)
            )
            return cursor.fetchone() is not None

        except sqlite3.Error as e:
            logger.error(
                f"Failed to check index configuration existence {index_name}: {e}"
            )
            self._error_count += 1
            raise

    # BaseStore abstract method implementations

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for this store's data."""
        # For now, return a simple schema - could be enhanced with actual JSON Schema
        return {
            "type": "object",
            "properties": {
                "index_name": {"type": "string"},
                "type": {"enum": ["fts", "embeddings"]},
                "space_id": {"type": "string"},
                "band_min": {"enum": ["GREEN", "AMBER", "RED", "BLACK"]},
            },
            "required": ["index_name", "type", "space_id", "band_min"],
        }

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record in the store."""
        config = IndexConfig.from_dict(data)
        self.create_config(config)
        return config.to_dict()

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record by ID."""
        config = self.get_config(record_id)
        return config.to_dict() if config else None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record."""
        config = IndexConfig.from_dict(data)
        config.index_name = record_id  # Ensure consistency
        self.update_config(config)
        return config.to_dict()

    def _delete_record(self, record_id: str) -> bool:
        """Delete a record by ID."""
        return self.delete_config(record_id)

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List records with optional filtering and pagination."""
        query = IndexConfigQuery(limit=limit or 100)

        if filters:
            if "type" in filters:
                query.type = filters["type"]
            if "space_id" in filters:
                query.space_id = filters["space_id"]
            if "band_min" in filters:
                query.band_min = filters["band_min"]

        configs = self.list_configs(query)
        return [config.to_dict() for config in configs]

    def _on_transaction_begin(self, conn: sqlite3.Connection) -> None:
        """Called when transaction begins."""
        pass

    def _on_transaction_commit(self, conn: sqlite3.Connection) -> None:
        """Called when transaction commits."""
        pass

    def _on_transaction_rollback(self, conn: sqlite3.Connection) -> None:
        """Called when transaction rolls back."""
        pass

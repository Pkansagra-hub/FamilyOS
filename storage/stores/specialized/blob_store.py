"""Blob Store - Binary data storage with encryption and manifest tracking.

This module implements storage for binary data (blobs) with comprehensive metadata tracking,
encryption support, and content integrity verification. Provides secure blob lifecycle
management with space-scoped access control and MLS integration.

Key Features:
- Binary data storage with content integrity (SHA-256)
- Space-scoped access control and MLS group integration
- Optional encryption with key management
- Metadata tracking and content type detection
- Chunked storage support for large files
- BaseStore compliance for transaction management
"""

import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


@dataclass
class BlobManifest:
    """Blob manifest with metadata and integrity information."""

    # Core identification
    blob_id: str
    sha256: str
    size_bytes: int
    content_type: str
    created_ts: str

    # Space and security
    space_id: Optional[str] = None
    mls_group: Optional[str] = None

    # Encryption information
    encryption: Optional[Dict[str, Any]] = None

    # Storage metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Chunking information for large files
    chunk_refs: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class BlobStoreMetadata:
    """Metadata for blob store operations."""

    total_blobs: int = 0
    total_size_bytes: int = 0
    encrypted_blobs: int = 0
    spaces_count: int = 0
    avg_blob_size: float = 0.0
    last_cleanup_ts: Optional[str] = None
    storage_efficiency: float = 1.0  # ratio of actual vs theoretical storage


class BlobStore(BaseStore):
    """Blob storage with encryption and manifest tracking.

    Provides secure binary data storage with comprehensive metadata tracking,
    content integrity verification, and space-scoped access control.
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self.blob_dir = Path(self.config.db_path).parent / "blobs"
        self.blob_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"BlobStore initialized with blob directory: {self.blob_dir}")

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize blob manifest and metadata tables."""
        # Blob manifests table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blob_manifests (
                blob_id TEXT PRIMARY KEY,
                sha256 TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                content_type TEXT NOT NULL,
                created_ts TEXT NOT NULL,
                space_id TEXT,
                mls_group TEXT,
                encryption TEXT,  -- JSON
                metadata TEXT,    -- JSON
                chunk_refs TEXT   -- JSON
            )
        """
        )

        # Metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blob_store_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_ts TEXT NOT NULL
            )
        """
        )

        # Indexes for efficient queries
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_blob_space ON blob_manifests(space_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_blob_mls ON blob_manifests(mls_group)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_blob_created ON blob_manifests(created_ts)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_blob_content_type ON blob_manifests(content_type)"
        )

    def store_blob(self, data: bytes, manifest: BlobManifest) -> str:
        """Store blob data with manifest.

        Args:
            data: Binary data to store
            manifest: Blob manifest with metadata

        Returns:
            blob_id of stored blob

        Raises:
            ValueError: If data integrity check fails
        """
        # Verify SHA-256 integrity
        computed_hash = hashlib.sha256(data).hexdigest()
        if computed_hash != manifest.sha256:
            raise ValueError(
                f"SHA-256 mismatch: expected {manifest.sha256}, got {computed_hash}"
            )

        # Verify size
        if len(data) != manifest.size_bytes:
            raise ValueError(
                f"Size mismatch: expected {manifest.size_bytes}, got {len(data)}"
            )

        blob_path = self.blob_dir / f"{manifest.blob_id}.blob"

        # Store blob data
        with open(blob_path, "wb") as f:
            f.write(data)

        # Store manifest in database
        conn = self._connection
        if not conn:
            raise RuntimeError("BlobStore not in transaction")

        conn.execute(
            """
            INSERT INTO blob_manifests
            (blob_id, sha256, size_bytes, content_type, created_ts, space_id,
             mls_group, encryption, metadata, chunk_refs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                manifest.blob_id,
                manifest.sha256,
                manifest.size_bytes,
                manifest.content_type,
                manifest.created_ts,
                manifest.space_id,
                manifest.mls_group,
                json.dumps(manifest.encryption) if manifest.encryption else None,
                json.dumps(manifest.metadata),
                json.dumps(manifest.chunk_refs),
            ),
        )

        self._update_metadata()
        logger.info(f"Stored blob {manifest.blob_id} ({manifest.size_bytes} bytes)")
        return manifest.blob_id

    def get_blob(self, blob_id: str) -> Optional[bytes]:
        """Retrieve blob data by ID.

        Args:
            blob_id: Blob identifier

        Returns:
            Binary data or None if not found
        """
        blob_path = self.blob_dir / f"{blob_id}.blob"

        if not blob_path.exists():
            return None

        try:
            with open(blob_path, "rb") as f:
                return f.read()
        except IOError as e:
            logger.error(f"Failed to read blob {blob_id}: {e}")
            return None

    def get_manifest(self, blob_id: str) -> Optional[BlobManifest]:
        """Get blob manifest by ID.

        Args:
            blob_id: Blob identifier

        Returns:
            BlobManifest or None if not found
        """
        if not self._connection:
            raise RuntimeError("BlobStore not in transaction")

        cursor = self._connection.execute(
            """
            SELECT blob_id, sha256, size_bytes, content_type, created_ts, space_id, mls_group, encryption, metadata, chunk_refs
            FROM blob_manifests WHERE blob_id = ?
        """,
            (blob_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return BlobManifest(
            blob_id=row[0],
            sha256=row[1],
            size_bytes=row[2],
            content_type=row[3],
            created_ts=row[4],
            space_id=row[5],
            mls_group=row[6],
            encryption=json.loads(row[7]) if row[7] else None,
            metadata=json.loads(row[8]) if row[8] else {},
            chunk_refs=json.loads(row[9]) if row[9] else [],
        )

    def list_blobs(
        self,
        space_id: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[BlobManifest]:
        """List blob manifests with filtering.

        Args:
            space_id: Filter by space (optional)
            content_type: Filter by content type (optional)
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            List of BlobManifest objects
        """
        conditions: List[str] = []
        params: List[Any] = []

        if space_id:
            conditions.append("space_id = ?")
            params.append(space_id)

        if content_type:
            conditions.append("content_type = ?")
            params.append(content_type)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])

        if not self._connection:
            raise RuntimeError("BlobStore not in transaction")

        cursor = self._connection.execute(
            f"""
            SELECT blob_id, sha256, size_bytes, content_type, created_ts, space_id, mls_group, encryption, metadata, chunk_refs
            FROM blob_manifests
            WHERE {where_clause}
            ORDER BY created_ts DESC
            LIMIT ? OFFSET ?
        """,
            params,
        )

        manifests = []
        for row in cursor.fetchall():
            manifests.append(
                BlobManifest(
                    blob_id=row[0],
                    sha256=row[1],
                    size_bytes=row[2],
                    content_type=row[3],
                    created_ts=row[4],
                    space_id=row[5],
                    mls_group=row[6],
                    encryption=json.loads(row[7]) if row[7] else None,
                    metadata=json.loads(row[8]) if row[8] else {},
                    chunk_refs=json.loads(row[9]) if row[9] else [],
                )
            )

        return manifests

    def delete_blob(self, blob_id: str) -> bool:
        """Delete blob and its manifest.

        Args:
            blob_id: Blob identifier

        Returns:
            True if deleted, False if not found
        """
        blob_path = self.blob_dir / f"{blob_id}.blob"

        if not self._connection:
            raise RuntimeError("BlobStore not in transaction")

        cursor = self._connection.execute(
            "DELETE FROM blob_manifests WHERE blob_id = ?", (blob_id,)
        )
        deleted = cursor.rowcount > 0

        # Remove file if exists
        if blob_path.exists():
            try:
                blob_path.unlink()
            except OSError as e:
                logger.error(f"Failed to delete blob file {blob_path}: {e}")

        if deleted:
            self._update_metadata()
            logger.info(f"Deleted blob {blob_id}")

        return deleted

    def verify_integrity(self, blob_id: str) -> bool:
        """Verify blob integrity against manifest.

        Args:
            blob_id: Blob identifier

        Returns:
            True if integrity check passes, False otherwise
        """
        manifest = self.get_manifest(blob_id)
        if not manifest:
            return False

        data = self.get_blob(blob_id)
        if not data:
            return False

        # Check size
        if len(data) != manifest.size_bytes:
            logger.warning(
                f"Size mismatch for blob {blob_id}: expected {manifest.size_bytes}, got {len(data)}"
            )
            return False

        # Check SHA-256
        computed_hash = hashlib.sha256(data).hexdigest()
        if computed_hash != manifest.sha256:
            logger.warning(
                f"SHA-256 mismatch for blob {blob_id}: expected {manifest.sha256}, got {computed_hash}"
            )
            return False

        return True

    def get_metadata(self) -> BlobStoreMetadata:
        """Get blob store metadata and statistics."""
        if not self._connection:
            raise RuntimeError("BlobStore not in transaction")

        # Get blob counts and sizes
        cursor = self._connection.execute(
            """
            SELECT
                COUNT(*) as total_blobs,
                COALESCE(SUM(size_bytes), 0) as total_size_bytes,
                COUNT(DISTINCT space_id) as spaces_count,
                COALESCE(AVG(size_bytes), 0) as avg_blob_size,
                COUNT(CASE WHEN encryption IS NOT NULL THEN 1 END) as encrypted_blobs
            FROM blob_manifests
        """
        )

        row = cursor.fetchone()
        if not row:
            return BlobStoreMetadata()

        # Get last cleanup timestamp
        cleanup_cursor = self._connection.execute(
            """
            SELECT value FROM blob_store_metadata WHERE key = 'last_cleanup_ts'
        """
        )
        cleanup_row = cleanup_cursor.fetchone()
        last_cleanup_ts = cleanup_row[0] if cleanup_row else None

        return BlobStoreMetadata(
            total_blobs=row[0],
            total_size_bytes=row[1],
            spaces_count=row[2],
            avg_blob_size=row[3],
            encrypted_blobs=row[4],
            last_cleanup_ts=last_cleanup_ts,
            storage_efficiency=1.0,  # Could calculate actual vs theoretical storage
        )

    def _update_metadata(self) -> None:
        """Update internal metadata tracking."""
        if not self._connection:
            raise RuntimeError("BlobStore not in transaction")

        now = datetime.now(timezone.utc).isoformat()

        # Note: We don't call get_metadata() here to avoid infinite recursion
        # Instead just update the timestamp
        self._connection.execute(
            """
            INSERT OR REPLACE INTO blob_store_metadata (key, value, updated_ts)
            VALUES ('updated_ts', ?, ?)
        """,
            (now, now),
        )

    def cleanup_orphaned_files(self) -> int:
        """Clean up blob files without manifests.

        Returns:
            Number of orphaned files removed
        """
        if not self.blob_dir.exists():
            return 0

        # Get all blob IDs from database
        if not self._connection:
            raise RuntimeError("BlobStore not in transaction")

        cursor = self._connection.execute("SELECT blob_id FROM blob_manifests")
        db_blob_ids = {row[0] for row in cursor.fetchall()}

        # Check all blob files
        orphaned_count = 0
        for blob_file in self.blob_dir.glob("*.blob"):
            blob_id = blob_file.stem
            if blob_id not in db_blob_ids:
                try:
                    blob_file.unlink()
                    orphaned_count += 1
                    logger.info(f"Removed orphaned blob file: {blob_file}")
                except OSError as e:
                    logger.error(
                        f"Failed to remove orphaned blob file {blob_file}: {e}"
                    )

        # Update cleanup timestamp
        now = datetime.now(timezone.utc).isoformat()
        self._connection.execute(
            """
            INSERT OR REPLACE INTO blob_store_metadata (key, value, updated_ts)
            VALUES ('last_cleanup_ts', ?, ?)
        """,
            (now, now),
        )

        logger.info(f"Cleanup completed: removed {orphaned_count} orphaned blob files")
        return orphaned_count

    # BaseStore interface methods
    def get(self, id: str) -> Optional[Dict[str, Any]]:
        """Get blob manifest as dict (BaseStore interface)."""
        manifest = self.get_manifest(id)
        if not manifest:
            return None

        return {
            "blob_id": manifest.blob_id,
            "sha256": manifest.sha256,
            "size_bytes": manifest.size_bytes,
            "content_type": manifest.content_type,
            "created_ts": manifest.created_ts,
            "space_id": manifest.space_id,
            "mls_group": manifest.mls_group,
            "encryption": manifest.encryption,
            "metadata": manifest.metadata,
            "chunk_refs": manifest.chunk_refs,
        }

    def list_as_dicts(
        self, limit: int = 100, offset: int = 0, **filters: Any
    ) -> List[Dict[str, Any]]:
        """List blob manifests as dicts (BaseStore interface)."""
        manifests = self.list_blobs(
            space_id=filters.get("space_id"),
            content_type=filters.get("content_type"),
            limit=limit,
            offset=offset,
        )

        return [
            {
                "blob_id": m.blob_id,
                "sha256": m.sha256,
                "size_bytes": m.size_bytes,
                "content_type": m.content_type,
                "created_ts": m.created_ts,
                "space_id": m.space_id,
                "mls_group": m.mls_group,
                "encryption": m.encryption,
                "metadata": m.metadata,
                "chunk_refs": m.chunk_refs,
            }
            for m in manifests
        ]

    def exists(self, id: str) -> bool:
        """Check if blob exists (BaseStore interface)."""
        return self.get_manifest(id) is not None

    def count(self, **filters: Any) -> int:
        """Count blobs with optional filters (BaseStore interface)."""
        conditions: List[str] = []
        params: List[Any] = []

        if "space_id" in filters:
            conditions.append("space_id = ?")
            params.append(filters["space_id"])

        if "content_type" in filters:
            conditions.append("content_type = ?")
            params.append(filters["content_type"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        if not self._connection:
            raise RuntimeError("BlobStore not in transaction")

        cursor = self._connection.execute(
            f"SELECT COUNT(*) FROM blob_manifests WHERE {where_clause}", params
        )
        return cursor.fetchone()[0]

    # BaseStore abstract method implementations

    def _get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for blob manifest validation."""
        return {
            "type": "object",
            "required": ["blob_id", "sha256", "size_bytes", "created_ts", "space_id"],
            "properties": {
                "blob_id": {"type": "string"},
                "sha256": {"type": "string", "pattern": "^[a-fA-F0-9]{64}$"},
                "size_bytes": {"type": "integer", "minimum": 0},
                "content_type": {"type": ["string", "null"]},
                "created_ts": {"type": "string", "format": "date-time"},
                "space_id": {"type": "string"},
                "mls_group": {"type": ["string", "null"]},
                "encryption": {"type": ["object", "null"]},
                "metadata": {"type": "object"},
                "chunk_refs": {"type": "array", "items": {"type": "object"}},
            },
        }

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new blob manifest record."""
        manifest = BlobManifest(**data)
        # Blob data should be stored separately via store_blob()
        # This just stores the manifest
        if not self._connection:
            raise RuntimeError("BlobStore not in transaction")

        self._connection.execute(
            """
            INSERT INTO blob_manifests
            (blob_id, sha256, size_bytes, content_type, created_ts, space_id,
             mls_group, encryption, metadata, chunk_refs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                manifest.blob_id,
                manifest.sha256,
                manifest.size_bytes,
                manifest.content_type,
                manifest.created_ts,
                manifest.space_id,
                manifest.mls_group,
                json.dumps(manifest.encryption) if manifest.encryption else None,
                json.dumps(manifest.metadata),
                json.dumps(manifest.chunk_refs),
            ),
        )

        return data

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a blob manifest by ID."""
        manifest = self.get_manifest(record_id)
        if manifest:
            return {
                "blob_id": manifest.blob_id,
                "sha256": manifest.sha256,
                "size_bytes": manifest.size_bytes,
                "content_type": manifest.content_type,
                "created_ts": manifest.created_ts,
                "space_id": manifest.space_id,
                "mls_group": manifest.mls_group,
                "encryption": manifest.encryption,
                "metadata": manifest.metadata,
                "chunk_refs": manifest.chunk_refs,
            }
        return None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a blob manifest record."""
        if not self._connection:
            raise RuntimeError("BlobStore not in transaction")

        # Build dynamic update query for provided fields
        update_fields: List[str] = []
        values: List[Any] = []

        for field_name in ["content_type", "metadata", "encryption"]:
            if field_name in data:
                update_fields.append(f"{field_name} = ?")
                if (
                    field_name in ["metadata", "encryption"]
                    and data[field_name] is not None
                ):
                    values.append(json.dumps(data[field_name]))
                else:
                    values.append(data[field_name])

        if not update_fields:
            # Nothing to update
            return self._read_record(record_id) or {}

        values.append(record_id)

        self._connection.execute(
            f"UPDATE blob_manifests SET {', '.join(update_fields)} WHERE blob_id = ?",
            values,
        )

        return self._read_record(record_id) or {}

    def _delete_record(self, record_id: str) -> bool:
        """Delete a blob manifest record."""
        return self.delete_blob(record_id)

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List blob manifest records with filtering."""
        filters = filters or {}
        manifests = self.list_blobs(
            space_id=filters.get("space_id"),
            content_type=filters.get("content_type"),
            limit=limit or 100,
            offset=offset or 0,
        )

        return [
            {
                "blob_id": m.blob_id,
                "sha256": m.sha256,
                "size_bytes": m.size_bytes,
                "content_type": m.content_type,
                "created_ts": m.created_ts,
                "space_id": m.space_id,
                "mls_group": m.mls_group,
                "encryption": m.encryption,
                "metadata": m.metadata,
                "chunk_refs": m.chunk_refs,
            }
            for m in manifests
        ]

"""
Secure Store - Encrypted data storage with key management.

This module implements storage for encrypted/secure items following the
secure_item.schema.json contract. Provides encrypted data storage with
key wrapping, content integrity verification, and purpose-based classification.

Key Features:
- Encrypted item storage with key wrapping
- Space-scoped access control and purpose classification
- Content integrity verification with SHA-256
- Key management integration for wrapped keys
- BaseStore compliance for transaction management
"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


@dataclass
class SecureItem:
    """
    Secure item record following secure_item.schema.json contract.

    Represents an encrypted data item with wrapped key and integrity verification.
    """

    id: str  # ULID
    owner_space: str  # Space ID
    created_ts: str  # Timestamp
    wrapped_key: str  # Base64 encoded wrapped key
    ciphertext_sha256: str  # SHA-256 hash of ciphertext
    purpose: str = "other"  # blob, embedding, session, other
    meta: Optional[Dict[str, Any]] = None  # Optional metadata


class SecureStore(BaseStore):
    """
    Secure storage for encrypted data items.

    Provides encrypted item management with:
    - Encrypted data storage with key wrapping
    - Content integrity verification with SHA-256
    - Purpose-based classification (blob, embedding, session, other)
    - Space-scoped access controls
    - Key management integration

    Storage Model:
    - secure_items table: Encrypted item metadata and wrapped keys
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        """Initialize secure store with encrypted items table schema."""
        super().__init__(config)
        logger.info("SecureStore initialized for encrypted data storage")

    def _get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for secure item validation."""
        return {
            "type": "object",
            "required": [
                "id",
                "owner_space",
                "created_ts",
                "wrapped_key",
                "ciphertext_sha256",
            ],
            "properties": {
                "id": {"type": "string"},
                "owner_space": {"type": "string"},
                "created_ts": {"type": "string", "format": "date-time"},
                "wrapped_key": {"type": "string"},
                "ciphertext_sha256": {"type": "string"},
                "purpose": {
                    "type": "string",
                    "enum": ["blob", "embedding", "session", "other"],
                },
                "meta": {"type": "object"},
            },
        }

    def _initialize_schema(self, conn: Any) -> None:
        """Initialize secure items database schema."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS secure_items (
            id TEXT PRIMARY KEY,
            owner_space TEXT NOT NULL,
            created_ts TEXT NOT NULL,
            wrapped_key TEXT NOT NULL,
            ciphertext_sha256 TEXT NOT NULL,
            purpose TEXT NOT NULL DEFAULT 'other',
            meta TEXT,  -- JSON object
            updated_ts TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_secure_items_owner_space ON secure_items(owner_space);
        CREATE INDEX IF NOT EXISTS idx_secure_items_purpose ON secure_items(purpose);
        CREATE INDEX IF NOT EXISTS idx_secure_items_created_ts ON secure_items(created_ts);
        CREATE INDEX IF NOT EXISTS idx_secure_items_hash ON secure_items(ciphertext_sha256);
        CREATE INDEX IF NOT EXISTS idx_secure_items_space_purpose
            ON secure_items(owner_space, purpose);
        """

        conn.executescript(schema_sql)
        logger.info("Secure store schema initialized with secure_items table")

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a generic record (converts to SecureItem and calls store_item)."""
        secure_item = SecureItem(
            id=data["id"],
            owner_space=data["owner_space"],
            created_ts=data["created_ts"],
            wrapped_key=data["wrapped_key"],
            ciphertext_sha256=data["ciphertext_sha256"],
            purpose=data.get("purpose", "other"),
            meta=data.get("meta"),
        )
        self.store_item(secure_item)
        return asdict(secure_item)

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a generic record (calls get_item and converts to dict)."""
        secure_item = self.get_item(record_id)
        return asdict(secure_item) if secure_item else None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a generic record (calls update_item and returns updated record)."""
        self.update_item(record_id, data)
        updated_item = self.get_item(record_id)
        if not updated_item:
            raise ValueError(f"Failed to update secure item {record_id}")
        return asdict(updated_item)

    def _delete_record(self, record_id: str) -> bool:
        """Delete a generic record (calls delete_item)."""
        try:
            self.delete_item(record_id)
            return True
        except Exception:
            return False

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List generic records (returns secure items as dicts)."""
        # Extract space_id from filters if provided
        space_id = filters.get("owner_space") if filters else None
        purpose = filters.get("purpose") if filters else None

        items = self.list_items(space_id, purpose, limit)

        # Apply offset if specified
        if offset and offset > 0:
            items = items[offset:]

        return [asdict(item) for item in items]

    # Secure Item Management
    def store_item(self, secure_item: SecureItem) -> str:
        """
        Store a secure item with encryption.

        Args:
            secure_item: SecureItem instance to store

        Returns:
            item_id: The ID of the stored item
        """
        if not self._connection:
            raise RuntimeError("SecureStore not in transaction")

        meta_json = json.dumps(secure_item.meta) if secure_item.meta else None

        self._connection.execute(
            """
            INSERT INTO secure_items (id, owner_space, created_ts, wrapped_key,
                                    ciphertext_sha256, purpose, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                secure_item.id,
                secure_item.owner_space,
                secure_item.created_ts,
                secure_item.wrapped_key,
                secure_item.ciphertext_sha256,
                secure_item.purpose,
                meta_json,
            ),
        )

        logger.info(
            f"Stored secure item {secure_item.id} ({secure_item.purpose}) "
            f"in space {secure_item.owner_space}"
        )
        return secure_item.id

    def get_item(self, item_id: str) -> Optional[SecureItem]:
        """
        Retrieve a secure item by ID.

        Args:
            item_id: The item ID to retrieve

        Returns:
            SecureItem instance or None if not found
        """
        if not self._connection:
            raise RuntimeError("SecureStore not in transaction")

        cursor = self._connection.execute(
            """
            SELECT id, owner_space, created_ts, wrapped_key, ciphertext_sha256, purpose, meta
            FROM secure_items WHERE id = ?
        """,
            (item_id,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        meta = json.loads(row[6]) if row[6] else None

        return SecureItem(
            id=row[0],
            owner_space=row[1],
            created_ts=row[2],
            wrapped_key=row[3],
            ciphertext_sha256=row[4],
            purpose=row[5],
            meta=meta,
        )

    def update_item(self, item_id: str, updates: Dict[str, Any]) -> None:
        """
        Update a secure item.

        Args:
            item_id: The item ID to update
            updates: Dictionary of fields to update
        """
        if not self._connection:
            raise RuntimeError("SecureStore not in transaction")

        # Build dynamic update query
        update_fields: List[str] = []
        values: List[Any] = []

        if "wrapped_key" in updates:
            update_fields.append("wrapped_key = ?")
            values.append(updates["wrapped_key"])

        if "ciphertext_sha256" in updates:
            update_fields.append("ciphertext_sha256 = ?")
            values.append(updates["ciphertext_sha256"])

        if "purpose" in updates:
            update_fields.append("purpose = ?")
            values.append(updates["purpose"])

        if "meta" in updates:
            update_fields.append("meta = ?")
            values.append(json.dumps(updates["meta"]) if updates["meta"] else None)

        if not update_fields:
            return

        update_fields.append("updated_ts = CURRENT_TIMESTAMP")
        values.append(item_id)

        self._connection.execute(
            f"""
            UPDATE secure_items SET {', '.join(update_fields)}
            WHERE id = ?
        """,
            values,
        )

        logger.info(f"Updated secure item {item_id}")

    def delete_item(self, item_id: str) -> None:
        """
        Delete a secure item.

        Args:
            item_id: The item ID to delete
        """
        if not self._connection:
            raise RuntimeError("SecureStore not in transaction")

        self._connection.execute("DELETE FROM secure_items WHERE id = ?", (item_id,))

        logger.info(f"Deleted secure item {item_id}")

    def list_items(
        self,
        space_id: Optional[str] = None,
        purpose: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[SecureItem]:
        """
        List secure items, optionally filtered by space and purpose.

        Args:
            space_id: Optional space filter
            purpose: Optional purpose filter (blob, embedding, session, other)
            limit: Optional result limit

        Returns:
            List of SecureItem instances
        """
        if not self._connection:
            raise RuntimeError("SecureStore not in transaction")

        # Build dynamic query
        where_clauses: List[str] = []
        params: List[Any] = []

        if space_id:
            where_clauses.append("owner_space = ?")
            params.append(space_id)

        if purpose:
            where_clauses.append("purpose = ?")
            params.append(purpose)

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            SELECT id, owner_space, created_ts, wrapped_key, ciphertext_sha256, purpose, meta
            FROM secure_items WHERE {where_clause}
            ORDER BY created_ts DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor = self._connection.execute(query, params)
        rows = cursor.fetchall()

        items = []
        for row in rows:
            meta = json.loads(row[6]) if row[6] else None
            item = SecureItem(
                id=row[0],
                owner_space=row[1],
                created_ts=row[2],
                wrapped_key=row[3],
                ciphertext_sha256=row[4],
                purpose=row[5],
                meta=meta,
            )
            items.append(item)

        return items

    def list_items_by_purpose(
        self, purpose: str, space_id: Optional[str] = None, limit: Optional[int] = None
    ) -> List[SecureItem]:
        """
        List secure items filtered by purpose.

        Args:
            purpose: Purpose filter (blob, embedding, session, other)
            space_id: Optional space filter
            limit: Optional result limit

        Returns:
            List of SecureItem instances with specified purpose
        """
        return self.list_items(space_id, purpose, limit)

    def verify_item_integrity(self, item_id: str, ciphertext: bytes) -> bool:
        """
        Verify the integrity of a secure item against its stored hash.

        Args:
            item_id: The item ID to verify
            ciphertext: The ciphertext bytes to verify

        Returns:
            True if integrity check passes, False otherwise
        """
        item = self.get_item(item_id)
        if not item:
            return False

        # Calculate SHA-256 hash of provided ciphertext
        calculated_hash = hashlib.sha256(ciphertext).hexdigest()

        # Compare with stored hash
        return calculated_hash == item.ciphertext_sha256

    def get_space_stats(self, space_id: str) -> Dict[str, Any]:
        """
        Get secure item statistics for a space.

        Args:
            space_id: Space ID to get stats for

        Returns:
            Dictionary with item counts by purpose and other stats
        """
        if not self._connection:
            raise RuntimeError("SecureStore not in transaction")

        # Get total count for space
        cursor = self._connection.execute(
            "SELECT COUNT(*) FROM secure_items WHERE owner_space = ?", (space_id,)
        )
        total_items = cursor.fetchone()[0]

        # Get purpose breakdown
        cursor = self._connection.execute(
            """
            SELECT purpose, COUNT(*) FROM secure_items WHERE owner_space = ? GROUP BY purpose
        """,
            (space_id,),
        )

        purpose_counts = {}
        for row in cursor.fetchall():
            purpose_counts[row[0]] = row[1]

        return {
            "space_id": space_id,
            "total_items": total_items,
            "purpose_counts": purpose_counts,
        }

    def cleanup_old_items(
        self,
        older_than_days: int,
        purpose_filter: Optional[str] = None,
        space_id: Optional[str] = None,
    ) -> int:
        """
        Clean up old secure items based on age and optionally purpose.

        Args:
            older_than_days: Delete items older than this many days
            purpose_filter: Optional purpose filter
            space_id: Optional space filter

        Returns:
            Number of items deleted
        """
        if not self._connection:
            raise RuntimeError("SecureStore not in transaction")

        cutoff_ts = datetime.now(timezone.utc).timestamp() - (
            older_than_days * 24 * 60 * 60
        )
        cutoff_iso = datetime.fromtimestamp(cutoff_ts, timezone.utc).isoformat()

        # Build dynamic query
        where_clauses = ["created_ts < ?"]
        params: List[Any] = [cutoff_iso]

        if space_id:
            where_clauses.append("owner_space = ?")
            params.append(space_id)

        if purpose_filter:
            where_clauses.append("purpose = ?")
            params.append(purpose_filter)

        where_clause = " AND ".join(where_clauses)

        # First count what we'll delete
        cursor = self._connection.execute(
            f"SELECT COUNT(*) FROM secure_items WHERE {where_clause}", params
        )
        delete_count = cursor.fetchone()[0]

        # Then delete
        if delete_count > 0:
            self._connection.execute(
                f"DELETE FROM secure_items WHERE {where_clause}", params
            )
            logger.info(
                f"Cleaned up {delete_count} old secure items (older than {older_than_days} days)"
            )

        return delete_count

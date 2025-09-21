"""Idempotency key store for preventing duplicate operations and ensuring transaction safety."""

import hashlib
import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


@dataclass
class IdempotencyRecord:
    """Represents an idempotency key record with operation context and result caching."""

    key: str
    operation: str
    payload_hash: str
    result: Optional[Dict[str, Any]]
    created_at: float
    expires_at: float
    request_id: Optional[str] = None
    actor_id: Optional[str] = None


class IdempotencyStore(BaseStore):
    """
    Store for managing idempotency keys to prevent duplicate operations.

    Provides:
    - Unique key generation based on operation and payload
    - Duplicate operation detection
    - Result caching for repeated operations
    - TTL-based expiration and cleanup
    - Integration with UnitOfWork transaction lifecycle

    Key Features:
    - SHA256-based deterministic key generation
    - Configurable TTL for key expiration (default 24 hours)
    - Automatic cleanup of expired keys
    - Thread-safe operation tracking
    - Performance metrics and monitoring
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        """Initialize idempotency store with configuration."""
        super().__init__(config)
        self.default_ttl = 86400  # 24 hours in seconds
        self._cleanup_interval = 3600  # 1 hour cleanup interval
        self._last_cleanup = time.time()

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for idempotency records."""
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string", "maxLength": 64},
                "operation": {"type": "string", "maxLength": 200},
                "payload_hash": {"type": "string", "maxLength": 64},
                "result": {"type": ["object", "null"]},
                "created_at": {"type": "number"},
                "expires_at": {"type": "number"},
                "request_id": {"type": ["string", "null"], "maxLength": 100},
                "actor_id": {"type": ["string", "null"], "maxLength": 100},
            },
            "required": [
                "key",
                "operation",
                "payload_hash",
                "created_at",
                "expires_at",
            ],
            "additionalProperties": False,
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize the idempotency keys table with proper indexes."""
        try:
            # Create main idempotency table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    key TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    result TEXT,  -- JSON serialized result
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    request_id TEXT,
                    actor_id TEXT
                )
            """
            )

            # Create indexes for efficient queries
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_idempotency_expires
                ON idempotency_keys(expires_at)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_idempotency_operation
                ON idempotency_keys(operation, created_at)
            """
            )

            # Create index on payload_hash for duplicate detection
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_idempotency_payload_hash
                ON idempotency_keys(payload_hash)
            """
            )

            conn.commit()
            logger.info("Idempotency store schema initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize idempotency schema: {e}")
            raise

    def generate_key(self, operation: str, payload: Dict[str, Any]) -> str:
        """
        Generate a deterministic idempotency key based on operation and payload.

        Args:
            operation: The operation type (e.g., 'create_user', 'update_balance')
            payload: The operation payload data

        Returns:
            SHA256 hash string as the idempotency key
        """
        try:
            # Create a normalized payload representation
            normalized_payload = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            )

            # Combine operation and payload for hashing
            key_material = f"{operation}:{normalized_payload}"

            # Generate SHA256 hash
            key_hash = hashlib.sha256(key_material.encode("utf-8")).hexdigest()

            logger.debug(
                f"Generated idempotency key for operation '{operation}': {key_hash[:8]}..."
            )
            return key_hash

        except Exception as e:
            logger.error(
                f"Failed to generate idempotency key for operation '{operation}': {e}"
            )
            raise

    def check_key(self, key: str) -> Optional[IdempotencyRecord]:
        """
        Check if an idempotency key exists and is still valid.

        Args:
            key: The idempotency key to check

        Returns:
            IdempotencyRecord if key exists and is valid, None otherwise
        """
        if not self._connection:
            raise RuntimeError(
                "Store not in transaction - cannot check idempotency key"
            )

        try:
            cursor = self._connection.execute(
                """
                SELECT key, operation, payload_hash, result, created_at, expires_at, request_id, actor_id
                FROM idempotency_keys
                WHERE key = ? AND expires_at > ?
            """,
                (key, time.time()),
            )

            row = cursor.fetchone()
            if row:
                return IdempotencyRecord(
                    key=row[0],
                    operation=row[1],
                    payload_hash=row[2],
                    result=json.loads(row[3]) if row[3] else None,
                    created_at=row[4],
                    expires_at=row[5],
                    request_id=row[6],
                    actor_id=row[7],
                )
            return None

        except Exception as e:
            logger.error(f"Failed to check idempotency key {key}: {e}")
            raise

    def store_key(
        self,
        key: str,
        operation: str,
        payload: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
        request_id: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> IdempotencyRecord:
        """
        Store an idempotency key with operation context and optional result.

        Args:
            key: The idempotency key
            operation: The operation type
            payload: The operation payload
            result: Optional operation result to cache
            ttl: Time-to-live in seconds (defaults to 24 hours)
            request_id: Optional request identifier for tracing
            actor_id: Optional actor identifier for auditing

        Returns:
            The stored IdempotencyRecord
        """
        if not self._connection:
            raise RuntimeError(
                "Store not in transaction - cannot store idempotency key"
            )

        try:
            current_time = time.time()
            effective_ttl = ttl or self.default_ttl
            expires_at = current_time + effective_ttl

            # Generate payload hash for duplicate detection
            payload_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode("utf-8")
            ).hexdigest()

            # Serialize result if provided
            result_json = json.dumps(result) if result else None

            # Insert or replace the idempotency key
            self._connection.execute(
                """
                INSERT OR REPLACE INTO idempotency_keys
                (key, operation, payload_hash, result, created_at, expires_at, request_id, actor_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    key,
                    operation,
                    payload_hash,
                    result_json,
                    current_time,
                    expires_at,
                    request_id,
                    actor_id,
                ),
            )

            record = IdempotencyRecord(
                key=key,
                operation=operation,
                payload_hash=payload_hash,
                result=result,
                created_at=current_time,
                expires_at=expires_at,
                request_id=request_id,
                actor_id=actor_id,
            )

            logger.debug(
                f"Stored idempotency key {key[:8]}... for operation '{operation}' with TTL {effective_ttl}s"
            )
            return record

        except Exception as e:
            logger.error(f"Failed to store idempotency key {key}: {e}")
            raise

    def remove_key(self, key: str) -> bool:
        """
        Remove an idempotency key from storage.

        Args:
            key: The idempotency key to remove

        Returns:
            True if key was removed, False if key didn't exist
        """
        if not self._connection:
            raise RuntimeError(
                "Store not in transaction - cannot remove idempotency key"
            )

        try:
            cursor = self._connection.execute(
                """
                DELETE FROM idempotency_keys WHERE key = ?
            """,
                (key,),
            )

            removed = cursor.rowcount > 0
            if removed:
                logger.debug(f"Removed idempotency key {key[:8]}...")

            return removed

        except Exception as e:
            logger.error(f"Failed to remove idempotency key {key}: {e}")
            raise

    def cleanup_expired(self, batch_size: int = 1000) -> int:
        """
        Remove expired idempotency keys in batches.

        Args:
            batch_size: Maximum number of keys to remove in one batch

        Returns:
            Number of expired keys removed
        """
        if not self._connection:
            logger.warning("Store not in transaction - skipping cleanup")
            return 0

        try:
            current_time = time.time()

            # Count expired keys first
            cursor = self._connection.execute(
                """
                SELECT COUNT(*) FROM idempotency_keys WHERE expires_at <= ?
            """,
                (current_time,),
            )

            total_expired = cursor.fetchone()[0]
            if total_expired == 0:
                return 0

            # Delete expired keys in batches to avoid long locks
            total_removed = 0
            while total_removed < total_expired:
                cursor = self._connection.execute(
                    """
                    DELETE FROM idempotency_keys
                    WHERE key IN (
                        SELECT key FROM idempotency_keys
                        WHERE expires_at <= ?
                        LIMIT ?
                    )
                """,
                    (current_time, batch_size),
                )

                removed_this_batch = cursor.rowcount
                if removed_this_batch == 0:
                    break

                total_removed += removed_this_batch

                # Commit batch to avoid holding locks too long
                self._connection.commit()

            if total_removed > 0:
                logger.info(f"Cleaned up {total_removed} expired idempotency keys")

            return total_removed

        except Exception as e:
            logger.error(f"Failed to cleanup expired idempotency keys: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about idempotency key usage.

        Returns:
            Dictionary with statistics including total keys, expired keys, operations
        """
        if not self._connection:
            logger.warning("Store not in transaction - returning empty statistics")
            return {}

        try:
            current_time = time.time()

            # Count total keys
            cursor = self._connection.execute("SELECT COUNT(*) FROM idempotency_keys")
            total_keys = cursor.fetchone()[0]

            # Count expired keys
            cursor = self._connection.execute(
                """
                SELECT COUNT(*) FROM idempotency_keys WHERE expires_at <= ?
            """,
                (current_time,),
            )
            expired_keys = cursor.fetchone()[0]

            # Count active keys
            active_keys = total_keys - expired_keys

            # Get operation statistics
            cursor = self._connection.execute(
                """
                SELECT operation, COUNT(*) as count
                FROM idempotency_keys
                WHERE expires_at > ?
                GROUP BY operation
                ORDER BY count DESC
                LIMIT 10
            """,
                (current_time,),
            )

            operation_stats = [
                {"operation": row[0], "count": row[1]} for row in cursor.fetchall()
            ]

            # Calculate oldest and newest keys
            cursor = self._connection.execute(
                """
                SELECT MIN(created_at), MAX(created_at)
                FROM idempotency_keys
                WHERE expires_at > ?
            """,
                (current_time,),
            )

            oldest, newest = cursor.fetchone()

            return {
                "total_keys": total_keys,
                "active_keys": active_keys,
                "expired_keys": expired_keys,
                "operation_stats": operation_stats,
                "oldest_key_age_seconds": current_time - oldest if oldest else 0,
                "newest_key_age_seconds": current_time - newest if newest else 0,
                "default_ttl_seconds": self.default_ttl,
                "last_cleanup_age_seconds": current_time - self._last_cleanup,
            }

        except Exception as e:
            logger.error(f"Failed to get idempotency statistics: {e}")
            return {"error": str(e)}

    def _should_cleanup(self) -> bool:
        """Check if automatic cleanup should be performed."""
        return (time.time() - self._last_cleanup) >= self._cleanup_interval

    def _on_transaction_begin(self, conn: sqlite3.Connection) -> None:
        """Called when transaction begins - perform automatic cleanup if needed."""
        try:
            if self._should_cleanup():
                cleanup_count = self.cleanup_expired()
                self._last_cleanup = time.time()
                if cleanup_count > 0:
                    logger.debug(
                        f"Auto-cleanup removed {cleanup_count} expired idempotency keys"
                    )
        except Exception as e:
            logger.warning(f"Auto-cleanup failed during transaction begin: {e}")

    def _on_transaction_commit(self, conn: sqlite3.Connection) -> None:
        """Called when transaction commits successfully."""
        self._operation_count += 1
        logger.debug(
            f"Idempotency store transaction committed (total operations: {self._operation_count})"
        )

    def _on_transaction_rollback(self, conn: sqlite3.Connection) -> None:
        """Called when transaction is rolled back."""
        self._error_count += 1
        logger.debug(
            f"Idempotency store transaction rolled back (total errors: {self._error_count})"
        )

    # Abstract method implementations for BaseStore compliance

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new idempotency record."""
        if not self._connection:
            raise RuntimeError("Store not in transaction - cannot create record")

        key = data.get("key")
        if not key:
            raise ValueError("Missing required field: key")

        operation = data.get("operation", "unknown")
        payload = data.get("payload", {})
        result = data.get("result")
        ttl = data.get("ttl")
        request_id = data.get("request_id")
        actor_id = data.get("actor_id")

        record = self.store_key(
            key=key,
            operation=operation,
            payload=payload,
            result=result,
            ttl=ttl,
            request_id=request_id,
            actor_id=actor_id,
        )

        return {
            "key": record.key,
            "operation": record.operation,
            "payload_hash": record.payload_hash,
            "result": record.result,
            "created_at": record.created_at,
            "expires_at": record.expires_at,
            "request_id": record.request_id,
            "actor_id": record.actor_id,
        }

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read an idempotency record by key."""
        record = self.check_key(record_id)
        if record:
            return {
                "key": record.key,
                "operation": record.operation,
                "payload_hash": record.payload_hash,
                "result": record.result,
                "created_at": record.created_at,
                "expires_at": record.expires_at,
                "request_id": record.request_id,
                "actor_id": record.actor_id,
            }
        return None

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an idempotency record (essentially replace it)."""
        # For idempotency records, update is essentially a store operation
        key = record_id
        operation = data.get("operation", "unknown")
        payload = data.get("payload", {})
        result = data.get("result")
        ttl = data.get("ttl")
        request_id = data.get("request_id")
        actor_id = data.get("actor_id")

        record = self.store_key(
            key=key,
            operation=operation,
            payload=payload,
            result=result,
            ttl=ttl,
            request_id=request_id,
            actor_id=actor_id,
        )

        return {
            "key": record.key,
            "operation": record.operation,
            "payload_hash": record.payload_hash,
            "result": record.result,
            "created_at": record.created_at,
            "expires_at": record.expires_at,
            "request_id": record.request_id,
            "actor_id": record.actor_id,
        }

    def _delete_record(self, record_id: str) -> bool:
        """Delete an idempotency record by key."""
        return self.remove_key(record_id)

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List idempotency records with optional filtering and pagination."""
        if not self._connection:
            raise RuntimeError("Store not in transaction - cannot list records")

        try:
            current_time = time.time()

            # Build query with filters
            where_conditions = ["expires_at > ?"]
            params = [current_time]

            if filters:
                if "operation" in filters:
                    where_conditions.append("operation = ?")
                    params.append(filters["operation"])
                if "actor_id" in filters:
                    where_conditions.append("actor_id = ?")
                    params.append(filters["actor_id"])
                if "request_id" in filters:
                    where_conditions.append("request_id = ?")
                    params.append(filters["request_id"])

            where_clause = " AND ".join(where_conditions)

            # Build full query
            query = f"""
                SELECT key, operation, payload_hash, result, created_at, expires_at, request_id, actor_id
                FROM idempotency_keys
                WHERE {where_clause}
                ORDER BY created_at DESC
            """

            if limit:
                query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"

            cursor = self._connection.execute(query, params)
            rows = cursor.fetchall()

            records: List[Dict[str, Any]] = []
            for row in rows:
                records.append(
                    {
                        "key": row[0],
                        "operation": row[1],
                        "payload_hash": row[2],
                        "result": json.loads(row[3]) if row[3] else None,
                        "created_at": row[4],
                        "expires_at": row[5],
                        "request_id": row[6],
                        "actor_id": row[7],
                    }
                )

            return records

        except Exception as e:
            logger.error(f"Failed to list idempotency records: {e}")
            raise

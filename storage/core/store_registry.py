"""Store Registry Store - Dynamic store discovery and management.

This module implements storage for dynamically registering, discovering, and managing
storage stores within the MemoryOS system. Provides comprehensive store lifecycle tracking,
capability management, performance monitoring, and metadata management.

Key Features:
- Dynamic store registration and discovery
- Comprehensive store metadata management (type, backend, class, version)
- Capability tracking (transactions, indexing, search, encryption, etc.)
- Performance monitoring and metrics collection
- Schema management and migration tracking
- Dependency tracking and validation
- Security and compliance configuration
- Health status monitoring
- BaseStore compliance for transaction management
"""

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


@dataclass
class StoreRecord:
    """Complete store record with metadata and capabilities."""

    # Core identification
    store_id: str
    store_name: str
    store_type: str  # cognitive, infrastructure, application, system,
    # cache, index, archive, temporary
    storage_backend: str  # sqlite, file_system, memory, redis, postgresql, custom
    store_class: str
    store_module: str

    # Versioning
    base_store_version: str = "1.0.0"
    store_version: str = "1.0.0"
    store_description: Optional[str] = None

    # Configuration
    configuration: Dict[str, Any] = field(
        default_factory=lambda: {
            "default_config": {},
            "config_schema": {},
            "required_config": [],
            "connection_params": {
                "max_connections": 10,
                "connection_timeout": 30.0,
                "retry_attempts": 3,
            },
        }
    )

    # Capabilities
    capabilities: Dict[str, Any] = field(
        default_factory=lambda: {
            "supports_transactions": False,
            "supports_indexing": False,
            "supports_search": False,
            "supports_encryption": False,
            "supports_compression": False,
            "supports_replication": False,
            "supports_backup": False,
            "supports_schema_migration": False,
            "max_record_size": 0,
            "max_records": 0,
        }
    )

    # Schema management
    schemas: Dict[str, Any] = field(
        default_factory=lambda: {
            "primary_schema": {},
            "supported_schemas": [],
            "migration_history": [],
        }
    )

    # Performance characteristics
    performance: Dict[str, Any] = field(
        default_factory=lambda: {
            "read_throughput": 0.0,
            "write_throughput": 0.0,
            "latency_p95": 0.0,
            "latency_p99": 0.0,
            "memory_usage": 0,
            "disk_usage": 0,
            "cache_hit_ratio": 0.0,
        }
    )

    # Dependencies
    dependencies: List[Dict[str, Any]] = field(default_factory=lambda: [])

    # Registration metadata
    registration_metadata: Dict[str, Any] = field(
        default_factory=lambda: {
            "registered_at": time.time(),
            "registered_by": "system",
            "last_updated": time.time(),
            "update_count": 0,
            "tags": [],
            "environment": "development",
            "priority": 5,
        }
    )

    # Status
    status: Dict[str, Any] = field(
        default_factory=lambda: {
            "state": "registered",
            "last_state_change": time.time(),
            "error_message": None,
            "health_status": "unknown",
            "last_health_check": None,
            "connection_count": 0,
            "last_backup": None,
        }
    )

    # Metrics
    metrics: Dict[str, Any] = field(
        default_factory=lambda: {
            "total_records": 0,
            "storage_size": 0,
            "read_operations": 0,
            "write_operations": 0,
            "error_count": 0,
            "last_activity": None,
            "average_response_time": 0.0,
            "uptime": 0.0,
        }
    )

    # Security
    security: Dict[str, Any] = field(
        default_factory=lambda: {
            "encryption_at_rest": False,
            "encryption_in_transit": False,
            "access_control": [],
            "audit_logging": False,
            "pii_protection": False,
            "compliance_frameworks": [],
        }
    )


@dataclass
class StoreRegistryMetadata:
    """Registry-wide metadata and configuration."""

    registry_version: str = "1.0.0"
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    total_stores: int = 0
    active_stores: int = 0
    store_types: Dict[str, int] = field(default_factory=lambda: {})
    backend_distribution: Dict[str, int] = field(default_factory=lambda: {})
    configuration: Dict[str, Any] = field(
        default_factory=lambda: {
            "auto_discovery": True,
            "health_check_interval": 60,
            "cleanup_interval": 3600,
            "max_registered_stores": 1000,
            "enable_metrics_collection": True,
        }
    )


class StoreRegistryStore(BaseStore):
    """
    Store Registry Store for dynamic store lifecycle management.

    Provides storage and querying capabilities for store registration,
    discovery, capability tracking, and lifecycle state management.
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._valid_store_types = {
            "cognitive",
            "infrastructure",
            "application",
            "system",
            "cache",
            "index",
            "archive",
            "temporary",
        }
        self._valid_backends = {
            "sqlite",
            "file_system",
            "memory",
            "redis",
            "postgresql",
            "custom",
        }
        self._valid_states = {
            "registered",
            "initializing",
            "ready",
            "degraded",
            "maintenance",
            "error",
            "offline",
            "unregistered",
        }
        self._valid_health_statuses = {"healthy", "degraded", "unhealthy", "unknown"}

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for store registry data."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Store Registry Schema",
            "type": "object",
            "properties": {
                "store_record": {
                    "type": "object",
                    "required": [
                        "store_id",
                        "store_name",
                        "store_type",
                        "storage_backend",
                    ],
                    "properties": {
                        "store_id": {"type": "string", "minLength": 1},
                        "store_name": {"type": "string", "minLength": 1},
                        "store_type": {
                            "type": "string",
                            "enum": list(self._valid_store_types),
                        },
                        "storage_backend": {
                            "type": "string",
                            "enum": list(self._valid_backends),
                        },
                        "status": {
                            "type": "object",
                            "properties": {
                                "state": {
                                    "type": "string",
                                    "enum": list(self._valid_states),
                                },
                                "health_status": {
                                    "type": "string",
                                    "enum": list(self._valid_health_statuses),
                                },
                            },
                        },
                    },
                }
            },
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize the store registry tables."""
        # Store records table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS store_registry (
                store_id TEXT PRIMARY KEY,
                store_name TEXT NOT NULL UNIQUE,
                store_type TEXT NOT NULL,
                storage_backend TEXT NOT NULL,
                store_class TEXT NOT NULL,
                store_module TEXT NOT NULL,
                base_store_version TEXT NOT NULL DEFAULT '1.0.0',
                store_version TEXT NOT NULL DEFAULT '1.0.0',
                store_description TEXT,
                configuration TEXT NOT NULL DEFAULT '{}',
                capabilities TEXT NOT NULL DEFAULT '{}',
                schemas TEXT NOT NULL DEFAULT '{}',
                performance TEXT NOT NULL DEFAULT '{}',
                dependencies TEXT NOT NULL DEFAULT '[]',
                registration_metadata TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT '{}',
                metrics TEXT NOT NULL DEFAULT '{}',
                security TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """
        )

        # Registry metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS store_registry_metadata (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                registry_version TEXT NOT NULL DEFAULT '1.0.0',
                created_at REAL NOT NULL,
                last_updated REAL NOT NULL,
                total_stores INTEGER NOT NULL DEFAULT 0,
                active_stores INTEGER NOT NULL DEFAULT 0,
                store_types TEXT NOT NULL DEFAULT '{}',
                backend_distribution TEXT NOT NULL DEFAULT '{}',
                configuration TEXT NOT NULL DEFAULT '{}'
            )
        """
        )

        # Initialize metadata if not exists
        current_time = time.time()
        conn.execute(
            """
            INSERT OR IGNORE INTO store_registry_metadata (
                id, created_at, last_updated
            ) VALUES (1, ?, ?)
        """,
            (current_time, current_time),
        )

        # Indexes for performance
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_store_type ON store_registry(store_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_storage_backend ON store_registry(storage_backend)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_store_name ON store_registry(store_name)"
        )

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new store record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Generate store ID if not provided
        if "store_id" not in data:
            data["store_id"] = f"store-{uuid4().hex[:16]}"

        # Set timestamps
        current_time = time.time()
        data.setdefault("created_at", current_time)
        data["updated_at"] = current_time

        # Validate store type and backend
        if data.get("store_type") not in self._valid_store_types:
            raise ValueError(f"Invalid store_type: {data.get('store_type')}")

        if data.get("storage_backend") not in self._valid_backends:
            raise ValueError(f"Invalid storage_backend: {data.get('storage_backend')}")

        # Convert complex fields to JSON strings
        json_fields = [
            "configuration",
            "capabilities",
            "schemas",
            "performance",
            "dependencies",
            "registration_metadata",
            "status",
            "metrics",
            "security",
        ]
        for json_field in json_fields:
            if json_field in data and not isinstance(data[json_field], str):
                data[json_field] = json.dumps(data[json_field])

        # Insert record
        placeholders = ", ".join(["?" for _ in data.keys()])
        columns = ", ".join(data.keys())

        self._connection.execute(
            f"INSERT INTO store_registry ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )

        # Update metadata counts
        self._update_metadata_counts()

        result = self._read_record(data["store_id"])
        if result is None:
            raise RuntimeError(f"Failed to create store record {data['store_id']}")
        return result

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a store record by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            "SELECT * FROM store_registry WHERE store_id = ?", (record_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        # Convert row to dict and parse JSON fields
        columns = [desc[0] for desc in cursor.description]
        record = dict(zip(columns, row))

        # Parse JSON fields
        json_fields = [
            "configuration",
            "capabilities",
            "schemas",
            "performance",
            "dependencies",
            "registration_metadata",
            "status",
            "metrics",
            "security",
        ]
        for json_field in json_fields:
            if json_field in record and record[json_field]:
                try:
                    record[json_field] = json.loads(record[json_field])
                except json.JSONDecodeError:
                    logger.warning(
                        f"Failed to parse JSON field {json_field}: {record[json_field]}"
                    )
                    if json_field == "dependencies":
                        record[json_field] = []
                    else:
                        record[json_field] = {}

        return record

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing store record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Check if record exists
        existing = self._read_record(record_id)
        if not existing:
            raise ValueError(f"Store record {record_id} not found")

        # Update timestamp
        data["updated_at"] = time.time()

        # Validate store type and backend if provided
        if "store_type" in data and data["store_type"] not in self._valid_store_types:
            raise ValueError(f"Invalid store_type: {data['store_type']}")

        if (
            "storage_backend" in data
            and data["storage_backend"] not in self._valid_backends
        ):
            raise ValueError(f"Invalid storage_backend: {data['storage_backend']}")

        # Convert complex fields to JSON strings
        json_fields = [
            "configuration",
            "capabilities",
            "schemas",
            "performance",
            "dependencies",
            "registration_metadata",
            "status",
            "metrics",
            "security",
        ]
        for json_field in json_fields:
            if json_field in data and not isinstance(data[json_field], str):
                data[json_field] = json.dumps(data[json_field])

        # Build update query
        set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
        values = list(data.values()) + [record_id]

        self._connection.execute(
            f"UPDATE store_registry SET {set_clause} WHERE store_id = ?", values
        )

        # Update metadata counts if store type changed
        if "store_type" in data or "storage_backend" in data:
            self._update_metadata_counts()

        result = self._read_record(record_id)
        if result is None:
            raise RuntimeError(f"Failed to update store record {record_id}")
        return result

    def _delete_record(self, record_id: str) -> bool:
        """Delete a store record by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            "DELETE FROM store_registry WHERE store_id = ?", (record_id,)
        )

        deleted = cursor.rowcount > 0
        if deleted:
            self._update_metadata_counts()

        return deleted

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List store records with optional filtering and pagination."""
        if not self._connection:
            raise RuntimeError("No active connection")

        query = "SELECT * FROM store_registry"
        params: List[Any] = []

        # Build WHERE clause from filters
        if filters:
            conditions: List[str] = []
            for key, value in filters.items():
                if key in [
                    "store_type",
                    "storage_backend",
                    "store_name",
                    "store_class",
                ]:
                    conditions.append(f"{key} = ?")
                    params.append(value)
                elif key == "capabilities":
                    # Search in capabilities JSON
                    conditions.append("capabilities LIKE ?")
                    params.append(f'%"{value}": true%')
                elif key == "tags":
                    # Search in registration_metadata tags
                    conditions.append("registration_metadata LIKE ?")
                    params.append(f'%"{value}"%')
                elif key == "state":
                    # Search in status state
                    conditions.append("status LIKE ?")
                    params.append(f'%"state": "{value}"%')

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        # Add ordering
        query += " ORDER BY created_at DESC"

        # Add pagination
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        if offset:
            query += " OFFSET ?"
            params.append(offset)

        cursor = self._connection.execute(query, params)
        columns = [desc[0] for desc in cursor.description]

        records: List[Dict[str, Any]] = []
        for row in cursor.fetchall():
            record = dict(zip(columns, row))

            # Parse JSON fields
            json_fields = [
                "configuration",
                "capabilities",
                "schemas",
                "performance",
                "dependencies",
                "registration_metadata",
                "status",
                "metrics",
                "security",
            ]
            for json_field in json_fields:
                if json_field in record and record[json_field]:
                    try:
                        record[json_field] = json.loads(record[json_field])
                    except json.JSONDecodeError:
                        if json_field == "dependencies":
                            record[json_field] = []
                        else:
                            record[json_field] = {}

            records.append(record)

        return records

    def _update_metadata_counts(self) -> None:
        """Update registry metadata counts."""
        if not self._connection:
            return

        # Count total stores
        cursor = self._connection.execute("SELECT COUNT(*) FROM store_registry")
        total_stores = cursor.fetchone()[0]

        # Count active stores (ready state)
        cursor = self._connection.execute(
            'SELECT COUNT(*) FROM store_registry WHERE status LIKE \'%"state": "ready"%\''
        )
        active_stores = cursor.fetchone()[0]

        # Count stores by type
        cursor = self._connection.execute(
            "SELECT store_type, COUNT(*) FROM store_registry GROUP BY store_type"
        )
        store_types = dict(cursor.fetchall())

        # Count stores by backend
        cursor = self._connection.execute(
            "SELECT storage_backend, COUNT(*) FROM store_registry GROUP BY storage_backend"
        )
        backend_distribution = dict(cursor.fetchall())

        # Update metadata
        self._connection.execute(
            """
            UPDATE store_registry_metadata
            SET total_stores = ?, active_stores = ?, store_types = ?,
                backend_distribution = ?, last_updated = ?
            WHERE id = 1
        """,
            (
                total_stores,
                active_stores,
                json.dumps(store_types),
                json.dumps(backend_distribution),
                time.time(),
            ),
        )

    # Extended functionality for store management

    def register_store(self, store_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new store with validation."""
        # Ensure required fields
        required_fields = [
            "store_name",
            "store_type",
            "storage_backend",
            "store_class",
            "store_module",
        ]
        for required_field in required_fields:
            if required_field not in store_data:
                raise ValueError(f"Missing required field: {required_field}")

        # Set initial state
        if "status" not in store_data:
            store_data["status"] = {"state": "registered", "health_status": "unknown"}

        return self.create(store_data)

    def update_store_status(
        self,
        store_id: str,
        state: str,
        health_status: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update store status."""
        if state not in self._valid_states:
            raise ValueError(f"Invalid state: {state}")

        if health_status and health_status not in self._valid_health_statuses:
            raise ValueError(f"Invalid health_status: {health_status}")

        existing = self.read(store_id)
        if not existing:
            raise ValueError(f"Store {store_id} not found")

        status_update = existing.get("status", {})
        status_update["state"] = state
        status_update["last_state_change"] = time.time()

        if health_status:
            status_update["health_status"] = health_status
            status_update["last_health_check"] = time.time()

        if error_message:
            status_update["error_message"] = error_message

        return self.update(store_id, {"status": status_update})

    def find_stores_by_capability(
        self, capability: str, enabled: bool = True
    ) -> List[Dict[str, Any]]:
        """Find stores that support a specific capability."""
        return self.list(filters={"capabilities": capability} if enabled else {})

    def find_stores_by_type(self, store_type: str) -> List[Dict[str, Any]]:
        """Find stores of a specific type."""
        return self.list(filters={"store_type": store_type})

    def find_stores_by_backend(self, backend: str) -> List[Dict[str, Any]]:
        """Find stores using a specific backend."""
        return self.list(filters={"storage_backend": backend})

    def get_ready_stores(self) -> List[Dict[str, Any]]:
        """Get all stores in ready state."""
        return self.list(filters={"state": "ready"})

    def get_registry_metadata(self) -> Optional[Dict[str, Any]]:
        """Get registry metadata and statistics."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            "SELECT * FROM store_registry_metadata WHERE id = 1"
        )
        row = cursor.fetchone()

        if not row:
            return None

        columns = [desc[0] for desc in cursor.description]
        metadata = dict(zip(columns, row))

        # Parse JSON fields
        json_fields = ["store_types", "backend_distribution", "configuration"]
        for json_field in json_fields:
            if metadata.get(json_field):
                try:
                    metadata[json_field] = json.loads(metadata[json_field])
                except json.JSONDecodeError:
                    metadata[json_field] = {}

        return metadata

    def update_registry_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update registry configuration."""
        if not self._connection:
            raise RuntimeError("No active connection")

        existing_metadata = self.get_registry_metadata()
        if not existing_metadata:
            raise RuntimeError("Registry metadata not found")

        existing_config = existing_metadata.get("configuration", {})
        existing_config.update(config)

        self._connection.execute(
            "UPDATE store_registry_metadata SET configuration = ?, last_updated = ? WHERE id = 1",
            (json.dumps(existing_config), time.time()),
        )

        result = self.get_registry_metadata()
        if result is None:
            raise RuntimeError("Failed to update registry configuration")
        return result

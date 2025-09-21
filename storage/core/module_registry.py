"""Module Registry Store - Dynamic module discovery and lifecycle management.

This module implements storage for dynamically registering, discovering, and managing
modules within the MemoryOS system. Provides comprehensive module lifecycle tracking,
health monitoring, dependency management, and runtime statistics.

Key Features:
- Dynamic module registration and discovery
- Comprehensive lifecycle state management (registered, loading, starting, running,
  stopping, stopped, error, unregistered)
- Health monitoring with configurable check methods (ping, http, custom)
- Dependency tracking and validation
- Capability and interface management
- Performance metrics and status tracking
- Auto-discovery support with configurable isolation levels
- BaseStore compliance for transaction management
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from storage.core.base_store import BaseStore, StoreConfig

logger = logging.getLogger(__name__)


@dataclass
class ModuleRecord:
    """Complete module record with lifecycle, health, and metadata."""

    # Core identification
    module_id: str
    module_name: str
    module_type: str
    version: str

    # Lifecycle management
    state: str = "registered"  # registered, loading, starting, running,
    # stopping, stopped, error, unregistered
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None

    # Dependencies and capabilities
    dependencies: List[str] = field(default_factory=lambda: [])
    provides_capabilities: List[str] = field(default_factory=lambda: [])
    requires_capabilities: List[str] = field(default_factory=lambda: [])
    interfaces: Dict[str, Any] = field(default_factory=lambda: {})

    # Health monitoring
    health_check: Dict[str, Any] = field(
        default_factory=lambda: {
            "method": "ping",
            "interval_seconds": 30,
            "timeout_seconds": 5,
            "failure_threshold": 3,
            "recovery_threshold": 2,
        }
    )
    health_status: str = "unknown"  # healthy, unhealthy, unknown
    last_health_check: Optional[str] = None
    consecutive_failures: int = 0

    # Runtime configuration
    config: Dict[str, Any] = field(default_factory=lambda: {})
    environment: Dict[str, str] = field(default_factory=lambda: {})
    restart_policy: str = "on-failure"  # never, always, on-failure
    max_restarts: int = 3
    restart_count: int = 0

    # Metrics and status
    status: Dict[str, Any] = field(default_factory=lambda: {})
    metrics: Dict[str, Any] = field(
        default_factory=lambda: {
            "startup_time_ms": 0,
            "memory_usage_bytes": 0,
            "cpu_usage_percent": 0.0,
            "request_count": 0,
            "error_count": 0,
            "last_activity": None,
        }
    )

    # Auto-discovery
    discovery_enabled: bool = True
    isolation_level: str = "process"  # thread, process, container

    # Metadata
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    documentation_url: Optional[str] = None
    tags: List[str] = field(default_factory=lambda: [])


@dataclass
class RegistryMetadata:
    """Registry-wide metadata and statistics."""

    total_modules: int = 0
    active_modules: int = 0
    failed_modules: int = 0
    last_cleanup: Optional[str] = None
    auto_discovery_enabled: bool = True
    discovery_paths: List[str] = field(default_factory=lambda: [])
    health_check_interval: int = 30
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ModuleRegistryStore(BaseStore):
    """
    Module Registry Store for dynamic module lifecycle management.

    Provides storage and querying capabilities for module registration,
    discovery, health monitoring, and lifecycle state tracking.
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._valid_states = {
            "registered",
            "loading",
            "starting",
            "running",
            "stopping",
            "stopped",
            "error",
            "unregistered",
        }
        self._valid_module_types = {
            "cognitive",
            "storage",
            "api",
            "worker",
            "integration",
            "tool",
            "middleware",
            "extension",
        }
        self._valid_health_methods = {"ping", "http", "custom"}
        self._valid_isolation_levels = {"thread", "process", "container"}

    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for module registry data."""
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Module Registry Schema",
            "type": "object",
            "properties": {
                "module_record": {
                    "type": "object",
                    "required": ["module_id", "module_name", "module_type", "version"],
                    "properties": {
                        "module_id": {"type": "string", "minLength": 1},
                        "module_name": {"type": "string", "minLength": 1},
                        "module_type": {
                            "type": "string",
                            "enum": list(self._valid_module_types),
                        },
                        "version": {"type": "string", "minLength": 1},
                        "state": {"type": "string", "enum": list(self._valid_states)},
                        "health_status": {
                            "type": "string",
                            "enum": ["healthy", "unhealthy", "unknown"],
                        },
                        "isolation_level": {
                            "type": "string",
                            "enum": list(self._valid_isolation_levels),
                        },
                    },
                }
            },
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize the module registry tables."""
        # Module records table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS module_registry (
                module_id TEXT PRIMARY KEY,
                module_name TEXT NOT NULL,
                module_type TEXT NOT NULL,
                version TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'registered',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                stopped_at TEXT,
                dependencies TEXT NOT NULL DEFAULT '[]',
                provides_capabilities TEXT NOT NULL DEFAULT '[]',
                requires_capabilities TEXT NOT NULL DEFAULT '[]',
                interfaces TEXT NOT NULL DEFAULT '{}',
                health_check TEXT NOT NULL DEFAULT '{}',
                health_status TEXT NOT NULL DEFAULT 'unknown',
                last_health_check TEXT,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                config TEXT NOT NULL DEFAULT '{}',
                environment TEXT NOT NULL DEFAULT '{}',
                restart_policy TEXT NOT NULL DEFAULT 'on-failure',
                max_restarts INTEGER NOT NULL DEFAULT 3,
                restart_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT '{}',
                metrics TEXT NOT NULL DEFAULT '{}',
                discovery_enabled BOOLEAN NOT NULL DEFAULT 1,
                isolation_level TEXT NOT NULL DEFAULT 'process',
                description TEXT,
                author TEXT,
                license TEXT,
                documentation_url TEXT,
                tags TEXT NOT NULL DEFAULT '[]',
                UNIQUE(module_name, version)
            )
        """
        )

        # Registry metadata table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS registry_metadata (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_modules INTEGER NOT NULL DEFAULT 0,
                active_modules INTEGER NOT NULL DEFAULT 0,
                failed_modules INTEGER NOT NULL DEFAULT 0,
                last_cleanup TEXT,
                auto_discovery_enabled BOOLEAN NOT NULL DEFAULT 1,
                discovery_paths TEXT NOT NULL DEFAULT '[]',
                health_check_interval INTEGER NOT NULL DEFAULT 30,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """
        )

        # Initialize metadata if not exists
        conn.execute(
            """
            INSERT OR IGNORE INTO registry_metadata (
                id, created_at, updated_at
            ) VALUES (
                1, ?, ?
            )
        """,
            (
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Indexes for performance
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_module_type ON module_registry(module_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_module_state ON module_registry(state)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_module_health ON module_registry(health_status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_module_name ON module_registry(module_name)"
        )

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new module record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Generate module ID if not provided
        if "module_id" not in data:
            data["module_id"] = f"mod-{uuid4().hex[:8]}"

        # Set timestamps
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data["updated_at"] = now

        # Validate state and type
        if data.get("state", "registered") not in self._valid_states:
            raise ValueError(f"Invalid state: {data.get('state')}")

        if data.get("module_type") not in self._valid_module_types:
            raise ValueError(f"Invalid module_type: {data.get('module_type')}")

        # Convert lists and dicts to JSON strings
        json_fields = [
            "dependencies",
            "provides_capabilities",
            "requires_capabilities",
            "interfaces",
            "health_check",
            "config",
            "environment",
            "status",
            "metrics",
            "tags",
        ]
        for json_field in json_fields:
            if json_field in data and not isinstance(data[json_field], str):
                data[json_field] = json.dumps(data[json_field])

        # Insert record
        placeholders = ", ".join(["?" for _ in data.keys()])
        columns = ", ".join(data.keys())

        self._connection.execute(
            f"INSERT INTO module_registry ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )

        # Update metadata counts
        self._update_metadata_counts()

        result = self._read_record(data["module_id"])
        if result is None:
            raise RuntimeError(f"Failed to create module record {data['module_id']}")
        return result

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a module record by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            "SELECT * FROM module_registry WHERE module_id = ?", (record_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        # Convert row to dict and parse JSON fields
        columns = [desc[0] for desc in cursor.description]
        record = dict(zip(columns, row))

        # Parse JSON fields
        json_fields = [
            "dependencies",
            "provides_capabilities",
            "requires_capabilities",
            "interfaces",
            "health_check",
            "config",
            "environment",
            "status",
            "metrics",
            "tags",
        ]
        for json_field in json_fields:
            if json_field in record and record[json_field]:
                try:
                    record[json_field] = json.loads(record[json_field])
                except json.JSONDecodeError:
                    logger.warning(
                        f"Failed to parse JSON field {json_field}: {record[json_field]}"
                    )
                    dict_fields = [
                        "interfaces",
                        "health_check",
                        "config",
                        "environment",
                        "status",
                        "metrics",
                    ]
                    record[json_field] = {} if json_field in dict_fields else []

        return record

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing module record."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Check if record exists
        existing = self._read_record(record_id)
        if not existing:
            raise ValueError(f"Module record {record_id} not found")

        # Update timestamp
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Validate state and type if provided
        if "state" in data and data["state"] not in self._valid_states:
            raise ValueError(f"Invalid state: {data['state']}")

        if (
            "module_type" in data
            and data["module_type"] not in self._valid_module_types
        ):
            raise ValueError(f"Invalid module_type: {data['module_type']}")

        # Convert lists and dicts to JSON strings
        json_fields = [
            "dependencies",
            "provides_capabilities",
            "requires_capabilities",
            "interfaces",
            "health_check",
            "config",
            "environment",
            "status",
            "metrics",
            "tags",
        ]
        for json_field in json_fields:
            if json_field in data and not isinstance(data[json_field], str):
                data[json_field] = json.dumps(data[json_field])

        # Build update query
        set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
        values = list(data.values()) + [record_id]

        self._connection.execute(
            f"UPDATE module_registry SET {set_clause} WHERE module_id = ?", values
        )

        # Update metadata counts if state changed
        if "state" in data:
            self._update_metadata_counts()

        result = self._read_record(record_id)
        if result is None:
            raise RuntimeError(f"Failed to update module record {record_id}")
        return result

    def _delete_record(self, record_id: str) -> bool:
        """Delete a module record by ID."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            "DELETE FROM module_registry WHERE module_id = ?", (record_id,)
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
        """List module records with optional filtering and pagination."""
        if not self._connection:
            raise RuntimeError("No active connection")

        query = "SELECT * FROM module_registry"
        params: List[Any] = []

        # Build WHERE clause from filters
        if filters:
            conditions: List[str] = []
            for key, value in filters.items():
                if key in [
                    "module_type",
                    "state",
                    "health_status",
                    "module_name",
                    "version",
                ]:
                    conditions.append(f"{key} = ?")
                    params.append(value)
                elif key == "capabilities":
                    # Search in provides_capabilities
                    conditions.append("provides_capabilities LIKE ?")
                    params.append(f'%"{value}"%')
                elif key == "tags":
                    # Search in tags array
                    conditions.append("tags LIKE ?")
                    params.append(f'%"{value}"%')

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
                "dependencies",
                "provides_capabilities",
                "requires_capabilities",
                "interfaces",
                "health_check",
                "config",
                "environment",
                "status",
                "metrics",
                "tags",
            ]
            for json_field in json_fields:
                if json_field in record and record[json_field]:
                    try:
                        record[json_field] = json.loads(record[json_field])
                    except json.JSONDecodeError:
                        dict_fields = [
                            "interfaces",
                            "health_check",
                            "config",
                            "environment",
                            "status",
                            "metrics",
                        ]
                        record[json_field] = {} if json_field in dict_fields else []

            records.append(record)

        return records

    def _update_metadata_counts(self) -> None:
        """Update registry metadata counts."""
        if not self._connection:
            return

        # Count total modules
        cursor = self._connection.execute("SELECT COUNT(*) FROM module_registry")
        total_modules = cursor.fetchone()[0]

        # Count active modules (running state)
        cursor = self._connection.execute(
            "SELECT COUNT(*) FROM module_registry WHERE state = 'running'"
        )
        active_modules = cursor.fetchone()[0]

        # Count failed modules (error state)
        cursor = self._connection.execute(
            "SELECT COUNT(*) FROM module_registry WHERE state = 'error'"
        )
        failed_modules = cursor.fetchone()[0]

        # Update metadata
        self._connection.execute(
            """
            UPDATE registry_metadata
            SET total_modules = ?, active_modules = ?, failed_modules = ?, updated_at = ?
            WHERE id = 1
        """,
            (
                total_modules,
                active_modules,
                failed_modules,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    # Extended functionality for module management

    def register_module(self, module_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new module with validation."""
        # Ensure required fields
        required_fields = ["module_name", "module_type", "version"]
        for required_field in required_fields:
            if required_field not in module_data:
                raise ValueError(f"Missing required field: {required_field}")

        # Set initial state
        module_data.setdefault("state", "registered")
        module_data.setdefault("health_status", "unknown")

        return self.create(module_data)

    def update_module_state(
        self, module_id: str, new_state: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update module state with optional metadata."""
        if new_state not in self._valid_states:
            raise ValueError(f"Invalid state: {new_state}")

        update_data = {"state": new_state}

        # Add state-specific timestamps
        now = datetime.now(timezone.utc).isoformat()
        if new_state in ["running"]:
            update_data["started_at"] = now
        elif new_state in ["stopped", "error"]:
            update_data["stopped_at"] = now

        # Add any additional metadata
        if metadata:
            update_data.update(metadata)

        return self.update(module_id, update_data)

    def update_health_status(
        self, module_id: str, health_status: str, check_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update module health status."""
        if health_status not in ["healthy", "unhealthy", "unknown"]:
            raise ValueError(f"Invalid health_status: {health_status}")

        update_data = {
            "health_status": health_status,
            "last_health_check": check_time or datetime.now(timezone.utc).isoformat(),
        }

        # Update consecutive failures
        if health_status == "unhealthy":
            existing = self.read(module_id)
            if existing:
                current_failures = existing.get("consecutive_failures", 0)
                update_data["consecutive_failures"] = str(current_failures + 1)
        else:
            update_data["consecutive_failures"] = "0"

        return self.update(module_id, update_data)

    def find_modules_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Find modules that provide a specific capability."""
        return self.list(filters={"capabilities": capability})

    def find_modules_by_type(self, module_type: str) -> List[Dict[str, Any]]:
        """Find modules of a specific type."""
        return self.list(filters={"module_type": module_type})

    def get_running_modules(self) -> List[Dict[str, Any]]:
        """Get all currently running modules."""
        return self.list(filters={"state": "running"})

    def get_failed_modules(self) -> List[Dict[str, Any]]:
        """Get all modules in error state."""
        return self.list(filters={"state": "error"})

    def get_registry_metadata(self) -> Optional[Dict[str, Any]]:
        """Get registry metadata and statistics."""
        if not self._connection:
            raise RuntimeError("No active connection")

        cursor = self._connection.execute(
            "SELECT * FROM registry_metadata WHERE id = 1"
        )
        row = cursor.fetchone()

        if not row:
            return None

        columns = [desc[0] for desc in cursor.description]
        metadata = dict(zip(columns, row))

        # Parse discovery_paths JSON
        if metadata.get("discovery_paths"):
            try:
                metadata["discovery_paths"] = json.loads(metadata["discovery_paths"])
            except json.JSONDecodeError:
                metadata["discovery_paths"] = []

        return metadata

    def update_registry_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Update registry metadata."""
        if not self._connection:
            raise RuntimeError("No active connection")

        # Convert discovery_paths to JSON if needed
        if "discovery_paths" in metadata and not isinstance(
            metadata["discovery_paths"], str
        ):
            metadata["discovery_paths"] = json.dumps(metadata["discovery_paths"])

        metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Build update query
        set_clause = ", ".join([f"{key} = ?" for key in metadata.keys()])
        values = list(metadata.values())

        self._connection.execute(
            f"UPDATE registry_metadata SET {set_clause} WHERE id = 1", values
        )

        result = self.get_registry_metadata()
        if result is None:
            raise RuntimeError("Failed to update registry metadata")
        return result

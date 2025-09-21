"""Base Store - Abstract base class for all storage implementations"""

import hashlib
import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Import storage core exceptions
from .exceptions import PolicyViolation
from .unit_of_work import StoreProtocol

# Import policy config and redactor conditionally to avoid dependency issues
try:
    from policy.config.config_loader import PolicyConfig, load_policy_config
    from policy.redactor import Redactor
except ImportError:
    load_policy_config = None
    PolicyConfig = None
    Redactor = None

# Import audit logging conditionally
try:
    from observability.audit import (
        AuditActor,
        AuditOutcome,
        AuditResource,
        get_audit_logger,
    )

    _audit_available = True
except ImportError:
    _audit_available = False
    AuditActor = None
    AuditOutcome = None
    AuditResource = None
    get_audit_logger = None

# Import metrics conditionally
try:
    import time

    from observability.metrics import record_storage, storage_op_duration_ms

    _metrics_available = True

    def _now_ms() -> int:
        return int(time.time() * 1000)

except ImportError:
    _metrics_available = False
    storage_op_duration_ms = None
    record_storage = None

    def _now_ms() -> int:
        return 0


logger = logging.getLogger(__name__)


def instrument_storage_operation(operation: str):
    """Decorator to instrument storage operations with metrics and performance monitoring."""

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            start_time = _now_ms()
            store_name = getattr(self, "name", self.__class__.__name__)
            success = True
            error_type = None
            caught_exception = None

            # Performance monitoring
            try:
                from observability.performance import get_performance_monitor

                monitor = get_performance_monitor(store_name)
                with monitor.transaction(operation):
                    result = func(self, *args, **kwargs)
                    return result
            except ImportError:
                # Fallback to basic monitoring if performance module unavailable
                try:
                    result = func(self, *args, **kwargs)
                    return result
                except sqlite3.IntegrityError as e:
                    success = False
                    error_type = "integrity_error"
                    caught_exception = e
                    raise
                except sqlite3.OperationalError as e:
                    success = False
                    error_type = "operational_error"
                    caught_exception = e
                    raise
                except Exception as e:
                    success = False
                    error_type = type(e).__name__.lower()
                    caught_exception = e
                    raise
                finally:
                    if _metrics_available and record_storage:
                        duration = _now_ms() - start_time
                        record_storage(store_name, operation, duration, success)

                        # Record error metrics if available
                        if not success and error_type and caught_exception:
                            try:
                                from observability.metrics import record_detailed_error

                                record_detailed_error(
                                    store_name, operation, caught_exception
                                )
                            except ImportError:
                                # Fallback to basic error recording
                                try:
                                    from observability.metrics import (
                                        record_storage_error,
                                    )

                                    record_storage_error(
                                        store_name, operation, error_type
                                    )
                                except ImportError:
                                    pass

        return wrapper

    return decorator


@dataclass
class ValidationResult:
    """Result of schema validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str] = field(default_factory=list)


@dataclass
class StoreConfig:
    """Configuration for store instances."""

    db_path: str = "family.db"
    enable_wal: bool = True
    enable_foreign_keys: bool = True
    cache_size: int = 10000
    timeout: float = 30.0
    schema_validation: bool = True
    auto_migrate: bool = True


class BaseStore(ABC, StoreProtocol):
    def __del__(self):
        """Ensure connection cleanup on deletion (especially for Windows)."""
        if hasattr(self, "_connection") and self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection in __del__: {e}")
            self._connection = None

    def __enter__(self):
        """Support context manager usage for standalone stores."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure clean resource management on context exit."""
        if hasattr(self, "_connection") and self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection in __exit__: {e}")
            self._connection = None

    """
    Abstract base class for all storage implementations.

    Provides common functionality including:
    - Connection management
    - Schema validation
    - Transaction lifecycle
    - Error handling patterns
    - Performance monitoring hooks
    """

    def __init__(self, config: Optional[StoreConfig] = None):
        self.config = config or StoreConfig()
        self._store_name = self.__class__.__name__.replace("Store", "").lower()
        self._schema: Optional[Dict[str, Any]] = None
        self._connection: Optional[sqlite3.Connection] = None
        self._in_transaction = False
        self._initialized = False

        # Performance tracking
        self._operation_count = 0
        self._error_count = 0

        # Redaction support
        self._redactor = None
        if Redactor:
            self._redactor = Redactor()
        self._redaction_cache: Dict[str, Dict[str, Any]] = {}

        # Policy configuration
        self._policy_config = None
        if load_policy_config:
            try:
                self._policy_config = load_policy_config(
                    "policy/config/policy.example.yaml"
                )
            except Exception as e:
                logger.warning(f"Failed to load policy configuration: {e}")
                self._policy_config = None

    # StoreProtocol implementation

    def get_store_name(self) -> str:
        """Get the name of this store for tracking and metrics."""
        return self._store_name

    def begin_transaction(self, conn: sqlite3.Connection) -> None:
        """Begin a transaction on the given connection."""
        if self._in_transaction:
            logger.warning(f"Store {self._store_name} already in transaction")
            return

        self._connection = conn
        self._in_transaction = True

        # Ensure store is initialized
        if not self._initialized:
            self._initialize_schema(conn)
            self._initialized = True

        self._on_transaction_begin(conn)
        logger.debug(f"Store {self._store_name} began transaction")

    def commit_transaction(self, conn: sqlite3.Connection) -> None:
        """Commit the transaction on the given connection."""
        if not self._in_transaction:
            logger.warning(f"Store {self._store_name} not in transaction")
            return

        try:
            self._on_transaction_commit(conn)
            self._in_transaction = False
            self._connection = None
            logger.debug(f"Store {self._store_name} committed transaction")
        except Exception as e:
            logger.error(f"Failed to commit store {self._store_name}: {e}")
            raise

    def rollback_transaction(self, conn: sqlite3.Connection) -> None:
        """Rollback the transaction on the given connection."""
        if not self._in_transaction:
            logger.warning(f"Store {self._store_name} not in transaction")
            return

        try:
            self._on_transaction_rollback(conn)
            self._in_transaction = False
            self._connection = None
            logger.debug(f"Store {self._store_name} rolled back transaction")
        except Exception as e:
            logger.error(f"Failed to rollback store {self._store_name}: {e}")
            # Don't re-raise rollback errors

    def get_connection_requirements(self) -> Dict[str, Any]:
        """Get any special connection requirements for this store."""
        return {
            "timeout": self.config.timeout,
            "enable_wal": self.config.enable_wal,
            "enable_foreign_keys": self.config.enable_foreign_keys,
            "cache_size": self.config.cache_size,
        }

    # Abstract methods for subclasses

    @abstractmethod
    def _get_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for this store's data."""
        pass

    @abstractmethod
    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema and tables."""
        pass

    @abstractmethod
    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record in the store."""
        pass

    @abstractmethod
    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a record by ID."""
        pass

    @abstractmethod
    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing record."""
        pass

    @abstractmethod
    def _delete_record(self, record_id: str) -> bool:
        """Delete a record by ID."""
        pass

    @abstractmethod
    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List records with optional filtering and pagination."""
        pass

    # Transaction lifecycle hooks (optional override)

    def _on_transaction_begin(self, conn: sqlite3.Connection) -> None:
        """Called when transaction begins. Override for custom logic."""
        pass

    def _on_transaction_commit(self, conn: sqlite3.Connection) -> None:
        """Called before transaction commits. Override for custom logic."""
        pass

    def _on_transaction_rollback(self, conn: sqlite3.Connection) -> None:
        """Called before transaction rolls back. Override for custom logic."""
        pass

    # Public CRUD interface

    def _check_policy_band(
        self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Check policy band restrictions for write operations."""
        if not context:
            return  # No policy context provided, allow operation

        band = context.get("policy_band", "GREEN")
        operation = context.get("operation", "WRITE")
        user_role = context.get("user_role", "user")

        # Use configured policy bands if available
        if self._policy_config and band in self._policy_config.policy_bands:
            band_config = self._policy_config.policy_bands[band]

            # Check if writes are allowed
            if not band_config.write_allowed:
                if band_config.system_only and user_role in ["system"]:
                    # System users can write to system-only bands
                    return
                elif band_config.override_required and context.get("override_token"):
                    # Override token provided for restricted bands
                    return
                else:
                    # Write not allowed
                    raise PolicyViolation(
                        f"{band} band - writes prohibited",
                        band=band,
                        operation=operation,
                        context=context,
                    )
        else:
            # Fallback to hardcoded logic for backward compatibility
            if band == "BLACK":
                # BLACK band - only system users can write
                if user_role not in ["system"]:
                    raise PolicyViolation(
                        "BLACK band - writes prohibited for non-system users",
                        band=band,
                        operation=operation,
                        context=context,
                    )

            if band == "RED" and not context.get("override_token"):
                raise PolicyViolation(
                    "RED band requires override token",
                    band=band,
                    operation=operation,
                    context=context,
                )

    def _apply_redaction(
        self, record: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply redaction based on policy band and user context."""
        if not self._redactor:
            return record

        # Extract band and user context
        band = context.get("policy_band", "GREEN")
        user_role = context.get("user_role", "user")
        data_sensitivity = context.get("data_sensitivity", "low")

        # Check cache for redacted version
        cache_key = f"{band}:{user_role}:{data_sensitivity}:{hash(str(record))}"
        if cache_key in self._redaction_cache:
            return self._redaction_cache[cache_key]

        # Apply redaction based on band configuration
        redacted_record = record.copy()

        # Use configured policy bands if available
        if self._policy_config and band in self._policy_config.policy_bands:
            band_config = self._policy_config.policy_bands[band]

            # Apply redaction categories from configuration
            if band_config.read_redaction and user_role not in ["admin", "system"]:
                # Special handling for BLACK band - return minimal record
                if band == "BLACK":
                    redacted_record = {
                        "id": record.get("id"),
                        "redacted": True,
                        "message": "Content redacted due to security policy",
                    }
                else:
                    # Use all redaction categories at once for better performance
                    if Redactor:
                        redactor = Redactor(band_config.read_redaction)
                        for key, value in redacted_record.items():
                            if isinstance(value, str):
                                result = redactor.redact_text(value)
                                redacted_record[key] = result.text
        else:
            # Fallback to hardcoded logic for backward compatibility
            if band == "GREEN":
                # GREEN: No redaction needed
                pass
            elif band == "AMBER":
                # AMBER: Light redaction for non-privileged users
                if user_role not in ["admin", "operator"]:
                    # Apply redaction with multiple categories at once
                    if Redactor:
                        redactor = Redactor(["pii.email", "pii.phone"])
                        for key, value in redacted_record.items():
                            if isinstance(value, str):
                                result = redactor.redact_text(value)
                                redacted_record[key] = result.text
            elif band == "RED":
                # RED: Heavy redaction for most users
                if user_role not in ["admin"]:
                    # Apply redaction with multiple categories at once
                    if Redactor:
                        redactor = Redactor(
                            ["pii.email", "pii.phone", "pii.cc", "pii.ssn"]
                        )
                        for key, value in redacted_record.items():
                            if isinstance(value, str):
                                result = redactor.redact_text(value)
                                redacted_record[key] = result.text
            elif band == "BLACK":
                # BLACK: Maximum redaction for all users except system
                if user_role not in ["system"]:
                    # For BLACK band, return minimal record with redaction markers
                    redacted_record = {
                        "id": record.get("id"),
                        "redacted": True,
                        "message": "Content redacted due to security policy",
                    }
                    # Apply all PII redaction types to any remaining data
                    pii_types = [
                        "pii.email",
                        "pii.phone",
                        "pii.cc",
                        "pii.ssn",
                        "pii.ip",
                    ]
                    for pii_type in pii_types:
                        key_policies = {}
                        for key, value in redacted_record.items():
                            if isinstance(value, str):
                                key_policies[key] = pii_type
                        if key_policies:
                            redacted_record = self._redactor.redact_payload(
                                redacted_record, key_policies
                            )

        # Cache the redacted result
        self._redaction_cache[cache_key] = redacted_record
        return redacted_record

    def _clear_redaction_cache(self):
        """Clear redaction cache."""
        self._redaction_cache.clear()

    @instrument_storage_operation("create")
    def create(
        self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new record with validation and wire receipt generation."""
        if not self._in_transaction:
            raise RuntimeError(f"Store {self._store_name} not in transaction")

        # Check policy band restrictions
        if context:
            self._check_policy_band(data, context)

        # Validate data if schema validation is enabled
        if self.config.schema_validation:
            validation = self.validate_data(data)
            if not validation.is_valid:
                raise ValueError(f"Invalid data: {validation.errors}")

        try:
            result = self._create_record(data)
            self._operation_count += 1

            # Audit logging - success case
            if (
                _audit_available
                and get_audit_logger
                and AuditActor
                and AuditResource
                and AuditOutcome
            ):
                audit_logger = get_audit_logger()
                actor = AuditActor(
                    actor_id=context.get("user_id", "system") if context else "system",
                    actor_type=(
                        "USER" if context and context.get("user_id") else "SYSTEM"
                    ),
                    device_id=context.get("device_id") if context else None,
                    session_id=context.get("session_id") if context else None,
                )
                resource = AuditResource(
                    resource_type="RECORD",
                    resource_id=result.get("id", "unknown"),
                    store_name=self.__class__.__name__,
                    space_id=context.get("space_id") if context else None,
                )
                outcome = AuditOutcome(
                    result="SUCCESS",
                    records_affected=1,
                )

                # Use async context if available, otherwise log synchronously
                try:
                    import asyncio

                    asyncio.get_running_loop()
                    asyncio.create_task(
                        audit_logger.log_operation(
                            operation="CREATE",
                            actor=actor,
                            resource=resource,
                            outcome=outcome,
                            context=context or {},
                        )
                    )
                except RuntimeError:
                    # No event loop running, skip audit logging for now
                    pass

            # Wire receipt generation after write
            uow = getattr(self, "uow", None)
            receipts_store = getattr(uow, "receipts_store", None) if uow else None
            if uow and receipts_store:
                receipt_hash = self._compute_hash(result)
                # Prepare for signature field (to be implemented later)
                receipts_store.create_receipt(
                    event_id=result.get("id"),
                    operation="CREATE",
                    store_name=self.__class__.__name__,
                    hash=receipt_hash,
                    signature="TODO: sign",  # Placeholder for future signing
                )
            return result
        except Exception as e:
            self._error_count += 1

            # Audit logging - failure case
            if (
                _audit_available
                and get_audit_logger
                and AuditActor
                and AuditResource
                and AuditOutcome
            ):
                audit_logger = get_audit_logger()
                actor = AuditActor(
                    actor_id=context.get("user_id", "system") if context else "system",
                    actor_type=(
                        "USER" if context and context.get("user_id") else "SYSTEM"
                    ),
                    device_id=context.get("device_id") if context else None,
                    session_id=context.get("session_id") if context else None,
                )
                resource = AuditResource(
                    resource_type="RECORD",
                    resource_id="unknown",
                    store_name=self.__class__.__name__,
                    space_id=context.get("space_id") if context else None,
                )
                outcome = AuditOutcome(
                    result="FAILURE",
                    error_message=str(e),
                )

                # Use async context if available, otherwise log synchronously
                try:
                    import asyncio

                    asyncio.get_running_loop()
                    asyncio.create_task(
                        audit_logger.log_operation(
                            operation="CREATE",
                            actor=actor,
                            resource=resource,
                            outcome=outcome,
                            context=context or {},
                        )
                    )
                except RuntimeError:
                    # No event loop running, skip audit logging for now
                    pass

            logger.error(f"Failed to create record in {self._store_name}: {e}")
            raise

    def _compute_hash(self, record: Dict[str, Any]) -> str:
        """Compute SHA256 hash of canonical JSON for receipt integrity."""
        canonical_json = json.dumps(record, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def read(
        self, record_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Read a record by ID with optional redaction based on policy context."""
        if not self._in_transaction:
            raise RuntimeError(f"Store {self._store_name} not in transaction")

        try:
            result = self._read_record(record_id)
            self._operation_count += 1

            # Apply redaction if context provided and result exists
            if result and context:
                result = self._apply_redaction(result, context)

            # Audit logging - success case (even if record not found)
            if (
                _audit_available
                and get_audit_logger
                and AuditActor
                and AuditResource
                and AuditOutcome
            ):
                audit_logger = get_audit_logger()
                actor = AuditActor(
                    actor_id=context.get("user_id", "system") if context else "system",
                    actor_type=(
                        "USER" if context and context.get("user_id") else "SYSTEM"
                    ),
                    device_id=context.get("device_id") if context else None,
                    session_id=context.get("session_id") if context else None,
                )
                resource = AuditResource(
                    resource_type="RECORD",
                    resource_id=record_id,
                    store_name=self.__class__.__name__,
                    space_id=context.get("space_id") if context else None,
                )
                outcome = AuditOutcome(
                    result="SUCCESS",
                    records_affected=1 if result else 0,
                )

                # Use async context if available, otherwise log synchronously
                try:
                    import asyncio

                    asyncio.get_running_loop()
                    asyncio.create_task(
                        audit_logger.log_operation(
                            operation="READ",
                            actor=actor,
                            resource=resource,
                            outcome=outcome,
                            context=context or {},
                        )
                    )
                except RuntimeError:
                    # No event loop running, skip audit logging for now
                    pass

            return result
        except Exception as e:
            self._error_count += 1

            # Audit logging - failure case
            if (
                _audit_available
                and get_audit_logger
                and AuditActor
                and AuditResource
                and AuditOutcome
            ):
                audit_logger = get_audit_logger()
                actor = AuditActor(
                    actor_id=context.get("user_id", "system") if context else "system",
                    actor_type=(
                        "USER" if context and context.get("user_id") else "SYSTEM"
                    ),
                    device_id=context.get("device_id") if context else None,
                    session_id=context.get("session_id") if context else None,
                )
                resource = AuditResource(
                    resource_type="RECORD",
                    resource_id=record_id,
                    store_name=self.__class__.__name__,
                    space_id=context.get("space_id") if context else None,
                )
                outcome = AuditOutcome(
                    result="FAILURE",
                    error_message=str(e),
                )

                # Use async context if available, otherwise log synchronously
                try:
                    import asyncio

                    asyncio.get_running_loop()
                    asyncio.create_task(
                        audit_logger.log_operation(
                            operation="READ",
                            actor=actor,
                            resource=resource,
                            outcome=outcome,
                            context=context or {},
                        )
                    )
                except RuntimeError:
                    # No event loop running, skip audit logging for now
                    pass

            logger.error(
                f"Failed to read record {record_id} from {self._store_name}: {e}"
            )
            raise

    @instrument_storage_operation("update")
    def update(
        self,
        record_id: str,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update an existing record with validation."""
        if not self._in_transaction:
            raise RuntimeError(f"Store {self._store_name} not in transaction")

        # Check policy band restrictions
        if context:
            self._check_policy_band(data, context)

        # Validate data if schema validation is enabled
        if self.config.schema_validation:
            validation = self.validate_data(data, allow_partial=True)
            if not validation.is_valid:
                raise ValueError(f"Invalid data: {validation.errors}")

        try:
            result = self._update_record(record_id, data)
            self._operation_count += 1

            # Audit logging - success case
            if (
                _audit_available
                and get_audit_logger
                and AuditActor
                and AuditResource
                and AuditOutcome
            ):
                audit_logger = get_audit_logger()
                actor = AuditActor(
                    actor_id=context.get("user_id", "system") if context else "system",
                    actor_type=(
                        "USER" if context and context.get("user_id") else "SYSTEM"
                    ),
                    device_id=context.get("device_id") if context else None,
                    session_id=context.get("session_id") if context else None,
                )
                resource = AuditResource(
                    resource_type="RECORD",
                    resource_id=record_id,
                    store_name=self.__class__.__name__,
                    space_id=context.get("space_id") if context else None,
                )
                outcome = AuditOutcome(
                    result="SUCCESS",
                    records_affected=1,
                )

                # Use async context if available, otherwise log synchronously
                try:
                    import asyncio

                    asyncio.get_running_loop()
                    asyncio.create_task(
                        audit_logger.log_operation(
                            operation="UPDATE",
                            actor=actor,
                            resource=resource,
                            outcome=outcome,
                            context=context or {},
                        )
                    )
                except RuntimeError:
                    # No event loop running, skip audit logging for now
                    pass

            return result
        except Exception as e:
            self._error_count += 1

            # Audit logging - failure case
            if (
                _audit_available
                and get_audit_logger
                and AuditActor
                and AuditResource
                and AuditOutcome
            ):
                audit_logger = get_audit_logger()
                actor = AuditActor(
                    actor_id=context.get("user_id", "system") if context else "system",
                    actor_type=(
                        "USER" if context and context.get("user_id") else "SYSTEM"
                    ),
                    device_id=context.get("device_id") if context else None,
                    session_id=context.get("session_id") if context else None,
                )
                resource = AuditResource(
                    resource_type="RECORD",
                    resource_id=record_id,
                    store_name=self.__class__.__name__,
                    space_id=context.get("space_id") if context else None,
                )
                outcome = AuditOutcome(
                    result="FAILURE",
                    error_message=str(e),
                )

                # Use async context if available, otherwise log synchronously
                try:
                    import asyncio

                    asyncio.get_running_loop()
                    asyncio.create_task(
                        audit_logger.log_operation(
                            operation="UPDATE",
                            actor=actor,
                            resource=resource,
                            outcome=outcome,
                            context=context or {},
                        )
                    )
                except RuntimeError:
                    # No event loop running, skip audit logging for now
                    pass

            logger.error(
                f"Failed to update record {record_id} in {self._store_name}: {e}"
            )
            raise
            logger.error(
                f"Failed to update record {record_id} in {self._store_name}: {e}"
            )
            raise

    @instrument_storage_operation("delete")
    def delete(self, record_id: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Delete a record by ID."""
        if not self._in_transaction:
            raise RuntimeError(f"Store {self._store_name} not in transaction")

        # Check policy band restrictions
        if context:
            # For delete operations, we pass empty data but maintain context
            delete_context = {**context, "operation": "DELETE"}
            self._check_policy_band({}, delete_context)

        try:
            result = self._delete_record(record_id)
            self._operation_count += 1

            # Audit logging - success case
            if (
                _audit_available
                and get_audit_logger
                and AuditActor
                and AuditResource
                and AuditOutcome
            ):
                audit_logger = get_audit_logger()
                actor = AuditActor(
                    actor_id=context.get("user_id", "system") if context else "system",
                    actor_type=(
                        "USER" if context and context.get("user_id") else "SYSTEM"
                    ),
                    device_id=context.get("device_id") if context else None,
                    session_id=context.get("session_id") if context else None,
                )
                resource = AuditResource(
                    resource_type="RECORD",
                    resource_id=record_id,
                    store_name=self.__class__.__name__,
                    space_id=context.get("space_id") if context else None,
                )
                outcome = AuditOutcome(
                    result="SUCCESS",
                    records_affected=1 if result else 0,
                )

                # Use async context if available, otherwise log synchronously
                try:
                    import asyncio

                    asyncio.get_running_loop()
                    asyncio.create_task(
                        audit_logger.log_operation(
                            operation="DELETE",
                            actor=actor,
                            resource=resource,
                            outcome=outcome,
                            context=context or {},
                        )
                    )
                except RuntimeError:
                    # No event loop running, skip audit logging for now
                    pass

            return result
        except Exception as e:
            self._error_count += 1

            # Audit logging - failure case
            if (
                _audit_available
                and get_audit_logger
                and AuditActor
                and AuditResource
                and AuditOutcome
            ):
                audit_logger = get_audit_logger()
                actor = AuditActor(
                    actor_id=context.get("user_id", "system") if context else "system",
                    actor_type=(
                        "USER" if context and context.get("user_id") else "SYSTEM"
                    ),
                    device_id=context.get("device_id") if context else None,
                    session_id=context.get("session_id") if context else None,
                )
                resource = AuditResource(
                    resource_type="RECORD",
                    resource_id=record_id,
                    store_name=self.__class__.__name__,
                    space_id=context.get("space_id") if context else None,
                )
                outcome = AuditOutcome(
                    result="FAILURE",
                    error_message=str(e),
                )

                # Use async context if available, otherwise log synchronously
                try:
                    import asyncio

                    asyncio.get_running_loop()
                    asyncio.create_task(
                        audit_logger.log_operation(
                            operation="DELETE",
                            actor=actor,
                            resource=resource,
                            outcome=outcome,
                            context=context or {},
                        )
                    )
                except RuntimeError:
                    # No event loop running, skip audit logging for now
                    pass

            logger.error(
                f"Failed to delete record {record_id} from {self._store_name}: {e}"
            )
            raise

    @instrument_storage_operation("list")
    def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """List records with optional filtering, pagination, and redaction."""
        if not self._in_transaction:
            raise RuntimeError(f"Store {self._store_name} not in transaction")

        try:
            result = self._list_records(filters, limit, offset)
            self._operation_count += 1

            # Apply redaction to each record if context provided
            if context:
                result = [self._apply_redaction(record, context) for record in result]

            return result
        except Exception as e:
            self._error_count += 1
            logger.error(f"Failed to list records from {self._store_name}: {e}")
            raise

    # Schema validation utilities

    def validate_data(
        self, data: Dict[str, Any], allow_partial: bool = False
    ) -> ValidationResult:
        """Validate data against the store's schema."""
        if not self._schema:
            self._schema = self._get_schema()

        errors = []
        warnings = []

        try:
            # Basic implementation - can be enhanced with jsonschema library
            required_fields = self._schema.get("required", [])
            properties = self._schema.get("properties", {})

            # Check required fields (unless partial update)
            if not allow_partial:
                for field in required_fields:
                    if field not in data:
                        errors.append(f"Missing required field: {field}")

            # Check data types
            for field, value in data.items():
                if field in properties:
                    expected_type = properties[field].get("type")
                    if expected_type and not self._check_type(value, expected_type):
                        errors.append(
                            f"Invalid type for field {field}: expected {expected_type}"
                        )
                else:
                    warnings.append(f"Unknown field: {field}")

            return ValidationResult(
                is_valid=len(errors) == 0, errors=errors, warnings=warnings
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=warnings,
            )

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Basic type checking."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }

        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, allow it

        return isinstance(value, expected_python_type)

    # Utility methods

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        return {
            "store_name": self._store_name,
            "operation_count": self._operation_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._operation_count, 1),
            "in_transaction": self._in_transaction,
            "initialized": self._initialized,
        }

    def reset_stats(self) -> None:
        """Reset performance statistics."""
        self._operation_count = 0
        self._error_count = 0

    def is_in_transaction(self) -> bool:
        """Check if store is currently in a transaction."""
        return self._in_transaction

    def get_current_connection(self) -> Optional[sqlite3.Connection]:
        """Get the current transaction connection."""
        return self._connection if self._in_transaction else None


class MockStore(BaseStore):
    def validate_transaction(self, conn: sqlite3.Connection) -> bool:
        """Stub for StoreProtocol compliance."""
        return True

    def get_transaction_size(self, conn: sqlite3.Connection) -> int:
        """Stub for StoreProtocol compliance."""
        return 0

    def supports_savepoints(self) -> bool:
        """Stub for StoreProtocol compliance."""
        return False

    """Mock store implementation for testing BaseStore functionality."""

    def __init__(self, name: str = "mock", config: Optional[StoreConfig] = None):
        super().__init__(config)
        self._store_name = name
        self._records: Dict[str, Dict[str, Any]] = {}
        self._next_id = 1

    def _get_schema(self) -> Dict[str, Any]:
        """Simple schema for testing."""
        return {
            "type": "object",
            "required": ["data"],
            "properties": {
                "id": {"type": "string"},
                "data": {"type": "string"},
                "metadata": {"type": "object"},
            },
        }

    def _initialize_schema(self, conn: sqlite3.Connection) -> None:
        """No schema initialization needed for mock."""
        pass

    def _create_record(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a mock record."""
        record_id = str(self._next_id)
        self._next_id += 1

        record = {"id": record_id, **data}
        self._records[record_id] = record
        return record

    def _read_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Read a mock record."""
        return self._records.get(record_id)

    def _update_record(self, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a mock record."""
        if record_id not in self._records:
            raise ValueError(f"Record {record_id} not found")

        self._records[record_id].update(data)
        return self._records[record_id]

    def _delete_record(self, record_id: str) -> bool:
        """Delete a mock record."""
        if record_id in self._records:
            del self._records[record_id]
            return True
        return False

    def _list_records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List mock records."""
        records = list(self._records.values())

        # Apply simple filtering
        if filters:
            filtered_records = []
            for record in records:
                match = True
                for key, value in filters.items():
                    if key not in record or record[key] != value:
                        match = False
                        break
                if match:
                    filtered_records.append(record)
            records = filtered_records

        # Apply pagination
        if offset:
            records = records[offset:]
        if limit:
            records = records[:limit]

        return records

"""
Index Lifecycle Management for automated index operations.

This module provides lifecycle management for search indexes, supporting:
- Lifecycle state management and transitions
- Automated create/update/rotate/delete operations
- Background task scheduling and execution
- Event-driven lifecycle triggers and hooks
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from storage.index_config_store import IndexConfig, IndexConfigStore

logger = logging.getLogger(__name__)


class LifecycleState(str, Enum):
    """Index lifecycle states."""

    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    UPDATING = "UPDATING"
    REBUILDING = "REBUILDING"
    ROTATING = "ROTATING"
    INACTIVE = "INACTIVE"
    DELETING = "DELETING"
    DELETED = "DELETED"
    ERROR = "ERROR"


class LifecycleOperationType(str, Enum):
    """Index lifecycle operations."""

    CREATE = "create"
    UPDATE = "update"
    ROTATE = "rotate"
    DELETE = "delete"
    REBUILD = "rebuild"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"


@dataclass
class LifecycleStateInfo:
    """Information about current lifecycle state."""

    current_state: LifecycleState
    previous_state: Optional[LifecycleState] = None
    transition_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    target_state: Optional[LifecycleState] = None
    state_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "current_state": self.current_state.value,
            "previous_state": (
                self.previous_state.value if self.previous_state else None
            ),
            "transition_timestamp": self.transition_timestamp.isoformat(),
            "target_state": self.target_state.value if self.target_state else None,
            "state_metadata": self.state_metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LifecycleStateInfo":
        """Create from dictionary."""
        return cls(
            current_state=LifecycleState(data["current_state"]),
            previous_state=(
                LifecycleState(data["previous_state"])
                if data.get("previous_state")
                else None
            ),
            transition_timestamp=datetime.fromisoformat(
                data["transition_timestamp"].replace("Z", "+00:00")
            ),
            target_state=(
                LifecycleState(data["target_state"])
                if data.get("target_state")
                else None
            ),
            state_metadata=data.get("state_metadata", {}),
        )


@dataclass
class LifecycleOperation:
    """Represents a lifecycle operation to be performed."""

    operation_id: str = field(default_factory=lambda: f"lifecycle-op-{uuid4().hex[:8]}")
    index_name: str = ""
    operation: LifecycleOperationType = LifecycleOperationType.CREATE
    requested_by: str = "system"
    space_id: str = ""
    config_reference: Optional[IndexConfig] = None
    lifecycle_state: Optional[LifecycleStateInfo] = None
    automation_triggers: Dict[str, Any] = field(default_factory=dict)
    operation_metadata: Dict[str, Any] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    status: str = "pending"
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class LifecycleTrigger:
    """Base class for lifecycle triggers."""

    def __init__(self, trigger_id: str, trigger_type: str):
        self.trigger_id = trigger_id
        self.trigger_type = trigger_type
        self.enabled = True

    async def should_trigger(
        self, index_name: str, current_state: LifecycleStateInfo
    ) -> bool:
        """Check if this trigger should fire."""
        raise NotImplementedError

    async def get_operation(self, index_name: str) -> LifecycleOperation:
        """Get the operation to perform when triggered."""
        raise NotImplementedError


class SizeTrigger(LifecycleTrigger):
    """Trigger based on index size threshold."""

    def __init__(
        self,
        trigger_id: str,
        max_size_mb: int,
        operation: LifecycleOperationType = LifecycleOperationType.ROTATE,
    ):
        super().__init__(trigger_id, "size_threshold")
        self.max_size_mb = max_size_mb
        self.operation = operation

    async def should_trigger(
        self, index_name: str, current_state: LifecycleStateInfo
    ) -> bool:
        """Check if index exceeds size threshold."""
        # TODO: Implement actual size checking against FTS/Embeddings stores
        current_size = current_state.state_metadata.get("size_mb", 0)
        return current_size >= self.max_size_mb

    async def get_operation(self, index_name: str) -> LifecycleOperation:
        """Create rotation operation."""
        return LifecycleOperation(
            index_name=index_name,
            operation=self.operation,
            automation_triggers={"size_threshold_mb": self.max_size_mb},
        )


class TimeTrigger(LifecycleTrigger):
    """Trigger based on time intervals."""

    def __init__(
        self,
        trigger_id: str,
        interval_hours: int,
        operation: LifecycleOperationType = LifecycleOperationType.ROTATE,
    ):
        super().__init__(trigger_id, "time_interval")
        self.interval_hours = interval_hours
        self.operation = operation

    async def should_trigger(
        self, index_name: str, current_state: LifecycleStateInfo
    ) -> bool:
        """Check if enough time has passed since last operation."""
        last_transition = current_state.transition_timestamp
        elapsed = datetime.now(timezone.utc) - last_transition
        return elapsed >= timedelta(hours=self.interval_hours)

    async def get_operation(self, index_name: str) -> LifecycleOperation:
        """Create time-based operation."""
        return LifecycleOperation(
            index_name=index_name,
            operation=self.operation,
            automation_triggers={"time_interval_hours": self.interval_hours},
        )


class ConfigChangeTrigger(LifecycleTrigger):
    """Trigger based on configuration changes."""

    def __init__(self, trigger_id: str):
        super().__init__(trigger_id, "config_change")
        self._last_config_hashes: Dict[str, str] = {}

    async def should_trigger(
        self, index_name: str, current_state: LifecycleStateInfo
    ) -> bool:
        """Check if configuration has changed."""
        # This would be called when config changes are detected
        # For now, return False as it's event-driven
        return False

    async def get_operation(self, index_name: str) -> LifecycleOperation:
        """Create update operation for config changes."""
        return LifecycleOperation(
            index_name=index_name,
            operation=LifecycleOperationType.UPDATE,
            automation_triggers={"config_change_trigger": True},
        )


class IndexLifecycleManager:
    """
    Central manager for index lifecycle operations.

    Handles:
    - State transitions and validation
    - Automated operations and triggers
    - Background task execution
    - Event publishing and hooks
    """

    def __init__(self, config_store: IndexConfigStore):
        self.config_store = config_store
        self._state_storage: Dict[str, LifecycleStateInfo] = {}
        self._operation_queue: List[LifecycleOperation] = []
        self._triggers: List[LifecycleTrigger] = []
        self._hooks: Dict[str, List[Callable[..., Any]]] = {}
        self._running = False

        # Valid state transitions
        self._valid_transitions = {
            LifecycleState.CREATING: [LifecycleState.ACTIVE, LifecycleState.ERROR],
            LifecycleState.ACTIVE: [
                LifecycleState.UPDATING,
                LifecycleState.REBUILDING,
                LifecycleState.ROTATING,
                LifecycleState.INACTIVE,
                LifecycleState.DELETING,
            ],
            LifecycleState.UPDATING: [LifecycleState.ACTIVE, LifecycleState.ERROR],
            LifecycleState.REBUILDING: [LifecycleState.ACTIVE, LifecycleState.ERROR],
            LifecycleState.ROTATING: [LifecycleState.ACTIVE, LifecycleState.ERROR],
            LifecycleState.INACTIVE: [LifecycleState.ACTIVE, LifecycleState.DELETING],
            LifecycleState.DELETING: [LifecycleState.DELETED, LifecycleState.ERROR],
            LifecycleState.ERROR: [LifecycleState.ACTIVE, LifecycleState.DELETING],
        }

    async def start(self) -> None:
        """Start the lifecycle manager background tasks."""
        if self._running:
            return

        self._running = True
        logger.info("Index lifecycle manager started")

        # Start background monitoring and processing
        asyncio.create_task(self._monitor_triggers())
        asyncio.create_task(self._process_operations())

    async def stop(self) -> None:
        """Stop the lifecycle manager."""
        self._running = False
        logger.info("Index lifecycle manager stopped")

    def add_trigger(self, trigger: LifecycleTrigger) -> None:
        """Add a lifecycle trigger."""
        self._triggers.append(trigger)
        logger.info(
            f"Added lifecycle trigger: {trigger.trigger_id} ({trigger.trigger_type})"
        )

    def add_hook(self, event: str, hook: Callable[..., Any]) -> None:
        """Add a lifecycle hook for specific events."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(hook)

    async def get_state(self, index_name: str) -> Optional[LifecycleStateInfo]:
        """Get current lifecycle state for an index."""
        return self._state_storage.get(index_name)

    async def set_state(
        self,
        index_name: str,
        new_state: LifecycleState,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Set lifecycle state for an index."""
        current_info = self._state_storage.get(index_name)
        current_state = current_info.current_state if current_info else None

        # Validate transition
        if current_state and new_state not in self._valid_transitions.get(
            current_state, []
        ):
            logger.warning(
                f"Invalid state transition for {index_name}: {current_state} -> {new_state}"
            )
            return False

        # Create new state info
        new_info = LifecycleStateInfo(
            current_state=new_state,
            previous_state=current_state,
            state_metadata=metadata or {},
        )

        self._state_storage[index_name] = new_info

        # Run hooks
        await self._run_hooks(
            "state_changed",
            {
                "index_name": index_name,
                "previous_state": current_state,
                "new_state": new_state,
                "metadata": metadata,
            },
        )

        logger.info(
            f"State transition for {index_name}: {current_state} -> {new_state}"
        )
        return True

    async def queue_operation(self, operation: LifecycleOperation) -> str:
        """Queue a lifecycle operation for execution."""
        self._operation_queue.append(operation)

        await self._run_hooks(
            "operation_queued",
            {
                "operation_id": operation.operation_id,
                "index_name": operation.index_name,
                "operation": operation.operation,
            },
        )

        logger.info(
            f"Queued operation {operation.operation_id}: {operation.operation} for {operation.index_name}"
        )
        return operation.operation_id

    async def create_index(self, config: IndexConfig) -> str:
        """Create a new index from configuration."""
        operation = LifecycleOperation(
            index_name=config.index_name,
            operation=LifecycleOperationType.CREATE,
            space_id=config.space_id,
            config_reference=config,
        )

        return await self.queue_operation(operation)

    async def update_index(self, index_name: str, new_config: IndexConfig) -> str:
        """Update an existing index with new configuration."""
        operation = LifecycleOperation(
            index_name=index_name,
            operation=LifecycleOperationType.UPDATE,
            space_id=new_config.space_id,
            config_reference=new_config,
        )

        return await self.queue_operation(operation)

    async def rotate_index(self, index_name: str, reason: str = "manual") -> str:
        """Rotate an index (create new, migrate data, retire old)."""
        operation = LifecycleOperation(
            index_name=index_name,
            operation=LifecycleOperationType.ROTATE,
            operation_metadata={"reason": reason},
        )

        return await self.queue_operation(operation)

    async def delete_index(self, index_name: str, force: bool = False) -> str:
        """Delete an index and its data."""
        operation = LifecycleOperation(
            index_name=index_name,
            operation=LifecycleOperationType.DELETE,
            operation_metadata={"force": force},
        )

        return await self.queue_operation(operation)

    async def _monitor_triggers(self) -> None:
        """Background task to monitor triggers."""
        while self._running:
            try:
                for index_name, state_info in self._state_storage.items():
                    for trigger in self._triggers:
                        if not trigger.enabled:
                            continue

                        if await trigger.should_trigger(index_name, state_info):
                            operation = await trigger.get_operation(index_name)
                            await self.queue_operation(operation)

                # TODO: Use event-driven monitoring instead of sleep polling
                await asyncio.sleep(10)  # Reduced from 60s

            except Exception as e:
                logger.error(f"Error in trigger monitoring: {e}")
                # TODO: Implement proper error recovery without fixed delays
                await asyncio.sleep(1)  # Reduced from 10s

    async def _process_operations(self) -> None:
        """Background task to process queued operations."""
        while self._running:
            try:
                if not self._operation_queue:
                    # TODO: Use queue event notifications instead of polling
                    await asyncio.sleep(0.1)  # Reduced from 1s
                    continue

                operation = self._operation_queue.pop(0)
                await self._execute_operation(operation)

            except Exception as e:
                logger.error(f"Error processing operations: {e}")
                # TODO: Implement proper error recovery without fixed delays
                await asyncio.sleep(0.5)  # Reduced from 5s

    async def _execute_operation(self, operation: LifecycleOperation) -> None:
        """Execute a single lifecycle operation."""
        try:
            operation.started_at = datetime.now(timezone.utc)
            operation.status = "running"

            logger.info(
                f"Executing operation {operation.operation_id}: {operation.operation} for {operation.index_name}"
            )

            # Set transitional state
            transitional_states = {
                LifecycleOperationType.CREATE: LifecycleState.CREATING,
                LifecycleOperationType.UPDATE: LifecycleState.UPDATING,
                LifecycleOperationType.ROTATE: LifecycleState.ROTATING,
                LifecycleOperationType.DELETE: LifecycleState.DELETING,
                LifecycleOperationType.REBUILD: LifecycleState.REBUILDING,
            }

            if operation.operation in transitional_states:
                await self.set_state(
                    operation.index_name, transitional_states[operation.operation]
                )

            # Execute the actual operation
            success = await self._perform_operation(operation)

            if success:
                operation.completed_at = datetime.now(timezone.utc)
                operation.status = "completed"

                # Set final state
                final_states = {
                    LifecycleOperationType.CREATE: LifecycleState.ACTIVE,
                    LifecycleOperationType.UPDATE: LifecycleState.ACTIVE,
                    LifecycleOperationType.ROTATE: LifecycleState.ACTIVE,
                    LifecycleOperationType.DELETE: LifecycleState.DELETED,
                    LifecycleOperationType.REBUILD: LifecycleState.ACTIVE,
                }

                if operation.operation in final_states:
                    await self.set_state(
                        operation.index_name, final_states[operation.operation]
                    )

                await self._run_hooks(
                    "operation_completed",
                    {
                        "operation_id": operation.operation_id,
                        "index_name": operation.index_name,
                        "operation": operation.operation,
                    },
                )

            else:
                operation.failed_at = datetime.now(timezone.utc)
                operation.status = "failed"
                await self.set_state(operation.index_name, LifecycleState.ERROR)

                await self._run_hooks(
                    "operation_failed",
                    {
                        "operation_id": operation.operation_id,
                        "index_name": operation.index_name,
                        "operation": operation.operation,
                        "error": operation.error_message,
                    },
                )

        except Exception as e:
            operation.failed_at = datetime.now(timezone.utc)
            operation.status = "failed"
            operation.error_message = str(e)

            logger.error(f"Operation {operation.operation_id} failed: {e}")
            await self.set_state(operation.index_name, LifecycleState.ERROR)

    async def _perform_operation(self, operation: LifecycleOperation) -> bool:
        """Perform the actual operation logic."""
        try:
            if operation.operation == LifecycleOperationType.CREATE:
                return await self._create_index_impl(operation)
            elif operation.operation == LifecycleOperationType.UPDATE:
                return await self._update_index_impl(operation)
            elif operation.operation == LifecycleOperationType.ROTATE:
                return await self._rotate_index_impl(operation)
            elif operation.operation == LifecycleOperationType.DELETE:
                return await self._delete_index_impl(operation)
            elif operation.operation == LifecycleOperationType.REBUILD:
                return await self._rebuild_index_impl(operation)
            else:
                operation.error_message = f"Unknown operation: {operation.operation}"
                return False

        except Exception as e:
            operation.error_message = str(e)
            return False

    async def _create_index_impl(self, operation: LifecycleOperation) -> bool:
        """Implementation for creating an index."""
        # TODO: Integrate with actual FTS/Embeddings store creation
        logger.info(f"Creating index {operation.index_name}")

        # TODO: Replace simulation with actual index creation
        # await asyncio.sleep(0.1)

        # Initialize state
        await self.set_state(
            operation.index_name,
            LifecycleState.ACTIVE,
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "size_mb": 0,
                "document_count": 0,
            },
        )

        return True

    async def _update_index_impl(self, operation: LifecycleOperation) -> bool:
        """Implementation for updating an index."""
        logger.info(f"Updating index {operation.index_name}")

        # TODO: Integrate with actual store update logic
        # await asyncio.sleep(0.1)

        # Update state metadata
        current_state = await self.get_state(operation.index_name)
        if current_state:
            metadata = current_state.state_metadata.copy()
            metadata["last_updated"] = datetime.now(timezone.utc).isoformat()
            await self.set_state(operation.index_name, LifecycleState.ACTIVE, metadata)

        return True

    async def _rotate_index_impl(self, operation: LifecycleOperation) -> bool:
        """Implementation for rotating an index."""
        logger.info(f"Rotating index {operation.index_name}")

        # TODO: Implement actual rotation logic
        # 1. Create new index with timestamp suffix
        # 2. Migrate data from old to new
        # 3. Update aliases/references
        # 4. Mark old index for deletion

        # await asyncio.sleep(0.2)
        return True

    async def _delete_index_impl(self, operation: LifecycleOperation) -> bool:
        """Implementation for deleting an index."""
        logger.info(f"Deleting index {operation.index_name}")

        # TODO: Integrate with actual store deletion
        # await asyncio.sleep(0.1)

        # Remove from state storage
        if operation.index_name in self._state_storage:
            del self._state_storage[operation.index_name]

        return True

    async def _rebuild_index_impl(self, operation: LifecycleOperation) -> bool:
        """Implementation for rebuilding an index."""
        logger.info(f"Rebuilding index {operation.index_name}")

        # TODO: Implement rebuild logic
        # 1. Mark index as rebuilding
        # 2. Reprocess all documents
        # 3. Swap in new index

        # await asyncio.sleep(0.3)
        return True

    async def _run_hooks(self, event: str, data: Dict[str, Any]) -> None:
        """Run registered hooks for an event."""
        hooks = self._hooks.get(event, [])
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(event, data)
                else:
                    hook(event, data)
            except Exception as e:
                logger.error(f"Hook error for event {event}: {e}")

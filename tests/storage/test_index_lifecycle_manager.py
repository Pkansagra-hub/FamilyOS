"""Tests for IndexLifecycleManager."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from ward import test

from storage.index_config_store import FTSConfig, IndexConfig, IndexConfigStore
from storage.index_lifecycle_manager import (
    IndexLifecycleManager,
    LifecycleOperation,
    LifecycleOperationType,
    LifecycleState,
    LifecycleStateInfo,
    SizeTrigger,
    TimeTrigger,
)


@test("can create lifecycle manager")
async def test_create_lifecycle_manager():
    """Test basic lifecycle manager creation."""
    mock_config_store = AsyncMock(spec=IndexConfigStore)
    lifecycle_manager = IndexLifecycleManager(mock_config_store)

    assert lifecycle_manager is not None
    assert not lifecycle_manager._running


@test("can set and get lifecycle state")
async def test_lifecycle_state_management():
    """Test state management functionality."""
    mock_config_store = AsyncMock(spec=IndexConfigStore)
    lifecycle_manager = IndexLifecycleManager(mock_config_store)
    index_name = "test_index"

    # Initially no state
    state = await lifecycle_manager.get_state(index_name)
    assert state is None

    # Set state to CREATING
    success = await lifecycle_manager.set_state(index_name, LifecycleState.CREATING)
    assert success

    # Verify state was set
    state = await lifecycle_manager.get_state(index_name)
    assert state is not None
    assert state.current_state == LifecycleState.CREATING
    assert state.previous_state is None

    # Transition to ACTIVE (valid transition)
    success = await lifecycle_manager.set_state(index_name, LifecycleState.ACTIVE)
    assert success

    state = await lifecycle_manager.get_state(index_name)
    assert state.current_state == LifecycleState.ACTIVE
    assert state.previous_state == LifecycleState.CREATING

    # Try invalid transition (ACTIVE to CREATING - not allowed)
    success = await lifecycle_manager.set_state(index_name, LifecycleState.CREATING)
    assert not success  # Should fail

    # State should remain ACTIVE
    state = await lifecycle_manager.get_state(index_name)
    assert state.current_state == LifecycleState.ACTIVE


@test("can queue and process operations")
async def test_operation_queuing():
    """Test operation queuing functionality."""
    mock_config_store = AsyncMock(spec=IndexConfigStore)
    lifecycle_manager = IndexLifecycleManager(mock_config_store)

    # Create test operation
    operation = LifecycleOperation(
        index_name="test_index",
        operation=LifecycleOperationType.CREATE,
        space_id="test_space",
    )

    # Queue operation
    operation_id = await lifecycle_manager.queue_operation(operation)
    assert operation_id == operation.operation_id

    # Verify operation is in queue
    assert len(lifecycle_manager._operation_queue) == 1
    assert lifecycle_manager._operation_queue[0] == operation


@test("size trigger works correctly")
async def test_size_trigger():
    """Test size-based trigger functionality."""
    trigger = SizeTrigger("test-trigger", max_size_mb=100)

    # Test state under threshold
    state_info = LifecycleStateInfo(
        current_state=LifecycleState.ACTIVE, state_metadata={"size_mb": 50}
    )

    should_trigger = await trigger.should_trigger("test_index", state_info)
    assert not should_trigger

    # Test state over threshold
    state_info.state_metadata["size_mb"] = 150
    should_trigger = await trigger.should_trigger("test_index", state_info)
    assert should_trigger

    # Test getting operation
    operation = await trigger.get_operation("test_index")
    assert operation.index_name == "test_index"
    assert operation.operation == LifecycleOperationType.ROTATE
    assert operation.automation_triggers["size_threshold_mb"] == 100


@test("time trigger works correctly")
async def test_time_trigger():
    """Test time-based trigger functionality."""
    trigger = TimeTrigger("test-trigger", interval_hours=1)

    # Recent transition - should not trigger
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    state_info = LifecycleStateInfo(
        current_state=LifecycleState.ACTIVE, transition_timestamp=recent_time
    )

    should_trigger = await trigger.should_trigger("test_index", state_info)
    assert not should_trigger

    # Old transition - should trigger
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    state_info.transition_timestamp = old_time
    should_trigger = await trigger.should_trigger("test_index", state_info)
    assert should_trigger

    # Test getting operation
    operation = await trigger.get_operation("test_index")
    assert operation.index_name == "test_index"
    assert operation.operation == LifecycleOperationType.ROTATE
    assert operation.automation_triggers["time_interval_hours"] == 1


@test("can add and manage triggers")
async def test_trigger_management():
    """Test trigger addition and management."""
    mock_config_store = AsyncMock(spec=IndexConfigStore)
    lifecycle_manager = IndexLifecycleManager(mock_config_store)

    # Initially no triggers
    assert len(lifecycle_manager._triggers) == 0

    # Add size trigger
    size_trigger = SizeTrigger("size-1", max_size_mb=100)
    lifecycle_manager.add_trigger(size_trigger)

    # Add time trigger
    time_trigger = TimeTrigger("time-1", interval_hours=24)
    lifecycle_manager.add_trigger(time_trigger)

    # Verify triggers were added
    assert len(lifecycle_manager._triggers) == 2
    assert size_trigger in lifecycle_manager._triggers
    assert time_trigger in lifecycle_manager._triggers


@test("can create index operation")
async def test_create_index_operation():
    """Test index creation operation."""
    mock_config_store = AsyncMock(spec=IndexConfigStore)
    lifecycle_manager = IndexLifecycleManager(mock_config_store)

    # Create test config
    config = IndexConfig(
        index_name="test_index",
        space_id="test_space",
        type="fts",
        band_min="GREEN",
        fts_config=FTSConfig(
            analyzer="porter", tokenizer="unicode61", stemming=True, languages=["en"]
        ),
    )

    # Create index
    operation_id = await lifecycle_manager.create_index(config)
    assert operation_id is not None

    # Verify operation was queued
    assert len(lifecycle_manager._operation_queue) == 1
    operation = lifecycle_manager._operation_queue[0]
    assert operation.index_name == "test_index"
    assert operation.operation == LifecycleOperationType.CREATE
    assert operation.config_reference == config


@test("lifecycle state info serialization")
async def test_state_info_serialization():
    """Test LifecycleStateInfo serialization."""
    state_info = LifecycleStateInfo(
        current_state=LifecycleState.ACTIVE,
        previous_state=LifecycleState.CREATING,
        state_metadata={"size_mb": 100, "docs": 500},
    )

    # Test to_dict
    data = state_info.to_dict()
    assert data["current_state"] == "ACTIVE"
    assert data["previous_state"] == "CREATING"
    assert data["state_metadata"]["size_mb"] == 100

    # Test from_dict
    restored = LifecycleStateInfo.from_dict(data)
    assert restored.current_state == LifecycleState.ACTIVE
    assert restored.previous_state == LifecycleState.CREATING
    assert restored.state_metadata["size_mb"] == 100
    assert restored.state_metadata["docs"] == 500


@test("hooks can be added and called")
async def test_hooks():
    """Test lifecycle hooks functionality."""
    mock_config_store = AsyncMock(spec=IndexConfigStore)
    lifecycle_manager = IndexLifecycleManager(mock_config_store)

    hook_calls = []

    def test_hook(event, data):
        hook_calls.append((event, data))

    # Add hook
    lifecycle_manager.add_hook("test_event", test_hook)

    # Run hooks
    await lifecycle_manager._run_hooks("test_event", {"key": "value"})

    # Verify hook was called
    assert len(hook_calls) == 1
    assert hook_calls[0][0] == "test_event"
    assert hook_calls[0][1]["key"] == "value"


if __name__ == "__main__":
    # Run tests manually if needed
    import asyncio
    import sys

    async def run_tests():
        """Run all tests manually."""
        print("Running lifecycle manager tests...")

        try:
            # Create fixtures
            config_store = AsyncMock(spec=IndexConfigStore)
            manager = IndexLifecycleManager(config_store)

            # Test basic functionality
            assert manager is not None
            print("✓ Manager creation")

            # Test state management
            success = await manager.set_state("test", LifecycleState.CREATING)
            assert success
            state = await manager.get_state("test")
            assert state.current_state == LifecycleState.CREATING
            print("✓ State management")

            # Test triggers
            trigger = SizeTrigger("test", 100)
            manager.add_trigger(trigger)
            assert len(manager._triggers) == 1
            print("✓ Trigger management")

            print("All tests passed!")

        except Exception as e:
            print(f"Test failed: {e}")
            sys.exit(1)

    asyncio.run(run_tests())

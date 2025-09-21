"""
Test for OutboxWorker Implementation

Basic smoke test to verify the OutboxWorker functionality.
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from storage.outbox_store import OutboxEvent
from storage.outbox_worker import OutboxWorker, WorkerConfig, WorkerStatus


class TestOutboxWorker:
    """Test suite for OutboxWorker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.outbox_store = Mock()
        self.event_bus = AsyncMock()
        self.uow_factory = Mock()
        self.config = WorkerConfig(
            poll_interval_seconds=0.1, batch_size=5, max_retry_attempts=3
        )

        self.worker = OutboxWorker(
            outbox_store=self.outbox_store,
            event_bus=self.event_bus,
            config=self.config,
            uow_factory=self.uow_factory,
        )

    @pytest.mark.asyncio
    async def test_worker_initialization(self):
        """Test worker initialization."""
        assert self.worker.status == WorkerStatus.STOPPED
        assert not self.worker.is_running
        assert self.worker.metrics.events_processed == 0

    @pytest.mark.asyncio
    async def test_worker_start_stop(self):
        """Test worker start and stop lifecycle."""
        # Start worker
        await self.worker.start()
        assert self.worker.status == WorkerStatus.RUNNING
        assert self.worker.is_running

        # Stop worker
        await self.worker.stop()
        assert self.worker.status == WorkerStatus.STOPPED
        assert not self.worker.is_running

    def test_should_retry_event(self):
        """Test retry logic."""
        event = OutboxEvent(
            id="test-event",
            aggregate_id="test-agg",
            event_type="test.event",
            payload='{"data": {}}',
            created_at=1234567890,
            retry_count=0,
        )

        # Should retry new event
        assert self.worker._should_retry_event(event)

        # Should not retry after max attempts
        event.retry_count = self.config.max_retry_attempts
        assert not self.worker._should_retry_event(event)

    def test_get_health_status(self):
        """Test health status reporting."""
        health = self.worker.get_health_status()

        assert "status" in health
        assert "is_running" in health
        assert "metrics" in health
        assert "config" in health
        assert health["status"] == WorkerStatus.STOPPED.value

    def test_event_handlers(self):
        """Test event handler registration."""
        handler = Mock()
        self.worker.add_event_handler("test_event", handler)

        # Emit test event
        self.worker._emit_event("test_event", {"key": "value"})

        handler.assert_called_once_with({"key": "value"})


if __name__ == "__main__":
    # Simple smoke test without pytest
    import logging

    logging.basicConfig(level=logging.INFO)

    async def smoke_test():
        """Run basic smoke test."""
        print("🧪 Running OutboxWorker smoke test...")

        # Mock dependencies
        outbox_store = Mock()
        outbox_store.get_pending_events.return_value = []

        event_bus = AsyncMock()
        uow_factory = Mock()

        config = WorkerConfig(poll_interval_seconds=0.1)

        worker = OutboxWorker(
            outbox_store=outbox_store,
            event_bus=event_bus,
            config=config,
            uow_factory=uow_factory,
        )

        print(f"✅ Worker created with status: {worker.status}")

        # Test health status
        health = worker.get_health_status()
        print(f"✅ Health status: {health['status']}")

        # Test event handler
        def test_handler(data):
            print(f"✅ Event handler received: {data}")

        worker.add_event_handler("test", test_handler)
        worker._emit_event("test", {"message": "Hello from OutboxWorker!"})

        print("🎉 OutboxWorker smoke test completed successfully!")

    # Run smoke test
    asyncio.run(smoke_test())

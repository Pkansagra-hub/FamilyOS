"""
Outbox Worker for Asynchronous Event Processing

This module provides the OutboxWorker service for processing events from the
outbox table. It handles retry logic, exponential backoff, poison message
handling, and integrates with the event bus for reliable event delivery.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from events.bus import EventBus
from events.types import Event
from storage.outbox_store import OutboxEvent, OutboxStore
from storage.unit_of_work import UnitOfWork

# Use standard logging for now, can be enhanced later
logger = logging.getLogger(__name__)


class WorkerStatus(Enum):
    """Status of the outbox worker."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class WorkerConfig:
    """
    Configuration for the OutboxWorker.

    Attributes:
        poll_interval_seconds: How often to check for events
        batch_size: How many events to process in one batch
        max_retry_attempts: Maximum retry attempts before poisoning
        initial_retry_delay_seconds: Initial delay for retries
        max_retry_delay_seconds: Maximum delay for retries
        retry_backoff_multiplier: Multiplier for exponential backoff
        poison_message_threshold: Retry count to mark as poison
        worker_timeout_seconds: Timeout for individual event processing
        shutdown_timeout_seconds: Timeout for graceful shutdown
    """

    poll_interval_seconds: float = 1.0
    batch_size: int = 10
    max_retry_attempts: int = 5
    initial_retry_delay_seconds: float = 1.0
    max_retry_delay_seconds: float = 300.0  # 5 minutes
    retry_backoff_multiplier: float = 2.0
    poison_message_threshold: int = 3
    worker_timeout_seconds: float = 30.0
    shutdown_timeout_seconds: float = 30.0


@dataclass
class WorkerMetrics:
    """
    Runtime metrics for the OutboxWorker.
    """

    events_processed: int = 0
    events_succeeded: int = 0
    events_failed: int = 0
    events_retried: int = 0
    events_poisoned: int = 0
    total_processing_time: float = 0.0
    last_processed_at: Optional[datetime] = None
    current_batch_size: int = 0

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.events_processed == 0:
            return 1.0
        return self.events_succeeded / self.events_processed

    def get_average_processing_time(self) -> float:
        """Calculate average processing time."""
        if self.events_processed == 0:
            return 0.0
        return self.total_processing_time / self.events_processed


class OutboxWorker:
    """
    Asynchronous worker for processing outbox events.

    Provides reliable background processing of events with retry logic,
    exponential backoff, poison message handling, and comprehensive monitoring.
    """

    def __init__(
        self,
        outbox_store: OutboxStore,
        event_bus: EventBus,
        config: Optional[WorkerConfig] = None,
        uow_factory: Optional[Callable[[], UnitOfWork]] = None,
    ):
        """
        Initialize OutboxWorker.

        Args:
            outbox_store: Store for outbox events
            event_bus: Event bus for publishing events
            config: Worker configuration
            uow_factory: Factory for creating UnitOfWork instances
        """
        self.outbox_store = outbox_store
        self.event_bus = event_bus
        self.config = config or WorkerConfig()
        self.uow_factory = uow_factory or (lambda: UnitOfWork())

        # Worker state
        self._status = WorkerStatus.STOPPED
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._shutdown_event = asyncio.Event()

        # Metrics and monitoring
        self.metrics = WorkerMetrics()
        self._failed_event_ids: Set[str] = set()

        # Event handlers for monitoring
        self._event_handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    @property
    def status(self) -> WorkerStatus:
        """Get current worker status."""
        return self._status

    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._status == WorkerStatus.RUNNING

    async def start(self) -> None:
        """
        Start the outbox worker.

        Raises:
            RuntimeError: If worker is already running
        """
        if self._status != WorkerStatus.STOPPED:
            raise RuntimeError(f"Worker is already {self._status.value}")

        logger.info(
            "Starting outbox worker with config: poll_interval=%s, batch_size=%s",
            self.config.poll_interval_seconds,
            self.config.batch_size,
        )

        self._status = WorkerStatus.STARTING
        self._shutdown_event.clear()

        try:
            # Start background processing task
            self._worker_task = asyncio.create_task(self._worker_loop())

            # Wait for worker to actually start
            await asyncio.sleep(0.1)

            if not self._worker_task.done():
                self._status = WorkerStatus.RUNNING
                logger.info("Outbox worker started successfully")
                self._emit_event("worker_started", {"status": self._status.value})
            else:
                # Worker task failed immediately
                self._status = WorkerStatus.ERROR
                raise RuntimeError("Worker task failed to start")

        except Exception as e:
            self._status = WorkerStatus.ERROR
            logger.error("Failed to start outbox worker: %s", e)
            raise

    async def stop(self) -> None:
        """
        Stop the outbox worker gracefully.

        Waits for current processing to complete before shutting down.
        """
        if self._status in (WorkerStatus.STOPPED, WorkerStatus.STOPPING):
            return

        logger.info("Stopping outbox worker")
        self._status = WorkerStatus.STOPPING

        # Signal shutdown
        self._shutdown_event.set()

        # Wait for worker task to complete
        if self._worker_task:
            try:
                await asyncio.wait_for(
                    self._worker_task, timeout=self.config.shutdown_timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.warning("Worker shutdown timed out, cancelling task")
                self._worker_task.cancel()
                try:
                    await self._worker_task
                except asyncio.CancelledError:
                    pass

        self._status = WorkerStatus.STOPPED
        logger.info("Outbox worker stopped")
        self._emit_event("worker_stopped", {"status": self._status.value})

    async def _worker_loop(self) -> None:
        """
        Main worker loop for processing outbox events.
        """
        logger.info("Outbox worker loop started")

        while not self._shutdown_event.is_set():
            try:
                # Process batch of events
                await self._process_batch()

                # Wait before next poll
                await asyncio.sleep(self.config.poll_interval_seconds)

            except Exception as e:
                logger.error("Error in worker loop: %s", e)
                self._status = WorkerStatus.ERROR

                # Brief pause before retrying to avoid tight error loop
                await asyncio.sleep(1.0)

                # Reset status to running if shutdown not requested
                if not self._shutdown_event.is_set():
                    self._status = WorkerStatus.RUNNING

        logger.info("Worker loop exited")

    async def _process_batch(self) -> None:
        """
        Process a batch of pending events from the outbox.
        """
        # Get pending events
        pending_events = self.outbox_store.get_pending_events(
            limit=self.config.batch_size
        )

        if not pending_events:
            return

        self.metrics.current_batch_size = len(pending_events)

        logger.debug("Processing outbox batch: %d events", len(pending_events))

        # Process events concurrently with semaphore for concurrency control
        semaphore = asyncio.Semaphore(min(self.config.batch_size, 5))

        tasks = [
            self._process_event_with_semaphore(event, semaphore)
            for event in pending_events
        ]

        # Wait for all events in batch to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        self.metrics.current_batch_size = 0

    async def _process_event_with_semaphore(
        self, event: OutboxEvent, semaphore: asyncio.Semaphore
    ) -> None:
        """
        Process a single event with semaphore for concurrency control.
        """
        async with semaphore:
            await self._process_single_event(event)

    async def _process_single_event(self, event: OutboxEvent) -> None:
        """
        Process a single outbox event.

        Args:
            event: The outbox event to process
        """
        start_time = time.time()

        try:
            # Check if we should retry this event
            if not self._should_retry_event(event):
                await self._mark_event_poisoned(event)
                return

            # Mark event as processing
            await self._mark_event_processing(event)

            # Publish event to bus
            await self._publish_event(event)

            # Mark event as processed
            await self._mark_event_processed(event)

            # Update metrics
            processing_time = time.time() - start_time
            self.metrics.events_processed += 1
            self.metrics.events_succeeded += 1
            self.metrics.total_processing_time += processing_time
            self.metrics.last_processed_at = datetime.now(timezone.utc)

            # Remove from failed set if it was there
            self._failed_event_ids.discard(event.id)

            logger.debug(
                "Event processed successfully: %s (%s) in %.3fs",
                event.id,
                event.event_type,
                processing_time,
            )

        except Exception as e:
            # Handle processing failure
            await self._handle_event_failure(event, e)

            processing_time = time.time() - start_time
            self.metrics.events_processed += 1
            self.metrics.events_failed += 1
            self.metrics.total_processing_time += processing_time

            logger.error(
                "Event processing failed: %s (%s) - %s (retry %d)",
                event.id,
                event.event_type,
                str(e),
                event.retry_count,
            )

    def _should_retry_event(self, event: OutboxEvent) -> bool:
        """
        Determine if an event should be retried.

        Args:
            event: The outbox event to check

        Returns:
            True if event should be retried, False otherwise
        """
        # Check if event has exceeded retry attempts
        if event.retry_count >= self.config.max_retry_attempts:
            return False

        # Check if event has been marked as poison
        if event.retry_count >= self.config.poison_message_threshold:
            return False

        # Check if scheduled time has passed (using next_retry field)
        if event.next_retry and event.next_retry > int(time.time()):
            return False

        return True

    async def _mark_event_processing(self, event: OutboxEvent) -> None:
        """Mark event as being processed."""
        event.mark_processing()
        with self.uow_factory() as uow:
            self.outbox_store.update_event_status(event)
            uow.commit()

    async def _mark_event_processed(self, event: OutboxEvent) -> None:
        """Mark event as successfully processed."""
        event.mark_processed()
        with self.uow_factory() as uow:
            self.outbox_store.update_event_status(event)
            uow.commit()

    async def _mark_event_poisoned(self, event: OutboxEvent) -> None:
        """Mark event as poisoned (too many failures)."""
        event.mark_poisoned("Too many retries")
        with self.uow_factory() as uow:
            self.outbox_store.update_event_status(event)
            uow.commit()

        self.metrics.events_poisoned += 1
        self._failed_event_ids.add(event.id)

        logger.warning(
            "Event marked as poisoned: %s (%s) after %d retries",
            event.id,
            event.event_type,
            event.retry_count,
        )

        self._emit_event(
            "event_poisoned",
            {
                "event_id": event.id,
                "event_type": event.event_type,
                "retry_count": event.retry_count,
            },
        )

    async def _publish_event(self, outbox_event: OutboxEvent) -> None:
        """
        Publish an outbox event to the event bus.

        Args:
            outbox_event: The outbox event to publish
        """
        # Parse JSON payload
        payload = json.loads(outbox_event.payload)
        event_data = payload.get("data", {})
        metadata = payload.get("metadata", {})

        # For now, create a minimal event structure
        # TODO: Properly map to EventMeta structure when interfaces are stable
        event = Event(meta=None, payload=event_data)  # Simplified for now

        # Get topic from metadata or default
        topic = metadata.get("topic", "outbox")

        # Publish to event bus
        await self.event_bus.publish(event, topic=topic)

    async def _handle_event_failure(self, event: OutboxEvent, error: Exception) -> None:
        """
        Handle failure of event processing.

        Args:
            event: The failed outbox event
            error: The exception that occurred
        """
        new_retry_count = event.retry_count + 1

        # Calculate next retry delay with exponential backoff
        delay = min(
            self.config.initial_retry_delay_seconds
            * (self.config.retry_backoff_multiplier**new_retry_count),
            self.config.max_retry_delay_seconds,
        )

        next_retry_at = int(time.time() + delay)

        # Determine new status and update event
        if new_retry_count >= self.config.poison_message_threshold:
            event.mark_poisoned(str(error))
            self.metrics.events_poisoned += 1
        else:
            event.mark_failed(str(error), int(delay))
            self.metrics.events_retried += 1

        # Update event in store
        with self.uow_factory() as uow:
            self.outbox_store.update_event_status(event)
            uow.commit()

        self._failed_event_ids.add(event.id)

        self._emit_event(
            "event_failed",
            {
                "event_id": event.id,
                "event_type": event.event_type,
                "error": str(error),
                "retry_count": new_retry_count,
                "next_retry_at": next_retry_at,
            },
        )

    def add_event_handler(
        self, event_type: str, handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Add an event handler for worker events.

        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit a worker event to registered handlers.

        Args:
            event_type: Type of event
            data: Event data
        """
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(
                    "Error in event handler %s for %s: %s",
                    handler.__name__,
                    event_type,
                    e,
                )

    def get_metrics(self) -> WorkerMetrics:
        """Get current worker metrics."""
        return self.metrics

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get worker health status.

        Returns:
            Dictionary with health information
        """
        return {
            "status": self._status.value,
            "is_running": self.is_running,
            "metrics": {
                "events_processed": self.metrics.events_processed,
                "events_succeeded": self.metrics.events_succeeded,
                "events_failed": self.metrics.events_failed,
                "events_retried": self.metrics.events_retried,
                "events_poisoned": self.metrics.events_poisoned,
                "success_rate": self.metrics.get_success_rate(),
                "average_processing_time": self.metrics.get_average_processing_time(),
                "last_processed_at": (
                    self.metrics.last_processed_at.isoformat()
                    if self.metrics.last_processed_at
                    else None
                ),
                "current_batch_size": self.metrics.current_batch_size,
            },
            "config": {
                "poll_interval": self.config.poll_interval_seconds,
                "batch_size": self.config.batch_size,
                "max_retry_attempts": self.config.max_retry_attempts,
            },
            "failed_events_count": len(self._failed_event_ids),
        }

    async def force_process_event(self, event_id: str) -> bool:
        """
        Force processing of a specific event.

        Args:
            event_id: ID of the event to process

        Returns:
            True if event was processed successfully, False otherwise
        """
        event = self.outbox_store.get_event_by_id(event_id)
        if not event:
            logger.warning("Event not found: %s", event_id)
            return False

        try:
            await self._process_single_event(event)
            return True
        except Exception as e:
            logger.error("Failed to force process event %s: %s", event_id, e)
            return False

    async def retry_failed_events(self, limit: Optional[int] = None) -> int:
        """
        Retry all failed events.

        Args:
            limit: Maximum number of events to retry

        Returns:
            Number of events retried
        """
        # Use default limit if None provided
        actual_limit = limit if limit is not None else 100
        failed_events = self.outbox_store.get_retry_events(limit=actual_limit)

        retried_count = 0
        for event in failed_events:
            try:
                await self._process_single_event(event)
                retried_count += 1
            except Exception as e:
                logger.error("Failed to retry event %s: %s", event.id, e)

        logger.info("Retried %d failed events", retried_count)
        return retried_count

    async def cleanup_processed_events(self, older_than_seconds: int = 86400) -> int:
        """
        Clean up old processed events.

        Args:
            older_than_seconds: Remove events processed longer than this

        Returns:
            Number of events cleaned up
        """
        removed_count = self.outbox_store.cleanup_processed_events(older_than_seconds)

        logger.info(
            "Cleaned up %d processed events older than %d seconds",
            removed_count,
            older_than_seconds,
        )

        return removed_count

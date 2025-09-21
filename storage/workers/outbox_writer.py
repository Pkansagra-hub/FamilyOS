"""
Outbox Writer for Transactional Event Publishing

This module provides a high-level interface for writing events to the outbox
within business transactions. It handles serialization, validation, and
ensures events are written atomically with business operations.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from storage.outbox_store import OutboxEvent, OutboxStore
from storage.unit_of_work import TransactionStatus, UnitOfWork

logger = logging.getLogger(__name__)


@dataclass
class EventMetadata:
    """
    Metadata for outbox events.

    Attributes:
        correlation_id: ID to correlate related events
        causation_id: ID of the event that caused this event
        actor_id: ID of the actor who triggered the event
        device_id: ID of the device where the event originated
        space_id: ID of the space where the event occurred
        timestamp: When the event occurred (defaults to current time)
    """

    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    actor_id: Optional[str] = None
    device_id: Optional[str] = None
    space_id: Optional[str] = None
    timestamp: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for inclusion in event payload."""
        result: Dict[str, Any] = {}
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id
        if self.causation_id:
            result["causation_id"] = self.causation_id
        if self.actor_id:
            result["actor_id"] = self.actor_id
        if self.device_id:
            result["device_id"] = self.device_id
        if self.space_id:
            result["space_id"] = self.space_id
        if self.timestamp:
            result["timestamp"] = self.timestamp
        return result


class OutboxWriter:
    """
    High-level interface for writing events to the outbox.

    Provides methods to write events within transactions with proper
    serialization, validation, and metadata handling.
    """

    def __init__(self, uow: UnitOfWork):
        """
        Initialize OutboxWriter with a UnitOfWork.

        Args:
            uow: UnitOfWork instance for transaction management
        """
        self.uow = uow
        self._outbox_store: Optional[OutboxStore] = None

    def _get_outbox_store(self) -> OutboxStore:
        """Get or create the outbox store."""
        if self._outbox_store is None:
            # Create and register outbox store
            self._outbox_store = OutboxStore()
            self.uow.register_store(self._outbox_store)
        return self._outbox_store

    def _check_transaction_active(self) -> None:
        """Check if we're in an active transaction."""
        if self.uow.status != TransactionStatus.PENDING:
            raise RuntimeError("OutboxWriter must be used within an active transaction")

    def write_event(
        self,
        aggregate_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        metadata: Optional[EventMetadata] = None,
        event_id: Optional[str] = None,
    ) -> OutboxEvent:
        """
        Write an event to the outbox within the current transaction.

        Args:
            aggregate_id: ID of the aggregate that generated the event
            event_type: Type/name of the event
            event_data: Event data payload
            metadata: Optional event metadata
            event_id: Optional custom event ID

        Returns:
            The created OutboxEvent

        Raises:
            ValueError: If event data is invalid
            RuntimeError: If not in a transaction
        """
        self._check_transaction_active()

        # Validate event data
        if not aggregate_id:
            raise ValueError("Aggregate ID is required")

        if not event_type:
            raise ValueError("Event type is required")

        # Prepare payload with metadata
        payload: Dict[str, Any] = {
            "data": event_data,
            "metadata": metadata.to_dict() if metadata else {},
            "schema_version": "1.0",
        }

        # Add timestamp if not provided
        if metadata is None or metadata.timestamp is None:
            payload["metadata"]["timestamp"] = int(time.time())

        try:
            # Get outbox store and write event
            outbox_store = self._get_outbox_store()
            event = outbox_store.add_event(
                aggregate_id=aggregate_id,
                event_type=event_type,
                payload=payload,
                event_id=event_id,
            )

            logger.info(
                "Event written to outbox",
                extra={
                    "event_id": event.id,
                    "event_type": event_type,
                    "aggregate_id": aggregate_id,
                    "correlation_id": metadata.correlation_id if metadata else None,
                },
            )

            return event

        except Exception as e:
            logger.error(
                "Failed to write event to outbox",
                extra={
                    "event_type": event_type,
                    "aggregate_id": aggregate_id,
                    "error": str(e),
                },
            )
            raise

    def write_domain_event(
        self,
        aggregate_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        version: int,
        metadata: Optional[EventMetadata] = None,
    ) -> OutboxEvent:
        """
        Write a domain event with versioning support.

        Args:
            aggregate_id: ID of the aggregate
            event_type: Type of domain event
            event_data: Event data payload
            version: Version of the aggregate after this event
            metadata: Optional event metadata

        Returns:
            The created OutboxEvent
        """
        # Add version to event data
        versioned_data: Dict[str, Any] = {**event_data, "aggregate_version": version}

        return self.write_event(
            aggregate_id=aggregate_id,
            event_type=event_type,
            event_data=versioned_data,
            metadata=metadata,
        )

    def write_integration_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        target_service: str,
        metadata: Optional[EventMetadata] = None,
    ) -> OutboxEvent:
        """
        Write an integration event for external services.

        Args:
            event_type: Type of integration event
            event_data: Event data payload
            target_service: Name of the target service
            metadata: Optional event metadata

        Returns:
            The created OutboxEvent
        """
        # Use target service as aggregate ID for integration events
        integration_data: Dict[str, Any] = {
            **event_data,
            "target_service": target_service,
            "event_category": "integration",
        }

        return self.write_event(
            aggregate_id=f"integration:{target_service}",
            event_type=event_type,
            event_data=integration_data,
            metadata=metadata,
        )

    def write_batch_events(self, events: List[Dict[str, Any]]) -> List[OutboxEvent]:
        """
        Write multiple events in the same transaction.

        Args:
            events: List of event dictionaries with keys:
                   - aggregate_id: str
                   - event_type: str
                   - event_data: Dict[str, Any]
                   - metadata: Optional[EventMetadata]
                   - event_id: Optional[str]

        Returns:
            List of created OutboxEvent objects

        Raises:
            ValueError: If any event is invalid
            RuntimeError: If not in a transaction
        """
        self._check_transaction_active()

        if not events:
            return []

        created_events: List[OutboxEvent] = []

        for i, event_spec in enumerate(events):
            try:
                # Validate event specification has required fields
                required_fields = ["aggregate_id", "event_type", "event_data"]
                for field in required_fields:
                    if field not in event_spec:
                        raise ValueError(f"Event {i}: missing required field '{field}'")

                # Extract fields
                aggregate_id = event_spec["aggregate_id"]
                event_type = event_spec["event_type"]
                event_data = event_spec["event_data"]
                metadata = event_spec.get("metadata")
                event_id = event_spec.get("event_id")

                # Write event
                event = self.write_event(
                    aggregate_id=aggregate_id,
                    event_type=event_type,
                    event_data=event_data,
                    metadata=metadata,
                    event_id=event_id,
                )

                created_events.append(event)

            except Exception as e:
                logger.error(
                    "Failed to write event in batch",
                    extra={"event_index": i, "error": str(e)},
                )
                raise ValueError(f"Event {i}: {e}") from e

        logger.info(
            "Batch of events written to outbox",
            extra={
                "event_count": len(created_events),
                "event_ids": [e.id for e in created_events],
            },
        )

        return created_events

    def get_pending_count(self) -> int:
        """
        Get the count of pending events in the outbox.

        Returns:
            Number of pending events
        """
        self._check_transaction_active()

        outbox_store = self._get_outbox_store()
        stats = outbox_store.get_statistics()
        return stats.get("pending", 0)

    def get_failed_count(self) -> int:
        """
        Get the count of failed events in the outbox.

        Returns:
            Number of failed events
        """
        self._check_transaction_active()

        outbox_store = self._get_outbox_store()
        stats = outbox_store.get_statistics()
        return stats.get("failed", 0)

    def cleanup_old_events(self, older_than_seconds: int = 86400) -> int:
        """
        Clean up old processed events.

        Args:
            older_than_seconds: Remove events processed longer than this

        Returns:
            Number of events cleaned up
        """
        self._check_transaction_active()

        outbox_store = self._get_outbox_store()
        removed_count = outbox_store.cleanup_processed_events(older_than_seconds)

        logger.info(
            "Cleaned up old outbox events",
            extra={
                "removed_count": removed_count,
                "older_than_seconds": older_than_seconds,
            },
        )

        return removed_count

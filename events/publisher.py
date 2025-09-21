"""
Event Publisher Interface and Implementations

This module provides the core interfaces and implementations for publishing events
to the MemoryOS event bus. It follows a contract-first approach with proper
validation, error handling, and observability.

Architecture:
- EventPublisher: Abstract interface for all publishers
- InMemoryPublisher: Development/testing implementation
- PublisherConfig: Configuration for publisher behavior
- PublisherFactory: Factory for creating publisher instances
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .persistence import (
    EventPersistence,
    PersistenceConfig,
    PersistenceType,
    create_persistence,
)
from .types import Event
from .types import Event


class PublisherError(Exception):
    """Base exception for publisher-related errors."""

    pass


class ValidationError(PublisherError):
    """Event validation failed."""

    pass


class TimeoutError(PublisherError):
    """Publisher operation timed out."""

    pass


class PublisherType(Enum):
    """Available publisher implementations."""

    IN_MEMORY = "in_memory"
    JSONL = "jsonl"
    REDIS = "redis"
    KAFKA = "kafka"


@dataclass
class PublishResult:
    """Result of a publish operation."""

    success: bool
    event_id: str
    published_at: datetime
    error: Optional[str] = None
    retry_count: int = 0

    @classmethod
    def success_result(cls, event_id: str) -> PublishResult:
        """Create a successful publish result."""
        return cls(
            success=True, event_id=event_id, published_at=datetime.now(timezone.utc)
        )

    @classmethod
    def error_result(
        cls, event_id: str, error: str, retry_count: int = 0
    ) -> PublishResult:
        """Create a failed publish result."""
        return cls(
            success=False,
            event_id=event_id,
            published_at=datetime.now(timezone.utc),
            error=error,
            retry_count=retry_count,
        )


@dataclass
class PublisherConfig:
    """Configuration for event publishers."""

    # Publisher type selection
    publisher_type: PublisherType = PublisherType.IN_MEMORY

    # Batch configuration
    max_batch_size: int = 100
    batch_timeout_ms: int = 1000

    # Retry configuration
    max_retries: int = 3
    retry_delay_ms: int = 1000
    retry_backoff_multiplier: float = 2.0

    # Timeout configuration
    publish_timeout_ms: int = 5000
    health_check_timeout_ms: int = 2000

    # Validation configuration
    validate_events: bool = True
    strict_validation: bool = True

    # Persistence configuration
    enable_persistence: bool = False
    persistence_type: Optional[PersistenceType] = None
    persistence_config: Optional[PersistenceConfig] = None

    # Publisher-specific configuration
    config: Dict[str, Any] = field(default_factory=dict)


class EventPublisher(ABC):
    """
    Abstract interface for event publishers.

    This interface defines the contract that all event publishers must implement.
    Publishers are responsible for:
    - Validating events before publishing
    - Publishing single events or batches
    - Providing health checks and metrics
    - Handling errors gracefully with retries
    """

    def __init__(self, config: PublisherConfig):
        """Initialize publisher with configuration."""
        self.config = config
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize persistence if enabled
        self._persistence: Optional[EventPersistence] = None
        if config.enable_persistence and config.persistence_type:
            persistence_config = config.persistence_config or PersistenceConfig()
            self._persistence = create_persistence(
                config.persistence_type, persistence_config
            )
            self._logger.info(f"Persistence enabled: {config.persistence_type}")
        else:
            self._logger.info("Persistence disabled")

    @abstractmethod
    async def publish(self, event: Event) -> PublishResult:
        """
        Publish a single event.

        Args:
            event: Event to publish

        Returns:
            PublishResult with success/failure details

        Raises:
            ValidationError: If event validation fails
            TimeoutError: If publish operation times out
            PublisherError: For other publisher-specific errors
        """
        pass

    @abstractmethod
    async def publish_batch(self, events: List[Event]) -> List[PublishResult]:
        """
        Publish a batch of events.

        Args:
            events: List of events to publish

        Returns:
            List of PublishResult, one per event

        Raises:
            ValidationError: If any event validation fails
            TimeoutError: If batch publish operation times out
            PublisherError: For other publisher-specific errors
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if publisher is healthy and ready to accept events.

        Returns:
            True if healthy, False otherwise
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close publisher and cleanup resources.
        """
        pass

    def validate_event(self, event: Event) -> None:
        """
        Validate an event before publishing.

        Args:
            event: Event to validate

        Raises:
            ValidationError: If validation fails
        """
        if not self.config.validate_events:
            return

        try:
            # Use the event's built-in validation
            event.validate()
        except Exception as e:
            raise ValidationError(f"Event validation failed: {e}") from e

    def validate_batch(self, events: List[Event]) -> None:
        """
        Validate a batch of events.

        Args:
            events: Events to validate

        Raises:
            ValidationError: If any event validation fails
        """
        if not events:
            raise ValidationError("Event batch cannot be empty")

        if len(events) > self.config.max_batch_size:
            raise ValidationError(
                f"Batch size {len(events)} exceeds maximum {self.config.max_batch_size}"
            )

        for i, event in enumerate(events):
            try:
                self.validate_event(event)
            except ValidationError as e:
                raise ValidationError(f"Event {i} validation failed: {e}") from e


class InMemoryPublisher(EventPublisher):
    """
    In-memory publisher for development and testing.

    This publisher stores events in memory and provides immediate delivery.
    It's useful for:
    - Development and testing
    - Single-process deployments
    - Testing event flows without external dependencies
    """

    def __init__(self, config: PublisherConfig):
        """Initialize in-memory publisher."""
        super().__init__(config)
        self._events: List[Event] = []
        self._published_events: List[Event] = []
        self._is_healthy = True
        self._closed = False

    async def publish(self, event: Event) -> PublishResult:
        """Publish a single event to memory."""
        if self._closed:
            return PublishResult.error_result(event.meta.id, "Publisher is closed")

        try:
            # Validate event
            self.validate_event(event)

            # Store event in memory
            self._events.append(event)
            self._published_events.append(event)

            # Persist event if persistence is enabled
            if self._persistence:
                try:
                    await self._persistence.append_event(event, event.meta.topic)
                    self._logger.debug(f"Event {event.meta.id} persisted")
                except Exception as e:
                    self._logger.warning(
                        f"Failed to persist event {event.meta.id}: {e}"
                    )
                    # Continue with publish even if persistence fails

            self._logger.debug(f"Published event {event.meta.id} to memory")

            return PublishResult.success_result(event.meta.id)

        except ValidationError as e:
            return PublishResult.error_result(event.meta.id, str(e))
        except Exception as e:
            self._logger.error(
                f"Unexpected error publishing event {event.meta.id}: {e}"
            )
            return PublishResult.error_result(event.meta.id, f"Unexpected error: {e}")

    async def publish_batch(self, events: List[Event]) -> List[PublishResult]:
        """Publish a batch of events to memory."""
        if self._closed:
            return [
                PublishResult.error_result(event.meta.id, "Publisher is closed")
                for event in events
            ]

        try:
            # Validate batch
            self.validate_batch(events)

            # Publish all events
            results = []
            for event in events:
                result = await self.publish(event)
                results.append(result)

            self._logger.debug(f"Published batch of {len(events)} events to memory")

            return results

        except ValidationError as e:
            # Return error for all events if batch validation fails
            return [
                PublishResult.error_result(event.meta.id, str(e)) for event in events
            ]
        except Exception as e:
            self._logger.error(f"Unexpected error publishing batch: {e}")
            return [
                PublishResult.error_result(event.meta.id, f"Unexpected error: {e}")
                for event in events
            ]

    async def health_check(self) -> bool:
        """Check if in-memory publisher is healthy."""
        # Check publisher health and persistence health
        is_healthy = self._is_healthy and not self._closed

        if self._persistence:
            is_healthy = is_healthy and await self._persistence.health_check()

        return is_healthy

    async def close(self) -> None:
        """Close in-memory publisher."""
        self._closed = True

        # Close persistence if enabled
        if self._persistence:
            await self._persistence.close()

        self._logger.info("In-memory publisher closed")

    # Additional methods for testing and inspection

    def get_published_events(self) -> List[Event]:
        """Get all published events (for testing)."""
        return self._published_events.copy()

    def get_event_count(self) -> int:
        """Get count of published events."""
        return len(self._published_events)

    def clear_events(self) -> None:
        """Clear all stored events (for testing)."""
        self._events.clear()
        self._published_events.clear()

    def set_healthy(self, healthy: bool) -> None:
        """Set health status (for testing)."""
        self._is_healthy = healthy


# Publisher factory function
def create_publisher(config: PublisherConfig) -> EventPublisher:
    """
    Create a publisher instance based on configuration.

    Args:
        config: Publisher configuration

    Returns:
        Publisher instance

    Raises:
        ValueError: If publisher type is not supported
    """
    if config.publisher_type == PublisherType.IN_MEMORY:
        return InMemoryPublisher(config)
    else:
        raise ValueError(f"Unsupported publisher type: {config.publisher_type}")


__all__ = [
    "EventPublisher",
    "InMemoryPublisher",
    "PublisherConfig",
    "PublisherType",
    "PublishResult",
    "PublisherError",
    "ValidationError",
    "TimeoutError",
    "create_publisher",
]

"""Event subscription registry for managing subscribers and topic matching.

This module implements the subscription management system for the MemoryOS event bus,
providing thread-safe registration, topic pattern matching, and subscription lifecycle
management for both sync and async handlers.

Architecture:
- Subscription: Dataclass holding subscription metadata and handler reference
- SubscriptionRegistry: Thread-safe registry with topic-based organization
- Topic matching: Supports exact, prefix, and regex patterns
- Priority handling: Subscribers executed in priority order (higher first)
- Lifecycle management: Active/inactive status tracking

Integration:
- Used by EventBus for subscribe/unsubscribe operations
- Integrated with EventDispatcher for routing events to subscribers
- Supports group-aware subscriptions for durable consumer patterns
- Thread-safe for concurrent subscription operations

Example:
    >>> registry = SubscriptionRegistry()
    >>> sub_id = registry.register_subscription(
    ...     topic="HIPPO_ENCODE",
    ...     handler=my_handler,
    ...     priority=100
    ... )
    >>> subs = registry.get_subscriptions_for_topic("HIPPO_ENCODE")
    >>> registry.unregister_subscription(sub_id)
"""

from __future__ import annotations

import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .filters import FilterExpression
from .types import Event
from .validation import validate_topic_format


@dataclass
class Subscription:
    """Represents a single event subscription with metadata and handler."""

    # Core identifiers
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    handler: Callable[[Event], Any] = field(default=lambda x: None)

    # Organization and routing
    group: Optional[str] = None  # For durable consumer groups
    priority: int = 0  # Higher values = higher priority

    # Filtering and conditions
    filters: Dict[str, Any] = field(default_factory=dict)
    advanced_filters: List[FilterExpression] = field(default_factory=list)
    topic_pattern: Optional[str] = None  # For regex matching

    # Lifecycle and status
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Handler metadata
    is_async: bool = False
    handler_type: str = "sync"

    def __post_init__(self):
        """Validate and initialize subscription after creation."""
        if not self.topic:
            raise ValueError("Topic cannot be empty")

        if not callable(self.handler):
            raise ValueError("Handler must be callable")

        # Determine if handler is async
        import asyncio

        self.is_async = asyncio.iscoroutinefunction(self.handler)
        self.handler_type = "async" if self.is_async else "sync"

        # Set topic pattern for regex matching if contains regex chars
        if any(
            char in self.topic for char in ["*", "+", ".", "^", "$", "[", "]", "(", ")"]
        ):
            self.topic_pattern = self.topic

    def matches_topic(self, topic: str) -> bool:
        """Check if this subscription matches the given topic."""
        if self.topic_pattern:
            try:
                return bool(re.match(self.topic_pattern, topic))
            except re.error:
                # Fallback to exact match if regex is invalid
                return self.topic == topic
        else:
            return self.topic == topic

    def matches_filters(self, event: Event) -> bool:
        """
        Check if event matches subscription filters.

        Supports both legacy simple filters and advanced FilterExpression objects.
        For advanced filters, uses the FilterManager for evaluation.

        Args:
            event: Event to match against filters

        Returns:
            True if event matches all filters, False otherwise
        """
        # Check legacy simple filters first
        if self.filters:
            for filter_key, filter_value in self.filters.items():
                # Check event meta fields
                if hasattr(event.meta, filter_key):
                    if getattr(event.meta, filter_key) != filter_value:
                        return False
                # Check payload fields
                elif filter_key in event.payload:
                    if event.payload[filter_key] != filter_value:
                        return False
                else:
                    # Filter key not found in event - no match
                    return False

        # Check advanced filters if present
        if self.advanced_filters:
            from .filters import get_filter_manager

            filter_manager = get_filter_manager()

            # Use FilterManager to evaluate all advanced filters
            result = filter_manager.evaluate_filters(self.advanced_filters, event)
            if not result.matches:
                return False

        return True

    def add_advanced_filter(self, filter_expr: FilterExpression) -> None:
        """
        Add an advanced filter expression to this subscription.

        Args:
            filter_expr: FilterExpression to add
        """
        filter_expr.validate()  # Validate before adding
        self.advanced_filters.append(filter_expr)

    def remove_advanced_filter(self, index: int) -> bool:
        """
        Remove an advanced filter by index.

        Args:
            index: Index of filter to remove

        Returns:
            True if filter was removed, False if index was invalid
        """
        if 0 <= index < len(self.advanced_filters):
            self.advanced_filters.pop(index)
            return True
        return False

    def clear_advanced_filters(self) -> None:
        """Remove all advanced filters from this subscription."""
        self.advanced_filters.clear()

    def get_filter_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all filters (simple and advanced) for this subscription.

        Returns:
            Dictionary with filter counts and types
        """
        return {
            "simple_filters": len(self.filters),
            "advanced_filters": len(self.advanced_filters),
            "advanced_filter_types": [type(f).__name__ for f in self.advanced_filters],
            "total_filters": len(self.filters) + len(self.advanced_filters),
        }


class SubscriptionRegistry:
    """Thread-safe registry for managing event subscriptions."""

    def __init__(self):
        """Initialize the subscription registry."""
        # Topic -> List[Subscription] mapping
        self._subscriptions: Dict[str, List[Subscription]] = {}

        # ID -> Subscription mapping for quick lookups
        self._subscription_index: Dict[str, Subscription] = {}

        # Thread safety
        self._lock = threading.RLock()

        # Stats tracking
        self._subscription_counter = 0
        self._total_registrations = 0
        self._total_unregistrations = 0

    def register_subscription(
        self,
        topic: str,
        handler: Callable[[Event], Any],
        group: Optional[str] = None,
        priority: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        advanced_filters: Optional[List[FilterExpression]] = None,
    ) -> tuple[str, Subscription]:
        """
        Register a new subscription and return its ID and object.

        Args:
            topic: Event topic to subscribe to (supports regex patterns)
            handler: Callable that accepts an Event object
            group: Optional group name for durable subscriptions
            priority: Priority level (higher = executed first)
            filters: Optional simple filters for event matching
            advanced_filters: Optional list of FilterExpression objects

        Returns:
            Tuple of (subscription_id, subscription_object)

        Raises:
            ValueError: If topic format is invalid or handler is not callable
        """
        if not topic:
            raise ValueError("Topic cannot be empty")

        if not callable(handler):
            raise ValueError("Handler must be callable")

        # Validate topic format against contracts
        if not validate_topic_format(topic):
            raise ValueError(f"Invalid topic format: {topic}")

        filters = filters or {}
        advanced_filters = advanced_filters or []

        # Validate all advanced filters
        for filter_expr in advanced_filters:
            filter_expr.validate()

        with self._lock:
            # Create subscription
            subscription = Subscription(
                topic=topic,
                handler=handler,
                group=group,
                priority=priority,
                filters=filters,
                advanced_filters=advanced_filters,
            )

            # Add to topic list (sorted by priority)
            if topic not in self._subscriptions:
                self._subscriptions[topic] = []

            self._subscriptions[topic].append(subscription)
            self._subscriptions[topic].sort(key=lambda s: s.priority, reverse=True)

            # Add to index
            self._subscription_index[subscription.subscription_id] = subscription

            # Update stats
            self._subscription_counter += 1
            self._total_registrations += 1

            return subscription.subscription_id, subscription

    def unregister_subscription(self, subscription_id: str) -> bool:
        """
        Unregister a subscription by ID.

        Args:
            subscription_id: ID of subscription to remove

        Returns:
            True if subscription was found and removed, False otherwise
        """
        with self._lock:
            subscription = self._subscription_index.get(subscription_id)
            if not subscription:
                return False

            # Mark as inactive first
            subscription.active = False

            # Remove from topic list
            topic_subs = self._subscriptions.get(subscription.topic, [])
            self._subscriptions[subscription.topic] = [
                s for s in topic_subs if s.subscription_id != subscription_id
            ]

            # Clean up empty topic lists
            if not self._subscriptions[subscription.topic]:
                del self._subscriptions[subscription.topic]

            # Remove from index
            del self._subscription_index[subscription_id]

            # Update stats
            self._subscription_counter -= 1
            self._total_unregistrations += 1

            return True

    def list_subscriptions(
        self, topic_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List active subscriptions with optional topic filtering.

        Args:
            topic_filter: Optional topic to filter by

        Returns:
            List of subscription summary dictionaries
        """
        with self._lock:
            summaries = []

            for subscription in self._subscription_index.values():
                if not subscription.active:
                    continue

                if topic_filter and subscription.topic != topic_filter:
                    continue

                summaries.append(
                    {
                        "subscription_id": subscription.subscription_id,
                        "topic": subscription.topic,
                        "group": subscription.group,
                        "priority": subscription.priority,
                        "handler_type": subscription.handler_type,
                        "filters": subscription.filters,
                        "created_at": subscription.created_at.isoformat(),
                    }
                )

            # Sort by priority then topic
            summaries.sort(key=lambda s: (s["priority"], s["topic"]), reverse=True)
            return summaries

    def get_subscriptions_for_topic(self, topic: str) -> List[Subscription]:
        """
        Get all active subscriptions matching a topic.

        Args:
            topic: Event topic to match against

        Returns:
            List of matching subscriptions sorted by priority (highest first)
        """
        with self._lock:
            matching_subscriptions = []

            # Check exact topic matches first
            if topic in self._subscriptions:
                matching_subscriptions.extend(
                    [s for s in self._subscriptions[topic] if s.active]
                )

            # Check pattern matches from other topics
            for other_topic, subscriptions in self._subscriptions.items():
                if other_topic == topic:
                    continue  # Already handled above

                for subscription in subscriptions:
                    if subscription.active and subscription.matches_topic(topic):
                        matching_subscriptions.append(subscription)

            # Sort by priority (highest first)
            matching_subscriptions.sort(key=lambda s: s.priority, reverse=True)
            return matching_subscriptions

    def get_handler_stats(self) -> Dict[str, Any]:
        """
        Get statistics about registered handlers.

        Returns:
            Dictionary with subscription statistics
        """
        with self._lock:
            topic_counts = {}
            group_counts = {}
            handler_types = {"sync": 0, "async": 0}

            for subscription in self._subscription_index.values():
                if not subscription.active:
                    continue

                # Count by topic
                topic_counts[subscription.topic] = (
                    topic_counts.get(subscription.topic, 0) + 1
                )

                # Count by group
                if subscription.group:
                    group_counts[subscription.group] = (
                        group_counts.get(subscription.group, 0) + 1
                    )

                # Count by handler type
                handler_types[subscription.handler_type] += 1

            return {
                "total_active": len(
                    [s for s in self._subscription_index.values() if s.active]
                ),
                "total_ever_registered": self._total_registrations,
                "total_unregistrations": self._total_unregistrations,
                "subscriptions_per_topic": topic_counts,
                "subscriptions_per_group": group_counts,
                "handler_types": handler_types,
                "topic_count": len(self._subscriptions),
            }

    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        """Get a subscription by ID."""
        with self._lock:
            return self._subscription_index.get(subscription_id)

    def clear_all(self) -> int:
        """
        Clear all subscriptions (mainly for testing).

        Returns:
            Number of subscriptions that were cleared
        """
        with self._lock:
            count = len(self._subscription_index)
            self._subscriptions.clear()
            self._subscription_index.clear()
            self._subscription_counter = 0
            return count

    def add_filter_to_subscription(
        self, subscription_id: str, filter_expr: FilterExpression
    ) -> bool:
        """
        Add an advanced filter to an existing subscription.

        Args:
            subscription_id: ID of subscription to modify
            filter_expr: FilterExpression to add

        Returns:
            True if filter was added, False if subscription not found
        """
        with self._lock:
            subscription = self._subscription_index.get(subscription_id)
            if subscription:
                subscription.add_advanced_filter(filter_expr)
                return True
            return False

    def remove_filter_from_subscription(
        self, subscription_id: str, filter_index: int
    ) -> bool:
        """
        Remove an advanced filter from an existing subscription.

        Args:
            subscription_id: ID of subscription to modify
            filter_index: Index of filter to remove

        Returns:
            True if filter was removed, False if subscription/filter not found
        """
        with self._lock:
            subscription = self._subscription_index.get(subscription_id)
            if subscription:
                return subscription.remove_advanced_filter(filter_index)
            return False

    def get_subscription_filter_summary(
        self, subscription_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get filter summary for a specific subscription.

        Args:
            subscription_id: ID of subscription

        Returns:
            Filter summary dict, or None if subscription not found
        """
        with self._lock:
            subscription = self._subscription_index.get(subscription_id)
            if subscription:
                return subscription.get_filter_summary()
            return None

    def get_filter_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about filtering across all subscriptions.

        Returns:
            Dictionary with filter usage statistics
        """
        with self._lock:
            total_simple_filters = 0
            total_advanced_filters = 0
            filter_type_counts = {}
            subscriptions_with_filters = 0

            for subscription in self._subscription_index.values():
                summary = subscription.get_filter_summary()

                if summary["total_filters"] > 0:
                    subscriptions_with_filters += 1

                total_simple_filters += summary["simple_filters"]
                total_advanced_filters += summary["advanced_filters"]

                for filter_type in summary["advanced_filter_types"]:
                    filter_type_counts[filter_type] = (
                        filter_type_counts.get(filter_type, 0) + 1
                    )

            return {
                "total_subscriptions": len(self._subscription_index),
                "subscriptions_with_filters": subscriptions_with_filters,
                "total_simple_filters": total_simple_filters,
                "total_advanced_filters": total_advanced_filters,
                "advanced_filter_types": filter_type_counts,
                "average_filters_per_subscription": (
                    (total_simple_filters + total_advanced_filters)
                    / max(1, len(self._subscription_index))
                ),
            }


# Global registry instance (can be overridden for testing)
_default_registry: Optional[SubscriptionRegistry] = None


def get_subscription_registry() -> SubscriptionRegistry:
    """Get the global subscription registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = SubscriptionRegistry()
    return _default_registry


def set_subscription_registry(registry: SubscriptionRegistry) -> None:
    """Set the global subscription registry (mainly for testing)."""
    global _default_registry
    _default_registry = registry

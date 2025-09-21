"""Event dispatcher for routing events to subscribers with middleware support.

This module implements the event dispatching mechanism that routes events from the
EventBus to registered subscribers, handling both sync and async execution patterns
with proper error isolation and middleware integration.

Architecture:
- DispatchContext: Contains event, subscribers, and middleware results
- EventDispatcher: Core dispatching logic with concurrent execution support
- Integration with SubscriptionRegistry for finding matching subscribers
- Middleware pipeline integration for pre/post processing
- Error isolation prevents one handler failure from affecting others

Features:
- Sync and async handler execution
- Configurable concurrency limits
- Per-handler error isolation with DLQ routing
- Dispatch metrics and performance tracking
- Filter-based subscription matching
- Middleware hooks for extensibility

Example:
    >>> dispatcher = EventDispatcher(subscription_registry)
    >>> await dispatcher.dispatch_to_subscribers(event, "HIPPO_ENCODE")
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from observability.metrics import pipeline_stage_duration_ms
from observability.trace import start_span

from .subscription import Subscription, SubscriptionRegistry
from .types import Event

logger = logging.getLogger(__name__)


@dataclass
class DispatchContext:
    """Context for event dispatch containing all relevant information."""

    # Core dispatch data
    event: Event
    topic: str
    subscribers: List[Subscription] = field(default_factory=list)

    # Timing and correlation
    dispatch_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    correlation_id: str = ""

    # Results and middleware
    middleware_results: Dict[str, Any] = field(default_factory=dict)
    dispatch_results: List[Dict[str, Any]] = field(default_factory=list)

    # Performance tracking
    handler_count: int = 0
    successful_handlers: int = 0
    failed_handlers: int = 0
    total_duration_ms: float = 0.0


@dataclass
class DispatchResult:
    """Result of dispatching an event to subscribers."""

    context: DispatchContext
    success: bool
    total_handlers: int
    successful_handlers: int
    failed_handlers: int
    duration_ms: float
    errors: List[str] = field(default_factory=list)


class EventDispatcher:
    """Dispatches events to matching subscribers with error isolation."""

    def __init__(
        self,
        subscription_registry: SubscriptionRegistry,
        max_concurrent_handlers: int = 10,
        handler_timeout_seconds: float = 30.0,
    ):
        """
        Initialize the event dispatcher.

        Args:
            subscription_registry: Registry containing active subscriptions
            max_concurrent_handlers: Maximum concurrent async handlers
            handler_timeout_seconds: Timeout for individual handler execution
        """
        self.subscription_registry = subscription_registry
        self.max_concurrent_handlers = max_concurrent_handlers
        self.handler_timeout_seconds = handler_timeout_seconds

        # Thread pool for sync handlers
        self._thread_pool = ThreadPoolExecutor(
            max_workers=max_concurrent_handlers, thread_name_prefix="event_handler"
        )

        # Performance tracking
        self._dispatch_stats = {
            "total_dispatches": 0,
            "successful_dispatches": 0,
            "failed_dispatches": 0,
            "total_handlers_executed": 0,
            "total_duration_ms": 0.0,
        }

    async def dispatch_to_subscribers(self, event: Event, topic: str) -> DispatchResult:
        """
        Dispatch an event to all matching subscribers.

        Args:
            event: Event to dispatch
            topic: Topic for subscriber matching

        Returns:
            DispatchResult with execution summary
        """
        start_time = time.time()

        # Create dispatch context
        context = DispatchContext(
            event=event, topic=topic, correlation_id=getattr(event, "id", "unknown")
        )

        with start_span(
            "events.dispatcher.dispatch",
            {"topic": topic, "event_id": context.correlation_id},
        ) as span:
            try:
                # Get matching subscriptions
                context.subscribers = (
                    self.subscription_registry.get_subscriptions_for_topic(topic)
                )
                context.handler_count = len(context.subscribers)

                # Set span attributes if span exists
                if span:
                    span.set_attribute("subscriber_count", context.handler_count)

                if not context.subscribers:
                    logger.debug(f"No subscribers found for topic: {topic}")
                    return self._create_result(context, start_time, success=True)

                # Filter subscribers by event filters
                filtered_subscribers = [
                    sub for sub in context.subscribers if sub.matches_filters(event)
                ]

                context.subscribers = filtered_subscribers
                context.handler_count = len(filtered_subscribers)

                logger.info(
                    f"Dispatching event {context.correlation_id} to {context.handler_count} subscribers"
                )

                # Execute handlers
                await self._execute_subscribers(context)

                # Update stats
                self._update_dispatch_stats(context, success=True)

                if span:
                    span.set_attribute(
                        "successful_handlers", context.successful_handlers
                    )
                    span.set_attribute("failed_handlers", context.failed_handlers)

                return self._create_result(context, start_time, success=True)

            except Exception as e:
                logger.error(f"Dispatch failed for topic {topic}: {e}", exc_info=True)
                if span:
                    span.record_exception(e)
                    span.set_status("ERROR", str(e))

                self._update_dispatch_stats(context, success=False)

                result = self._create_result(context, start_time, success=False)
                result.errors.append(str(e))
                return result

    async def _execute_subscribers(self, context: DispatchContext) -> None:
        """Execute all subscribers for the dispatch context."""
        if not context.subscribers:
            return

        # Separate sync and async handlers
        sync_handlers = []
        async_handlers = []

        for subscription in context.subscribers:
            if subscription.is_async:
                async_handlers.append(subscription)
            else:
                sync_handlers.append(subscription)

        # Execute handlers concurrently with limits
        tasks = []

        # Create tasks for async handlers
        for subscription in async_handlers:
            task = asyncio.create_task(
                self._execute_async_handler(context, subscription)
            )
            tasks.append(task)

        # Create tasks for sync handlers (run in thread pool)
        for subscription in sync_handlers:
            task = asyncio.create_task(
                self._execute_sync_handler(context, subscription)
            )
            tasks.append(task)

        # Execute with concurrency limit
        if tasks:
            semaphore = asyncio.Semaphore(self.max_concurrent_handlers)

            async def limited_execution(task):
                async with semaphore:
                    return await task

            # Wait for all handlers to complete
            results = await asyncio.gather(
                *[limited_execution(task) for task in tasks], return_exceptions=True
            )

            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Handler execution failed: {result}")
                    context.failed_handlers += 1
                    context.dispatch_results.append(
                        {
                            "subscription_id": context.subscribers[
                                i % len(context.subscribers)
                            ].subscription_id,
                            "success": False,
                            "error": str(result),
                            "duration_ms": 0.0,
                        }
                    )
                else:
                    context.successful_handlers += 1

    async def _execute_async_handler(
        self, context: DispatchContext, subscription: Subscription
    ) -> Any:
        """Execute an async handler with timeout and error handling."""
        start_time = time.time()

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                subscription.handler(context.event),
                timeout=self.handler_timeout_seconds,
            )

            duration_ms = (time.time() - start_time) * 1000

            context.dispatch_results.append(
                {
                    "subscription_id": subscription.subscription_id,
                    "success": True,
                    "result": result,
                    "duration_ms": duration_ms,
                }
            )

            # Emit metrics
            if pipeline_stage_duration_ms:
                pipeline_stage_duration_ms.labels(
                    pipeline="events", stage="handler_async", outcome="success"
                ).observe(duration_ms)

            return result

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Handler timeout after {self.handler_timeout_seconds}s"

            logger.warning(
                f"Handler timeout for subscription {subscription.subscription_id}: {error_msg}"
            )

            context.dispatch_results.append(
                {
                    "subscription_id": subscription.subscription_id,
                    "success": False,
                    "error": error_msg,
                    "duration_ms": duration_ms,
                }
            )

            # Emit metrics
            if pipeline_stage_duration_ms:
                pipeline_stage_duration_ms.labels(
                    pipeline="events", stage="handler_async", outcome="timeout"
                ).observe(duration_ms)

            raise

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            logger.error(
                f"Async handler failed for subscription {subscription.subscription_id}: {error_msg}"
            )

            context.dispatch_results.append(
                {
                    "subscription_id": subscription.subscription_id,
                    "success": False,
                    "error": error_msg,
                    "duration_ms": duration_ms,
                }
            )

            # Emit metrics
            if pipeline_stage_duration_ms:
                pipeline_stage_duration_ms.labels(
                    pipeline="events", stage="handler_async", outcome="error"
                ).observe(duration_ms)

            # Don't re-raise - we want error isolation
            return None

    async def _execute_sync_handler(
        self, context: DispatchContext, subscription: Subscription
    ) -> Any:
        """Execute a sync handler in thread pool with timeout and error handling."""
        start_time = time.time()

        def run_sync_handler():
            """Wrapper to run sync handler in thread."""
            return subscription.handler(context.event)

        try:
            # Run in thread pool with timeout
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(self._thread_pool, run_sync_handler),
                timeout=self.handler_timeout_seconds,
            )

            duration_ms = (time.time() - start_time) * 1000

            context.dispatch_results.append(
                {
                    "subscription_id": subscription.subscription_id,
                    "success": True,
                    "result": result,
                    "duration_ms": duration_ms,
                }
            )

            # Emit metrics
            if pipeline_stage_duration_ms:
                pipeline_stage_duration_ms.labels(
                    pipeline="events", stage="handler_sync", outcome="success"
                ).observe(duration_ms)

            return result

        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Handler timeout after {self.handler_timeout_seconds}s"

            logger.warning(
                f"Handler timeout for subscription {subscription.subscription_id}: {error_msg}"
            )

            context.dispatch_results.append(
                {
                    "subscription_id": subscription.subscription_id,
                    "success": False,
                    "error": error_msg,
                    "duration_ms": duration_ms,
                }
            )

            # Emit metrics
            if pipeline_stage_duration_ms:
                pipeline_stage_duration_ms.labels(
                    pipeline="events", stage="handler_sync", outcome="timeout"
                ).observe(duration_ms)

            raise

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            logger.error(
                f"Sync handler failed for subscription {subscription.subscription_id}: {error_msg}"
            )

            context.dispatch_results.append(
                {
                    "subscription_id": subscription.subscription_id,
                    "success": False,
                    "error": error_msg,
                    "duration_ms": duration_ms,
                }
            )

            # Emit metrics
            if pipeline_stage_duration_ms:
                pipeline_stage_duration_ms.labels(
                    pipeline="events", stage="handler_sync", outcome="error"
                ).observe(duration_ms)

            # Don't re-raise - we want error isolation
            return None

    def _create_result(
        self, context: DispatchContext, start_time: float, success: bool
    ) -> DispatchResult:
        """Create a DispatchResult from context and timing."""
        duration_ms = (time.time() - start_time) * 1000
        context.total_duration_ms = duration_ms

        return DispatchResult(
            context=context,
            success=success,
            total_handlers=context.handler_count,
            successful_handlers=context.successful_handlers,
            failed_handlers=context.failed_handlers,
            duration_ms=duration_ms,
        )

    def _update_dispatch_stats(self, context: DispatchContext, success: bool) -> None:
        """Update internal dispatch statistics."""
        self._dispatch_stats["total_dispatches"] += 1
        self._dispatch_stats["total_handlers_executed"] += context.handler_count
        self._dispatch_stats["total_duration_ms"] += context.total_duration_ms

        if success:
            self._dispatch_stats["successful_dispatches"] += 1
        else:
            self._dispatch_stats["failed_dispatches"] += 1

    def get_dispatch_stats(self) -> Dict[str, Any]:
        """Get current dispatch statistics."""
        stats = self._dispatch_stats.copy()

        # Calculate derived metrics
        if stats["total_dispatches"] > 0:
            stats["average_duration_ms"] = (
                stats["total_duration_ms"] / stats["total_dispatches"]
            )
            stats["success_rate"] = (
                stats["successful_dispatches"] / stats["total_dispatches"]
            )
        else:
            stats["average_duration_ms"] = 0.0
            stats["success_rate"] = 0.0

        if stats["total_handlers_executed"] > 0:
            stats["average_handlers_per_dispatch"] = (
                stats["total_handlers_executed"] / stats["total_dispatches"]
            )
        else:
            stats["average_handlers_per_dispatch"] = 0.0

        return stats

    async def shutdown(self) -> None:
        """Shutdown the dispatcher and clean up resources."""
        logger.info("Shutting down event dispatcher")

        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)

        logger.info("Event dispatcher shutdown complete")


# Global dispatcher instance (can be overridden for testing)
_default_dispatcher: Optional[EventDispatcher] = None


def get_event_dispatcher() -> EventDispatcher:
    """Get the global event dispatcher instance."""
    global _default_dispatcher
    if _default_dispatcher is None:
        from .subscription import get_subscription_registry

        _default_dispatcher = EventDispatcher(get_subscription_registry())
    return _default_dispatcher


def set_event_dispatcher(dispatcher: EventDispatcher) -> None:
    """Set the global event dispatcher (mainly for testing)."""
    global _default_dispatcher
    _default_dispatcher = dispatcher

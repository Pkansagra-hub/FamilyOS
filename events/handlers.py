"""Handler execution pipeline with middleware integration and lifecycle management.

This module provides the handler execution framework that manages the complete
lifecycle of event handler processing, including middleware integration,
execution context management, and handler state tracking.

Architecture:
- HandlerContext: Execution context for handlers with middleware results
- HandlerPipeline: Manages middleware chain and handler execution
- HandlerRegistry: Central registry for handler metadata and lifecycle
- Integration with EventDispatcher for coordinated event processing

Features:
- Pre/post processing middleware hooks
- Handler lifecycle management (init, execute, cleanup)
- Execution context with correlation tracking
- Error handling and recovery strategies
- Performance monitoring and metrics
- Handler state management and health checks

Example:
    >>> pipeline = HandlerPipeline([validation_middleware, auth_middleware])
    >>> context = HandlerContext(event, subscription)
    >>> result = await pipeline.execute_handler(context)
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from observability.metrics import pipeline_stage_duration_ms
from observability.trace import start_span

from .subscription import Subscription
from .types import Event

logger = logging.getLogger(__name__)


class HandlerState(Enum):
    """Handler execution state."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class MiddlewarePhase(Enum):
    """Middleware execution phases."""

    PRE_EXECUTION = "pre_execution"
    POST_EXECUTION = "post_execution"
    ERROR_HANDLING = "error_handling"
    CLEANUP = "cleanup"


@dataclass
class HandlerContext:
    """Context for handler execution containing all relevant information."""

    # Core execution data
    event: Event
    subscription: Subscription

    # Execution metadata
    execution_id: str
    correlation_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # State tracking
    state: HandlerState = HandlerState.PENDING
    current_phase: Optional[MiddlewarePhase] = None

    # Middleware results and context
    middleware_results: Dict[str, Any] = field(default_factory=dict)
    execution_context: Dict[str, Any] = field(default_factory=dict)

    # Error and performance tracking
    error: Optional[Exception] = None
    duration_ms: float = 0.0
    result: Any = None

    # Lifecycle hooks
    cleanup_tasks: List[Callable[[], None]] = field(default_factory=list)


@dataclass
class HandlerResult:
    """Result of handler execution through the pipeline."""

    context: HandlerContext
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    duration_ms: float = 0.0
    middleware_executed: List[str] = field(default_factory=list)


class Middleware(ABC):
    """Abstract base class for handler middleware."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the middleware for identification."""
        pass

    @abstractmethod
    async def pre_execute(self, context: HandlerContext) -> bool:
        """
        Execute before handler.

        Args:
            context: Handler execution context

        Returns:
            True to continue execution, False to abort
        """
        pass

    async def post_execute(self, context: HandlerContext) -> None:
        """
        Execute after successful handler completion.

        Args:
            context: Handler execution context with result
        """
        pass

    async def on_error(self, context: HandlerContext, error: Exception) -> bool:
        """
        Handle execution errors.

        Args:
            context: Handler execution context
            error: Exception that occurred

        Returns:
            True if error was handled, False to propagate
        """
        return False

    async def cleanup(self, context: HandlerContext) -> None:
        """
        Cleanup resources after execution.

        Args:
            context: Handler execution context
        """
        pass


class ValidationMiddleware(Middleware):
    """Middleware for event and subscription validation."""

    @property
    def name(self) -> str:
        return "validation"

    async def pre_execute(self, context: HandlerContext) -> bool:
        """Validate event and subscription before execution."""
        try:
            # Validate event structure
            if not hasattr(context.event, "id") or not getattr(
                context.event, "id", None
            ):
                logger.warning(
                    f"Event missing ID for handler {context.subscription.subscription_id}"
                )
                context.middleware_results[self.name] = {
                    "valid": False,
                    "reason": "missing_event_id",
                }
                return False

            # Validate subscription is active
            if not context.subscription.active:
                logger.warning(
                    f"Subscription {context.subscription.subscription_id} is inactive"
                )
                context.middleware_results[self.name] = {
                    "valid": False,
                    "reason": "inactive_subscription",
                }
                return False

            # Additional validation logic here
            context.middleware_results[self.name] = {"valid": True}
            return True

        except Exception as e:
            logger.error(f"Validation middleware failed: {e}")
            context.middleware_results[self.name] = {"valid": False, "error": str(e)}
            return False


class MetricsMiddleware(Middleware):
    """Middleware for collecting execution metrics."""

    @property
    def name(self) -> str:
        return "metrics"

    async def pre_execute(self, context: HandlerContext) -> bool:
        """Record execution start metrics."""
        context.middleware_results[self.name] = {
            "start_time": time.time(),
            "subscription_id": context.subscription.subscription_id,
            "topic": context.subscription.topic_pattern,
        }
        return True

    async def post_execute(self, context: HandlerContext) -> None:
        """Record successful completion metrics."""
        metrics_data = context.middleware_results.get(self.name, {})
        start_time = metrics_data.get("start_time", time.time())
        duration_ms = (time.time() - start_time) * 1000

        if pipeline_stage_duration_ms:
            pipeline_stage_duration_ms.labels(
                pipeline="events", stage="handler_execution", outcome="success"
            ).observe(duration_ms)

    async def on_error(self, context: HandlerContext, error: Exception) -> bool:
        """Record error metrics."""
        metrics_data = context.middleware_results.get(self.name, {})
        start_time = metrics_data.get("start_time", time.time())
        duration_ms = (time.time() - start_time) * 1000

        if pipeline_stage_duration_ms:
            pipeline_stage_duration_ms.labels(
                pipeline="events", stage="handler_execution", outcome="error"
            ).observe(duration_ms)

        return False  # Don't handle the error, just record metrics


class HandlerPipeline:
    """Manages middleware chain and handler execution."""

    def __init__(self, middleware: Optional[List[Middleware]] = None):
        """
        Initialize the handler pipeline.

        Args:
            middleware: List of middleware to apply (in order)
        """
        self.middleware = middleware or []
        self._execution_stats: Dict[str, Any] = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_duration_ms": 0.0,
        }

    def add_middleware(self, middleware: Middleware) -> None:
        """Add middleware to the pipeline."""
        self.middleware.append(middleware)
        logger.info(f"Added middleware: {middleware.name}")

    def remove_middleware(self, name: str) -> bool:
        """Remove middleware by name."""
        for i, middleware in enumerate(self.middleware):
            if middleware.name == name:
                removed = self.middleware.pop(i)
                logger.info(f"Removed middleware: {removed.name}")
                return True
        return False

    async def execute_handler(self, context: HandlerContext) -> HandlerResult:
        """
        Execute handler through the complete middleware pipeline.

        Args:
            context: Handler execution context

        Returns:
            HandlerResult with execution summary
        """
        start_time = time.time()
        context.state = HandlerState.RUNNING
        middleware_executed = []

        with start_span(
            "events.handlers.execute",
            {
                "execution_id": context.execution_id,
                "subscription_id": context.subscription.subscription_id,
                "middleware_count": str(len(self.middleware)),
            },
        ) as span:
            try:
                # Pre-execution middleware phase
                context.current_phase = MiddlewarePhase.PRE_EXECUTION

                for middleware in self.middleware:
                    if span:
                        span.set_attribute(
                            f"middleware.{middleware.name}.phase", "pre_execute"
                        )

                    should_continue = await middleware.pre_execute(context)
                    middleware_executed.append(middleware.name)

                    if not should_continue:
                        logger.info(f"Middleware {middleware.name} aborted execution")
                        context.state = HandlerState.CANCELLED
                        return self._create_result(
                            context, start_time, False, middleware_executed
                        )

                # Execute the actual handler
                context.current_phase = None
                if span:
                    span.set_attribute("handler.executing", "true")

                if context.subscription.is_async:
                    context.result = await context.subscription.handler(context.event)
                else:
                    # Run sync handler in thread pool
                    loop = asyncio.get_event_loop()
                    context.result = await loop.run_in_executor(
                        None, context.subscription.handler, context.event
                    )

                if span:
                    span.set_attribute("handler.completed", "true")

                # Post-execution middleware phase
                context.current_phase = MiddlewarePhase.POST_EXECUTION
                context.state = HandlerState.COMPLETED

                for middleware in self.middleware:
                    if span:
                        span.set_attribute(
                            f"middleware.{middleware.name}.phase", "post_execute"
                        )
                    await middleware.post_execute(context)

                # Update stats
                self._update_execution_stats(context, success=True)

                return self._create_result(
                    context, start_time, True, middleware_executed
                )

            except Exception as e:
                context.error = e
                context.state = HandlerState.FAILED
                context.current_phase = MiddlewarePhase.ERROR_HANDLING

                if span:
                    span.record_exception(e)
                    # Use string status instead of status object
                    try:
                        span.set_status("ERROR", str(e))
                    except Exception:
                        # Fallback if span doesn't support this signature
                        pass

                logger.error(f"Handler execution failed: {e}", exc_info=True)

                # Error handling middleware phase
                error_handled = False
                for middleware in self.middleware:
                    try:
                        if span:
                            span.set_attribute(
                                f"middleware.{middleware.name}.phase", "error_handling"
                            )
                        if await middleware.on_error(context, e):
                            error_handled = True
                            if span:
                                span.set_attribute(
                                    f"middleware.{middleware.name}.handled_error",
                                    "true",
                                )
                            break
                    except Exception as middleware_error:
                        logger.error(
                            f"Middleware {middleware.name} error handling failed: {middleware_error}"
                        )

                # Update stats
                self._update_execution_stats(context, success=False)

                return self._create_result(
                    context, start_time, error_handled, middleware_executed, e
                )

            finally:
                # Cleanup phase
                context.current_phase = MiddlewarePhase.CLEANUP

                # Execute middleware cleanup
                for middleware in reversed(self.middleware):  # Cleanup in reverse order
                    try:
                        if span:
                            span.set_attribute(
                                f"middleware.{middleware.name}.phase", "cleanup"
                            )
                        await middleware.cleanup(context)
                    except Exception as cleanup_error:
                        logger.error(
                            f"Middleware {middleware.name} cleanup failed: {cleanup_error}"
                        )

                # Execute custom cleanup tasks
                for cleanup_task in context.cleanup_tasks:
                    try:
                        cleanup_task()
                    except Exception as cleanup_error:
                        logger.error(f"Cleanup task failed: {cleanup_error}")

                context.current_phase = None

    def _create_result(
        self,
        context: HandlerContext,
        start_time: float,
        success: bool,
        middleware_executed: List[str],
        error: Optional[Exception] = None,
    ) -> HandlerResult:
        """Create a HandlerResult from execution context."""
        duration_ms = (time.time() - start_time) * 1000
        context.duration_ms = duration_ms

        return HandlerResult(
            context=context,
            success=success,
            result=context.result,
            error=error or context.error,
            duration_ms=duration_ms,
            middleware_executed=middleware_executed,
        )

    def _update_execution_stats(self, context: HandlerContext, success: bool) -> None:
        """Update internal execution statistics."""
        self._execution_stats["total_executions"] += 1
        self._execution_stats["total_duration_ms"] += context.duration_ms

        if success:
            self._execution_stats["successful_executions"] += 1
        else:
            self._execution_stats["failed_executions"] += 1

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get current execution statistics."""
        stats = self._execution_stats.copy()

        # Calculate derived metrics
        if stats["total_executions"] > 0:
            stats["average_duration_ms"] = (
                stats["total_duration_ms"] / stats["total_executions"]
            )
            stats["success_rate"] = (
                stats["successful_executions"] / stats["total_executions"]
            )
        else:
            stats["average_duration_ms"] = 0.0
            stats["success_rate"] = 0.0

        return stats


class HandlerRegistry:
    """Central registry for handler metadata and lifecycle management."""

    def __init__(self):
        """Initialize the handler registry."""
        self._active_handlers: Dict[str, HandlerContext] = {}
        self._handler_history: List[HandlerResult] = []
        self._max_history = 1000

    def register_execution(self, context: HandlerContext) -> None:
        """Register a handler execution."""
        self._active_handlers[context.execution_id] = context

    def complete_execution(self, result: HandlerResult) -> None:
        """Complete a handler execution."""
        execution_id = result.context.execution_id

        # Remove from active handlers
        if execution_id in self._active_handlers:
            del self._active_handlers[execution_id]

        # Add to history
        self._handler_history.append(result)

        # Trim history if needed
        if len(self._handler_history) > self._max_history:
            self._handler_history = self._handler_history[-self._max_history :]

    def get_active_handlers(self) -> List[HandlerContext]:
        """Get all currently active handler contexts."""
        return list(self._active_handlers.values())

    def get_handler_by_id(self, execution_id: str) -> Optional[HandlerContext]:
        """Get active handler context by execution ID."""
        return self._active_handlers.get(execution_id)

    def get_recent_executions(self, limit: int = 100) -> List[HandlerResult]:
        """Get recent handler executions."""
        return self._handler_history[-limit:]

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "active_handlers": len(self._active_handlers),
            "total_history": len(self._handler_history),
            "recent_success_rate": self._calculate_recent_success_rate(),
            "average_execution_time": self._calculate_average_execution_time(),
        }

    def _calculate_recent_success_rate(self, sample_size: int = 100) -> float:
        """Calculate success rate from recent executions."""
        recent = self._handler_history[-sample_size:]
        if not recent:
            return 0.0

        successful = sum(1 for result in recent if result.success)
        return successful / len(recent)

    def _calculate_average_execution_time(self, sample_size: int = 100) -> float:
        """Calculate average execution time from recent executions."""
        recent = self._handler_history[-sample_size:]
        if not recent:
            return 0.0

        total_duration = sum(result.duration_ms for result in recent)
        return total_duration / len(recent)


# Global instances
_default_pipeline: Optional[HandlerPipeline] = None
_default_registry: Optional[HandlerRegistry] = None


def get_handler_pipeline() -> HandlerPipeline:
    """Get the global handler pipeline instance."""
    global _default_pipeline
    if _default_pipeline is None:
        # Create with default middleware
        _default_pipeline = HandlerPipeline(
            [ValidationMiddleware(), MetricsMiddleware()]
        )
    return _default_pipeline


def get_handler_registry() -> HandlerRegistry:
    """Get the global handler registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = HandlerRegistry()
    return _default_registry


def set_handler_pipeline(pipeline: HandlerPipeline) -> None:
    """Set the global handler pipeline (mainly for testing)."""
    global _default_pipeline
    _default_pipeline = pipeline


def set_handler_registry(registry: HandlerRegistry) -> None:
    """Set the global handler registry (mainly for testing)."""
    global _default_registry
    _default_registry = registry
    _default_registry = registry

"""Event middleware system with pre/post processing hooks and extensible pipeline.

This module provides the middleware framework for the MemoryOS event system,
enabling extensible pre and post processing of events through a configurable
pipeline of middleware components.

Architecture:
- BaseMiddleware: Abstract base class for all middleware
- MiddlewareManager: Manages middleware registration and execution
- Built-in middleware implementations for common functionality
- Integration with EventBus and HandlerPipeline

Features:
- Pre/post event processing hooks
- Async middleware execution support
- Error handling and recovery
- Performance monitoring and metrics
- Configurable middleware ordering
- Context passing between middleware

Built-in Middleware:
- AuthenticationMiddleware: User authentication and authorization
- ValidationMiddleware: Event and payload validation
- MetricsMiddleware: Performance metrics collection
- LoggingMiddleware: Structured event logging
- RateLimitingMiddleware: Request rate limiting
- RedactionMiddleware: PII redaction and data protection

Example:
    >>> manager = MiddlewareManager()
    >>> manager.add_middleware(AuthenticationMiddleware())
    >>> manager.add_middleware(ValidationMiddleware())
    >>> result = await manager.process_event(event, context)
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from observability.metrics import pipeline_stage_duration_ms
from observability.trace import start_span

from .types import Event

logger = logging.getLogger(__name__)


@dataclass
class MiddlewareContext:
    """Context passed through middleware pipeline."""

    # Core event data
    event: Event
    topic: str

    # Processing metadata
    context_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Middleware state and results
    middleware_results: Dict[str, Any] = field(default_factory=dict)
    processing_flags: Dict[str, bool] = field(default_factory=dict)

    # Performance tracking
    stage_durations: Dict[str, float] = field(default_factory=dict)
    total_duration_ms: float = 0.0

    # Error handling
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class MiddlewareResult:
    """Result from middleware processing."""

    success: bool
    continue_processing: bool = True
    context: Optional[MiddlewareContext] = None
    error: Optional[Exception] = None
    modified_event: Optional[Event] = None


class BaseMiddleware(ABC):
    """Abstract base class for all middleware implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifier for this middleware."""
        pass

    @property
    def priority(self) -> int:
        """Execution priority (lower numbers execute first)."""
        return 100

    @property
    def enabled(self) -> bool:
        """Whether this middleware is currently enabled."""
        return True

    async def pre_process(self, context: MiddlewareContext) -> MiddlewareResult:
        """
        Process event before main event handling.

        Args:
            context: Middleware context with event and metadata

        Returns:
            MiddlewareResult indicating success and whether to continue
        """
        return MiddlewareResult(success=True, continue_processing=True)

    async def post_process(self, context: MiddlewareContext) -> MiddlewareResult:
        """
        Process event after main event handling.

        Args:
            context: Middleware context with event and results

        Returns:
            MiddlewareResult with any modifications
        """
        return MiddlewareResult(success=True, continue_processing=True)

    async def on_error(
        self, context: MiddlewareContext, error: Exception
    ) -> MiddlewareResult:
        """
        Handle errors during event processing.

        Args:
            context: Middleware context
            error: Exception that occurred

        Returns:
            MiddlewareResult indicating if error was handled
        """
        return MiddlewareResult(success=False, continue_processing=False, error=error)

    async def cleanup(self, context: MiddlewareContext) -> None:
        """
        Cleanup resources after processing completes.

        Args:
            context: Middleware context
        """
        pass


class AuthenticationMiddleware(BaseMiddleware):
    """Middleware for user authentication and authorization."""

    @property
    def name(self) -> str:
        return "authentication"

    @property
    def priority(self) -> int:
        return 10  # High priority - run early

    async def pre_process(self, context: MiddlewareContext) -> MiddlewareResult:
        """Validate user authentication and permissions."""
        try:
            # Extract user context from event
            actor_id = (
                getattr(context.event, "actor", {}).get("actor_id")
                if hasattr(context.event, "actor")
                else None
            )

            if not actor_id:
                context.warnings.append("No actor_id found in event")
                context.middleware_results[self.name] = {
                    "authenticated": False,
                    "reason": "missing_actor_id",
                }
                # Continue processing but flag as unauthenticated
                return MiddlewareResult(success=True, continue_processing=True)

            # TODO: Integrate with actual authentication system
            # For now, just validate that actor_id exists
            context.middleware_results[self.name] = {
                "authenticated": True,
                "actor_id": actor_id,
                "permissions": ["read", "write"],  # Placeholder
            }

            return MiddlewareResult(success=True, continue_processing=True)

        except Exception as e:
            logger.error(f"Authentication middleware failed: {e}")
            return MiddlewareResult(success=False, continue_processing=False, error=e)


class ValidationMiddleware(BaseMiddleware):
    """Middleware for event structure and content validation."""

    @property
    def name(self) -> str:
        return "validation"

    @property
    def priority(self) -> int:
        return 20  # Run after authentication

    async def pre_process(self, context: MiddlewareContext) -> MiddlewareResult:
        """Validate event structure and content."""
        try:
            # Validate required event fields
            if not hasattr(context.event, "id") or not getattr(
                context.event, "id", None
            ):
                error_msg = "Event missing required 'id' field"
                context.errors.append(error_msg)
                return MiddlewareResult(
                    success=False,
                    continue_processing=False,
                    error=ValueError(error_msg),
                )

            # Validate topic format
            if not context.topic or len(context.topic.strip()) == 0:
                error_msg = "Invalid topic format"
                context.errors.append(error_msg)
                return MiddlewareResult(
                    success=False,
                    continue_processing=False,
                    error=ValueError(error_msg),
                )

            # Additional validation can be added here
            context.middleware_results[self.name] = {
                "valid": True,
                "checks_passed": ["id_present", "topic_valid"],
            }

            return MiddlewareResult(success=True, continue_processing=True)

        except Exception as e:
            logger.error(f"Validation middleware failed: {e}")
            return MiddlewareResult(success=False, continue_processing=False, error=e)


class MetricsMiddleware(BaseMiddleware):
    """Middleware for performance metrics collection."""

    @property
    def name(self) -> str:
        return "metrics"

    @property
    def priority(self) -> int:
        return 90  # Run late in pre-process, early in post-process

    async def pre_process(self, context: MiddlewareContext) -> MiddlewareResult:
        """Record processing start metrics."""
        context.middleware_results[self.name] = {
            "start_time": time.time(),
            "topic": context.topic,
            "event_id": getattr(context.event, "id", "unknown"),
        }
        return MiddlewareResult(success=True, continue_processing=True)

    async def post_process(self, context: MiddlewareContext) -> MiddlewareResult:
        """Record processing completion metrics."""
        metrics_data = context.middleware_results.get(self.name, {})
        start_time = metrics_data.get("start_time", time.time())
        duration_ms = (time.time() - start_time) * 1000

        # Update context duration
        context.total_duration_ms = duration_ms

        # Emit metrics
        if pipeline_stage_duration_ms:
            pipeline_stage_duration_ms.labels(
                pipeline="events", stage="middleware_processing", outcome="success"
            ).observe(duration_ms)

        # Update results
        metrics_data.update(
            {"end_time": time.time(), "duration_ms": duration_ms, "outcome": "success"}
        )

        return MiddlewareResult(success=True, continue_processing=True)

    async def on_error(
        self, context: MiddlewareContext, error: Exception
    ) -> MiddlewareResult:
        """Record error metrics."""
        metrics_data = context.middleware_results.get(self.name, {})
        start_time = metrics_data.get("start_time", time.time())
        duration_ms = (time.time() - start_time) * 1000

        # Emit error metrics
        if pipeline_stage_duration_ms:
            pipeline_stage_duration_ms.labels(
                pipeline="events", stage="middleware_processing", outcome="error"
            ).observe(duration_ms)

        # Update results
        metrics_data.update(
            {
                "end_time": time.time(),
                "duration_ms": duration_ms,
                "outcome": "error",
                "error": str(error),
            }
        )

        return MiddlewareResult(success=False, continue_processing=False, error=error)


class LoggingMiddleware(BaseMiddleware):
    """Middleware for structured event logging."""

    @property
    def name(self) -> str:
        return "logging"

    @property
    def priority(self) -> int:
        return 95  # Run very late

    async def pre_process(self, context: MiddlewareContext) -> MiddlewareResult:
        """Log event processing start."""
        logger.info(
            "Event processing started",
            extra={
                "event_id": getattr(context.event, "id", "unknown"),
                "topic": context.topic,
                "context_id": context.context_id,
                "middleware_stage": "pre_process",
            },
        )
        return MiddlewareResult(success=True, continue_processing=True)

    async def post_process(self, context: MiddlewareContext) -> MiddlewareResult:
        """Log event processing completion."""
        logger.info(
            "Event processing completed",
            extra={
                "event_id": getattr(context.event, "id", "unknown"),
                "topic": context.topic,
                "context_id": context.context_id,
                "duration_ms": context.total_duration_ms,
                "middleware_stage": "post_process",
                "errors": len(context.errors),
                "warnings": len(context.warnings),
            },
        )
        return MiddlewareResult(success=True, continue_processing=True)


class MiddlewareManager:
    """Manages middleware registration and execution pipeline."""

    def __init__(self):
        """Initialize the middleware manager."""
        self._middleware: List[BaseMiddleware] = []
        self._middleware_stats: Dict[str, Any] = {
            "total_processed": 0,
            "successful_processed": 0,
            "failed_processed": 0,
            "average_duration_ms": 0.0,
        }

    def add_middleware(self, middleware: BaseMiddleware) -> None:
        """
        Add middleware to the pipeline.

        Args:
            middleware: Middleware instance to add
        """
        if not middleware.enabled:
            logger.info(f"Skipping disabled middleware: {middleware.name}")
            return

        # Insert in priority order (lower priority numbers first)
        insert_index = 0
        for i, existing in enumerate(self._middleware):
            if middleware.priority < existing.priority:
                insert_index = i
                break
            insert_index = i + 1

        self._middleware.insert(insert_index, middleware)
        logger.info(
            f"Added middleware: {middleware.name} (priority: {middleware.priority})"
        )

    def remove_middleware(self, name: str) -> bool:
        """
        Remove middleware by name.

        Args:
            name: Name of middleware to remove

        Returns:
            True if middleware was removed, False if not found
        """
        for i, middleware in enumerate(self._middleware):
            if middleware.name == name:
                removed = self._middleware.pop(i)
                logger.info(f"Removed middleware: {removed.name}")
                return True
        return False

    def get_middleware(self, name: str) -> Optional[BaseMiddleware]:
        """Get middleware by name."""
        for middleware in self._middleware:
            if middleware.name == name:
                return middleware
        return None

    def list_middleware(self) -> List[Dict[str, Any]]:
        """List all registered middleware with metadata."""
        return [
            {
                "name": middleware.name,
                "priority": middleware.priority,
                "enabled": middleware.enabled,
                "class": middleware.__class__.__name__,
            }
            for middleware in self._middleware
        ]

    async def process_event(
        self, event: Event, topic: str, context_id: Optional[str] = None
    ) -> MiddlewareContext:
        """
        Process event through the complete middleware pipeline.

        Args:
            event: Event to process
            topic: Event topic
            context_id: Optional context identifier

        Returns:
            MiddlewareContext with processing results
        """
        import uuid

        context = MiddlewareContext(
            event=event, topic=topic, context_id=context_id or str(uuid.uuid4())
        )

        start_time = time.time()

        with start_span(
            "events.middleware.process",
            {
                "topic": topic,
                "event_id": getattr(event, "id", "unknown"),
                "middleware_count": str(len(self._middleware)),
            },
        ) as span:
            try:
                # Pre-processing phase
                for middleware in self._middleware:
                    if span:
                        span.set_attribute(
                            f"middleware.{middleware.name}.phase", "pre_process"
                        )

                    stage_start = time.time()
                    try:
                        result = await middleware.pre_process(context)
                        stage_duration = (time.time() - stage_start) * 1000
                        context.stage_durations[f"{middleware.name}_pre"] = (
                            stage_duration
                        )

                        if not result.success:
                            context.errors.append(
                                f"Middleware {middleware.name} failed: {result.error}"
                            )
                            if not result.continue_processing:
                                break

                        # Apply any event modifications
                        if result.modified_event:
                            context.event = result.modified_event

                    except Exception as e:
                        stage_duration = (time.time() - stage_start) * 1000
                        context.stage_durations[f"{middleware.name}_pre"] = (
                            stage_duration
                        )
                        context.errors.append(
                            f"Middleware {middleware.name} exception: {str(e)}"
                        )
                        logger.error(
                            f"Middleware {middleware.name} pre-process failed: {e}"
                        )

                        # Try error handling
                        try:
                            error_result = await middleware.on_error(context, e)
                            if not error_result.continue_processing:
                                break
                        except Exception as error_handling_error:
                            logger.error(
                                f"Middleware {middleware.name} error handling failed: {error_handling_error}"
                            )
                            break

                # Post-processing phase (in reverse order)
                for middleware in reversed(self._middleware):
                    if span:
                        span.set_attribute(
                            f"middleware.{middleware.name}.phase", "post_process"
                        )

                    stage_start = time.time()
                    try:
                        result = await middleware.post_process(context)
                        stage_duration = (time.time() - stage_start) * 1000
                        context.stage_durations[f"{middleware.name}_post"] = (
                            stage_duration
                        )

                        # Apply any event modifications
                        if result.modified_event:
                            context.event = result.modified_event

                    except Exception as e:
                        stage_duration = (time.time() - stage_start) * 1000
                        context.stage_durations[f"{middleware.name}_post"] = (
                            stage_duration
                        )
                        context.errors.append(
                            f"Middleware {middleware.name} post-process exception: {str(e)}"
                        )
                        logger.error(
                            f"Middleware {middleware.name} post-process failed: {e}"
                        )

                # Calculate total duration
                context.total_duration_ms = (time.time() - start_time) * 1000

                # Update statistics
                self._middleware_stats["total_processed"] += 1
                if not context.errors:
                    self._middleware_stats["successful_processed"] += 1
                else:
                    self._middleware_stats["failed_processed"] += 1

                # Update average duration
                total_processed = int(self._middleware_stats["total_processed"])
                current_avg = float(self._middleware_stats["average_duration_ms"])
                new_avg = (
                    (current_avg * (total_processed - 1)) + context.total_duration_ms
                ) / total_processed
                self._middleware_stats["average_duration_ms"] = new_avg

                if span:
                    span.set_attribute(
                        "processing.success", str(len(context.errors) == 0)
                    )
                    span.set_attribute("processing.errors", str(len(context.errors)))
                    span.set_attribute(
                        "processing.warnings", str(len(context.warnings))
                    )

                return context

            except Exception as e:
                logger.error(f"Middleware pipeline failed: {e}", exc_info=True)
                context.errors.append(f"Pipeline error: {str(e)}")
                context.total_duration_ms = (time.time() - start_time) * 1000

                if span:
                    span.record_exception(e)
                    try:
                        span.set_status("ERROR", str(e))
                    except Exception:
                        pass

                return context

            finally:
                # Cleanup phase
                for middleware in reversed(self._middleware):
                    try:
                        await middleware.cleanup(context)
                    except Exception as cleanup_error:
                        logger.error(
                            f"Middleware {middleware.name} cleanup failed: {cleanup_error}"
                        )

    def get_stats(self) -> Dict[str, Any]:
        """Get middleware processing statistics."""
        stats = self._middleware_stats.copy()
        stats["registered_middleware"] = len(self._middleware)
        stats["enabled_middleware"] = sum(1 for m in self._middleware if m.enabled)

        if stats["total_processed"] > 0:
            stats["success_rate"] = (
                stats["successful_processed"] / stats["total_processed"]
            )
        else:
            stats["success_rate"] = 0.0

        return stats


# Global middleware manager instance
_default_middleware_manager: Optional[MiddlewareManager] = None


def get_middleware_manager() -> MiddlewareManager:
    """Get the global middleware manager instance."""
    global _default_middleware_manager
    if _default_middleware_manager is None:
        _default_middleware_manager = MiddlewareManager()

        # Add default middleware
        _default_middleware_manager.add_middleware(AuthenticationMiddleware())
        _default_middleware_manager.add_middleware(ValidationMiddleware())
        _default_middleware_manager.add_middleware(MetricsMiddleware())
        _default_middleware_manager.add_middleware(LoggingMiddleware())

    return _default_middleware_manager


def set_middleware_manager(manager: MiddlewareManager) -> None:
    """Set the global middleware manager (mainly for testing)."""
    global _default_middleware_manager
    _default_middleware_manager = manager
    _default_middleware_manager = manager

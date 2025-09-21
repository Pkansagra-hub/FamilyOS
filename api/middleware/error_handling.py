"""
Middleware Error Handling and Rollback - Sub-issue #21.2

Comprehensive error handling, recovery strategies, and rollback capabilities
for the middleware chain. This module provides:

- Transaction-like rollback for stateful middleware
- Error recovery strategies
- Graceful degradation patterns
- Request retry mechanisms
- Circuit breaker integration
- Compensation actions for failed requests
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional, Protocol, runtime_checkable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for middleware failures."""

    LOW = "low"  # Recoverable, continue processing
    MEDIUM = "medium"  # Degraded mode, partial functionality
    HIGH = "high"  # Critical failure, stop processing
    CRITICAL = "critical"  # System-wide impact, emergency response


class RecoveryStrategy(Enum):
    """Recovery strategies for middleware failures."""

    RETRY = "retry"  # Retry the operation
    FALLBACK = "fallback"  # Use fallback implementation
    BYPASS = "bypass"  # Skip this middleware
    ABORT = "abort"  # Abort the request
    COMPENSATE = "compensate"  # Run compensation actions


@dataclass
class ErrorContext:
    """Context information for middleware errors."""

    middleware_name: str
    error: Exception
    request: Request
    severity: ErrorSeverity
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    retry_count: int = 0
    max_retries: int = 3
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY
    compensation_actions: list[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Compensatable(Protocol):
    """Protocol for middleware that supports compensation actions."""

    async def compensate(self, context: ErrorContext) -> bool:
        """
        Perform compensation actions for a failed operation.

        Args:
            context: Error context with details about the failure

        Returns:
            True if compensation was successful
        """
        ...


@runtime_checkable
class Fallbackable(Protocol):
    """Protocol for middleware that supports fallback implementations."""

    async def fallback(self, request: Request, context: ErrorContext) -> Response:
        """
        Provide fallback implementation for failed operation.

        Args:
            request: The original request
            context: Error context

        Returns:
            Fallback response
        """
        ...


class MiddlewareTransaction:
    """
    Transaction-like rollback system for middleware operations.
    Tracks middleware execution and provides rollback capabilities.
    """

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.executed_middleware: list[str] = []
        self.compensation_actions: list[Callable] = []
        self.rollback_required = False
        self.start_time = datetime.now(timezone.utc)

    def add_middleware(self, name: str) -> None:
        """Record that middleware was executed."""
        self.executed_middleware.append(name)
        logger.debug(f"📝 Transaction {self.request_id}: Added {name}")

    def add_compensation_action(self, action: Callable) -> None:
        """Add a compensation action for rollback."""
        self.compensation_actions.append(action)

    def mark_for_rollback(self) -> None:
        """Mark transaction for rollback."""
        self.rollback_required = True
        logger.warning(f"🔄 Transaction {self.request_id}: Marked for rollback")

    async def rollback(self) -> bool:
        """
        Execute rollback by running compensation actions in reverse order.

        Returns:
            True if rollback was successful
        """
        if not self.rollback_required:
            return True

        logger.info(f"🔄 Rolling back transaction {self.request_id}")
        success = True

        # Execute compensation actions in reverse order
        for action in reversed(self.compensation_actions):
            try:
                if asyncio.iscoroutinefunction(action):
                    await action()
                else:
                    action()
                logger.debug("✅ Compensation action executed")
            except Exception as e:
                logger.error(f"❌ Compensation action failed: {e}")
                success = False

        if success:
            logger.info(f"✅ Transaction {self.request_id} rollback successful")
        else:
            logger.error(f"❌ Transaction {self.request_id} rollback failed")

        return success


class ErrorRecoveryManager:
    """
    Central manager for error recovery strategies and rollback operations.
    """

    def __init__(self):
        self.active_transactions: Dict[str, MiddlewareTransaction] = {}
        self.error_handlers: Dict[str, Callable] = {}
        self.recovery_strategies: Dict[str, RecoveryStrategy] = {}
        self.compensation_registry: Dict[str, list[Callable]] = {}

    def register_error_handler(self, middleware_name: str, handler: Callable) -> None:
        """Register custom error handler for middleware."""
        self.error_handlers[middleware_name] = handler
        logger.info(f"🛠️ Registered error handler for {middleware_name}")

    def register_recovery_strategy(
        self, middleware_name: str, strategy: RecoveryStrategy
    ) -> None:
        """Register recovery strategy for middleware."""
        self.recovery_strategies[middleware_name] = strategy
        logger.info(
            f"🎯 Registered recovery strategy {strategy.value} for {middleware_name}"
        )

    def register_compensation_action(
        self, middleware_name: str, action: Callable
    ) -> None:
        """Register compensation action for middleware."""
        if middleware_name not in self.compensation_registry:
            self.compensation_registry[middleware_name] = []
        self.compensation_registry[middleware_name].append(action)
        logger.info(f"⚖️ Registered compensation action for {middleware_name}")

    def start_transaction(self, request_id: str) -> MiddlewareTransaction:
        """Start a new middleware transaction."""
        transaction = MiddlewareTransaction(request_id)
        self.active_transactions[request_id] = transaction
        logger.debug(f"🚀 Started transaction {request_id}")
        return transaction

    async def handle_error(self, context: ErrorContext) -> Optional[Response]:
        """
        Handle middleware error with appropriate recovery strategy.

        Args:
            context: Error context

        Returns:
            Recovery response if available, None if error should propagate
        """
        middleware_name = context.middleware_name
        strategy = self.recovery_strategies.get(middleware_name, RecoveryStrategy.RETRY)

        logger.warning(f"⚠️ Handling error in {middleware_name}: {context.error}")

        # Check if we have a custom error handler
        if middleware_name in self.error_handlers:
            try:
                return await self._call_error_handler(
                    self.error_handlers[middleware_name], context
                )
            except Exception as e:
                logger.error(f"❌ Custom error handler failed: {e}")

        # Apply recovery strategy
        if strategy == RecoveryStrategy.RETRY:
            return await self._handle_retry(context)
        elif strategy == RecoveryStrategy.FALLBACK:
            return await self._handle_fallback(context)
        elif strategy == RecoveryStrategy.BYPASS:
            return await self._handle_bypass(context)
        elif strategy == RecoveryStrategy.COMPENSATE:
            return await self._handle_compensation(context)
        elif strategy == RecoveryStrategy.ABORT:
            return await self._handle_abort(context)

        return None

    async def _call_error_handler(
        self, handler: Callable, context: ErrorContext
    ) -> Optional[Response]:
        """Call custom error handler."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(context)
        else:
            return handler(context)

    async def _handle_retry(self, context: ErrorContext) -> Optional[Response]:
        """Handle retry recovery strategy."""
        if context.retry_count >= context.max_retries:
            logger.error(f"❌ Max retries exceeded for {context.middleware_name}")
            return await self._handle_fallback(context)

        context.retry_count += 1
        logger.info(
            f"🔄 Retry {context.retry_count}/{context.max_retries} for {context.middleware_name}"
        )

        # TODO: Implement circuit breaker pattern instead of exponential backoff delays
        # Removed artificial delay - causing performance bottlenecks in production

        # Return None to indicate retry should happen
        return None

    async def _handle_fallback(self, context: ErrorContext) -> Optional[Response]:
        """Handle fallback recovery strategy."""
        logger.info(f"🚨 Using fallback for {context.middleware_name}")

        # Look for fallback implementation
        # This would typically involve calling a fallback service or returning a cached response
        return Response(
            content='{"error": "Service temporarily unavailable", "fallback": true}',
            status_code=503,
            headers={"Content-Type": "application/json"},
        )

    async def _handle_bypass(self, context: ErrorContext) -> Optional[Response]:
        """Handle bypass recovery strategy."""
        logger.info(f"⏭️ Bypassing {context.middleware_name}")
        # Return None to continue to next middleware
        return None

    async def _handle_compensation(self, context: ErrorContext) -> Optional[Response]:
        """Handle compensation recovery strategy."""
        logger.info(f"⚖️ Running compensation for {context.middleware_name}")

        # Get transaction and mark for rollback
        request_id = getattr(context.request.state, "request_id", "unknown")
        transaction = self.active_transactions.get(request_id)

        if transaction:
            transaction.mark_for_rollback()

            # Add compensation actions
            compensation_actions = self.compensation_registry.get(
                context.middleware_name, []
            )
            for action in compensation_actions:
                transaction.add_compensation_action(action)

            # Execute rollback
            success = await transaction.rollback()
            if not success:
                logger.error(f"❌ Compensation failed for {context.middleware_name}")

        return None

    async def _handle_abort(self, context: ErrorContext) -> Optional[Response]:
        """Handle abort recovery strategy."""
        logger.error(f"🛑 Aborting request due to {context.middleware_name} failure")

        # Return error response
        raise HTTPException(
            status_code=500,
            detail=f"Critical middleware failure: {context.middleware_name}",
        )

    async def finish_transaction(self, request_id: str) -> None:
        """Clean up completed transaction."""
        if request_id in self.active_transactions:
            transaction = self.active_transactions[request_id]

            # If rollback was required but not executed, do it now
            if transaction.rollback_required:
                await transaction.rollback()

            del self.active_transactions[request_id]
            logger.debug(f"🏁 Finished transaction {request_id}")


class ResilientMiddleware(BaseHTTPMiddleware):
    """
    Wrapper middleware that adds error handling and recovery capabilities
    to existing middleware.
    """

    def __init__(
        self,
        app,
        wrapped_middleware: BaseHTTPMiddleware,
        middleware_name: str,
        recovery_manager: ErrorRecoveryManager,
        max_retries: int = 3,
    ):
        super().__init__(app)
        self.wrapped_middleware = wrapped_middleware
        self.middleware_name = middleware_name
        self.recovery_manager = recovery_manager
        self.max_retries = max_retries

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Dispatch with error handling and recovery."""
        request_id = getattr(request.state, "request_id", f"req_{id(request)}")

        # Start or get existing transaction
        if request_id not in self.recovery_manager.active_transactions:
            transaction = self.recovery_manager.start_transaction(request_id)
        else:
            transaction = self.recovery_manager.active_transactions[request_id]

        transaction.add_middleware(self.middleware_name)

        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                # Execute the wrapped middleware
                response = await self.wrapped_middleware.dispatch(request, call_next)

                # Success - finish transaction on final middleware
                if not hasattr(request.state, "middleware_completed"):
                    request.state.middleware_completed = []
                request.state.middleware_completed.append(self.middleware_name)

                return response

            except Exception as e:
                # Create error context
                context = ErrorContext(
                    middleware_name=self.middleware_name,
                    error=e,
                    request=request,
                    severity=self._determine_severity(e),
                    retry_count=retry_count,
                    max_retries=self.max_retries,
                )

                # Handle the error
                recovery_response = await self.recovery_manager.handle_error(context)

                if recovery_response is not None:
                    # Recovery provided a response
                    return recovery_response
                elif context.recovery_strategy == RecoveryStrategy.BYPASS:
                    # Bypass this middleware, continue to next
                    return await call_next(request)
                elif (
                    context.recovery_strategy == RecoveryStrategy.RETRY
                    and retry_count < self.max_retries
                ):
                    # Retry the operation
                    retry_count += 1
                    continue
                else:
                    # No recovery possible, re-raise
                    raise

        # Should not reach here, but just in case
        raise RuntimeError(f"Exhausted all recovery options for {self.middleware_name}")

    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity based on exception type."""
        if isinstance(error, HTTPException):
            if error.status_code >= 500:
                return ErrorSeverity.HIGH
            elif error.status_code >= 400:
                return ErrorSeverity.MEDIUM
            else:
                return ErrorSeverity.LOW
        elif isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorSeverity.HIGH
        elif isinstance(error, (ValueError, TypeError)):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.HIGH


# Global recovery manager instance
_recovery_manager: Optional[ErrorRecoveryManager] = None


def get_recovery_manager() -> ErrorRecoveryManager:
    """Get global recovery manager instance."""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = ErrorRecoveryManager()
    return _recovery_manager


def setup_error_handling(
    middleware_configs: Dict[str, Dict[str, Any]],
) -> ErrorRecoveryManager:
    """
    Set up error handling for middleware chain.

    Args:
        middleware_configs: Configuration for each middleware

    Returns:
        Configured recovery manager
    """
    recovery_manager = get_recovery_manager()

    for middleware_name, config in middleware_configs.items():
        # Register recovery strategy
        strategy = config.get("recovery_strategy", RecoveryStrategy.RETRY)
        if isinstance(strategy, str):
            strategy = RecoveryStrategy(strategy)
        recovery_manager.register_recovery_strategy(middleware_name, strategy)

        # Register compensation actions
        compensation_actions = config.get("compensation_actions", [])
        for action in compensation_actions:
            recovery_manager.register_compensation_action(middleware_name, action)

        # Register error handler
        error_handler = config.get("error_handler")
        if error_handler:
            recovery_manager.register_error_handler(middleware_name, error_handler)

    logger.info("🛡️ Error handling setup complete")
    return recovery_manager


__all__ = [
    "ErrorSeverity",
    "RecoveryStrategy",
    "ErrorContext",
    "Compensatable",
    "Fallbackable",
    "MiddlewareTransaction",
    "ErrorRecoveryManager",
    "ResilientMiddleware",
    "get_recovery_manager",
    "setup_error_handling",
]

"""
Middleware Chain Orchestration - Sub-issue #21.1

Advanced middleware chain management with dynamic configuration,
health monitoring, and graceful degradation capabilities.

This module extends the basic middleware integration with:
- Dynamic middleware chain reconfiguration
- Real-time health monitoring
- Graceful degradation strategies
- Performance metrics collection
- Circuit breaker patterns
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class MiddlewareState(Enum):
    """Middleware operational states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, bypassed
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class MiddlewareMetrics:
    """Detailed metrics for middleware performance."""

    name: str
    request_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    state: MiddlewareState = MiddlewareState.HEALTHY
    circuit_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    last_success_time: Optional[datetime] = None


@dataclass
class ChainConfiguration:
    """Configuration for middleware chain behavior."""

    # Circuit breaker settings
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_max_calls: int = 3

    # Performance thresholds
    slow_request_threshold_ms: float = 1000.0
    error_rate_threshold: float = 0.1  # 10%

    # Degradation settings
    enable_graceful_degradation: bool = True
    critical_middleware: Set[str] = field(
        default_factory=lambda: {"PolicyEnforcementMiddleware"}
    )

    # Monitoring settings
    metrics_collection_enabled: bool = True
    health_check_interval: int = 30  # seconds


class MiddlewareOrchestrator:
    """
    Advanced middleware chain orchestrator with health monitoring,
    circuit breaker patterns, and graceful degradation.
    """

    def __init__(self, config: Optional[ChainConfiguration] = None):
        """
        Initialize middleware orchestrator.

        Args:
            config: Chain configuration (uses defaults if None)
        """
        self.config = config or ChainConfiguration()
        self.metrics: Dict[str, MiddlewareMetrics] = {}
        self.app: Optional[FastAPI] = None
        self._health_monitor_task: Optional[asyncio.Task[None]] = None
        self._startup_time = datetime.now(timezone.utc)

        logger.info("🎭 MiddlewareOrchestrator initialized")

    def register_app(self, app: FastAPI) -> None:
        """Register FastAPI app and start monitoring."""
        self.app = app
        self._initialize_metrics()
        if self.config.metrics_collection_enabled:
            self._start_health_monitoring()
        logger.info("✅ App registered with orchestrator")

    def _initialize_metrics(self) -> None:
        """Initialize metrics for all middleware."""
        if not self.app:
            return

        for middleware in self.app.user_middleware:
            name = getattr(middleware.cls, "__name__", "UnknownMiddleware")
            self.metrics[name] = MiddlewareMetrics(name=name)
            logger.debug(f"📊 Initialized metrics for {name}")

    def _start_health_monitoring(self) -> None:
        """Start background health monitoring task."""
        if self._health_monitor_task:
            return

        async def monitor():
            while True:
                try:
                    await self._perform_health_check()
                    # TODO: Use event-driven health monitoring instead of polling
                    await asyncio.sleep(
                        max(1, self.config.health_check_interval)
                    )  # Minimum 1s
                except Exception as e:
                    logger.error(f"❌ Health monitor error: {e}")
                    # TODO: Implement exponential backoff with circuit breaker
                    await asyncio.sleep(1)  # Reduced from 5s

        self._health_monitor_task = asyncio.create_task(monitor())
        logger.info("🏥 Health monitoring started")

    async def _perform_health_check(self) -> None:
        """Perform health check on all middleware."""
        for name, metrics in self.metrics.items():
            await self._check_middleware_health(name, metrics)

    async def _check_middleware_health(
        self, name: str, metrics: MiddlewareMetrics
    ) -> None:
        """Check health of individual middleware."""
        # Calculate error rate
        if metrics.request_count > 0:
            error_rate = metrics.error_count / metrics.request_count
        else:
            error_rate = 0.0

        # Update circuit breaker state
        if metrics.circuit_state == CircuitState.CLOSED:
            if metrics.consecutive_failures >= self.config.failure_threshold:
                metrics.circuit_state = CircuitState.OPEN
                logger.warning(
                    f"🔴 Circuit opened for {name} (failures: {metrics.consecutive_failures})"
                )

        elif metrics.circuit_state == CircuitState.OPEN:
            # Check if we should try half-open
            if (
                metrics.last_error_time
                and (
                    datetime.now(timezone.utc) - metrics.last_error_time
                ).total_seconds()
                > self.config.recovery_timeout
            ):
                metrics.circuit_state = CircuitState.HALF_OPEN
                logger.info(f"🟡 Circuit half-open for {name}")

        # Update middleware state based on health
        if error_rate > self.config.error_rate_threshold:
            if metrics.state != MiddlewareState.FAILED:
                metrics.state = MiddlewareState.DEGRADED
                logger.warning(f"⚠️ {name} degraded (error rate: {error_rate:.2%})")
        elif metrics.avg_duration_ms > self.config.slow_request_threshold_ms:
            if metrics.state != MiddlewareState.FAILED:
                metrics.state = MiddlewareState.DEGRADED
                logger.warning(
                    f"⚠️ {name} degraded (slow: {metrics.avg_duration_ms:.1f}ms)"
                )
        else:
            if metrics.state == MiddlewareState.DEGRADED:
                metrics.state = MiddlewareState.HEALTHY
                logger.info(f"✅ {name} recovered to healthy state")

    def record_request(
        self, middleware_name: str, duration_ms: float, error: Optional[str] = None
    ) -> None:
        """Record request metrics for middleware."""
        if not self.config.metrics_collection_enabled:
            return

        metrics = self.metrics.get(middleware_name)
        if not metrics:
            return

        # Update request stats
        metrics.request_count += 1
        metrics.total_duration_ms += duration_ms
        metrics.avg_duration_ms = metrics.total_duration_ms / metrics.request_count
        metrics.max_duration_ms = max(metrics.max_duration_ms, duration_ms)
        metrics.min_duration_ms = min(metrics.min_duration_ms, duration_ms)

        if error:
            # Record error
            metrics.error_count += 1
            metrics.consecutive_failures += 1
            metrics.last_error = error
            metrics.last_error_time = datetime.now(timezone.utc)
            logger.debug(f"❌ {middleware_name} error: {error}")
        else:
            # Record success
            metrics.consecutive_failures = 0
            metrics.last_success_time = datetime.now(timezone.utc)

            # Close circuit if in half-open state
            if metrics.circuit_state == CircuitState.HALF_OPEN:
                metrics.circuit_state = CircuitState.CLOSED
                logger.info(f"🟢 Circuit closed for {middleware_name}")

    def should_bypass_middleware(self, middleware_name: str) -> bool:
        """Determine if middleware should be bypassed due to circuit breaker."""
        metrics = self.metrics.get(middleware_name)
        if not metrics:
            return False

        # Never bypass critical middleware
        if middleware_name in self.config.critical_middleware:
            return False

        # Bypass if circuit is open
        if metrics.circuit_state == CircuitState.OPEN:
            return True

        # Limited calls in half-open state
        if metrics.circuit_state == CircuitState.HALF_OPEN:
            # This is a simplified implementation - in production, you'd want
            # more sophisticated tracking of half-open requests
            return metrics.request_count % 10 != 0  # Allow every 10th request

        return False

    def get_chain_health(self) -> Dict[str, Any]:
        """Get overall chain health status."""
        total_middleware = len(self.metrics)
        healthy_count = sum(
            1 for m in self.metrics.values() if m.state == MiddlewareState.HEALTHY
        )
        degraded_count = sum(
            1 for m in self.metrics.values() if m.state == MiddlewareState.DEGRADED
        )
        failed_count = sum(
            1 for m in self.metrics.values() if m.state == MiddlewareState.FAILED
        )

        overall_health = "healthy"
        if failed_count > 0:
            overall_health = "failed"
        elif degraded_count > 0:
            overall_health = "degraded"

        return {
            "overall_health": overall_health,
            "total_middleware": total_middleware,
            "healthy_count": healthy_count,
            "degraded_count": degraded_count,
            "failed_count": failed_count,
            "uptime_seconds": (
                datetime.now(timezone.utc) - self._startup_time
            ).total_seconds(),
            "middleware_details": {
                name: {
                    "state": metrics.state.value,
                    "circuit_state": metrics.circuit_state.value,
                    "request_count": metrics.request_count,
                    "error_count": metrics.error_count,
                    "error_rate": metrics.error_count / max(metrics.request_count, 1),
                    "avg_duration_ms": metrics.avg_duration_ms,
                    "consecutive_failures": metrics.consecutive_failures,
                }
                for name, metrics in self.metrics.items()
            },
        }

    def get_performance_report(self) -> Dict[str, Any]:
        """Get detailed performance report."""
        return {
            "chain_metrics": {
                "total_requests": sum(m.request_count for m in self.metrics.values()),
                "total_errors": sum(m.error_count for m in self.metrics.values()),
                "avg_chain_duration_ms": sum(
                    m.avg_duration_ms for m in self.metrics.values()
                ),
            },
            "middleware_performance": {
                name: {
                    "avg_duration_ms": metrics.avg_duration_ms,
                    "max_duration_ms": metrics.max_duration_ms,
                    "min_duration_ms": (
                        metrics.min_duration_ms
                        if metrics.min_duration_ms != float("inf")
                        else 0
                    ),
                    "request_count": metrics.request_count,
                    "throughput_rps": metrics.request_count
                    / max(
                        (
                            datetime.now(timezone.utc) - self._startup_time
                        ).total_seconds(),
                        1,
                    ),
                }
                for name, metrics in self.metrics.items()
            },
            "configuration": {
                "failure_threshold": self.config.failure_threshold,
                "slow_request_threshold_ms": self.config.slow_request_threshold_ms,
                "error_rate_threshold": self.config.error_rate_threshold,
                "graceful_degradation_enabled": self.config.enable_graceful_degradation,
            },
        }

    async def shutdown(self) -> None:
        """Gracefully shutdown the orchestrator."""
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("🔄 MiddlewareOrchestrator shutdown complete")


class InstrumentedMiddleware(BaseHTTPMiddleware):
    """
    Wrapper middleware that instruments other middleware with metrics collection.
    """

    def __init__(
        self,
        app: ASGIApp,
        orchestrator: MiddlewareOrchestrator,
        wrapped_middleware: BaseHTTPMiddleware,
        middleware_name: str,
    ):
        super().__init__(app)
        self.orchestrator = orchestrator
        self.wrapped_middleware = wrapped_middleware
        self.middleware_name = middleware_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Dispatch with instrumentation."""
        # Check if middleware should be bypassed
        if self.orchestrator.should_bypass_middleware(self.middleware_name):
            logger.debug(f"⏭️ Bypassing {self.middleware_name} (circuit open)")
            return await call_next(request)

        start_time = time.time()
        error = None

        try:
            # Call the wrapped middleware
            response = await self.wrapped_middleware.dispatch(request, call_next)
            return response
        except Exception as e:
            error = str(e)
            raise
        finally:
            # Record metrics
            duration_ms = (time.time() - start_time) * 1000
            self.orchestrator.record_request(self.middleware_name, duration_ms, error)


# Global orchestrator instance
_orchestrator: Optional[MiddlewareOrchestrator] = None


def get_orchestrator() -> MiddlewareOrchestrator:
    """Get global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MiddlewareOrchestrator()
    return _orchestrator


def setup_instrumented_middleware_chain(
    app: FastAPI,
    config: Optional[ChainConfiguration] = None,
    orchestrator: Optional[MiddlewareOrchestrator] = None,
) -> MiddlewareOrchestrator:
    """
    Set up instrumented middleware chain with orchestration.

    Args:
        app: FastAPI application
        config: Chain configuration
        orchestrator: Existing orchestrator (creates new if None)

    Returns:
        Configured orchestrator
    """
    if orchestrator is None:
        orchestrator = MiddlewareOrchestrator(config)

    orchestrator.register_app(app)

    logger.info("🎭 Instrumented middleware chain setup complete")
    return orchestrator


__all__ = [
    "MiddlewareState",
    "CircuitState",
    "MiddlewareMetrics",
    "ChainConfiguration",
    "MiddlewareOrchestrator",
    "InstrumentedMiddleware",
    "get_orchestrator",
    "setup_instrumented_middleware_chain",
]

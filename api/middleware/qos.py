"""
Quality of Service Middleware (MW_QOS)
Provides performance monitoring, resource management, and service quality controls.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .types import MiddlewareMetrics, QoSContext, QoSPriority

logger = logging.getLogger(__name__)


class QualityOfServiceMiddleware(BaseHTTPMiddleware):
    """
    Quality of Service Middleware (MW_QOS)

    Provides:
    - Performance monitoring
    - Resource usage tracking
    - Request prioritization
    - Response time optimization
    - Load balancing support
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.performance_metrics: Dict[str, Dict[str, Any]] = {}
        self.resource_usage: Dict[str, Any] = {
            "active_requests": 0,
            "total_requests": 0,
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
        }
        self.priority_queue: Dict[QoSPriority, List[Dict[str, Any]]] = {
            QoSPriority.CRITICAL: [],
            QoSPriority.HIGH: [],
            QoSPriority.NORMAL: [],
            QoSPriority.LOW: [],
        }
        self.max_concurrent_requests = 100
        self.timeout_limits: Dict[QoSPriority, float] = {
            QoSPriority.CRITICAL: 60.0,
            QoSPriority.HIGH: 30.0,
            QoSPriority.NORMAL: 15.0,
            QoSPriority.LOW: 10.0,
        }

    def _determine_priority(self, request: Request) -> QoSPriority:
        """Determine request priority based on various factors."""

        # Check for explicit priority headers
        priority_header = request.headers.get("X-Priority", "").lower()
        if priority_header == "critical":
            return QoSPriority.CRITICAL
        elif priority_header == "high":
            return QoSPriority.HIGH
        elif priority_header == "low":
            return QoSPriority.LOW

        # Determine priority based on endpoint
        path = request.url.path
        method = request.method

        # Critical operations
        critical_patterns = ["/api/emergency/", "/api/alerts/", "/api/system/health"]

        for pattern in critical_patterns:
            if pattern in path:
                return QoSPriority.CRITICAL

        # High priority operations
        high_priority_patterns = ["/api/auth/", "/api/admin/", "/api/policy/check"]

        for pattern in high_priority_patterns:
            if pattern in path:
                return QoSPriority.HIGH

        # Low priority operations
        low_priority_patterns = ["/api/reports/", "/api/logs/", "/api/analytics/"]

        for pattern in low_priority_patterns:
            if pattern in path:
                return QoSPriority.LOW

        # Default to normal priority
        return QoSPriority.NORMAL

    def _calculate_resource_limits(self, priority: QoSPriority) -> Dict[str, Any]:
        """Calculate resource limits based on priority."""
        base_limits = {
            "max_memory_mb": 100,
            "max_cpu_percent": 20,
            "max_execution_time": 15.0,
            "max_concurrent_ops": 5,
        }

        multipliers = {
            QoSPriority.CRITICAL: 3.0,
            QoSPriority.HIGH: 2.0,
            QoSPriority.NORMAL: 1.0,
            QoSPriority.LOW: 0.5,
        }

        multiplier = multipliers[priority]

        return {
            "max_memory_mb": int(base_limits["max_memory_mb"] * multiplier),
            "max_cpu_percent": int(base_limits["max_cpu_percent"] * multiplier),
            "max_execution_time": base_limits["max_execution_time"] * multiplier,
            "max_concurrent_ops": int(base_limits["max_concurrent_ops"] * multiplier),
        }

    def _track_performance_metrics(
        self, endpoint: str, duration: float, priority: QoSPriority
    ):
        """Track performance metrics for the endpoint."""
        if endpoint not in self.performance_metrics:
            self.performance_metrics[endpoint] = {
                "total_requests": 0,
                "total_duration": 0.0,
                "min_duration": float("inf"),
                "max_duration": 0.0,
                "avg_duration": 0.0,
                "priority_breakdown": {p: 0 for p in QoSPriority},
            }

        metrics = self.performance_metrics[endpoint]
        metrics["total_requests"] += 1
        metrics["total_duration"] += duration
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)
        metrics["avg_duration"] = metrics["total_duration"] / metrics["total_requests"]
        metrics["priority_breakdown"][priority] += 1

    def _check_system_load(self) -> Dict[str, Any]:
        """Check current system load and resource usage."""
        # Simulate system metrics (in a real implementation, this would query actual system resources)
        import random

        return {
            "active_requests": self.resource_usage["active_requests"],
            "cpu_usage": min(
                100.0, self.resource_usage["cpu_usage"] + random.uniform(-5, 5)
            ),
            "memory_usage": min(
                100.0, self.resource_usage["memory_usage"] + random.uniform(-3, 3)
            ),
            "load_average": self.resource_usage["active_requests"]
            / self.max_concurrent_requests
            * 100,
        }

    def _should_throttle_request(
        self, priority: QoSPriority, system_load: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Determine if request should be throttled based on system load and priority."""

        # Never throttle critical requests
        if priority == QoSPriority.CRITICAL:
            return False, ""

        # Check if we're at maximum concurrent requests
        if system_load["active_requests"] >= self.max_concurrent_requests:
            if priority == QoSPriority.LOW:
                return True, "System overloaded - low priority requests throttled"
            elif priority == QoSPriority.NORMAL and system_load["load_average"] > 90:
                return (
                    True,
                    "System heavily loaded - normal priority requests throttled",
                )

        # Check CPU usage
        if system_load["cpu_usage"] > 85:
            if priority == QoSPriority.LOW:
                return True, "High CPU usage - low priority requests throttled"
            elif priority == QoSPriority.NORMAL and system_load["cpu_usage"] > 95:
                return True, "Very high CPU usage - normal priority requests throttled"

        # Check memory usage
        if system_load["memory_usage"] > 90:
            if priority in [QoSPriority.LOW, QoSPriority.NORMAL]:
                return True, "High memory usage - lower priority requests throttled"

        return False, ""

    async def _wait_for_resources(self, priority: QoSPriority) -> None:
        """Wait for resources to become available based on priority."""
        # Implement priority-based queuing logic
        if self.resource_usage["active_requests"] >= self.max_concurrent_requests:
            # Add to priority queue if system is at capacity
            queue_entry: Dict[str, Any] = {
                "priority": priority,
                "timestamp": datetime.now(),
                "event": asyncio.Event(),
            }
            self.priority_queue[priority].append(queue_entry)

            # Wait for our turn based on priority
            await queue_entry["event"].wait()

            # Remove from queue when processed
            if queue_entry in self.priority_queue[priority]:
                self.priority_queue[priority].remove(queue_entry)

        # Process queue - signal next highest priority request
        self._process_priority_queue()

    def _process_priority_queue(self) -> None:
        """Process priority queue and signal next request to proceed."""
        if self.resource_usage["active_requests"] < self.max_concurrent_requests:
            # Find highest priority request waiting
            for priority in [
                QoSPriority.CRITICAL,
                QoSPriority.HIGH,
                QoSPriority.NORMAL,
                QoSPriority.LOW,
            ]:
                if self.priority_queue[priority]:
                    # Signal the oldest request at this priority level
                    next_request = self.priority_queue[priority][0]
                    next_request["event"].set()
                    break

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process QoS middleware."""
        start_time = datetime.now()
        metrics = MiddlewareMetrics(start_time=start_time)

        try:
            # Determine request priority
            priority = self._determine_priority(request)

            # Calculate resource limits
            resource_limits = self._calculate_resource_limits(priority)

            # Check system load
            system_load = self._check_system_load()

            # Check if request should be throttled
            should_throttle, throttle_reason = self._should_throttle_request(
                priority, system_load
            )

            if should_throttle:
                logger.warning(
                    f"Throttling request: {throttle_reason} (Priority: {priority.name})"
                )
                raise HTTPException(
                    status_code=503,
                    detail=f"Service temporarily unavailable: {throttle_reason}",
                )

            # Wait for resources if needed
            await self._wait_for_resources(priority)

            # Update active request count
            self.resource_usage["active_requests"] += 1
            self.resource_usage["total_requests"] += 1

            # Create QoS context
            qos_context = QoSContext(
                priority=priority,
                max_execution_time=self.timeout_limits[priority],
                resource_limits=resource_limits,
                performance_requirements={
                    "target_response_time": resource_limits["max_execution_time"] * 0.8,
                    "max_retries": (
                        3 if priority in [QoSPriority.CRITICAL, QoSPriority.HIGH] else 1
                    ),
                },
            )

            # Add QoS context to request state
            request.state.qos_context = qos_context
            request.state.system_load = system_load

            # Process request with timeout
            try:
                response = await asyncio.wait_for(
                    call_next(request), timeout=self.timeout_limits[priority]
                )

                # Add QoS headers to response (lowercase to match test expectations)
                response.headers["x-qos-priority"] = priority.name.lower()
                response.headers["x-qos-processing-time"] = str(
                    (datetime.now() - start_time).total_seconds()
                )
                response.headers["x-qos-system-load"] = str(
                    int(system_load["load_average"])
                )

                metrics.status = "success"
                metrics.end_time = datetime.now()
                metrics.duration_ms = (
                    metrics.end_time - metrics.start_time
                ).total_seconds() * 1000

                # Track performance metrics
                endpoint = f"{request.method} {request.url.path}"
                self._track_performance_metrics(
                    endpoint, metrics.duration_ms / 1000, priority
                )

                return response

            except asyncio.TimeoutError:
                logger.warning(
                    f"Request timeout (Priority: {priority.name}, "
                    f"Timeout: {self.timeout_limits[priority]}s)"
                )
                metrics.status = "timeout"
                metrics.errors.append("Request timeout")
                raise HTTPException(
                    status_code=504,
                    detail=f"Request timeout after {self.timeout_limits[priority]}s",
                )

        except HTTPException:
            metrics.status = "rejected"
            metrics.end_time = datetime.now()
            metrics.duration_ms = (
                metrics.end_time - metrics.start_time
            ).total_seconds() * 1000
            raise

        except Exception as e:
            logger.error(f"QoS middleware error: {str(e)}")
            metrics.status = "error"
            metrics.errors.append(str(e))
            metrics.end_time = datetime.now()
            metrics.duration_ms = (
                metrics.end_time - metrics.start_time
            ).total_seconds() * 1000
            raise HTTPException(status_code=500, detail="QoS processing error")

        finally:
            # Decrease active request count
            self.resource_usage["active_requests"] = max(
                0, self.resource_usage["active_requests"] - 1
            )

            # Process priority queue to allow next request
            self._process_priority_queue()

            # Store metrics in request state
            if hasattr(request.state, "middleware_metrics"):
                request.state.middleware_metrics["qos"] = metrics
            else:
                request.state.middleware_metrics = {"qos": metrics}

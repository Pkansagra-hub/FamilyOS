"""
Observability Middleware (MW_OBS)
Provides comprehensive monitoring, logging, metrics, and tracing.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from .types import MiddlewareMetrics

logger = logging.getLogger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Observability Middleware (MW_OBS)

    Provides:
    - Request/response logging
    - Performance metrics collection
    - Distributed tracing
    - Error tracking
    - System health monitoring
    """

    def __init__(self, app):
        super().__init__(app)
        self.request_metrics = {}
        self.error_tracking = {}
        self.performance_baselines = {}
        self.trace_storage = {}

    def _generate_trace_id(self) -> str:
        """Generate a unique trace ID for request tracking."""
        return str(uuid.uuid4())

    def _extract_user_info(self, request: Request) -> Dict[str, Any]:
        """Extract user information from request."""
        user_info = {
            "user_id": None,
            "user_agent": request.headers.get("User-Agent", "Unknown"),
            "ip_address": request.client.host if request.client else "Unknown",
            "forwarded_for": request.headers.get("X-Forwarded-For"),
            "real_ip": request.headers.get("X-Real-IP"),
        }

        # Try to extract user ID from various sources
        if hasattr(request.state, "user_context"):
            user_info["user_id"] = getattr(request.state.user_context, "user_id", None)
        elif hasattr(request.state, "security_context"):
            user_info["user_id"] = getattr(
                request.state.security_context, "user_id", None
            )

        return user_info

    def _collect_request_metadata(self, request: Request) -> Dict[str, Any]:
        """Collect comprehensive request metadata."""
        return {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "content_type": request.headers.get("Content-Type"),
            "content_length": request.headers.get("Content-Length"),
            "host": request.headers.get("Host"),
            "referer": request.headers.get("Referer"),
            "origin": request.headers.get("Origin"),
        }

    def _collect_middleware_metrics(self, request: Request) -> Dict[str, Any]:
        """Collect metrics from all middleware components."""
        middleware_metrics = {}

        if hasattr(request.state, "middleware_metrics"):
            for middleware_name, metrics in request.state.middleware_metrics.items():
                middleware_metrics[middleware_name] = {
                    "duration_ms": metrics.duration_ms,
                    "status": metrics.status,
                    "errors": metrics.errors,
                    "start_time": metrics.start_time.isoformat(),
                    "end_time": (
                        metrics.end_time.isoformat() if metrics.end_time else None
                    ),
                }

        return middleware_metrics

    def _collect_context_information(self, request: Request) -> Dict[str, Any]:
        """Collect context from various middleware components."""
        context = {}

        # Security context
        if hasattr(request.state, "security_context"):
            sec_ctx = request.state.security_context
            context["security"] = {
                "security_level": sec_ctx.security_level.value,
                "threat_indicators": sec_ctx.threat_indicators,
                "user_id": sec_ctx.user_id,
                "roles": sec_ctx.roles,
                "permissions": sec_ctx.permissions,
            }

        # QoS context
        if hasattr(request.state, "qos_context"):
            qos_ctx = request.state.qos_context
            context["qos"] = {
                "priority": qos_ctx.priority.name,
                "max_execution_time": qos_ctx.max_execution_time,
                "resource_limits": qos_ctx.resource_limits,
                "performance_requirements": qos_ctx.performance_requirements,
            }

        # Safety context
        if hasattr(request.state, "safety_context"):
            safety_ctx = request.state.safety_context
            context["safety"] = {
                "safety_level": safety_ctx.safety_level.value,
                "risk_factors": safety_ctx.risk_factors,
                "safety_checks": safety_ctx.safety_checks,
                "warnings": safety_ctx.warnings,
            }

        # System load information
        if hasattr(request.state, "system_load"):
            context["system_load"] = request.state.system_load

        # Access pattern information
        if hasattr(request.state, "access_pattern"):
            context["access_pattern"] = request.state.access_pattern

        return context

    def _calculate_performance_metrics(
        self, start_time: datetime, end_time: datetime, endpoint: str
    ) -> Dict[str, Any]:
        """Calculate performance metrics and compare against baselines."""
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Update performance baselines
        if endpoint not in self.performance_baselines:
            self.performance_baselines[endpoint] = {
                "total_requests": 0,
                "total_duration": 0.0,
                "min_duration": float("inf"),
                "max_duration": 0.0,
                "avg_duration": 0.0,
            }

        baseline = self.performance_baselines[endpoint]
        baseline["total_requests"] += 1
        baseline["total_duration"] += duration_ms
        baseline["min_duration"] = min(baseline["min_duration"], duration_ms)
        baseline["max_duration"] = max(baseline["max_duration"], duration_ms)
        baseline["avg_duration"] = (
            baseline["total_duration"] / baseline["total_requests"]
        )

        # Calculate performance indicators
        performance_metrics = {
            "duration_ms": duration_ms,
            "baseline_avg": baseline["avg_duration"],
            "performance_ratio": (
                duration_ms / baseline["avg_duration"]
                if baseline["avg_duration"] > 0
                else 1.0
            ),
            "is_slow": (
                duration_ms > baseline["avg_duration"] * 2
                if baseline["avg_duration"] > 0
                else False
            ),
            "percentile_rank": "unknown",  # Would need more sophisticated calculation
        }

        return performance_metrics

    def _log_request_event(
        self,
        trace_id: str,
        event_type: str,
        request_data: Dict[str, Any],
        additional_data: Dict[str, Any] = None,
    ):
        """Log request events with structured logging."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": trace_id,
            "event_type": event_type,
            "request": request_data,
            "additional_data": additional_data or {},
        }

        # Use different log levels based on event type
        if event_type == "request_error":
            logger.error(f"Request Error - Trace: {trace_id}", extra=log_entry)
        elif event_type == "security_event":
            logger.warning(f"Security Event - Trace: {trace_id}", extra=log_entry)
        elif event_type == "performance_issue":
            logger.warning(f"Performance Issue - Trace: {trace_id}", extra=log_entry)
        else:
            logger.info(f"Request Event - Trace: {trace_id}", extra=log_entry)

    def _track_error(
        self, trace_id: str, error: Exception, request_data: Dict[str, Any]
    ):
        """Track errors for analysis and alerting."""
        error_key = f"{type(error).__name__}:{str(error)}"

        if error_key not in self.error_tracking:
            self.error_tracking[error_key] = {
                "count": 0,
                "first_seen": datetime.now(),
                "last_seen": datetime.now(),
                "examples": [],
            }

        error_info = self.error_tracking[error_key]
        error_info["count"] += 1
        error_info["last_seen"] = datetime.now()

        # Keep only recent examples
        if len(error_info["examples"]) < 5:
            error_info["examples"].append(
                {
                    "trace_id": trace_id,
                    "timestamp": datetime.now().isoformat(),
                    "request_path": request_data.get("path", "unknown"),
                }
            )

    def _create_trace_summary(
        self,
        trace_id: str,
        request_metadata: Dict[str, Any],
        user_info: Dict[str, Any],
        context: Dict[str, Any],
        middleware_metrics: Dict[str, Any],
        performance_metrics: Dict[str, Any],
        response_data: Dict[str, Any],
        error_data: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create comprehensive trace summary."""
        return {
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "request": request_metadata,
            "user": user_info,
            "context": context,
            "middleware_metrics": middleware_metrics,
            "performance": performance_metrics,
            "response": response_data,
            "error": error_data,
            "total_processing_time": sum(
                m.get("duration_ms", 0) for m in middleware_metrics.values()
            ),
        }

    async def dispatch(self, request: Request, call_next):
        """Process observability middleware."""
        start_time = datetime.now()
        trace_id = self._generate_trace_id()
        metrics = MiddlewareMetrics(start_time=start_time)

        # Add trace ID to request state
        request.state.trace_id = trace_id

        try:
            # Collect request information
            user_info = self._extract_user_info(request)
            request_metadata = self._collect_request_metadata(request)

            # Log request start
            self._log_request_event(
                trace_id, "request_start", request_metadata, {"user_info": user_info}
            )

            # Process request
            response = await call_next(request)
            end_time = datetime.now()

            # Collect post-processing information
            context = self._collect_context_information(request)
            middleware_metrics = self._collect_middleware_metrics(request)

            # Calculate performance metrics
            endpoint = f"{request.method} {request.url.path}"
            performance_metrics = self._calculate_performance_metrics(
                start_time, end_time, endpoint
            )

            # Collect response information
            response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content_type": response.headers.get("Content-Type"),
            }

            # Add observability headers (lowercase to match test expectations)
            response.headers["x-trace-id"] = trace_id
            response.headers["x-processing-time"] = str(
                performance_metrics["duration_ms"]
            )
            response.headers["x-timestamp"] = datetime.now().isoformat()

            # Create and store trace summary
            trace_summary = self._create_trace_summary(
                trace_id,
                request_metadata,
                user_info,
                context,
                middleware_metrics,
                performance_metrics,
                response_data,
            )
            self.trace_storage[trace_id] = trace_summary

            # Log successful request completion
            self._log_request_event(
                trace_id,
                "request_completed",
                request_metadata,
                {
                    "response": response_data,
                    "performance": performance_metrics,
                    "context_summary": {
                        "security_level": context.get("security", {}).get(
                            "security_level"
                        ),
                        "qos_priority": context.get("qos", {}).get("priority"),
                        "safety_level": context.get("safety", {}).get("safety_level"),
                    },
                },
            )

            # Check for performance issues
            if performance_metrics["is_slow"]:
                self._log_request_event(
                    trace_id,
                    "performance_issue",
                    request_metadata,
                    {"performance": performance_metrics},
                )

            metrics.status = "success"
            metrics.end_time = end_time
            metrics.duration_ms = performance_metrics["duration_ms"]

            return response

        except Exception as e:
            end_time = datetime.now()

            # Track the error
            self._track_error(trace_id, e, request_metadata)

            # Create error trace summary
            error_data = {
                "type": type(e).__name__,
                "message": str(e),
                "timestamp": end_time.isoformat(),
            }

            context = self._collect_context_information(request)
            middleware_metrics = self._collect_middleware_metrics(request)

            endpoint = f"{request.method} {request.url.path}"
            performance_metrics = self._calculate_performance_metrics(
                start_time, end_time, endpoint
            )

            trace_summary = self._create_trace_summary(
                trace_id,
                request_metadata,
                user_info,
                context,
                middleware_metrics,
                performance_metrics,
                {},
                error_data,
            )
            self.trace_storage[trace_id] = trace_summary

            # Log error event
            self._log_request_event(
                trace_id,
                "request_error",
                request_metadata,
                {
                    "error": error_data,
                    "context": context,
                    "performance": performance_metrics,
                },
            )

            metrics.status = "error"
            metrics.errors.append(str(e))
            metrics.end_time = end_time
            metrics.duration_ms = (end_time - start_time).total_seconds() * 1000

            # Re-raise the exception
            raise

        finally:
            # Store observability metrics in request state
            if hasattr(request.state, "middleware_metrics"):
                request.state.middleware_metrics["observability"] = metrics
            else:
                request.state.middleware_metrics = {"observability": metrics}

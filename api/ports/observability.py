"""
Observability Port - Issue #25: Complete Observability Implementation
====================================================================

Port abstraction for observability operations including metrics, logging, and auditing.
From MMD diagram: Observability → ObservabilityPort → Monitoring Systems

Contract compliance with:
- /v1/healthz, /v1/readyz (main.yaml)
- /v1/metrics (main.yaml)
- observability-metrics.yaml (contracts/observability/metrics/)

This port handles all observability operations:
- Issue #25.1: Metrics collection interface (Prometheus exposition format)
- Issue #25.2: Health check aggregation (liveness/readiness probes)
- Issue #25.3: Audit log coordination (structured audit trails)
- Operation logging and auditing
- Error tracking and reporting
- Performance metrics collection

Architecture:
HTTP Handler → IngressAdapter → ObservabilityPort → Monitoring Systems
"""

# type: ignore

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

from ..schemas.core import Envelope, SecurityBand

logger = logging.getLogger(__name__)


# Issue #25.2: Health check aggregation - Component status tracking
class HealthStatus(Enum):
    """Health status levels matching OpenAPI contract."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status for individual system components."""

    component: str
    status: HealthStatus
    message: str = ""
    last_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """Aggregated system health status."""

    overall_status: HealthStatus
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Issue #25.1: Metrics collection interface - Prometheus format support
@dataclass
class MetricSample:
    """Individual metric sample following Prometheus format."""

    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    help_text: str = ""
    metric_type: str = "gauge"  # counter, gauge, histogram, summary


@dataclass
class PrometheusMetrics:
    """Prometheus exposition format metrics collection."""

    counters: Dict[str, float] = field(default_factory=dict)
    gauges: Dict[str, float] = field(default_factory=dict)
    histograms: Dict[str, List[float]] = field(default_factory=dict)
    labels: Dict[str, Dict[str, str]] = field(default_factory=dict)
    last_scrape: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Issue #25.3: Audit log coordination - Structured audit events
@dataclass
class AuditEvent:
    """Structured audit event for compliance tracking."""

    audit_id: str
    timestamp: datetime
    action: str
    actor: str
    resource: str
    outcome: str
    security_band: SecurityBand
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None


class ObservabilityError(Exception):
    """Observability-specific error types."""

    pass


class MetricsUnavailableError(ObservabilityError):
    """Raised when metrics endpoint is disabled (OBS-UNAVAILABLE 503)."""

    pass


class ObservabilityPort(ABC):
    """
    Abstract base class for observability implementations.

    Issue #25: Complete Observability Implementation
    - Sub-issue #25.1: Metrics collection interface (Prometheus exposition format)
    - Sub-issue #25.2: Health check aggregation (liveness/readiness probes)
    - Sub-issue #25.3: Audit log coordination (structured audit trails)

    The observability port is responsible for:
    1. Logging operations and their outcomes
    2. Collecting performance metrics (Prometheus format)
    3. Generating audit trails (structured events)
    4. Tracking errors and exceptions
    5. Coordinating health checks (component aggregation)
    6. Contract compliance with /v1/healthz, /v1/readyz, /v1/metrics
    """

    # Issue #25.1: Metrics collection interface
    @abstractmethod
    async def collect_metrics(self) -> str:
        """
        Collect and export metrics in Prometheus exposition format.

        Contract: GET /v1/metrics (main.yaml)
        Response: text/plain with Prometheus format

        Returns:
            Prometheus exposition format metrics as string

        Raises:
            MetricsUnavailableError: When metrics endpoint is disabled (503)
        """
        pass

    @abstractmethod
    async def record_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Record a counter metric (monotonically increasing)."""
        pass

    @abstractmethod
    async def record_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Record a gauge metric (can go up or down)."""
        pass

    @abstractmethod
    async def record_histogram(
        self,
        name: str,
        value: float,
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Record a histogram metric with configurable buckets."""
        pass

    # Issue #25.2: Health check aggregation
    @abstractmethod
    async def health_check(self) -> SystemHealth:
        """
        Perform comprehensive health check across all components.

        Contract: GET /v1/healthz (main.yaml)
        Response: 200 OK or 500 Server Error

        Returns:
            SystemHealth with overall status and component details
        """
        pass

    @abstractmethod
    async def readiness_check(self) -> SystemHealth:
        """
        Perform readiness check for service availability.

        Contract: GET /v1/readyz (main.yaml)
        Response: 200 Ready or 503 Not Ready

        Returns:
            SystemHealth with readiness status
        """
        pass

    @abstractmethod
    async def register_health_component(
        self, component: str, check_func: Callable[[], Any]
    ) -> bool:
        """Register a component for health monitoring."""
        pass

    @abstractmethod
    async def update_component_health(
        self,
        component: str,
        status: HealthStatus,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update health status for a specific component."""
        pass

    # Issue #25.3: Audit log coordination
    @abstractmethod
    async def create_audit_event(self, audit_event: AuditEvent) -> str:
        """
        Create a structured audit event for compliance tracking.

        Returns:
            audit_id for the created event
        """
        pass

    @abstractmethod
    async def query_audit_logs(
        self, filters: Dict[str, Any], limit: int = 100
    ) -> List[AuditEvent]:
        """Query audit logs with filtering capabilities."""
        pass

    @abstractmethod
    async def export_audit_trail(
        self, start_time: datetime, end_time: datetime, format: str = "json"
    ) -> str:
        """Export audit trail for compliance reporting."""
        pass

    # Original methods (preserved for compatibility)
    @abstractmethod
    async def log_operation(
        self,
        operation: str,
        result_type: str,
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> bool:
        """
        Log a successful operation.

        Args:
            operation: Operation name
            result_type: Type of result returned
            envelope: Request envelope
            metadata: Operation metadata

        Returns:
            True if logging successful
        """
        pass

    @abstractmethod
    async def log_error(
        self,
        operation: str,
        error: str,
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> bool:
        """
        Log an operation error.

        Args:
            operation: Operation name
            error: Error message
            envelope: Request envelope
            metadata: Operation metadata

        Returns:
            True if logging successful
        """
        pass

    @abstractmethod
    async def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Record a performance metric.

        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional metric tags

        Returns:
            True if recording successful
        """
        pass

    @abstractmethod
    async def create_audit_log(
        self,
        action: str,
        actor: str,
        resource: str,
        outcome: str,
        metadata: Dict[str, Any],
    ) -> str:
        """
        Create an audit log entry.

        Args:
            action: Action performed
            actor: Actor performing action
            resource: Resource acted upon
            outcome: Action outcome
            metadata: Additional metadata

        Returns:
            Audit log ID
        """
        pass

    @abstractmethod
    async def handle_operation(
        self,
        operation: str,
        data: Any,
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Any:
        """
        Handle observability-specific operations.

        Args:
            operation: Operation name
            data: Operation data
            envelope: Request envelope
            metadata: Operation metadata

        Returns:
            Operation result
        """
        pass


class ObservabilityImplementation(ObservabilityPort):
    """
    Production implementation of ObservabilityPort for Issue #25.

    Sub-issue #25.1: Metrics collection interface (Prometheus exposition format)
    Sub-issue #25.2: Health check aggregation (liveness/readiness probes)
    Sub-issue #25.3: Audit log coordination (structured audit trails)

    This implementation provides:
    - Contract-compliant /v1/healthz, /v1/readyz, /v1/metrics endpoints
    - Prometheus metrics exposition format
    - Component-based health monitoring
    - Structured audit event tracking
    - Performance metrics collection
    - Error tracking with context
    """

    def __init__(self, enable_metrics: bool = True, metrics_retention_hours: int = 24):
        # Issue #25.1: Metrics collection interface
        self._metrics_enabled = enable_metrics
        self._prometheus_metrics = PrometheusMetrics()
        self._metric_samples: Deque[MetricSample] = deque()  # Remove maxsize parameter
        self._retention_seconds = metrics_retention_hours * 3600

        # Issue #25.2: Health check aggregation
        self._component_health: Dict[str, ComponentHealth] = {}
        self._health_check_functions: Dict[str, Callable[[], Any]] = {}
        self._system_health = SystemHealth(overall_status=HealthStatus.HEALTHY)

        # Issue #25.3: Audit log coordination
        self._audit_events: Dict[str, AuditEvent] = {}
        self._audit_counter = 0

        # Original implementation (preserved)
        self._operation_logs: Dict[str, Any] = {}
        self._error_logs: Dict[str, Any] = {}
        self._metrics: Dict[str, Any] = {}
        self._audit_logs: Dict[str, Any] = {}

        # Initialize default component health checks
        self._register_default_components()

        # Phase 2: Service integration
        from services import default_service_registry

        self.service_registry = default_service_registry
        self.observability_service = self.service_registry.get_observability_service()

        logger.info(
            "ObservabilityImplementation initialized with Issue #25 features and service layer"
        )

    def _register_default_components(self):
        """Register default system components for health monitoring."""
        default_components = [
            "logging",
            "metrics",
            "audit",
            "storage",
            "network",
            "authentication",
        ]
        for component in default_components:
            self._component_health[component] = ComponentHealth(
                component=component,
                status=HealthStatus.HEALTHY,
                message="Component initialized",
            )

    # Issue #25.1: Metrics collection interface
    async def collect_metrics(self) -> str:
        """Collect and export metrics in Prometheus exposition format."""
        if not self._metrics_enabled:
            raise MetricsUnavailableError("Metrics endpoint disabled")

        # Clean old metrics
        await self._cleanup_old_metrics()

        # Generate Prometheus exposition format
        lines: List[str] = []

        # Add help and type information
        lines.append("# HELP obs_operations_total Total number of operations processed")
        lines.append("# TYPE obs_operations_total counter")
        lines.append(f"obs_operations_total {len(self._operation_logs)}")

        lines.append("# HELP obs_errors_total Total number of errors encountered")
        lines.append("# TYPE obs_errors_total counter")
        lines.append(f"obs_errors_total {len(self._error_logs)}")

        lines.append("# HELP obs_audit_events_total Total number of audit events")
        lines.append("# TYPE obs_audit_events_total counter")
        lines.append(f"obs_audit_events_total {len(self._audit_events)}")

        # Component health as gauge
        lines.append(
            "# HELP obs_component_health Component health status (1=healthy, 0.5=degraded, 0=unhealthy)"
        )
        lines.append("# TYPE obs_component_health gauge")
        for component, health in self._component_health.items():
            status_value = {"healthy": 1, "degraded": 0.5, "unhealthy": 0}[health.status.value]  # type: ignore
            lines.append(
                f'obs_component_health{{component="{component}"}} {status_value}'
            )

        # Custom metrics from prometheus_metrics
        for name, value in self._prometheus_metrics.counters.items():
            lines.append(f"# TYPE {name} counter")
            labels = self._prometheus_metrics.labels.get(name, {})
            label_str = ",".join([f'{k}="{v}"' for k, v in labels.items()])
            label_part = f"{{{label_str}}}" if label_str else ""
            lines.append(f"{name}{label_part} {value}")

        for name, value in self._prometheus_metrics.gauges.items():
            lines.append(f"# TYPE {name} gauge")
            labels = self._prometheus_metrics.labels.get(name, {})
            label_str = ",".join([f'{k}="{v}"' for k, v in labels.items()])
            label_part = f"{{{label_str}}}" if label_str else ""
            lines.append(f"{name}{label_part} {value}")

        # Update last scrape time
        self._prometheus_metrics.last_scrape = datetime.now(timezone.utc)

        return "\n".join(lines) + "\n"

    async def _cleanup_old_metrics(self):
        """Remove old metric samples beyond retention period."""
        cutoff_time = time.time() - self._retention_seconds
        while self._metric_samples and self._metric_samples[0].timestamp < cutoff_time:
            self._metric_samples.popleft()

    async def record_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Record a counter metric (monotonically increasing)."""
        if not self._metrics_enabled:
            return False

        if name in self._prometheus_metrics.counters:
            self._prometheus_metrics.counters[name] += value
        else:
            self._prometheus_metrics.counters[name] = value

        if labels:
            self._prometheus_metrics.labels[name] = labels

        # Store sample
        sample = MetricSample(
            name=name, value=value, labels=labels or {}, metric_type="counter"
        )
        self._metric_samples.append(sample)

        logger.debug(f"Recorded counter metric: {name} += {value}")
        return True

    async def record_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> bool:
        """Record a gauge metric (can go up or down)."""
        if not self._metrics_enabled:
            return False

        self._prometheus_metrics.gauges[name] = value

        if labels:
            self._prometheus_metrics.labels[name] = labels

        # Store sample
        sample = MetricSample(
            name=name, value=value, labels=labels or {}, metric_type="gauge"
        )
        self._metric_samples.append(sample)

        logger.debug(f"Recorded gauge metric: {name} = {value}")
        return True

    async def record_histogram(
        self,
        name: str,
        value: float,
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Record a histogram metric with configurable buckets."""
        if not self._metrics_enabled:
            return False

        if name not in self._prometheus_metrics.histograms:
            self._prometheus_metrics.histograms[name] = []

        self._prometheus_metrics.histograms[name].append(value)

        if labels:
            self._prometheus_metrics.labels[name] = labels

        # Store sample
        sample = MetricSample(
            name=name, value=value, labels=labels or {}, metric_type="histogram"
        )
        self._metric_samples.append(sample)

        logger.debug(f"Recorded histogram metric: {name} = {value}")
        return True

    # Issue #25.2: Health check aggregation
    async def health_check(self) -> SystemHealth:
        """Perform comprehensive health check across all components."""
        # Update component health by running registered check functions
        for component, check_func in self._health_check_functions.items():
            try:
                result = (
                    await check_func()
                    if asyncio.iscoroutinefunction(check_func)
                    else check_func()
                )
                if isinstance(result, ComponentHealth):
                    self._component_health[component] = result
                elif isinstance(result, bool):
                    status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                    self._component_health[component].status = status
                    self._component_health[component].last_check = datetime.now(
                        timezone.utc
                    )
            except Exception as e:
                self._component_health[component].status = HealthStatus.UNHEALTHY
                self._component_health[component].message = (
                    f"Health check failed: {str(e)}"
                )
                self._component_health[component].last_check = datetime.now(
                    timezone.utc
                )
                logger.error(f"Health check failed for {component}: {e}")

        # Determine overall system health
        unhealthy_count = sum(
            1
            for health in self._component_health.values()
            if health.status == HealthStatus.UNHEALTHY
        )
        degraded_count = sum(
            1
            for health in self._component_health.values()
            if health.status == HealthStatus.DEGRADED
        )

        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        self._system_health = SystemHealth(
            overall_status=overall_status,
            components=self._component_health.copy(),
            timestamp=datetime.now(timezone.utc),
        )

        logger.info(f"System health check completed: {overall_status.value}")
        return self._system_health

    async def readiness_check(self) -> SystemHealth:
        """Perform readiness check for service availability."""
        # For readiness, we focus on critical components needed for operation
        critical_components = ["authentication", "storage", "network"]

        ready = True
        for component in critical_components:
            if component in self._component_health:
                if self._component_health[component].status == HealthStatus.UNHEALTHY:
                    ready = False
                    break

        overall_status = HealthStatus.HEALTHY if ready else HealthStatus.UNHEALTHY

        readiness_health = SystemHealth(
            overall_status=overall_status,
            components={
                k: v
                for k, v in self._component_health.items()
                if k in critical_components
            },
            timestamp=datetime.now(timezone.utc),
        )

        logger.info(f"Readiness check completed: {overall_status.value}")
        return readiness_health

    async def register_health_component(
        self, component: str, check_func: Callable[[], Any]
    ) -> bool:
        """Register a component for health monitoring."""
        self._health_check_functions[component] = check_func

        # Initialize component health if not exists
        if component not in self._component_health:
            self._component_health[component] = ComponentHealth(
                component=component,
                status=HealthStatus.HEALTHY,
                message="Component registered",
            )

        logger.info(f"Registered health component: {component}")
        return True

    async def update_component_health(
        self,
        component: str,
        status: HealthStatus,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update health status for a specific component."""
        if component not in self._component_health:
            self._component_health[component] = ComponentHealth(
                component=component, status=status, message=message
            )
        else:
            self._component_health[component].status = status
            self._component_health[component].message = message
            self._component_health[component].last_check = datetime.now(timezone.utc)
            if details:
                self._component_health[component].details.update(details)

        logger.info(f"Updated component health: {component} -> {status.value}")
        return True

    # Issue #25.3: Audit log coordination
    async def create_audit_event(self, audit_event: AuditEvent) -> str:
        """Create a structured audit event for compliance tracking."""
        if not audit_event.audit_id:
            self._audit_counter += 1
            audit_event.audit_id = f"audit_{self._audit_counter}_{int(time.time())}"

        self._audit_events[audit_event.audit_id] = audit_event

        # Record audit metric
        await self.record_counter(
            "obs_audit_events_total", labels={"action": audit_event.action}
        )

        logger.info(
            f"Created audit event: {audit_event.action} by {audit_event.actor} -> {audit_event.outcome}"
        )
        return audit_event.audit_id

    async def query_audit_logs(
        self, filters: Dict[str, Any], limit: int = 100
    ) -> List[AuditEvent]:
        """Query audit logs with filtering capabilities."""
        results: List[AuditEvent] = []
        count = 0

        for audit_event in self._audit_events.values():
            if count >= limit:
                break

            match = True
            for key, value in filters.items():
                if hasattr(audit_event, key):
                    if getattr(audit_event, key) != value:
                        match = False
                        break

            if match:
                results.append(audit_event)
                count += 1

        logger.info(f"Queried audit logs: {len(results)} results for filters {filters}")
        return results

    async def export_audit_trail(
        self, start_time: datetime, end_time: datetime, format: str = "json"
    ) -> str:
        """Export audit trail for compliance reporting."""
        filtered_events = [
            event
            for event in self._audit_events.values()
            if start_time <= event.timestamp <= end_time
        ]

        if format == "json":
            import json

            return json.dumps(
                [
                    {
                        "audit_id": event.audit_id,
                        "timestamp": event.timestamp.isoformat(),
                        "action": event.action,
                        "actor": event.actor,
                        "resource": event.resource,
                        "outcome": event.outcome,
                        "security_band": event.security_band.value,
                        "metadata": event.metadata,
                        "correlation_id": event.correlation_id,
                    }
                    for event in filtered_events
                ],
                indent=2,
            )
        else:
            # CSV format
            lines = [
                "audit_id,timestamp,action,actor,resource,outcome,security_band,correlation_id"
            ]
            for event in filtered_events:
                lines.append(
                    f"{event.audit_id},{event.timestamp.isoformat()},{event.action},{event.actor},{event.resource},{event.outcome},{event.security_band.value},{event.correlation_id or ''}"
                )
            return "\n".join(lines)

    # Original methods (preserved for compatibility)
    async def log_operation(
        self,
        operation: str,
        result_type: str,
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> bool:
        """Log successful operation with context."""
        timestamp = datetime.now(timezone.utc)
        log_entry = {
            "timestamp": timestamp,
            "operation": operation,
            "result_type": result_type,
            "envelope_id": envelope.envelope_id,
            "user_id": envelope.user_id,
            "trace_id": metadata.get("trace_id"),
            "metadata": metadata,
        }

        log_id = f"{operation}_{timestamp.isoformat()}"
        self._operation_logs[log_id] = log_entry

        # Record metrics
        await self.record_counter(
            "obs_operations_total",
            labels={"operation": operation, "result_type": result_type},
        )

        logger.info(f"Logged operation: {operation} (result: {result_type})")
        return True

    async def log_error(
        self,
        operation: str,
        error: str,
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> bool:
        """Log operation error with context."""
        timestamp = datetime.now(timezone.utc)
        error_entry = {
            "timestamp": timestamp,
            "operation": operation,
            "error": error,
            "envelope_id": envelope.envelope_id,
            "user_id": envelope.user_id,
            "trace_id": metadata.get("trace_id"),
            "metadata": metadata,
        }

        error_id = f"error_{operation}_{timestamp.isoformat()}"
        self._error_logs[error_id] = error_entry

        # Record metrics
        await self.record_counter("obs_errors_total", labels={"operation": operation})

        logger.error(f"Logged error for operation: {operation} - {error}")
        return True

    async def record_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Record performance metric (compatibility method)."""
        return await self.record_gauge(metric_name, value, tags)

    async def create_audit_log(
        self,
        action: str,
        actor: str,
        resource: str,
        outcome: str,
        metadata: Dict[str, Any],
    ) -> str:
        """Create audit log entry (compatibility method)."""
        audit_event = AuditEvent(
            audit_id="",
            timestamp=datetime.now(timezone.utc),
            action=action,
            actor=actor,
            resource=resource,
            outcome=outcome,
            security_band=SecurityBand.GREEN,  # Default band
            metadata=metadata,
        )

        return await self.create_audit_event(audit_event)

    async def handle_operation(
        self,
        operation: str,
        data: Any,
        envelope: Envelope,
        metadata: Dict[str, Any],
    ) -> Any:
        """Handle observability operations."""
        logger.info(f"Handling observability operation: {operation}")

        if operation == "get_metrics":
            if self._metrics_enabled:
                return await self.collect_metrics()
            else:
                raise MetricsUnavailableError("Metrics endpoint disabled")

        elif operation == "health_check":
            health = await self.health_check()
            return {
                "status": health.overall_status.value,
                "timestamp": health.timestamp.isoformat(),
                "components": {
                    name: {
                        "status": comp.status.value,
                        "message": comp.message,
                        "last_check": comp.last_check.isoformat(),
                    }
                    for name, comp in health.components.items()
                },
            }

        elif operation == "readiness_check":
            readiness = await self.readiness_check()
            return {
                "status": readiness.overall_status.value,
                "ready": readiness.overall_status == HealthStatus.HEALTHY,
                "timestamp": readiness.timestamp.isoformat(),
            }

        elif operation == "metrics":
            return await self.collect_metrics()

        else:
            return {
                "operation": operation,
                "status": "not_implemented",
                "message": f"Observability operation {operation} not implemented",
            }


# Default instance for dependency injection
default_observability = ObservabilityImplementation()

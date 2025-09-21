"""
Service Registry Implementation - Service Discovery and Dependency Injection
============================================================================

Mock service registry for testing API infrastructure with configurable service implementations.
Supports both mock and production service implementations via configuration.

Contract compliance:
- Implements ServiceRegistryInterface from api/contracts/service_interfaces.py
- Provides service discovery and lifecycle management
- Supports dependency injection patterns
- Configurable service implementations (mock/production)

Usage:
    registry = ServiceRegistry(mode="mock")
    write_service = registry.get_write_service()
    result = await write_service.submit_memory(...)
"""

import logging
from typing import Any, Dict, Optional

from api.contracts.service_interfaces import (
    ConsolidationServiceInterface,
    IndexingServiceInterface,
    ObservabilityServiceInterface,
    RetrievalServiceInterface,
    ServiceRegistryInterface,
    WriteServiceInterface,
)

from .indexing_service import IndexingService
from .retrieval_service import RetrievalService

# Import mock service implementations
from .write_service import WriteService

logger = logging.getLogger(__name__)


class ServiceRegistry(ServiceRegistryInterface):
    """
    Service Registry Implementation

    Provides service discovery and dependency injection for all backend services.
    Supports configuration-driven service implementation selection.
    """

    def __init__(self, mode: str = "mock", config: Optional[Dict[str, Any]] = None):
        """
        Initialize service registry.

        Args:
            mode: Service mode ("mock" or "production")
            config: Optional configuration for service initialization
        """
        self.mode = mode
        self.config = config or {}
        self._services: Dict[str, Any] = {}

        # Initialize services based on mode
        self._initialize_services()

        logger.info(f"ServiceRegistry initialized in {mode} mode")

    def _initialize_services(self) -> None:
        """Initialize all services based on configuration."""
        if self.mode == "mock":
            self._initialize_mock_services()
        else:
            self._initialize_production_services()

    def _initialize_mock_services(self) -> None:
        """Initialize mock service implementations for testing."""
        self._services = {
            "write": WriteService(),
            "retrieval": RetrievalService(),
            "indexing": IndexingService(),
            "consolidation": MockConsolidationService(),
            "observability": MockObservabilityService(),
        }
        logger.info("Mock services initialized")

    def _initialize_production_services(self) -> None:
        """Initialize production service implementations."""
        # TODO: Import and initialize production services
        raise NotImplementedError("Production services not yet implemented")

    def get_write_service(self) -> WriteServiceInterface:
        """Get write service instance."""
        return self._services["write"]

    def get_retrieval_service(self) -> RetrievalServiceInterface:
        """Get retrieval service instance."""
        return self._services["retrieval"]

    def get_indexing_service(self) -> IndexingServiceInterface:
        """Get indexing service instance."""
        return self._services["indexing"]

    def get_consolidation_service(self) -> ConsolidationServiceInterface:
        """Get consolidation service instance."""
        return self._services["consolidation"]

    def get_observability_service(self) -> ObservabilityServiceInterface:
        """Get observability service instance."""
        return self._services["observability"]

    async def health_check(self) -> Dict[str, Any]:
        """Get overall service registry health."""
        service_health = {}
        overall_status = "healthy"

        # Check each service
        for service_name, service in self._services.items():
            try:
                if hasattr(service, "health_check"):
                    health = await service.health_check()
                else:
                    health = {"status": "healthy", "message": "Service available"}

                service_health[service_name] = health

                if health.get("status") != "healthy":
                    overall_status = "degraded"

            except Exception as e:
                service_health[service_name] = {"status": "unhealthy", "error": str(e)}
                overall_status = "unhealthy"

        return {
            "overall_status": overall_status,
            "mode": self.mode,
            "services": service_health,
            "registry_info": {
                "initialized_services": list(self._services.keys()),
                "config": self.config,
            },
        }


# ============================================================================
# MOCK IMPLEMENTATIONS FOR MISSING SERVICES
# ============================================================================


class MockConsolidationService(ConsolidationServiceInterface):
    """Mock consolidation service for testing."""

    async def consolidate_memories(
        self,
        space_id: str,
        security_context: Dict[str, Any],
        consolidation_rules: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Mock consolidation implementation."""
        from datetime import datetime, timezone
        from uuid import uuid4

        job_id = f"consol_{uuid4().hex[:8]}"

        return {
            "job_id": job_id,
            "status": "accepted",
            "space_id": space_id,
            "affected_memories": ["mem_001", "mem_002", "mem_003"],
            "rollup_records": 1,
            "estimated_duration_seconds": 180,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def create_rollup(
        self,
        memory_ids: list[str],
        rollup_config: Dict[str, Any],
        security_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Mock rollup creation."""
        from datetime import datetime, timezone
        from uuid import uuid4

        rollup_id = f"rollup_{uuid4().hex[:8]}"

        return {
            "rollup_id": rollup_id,
            "status": "completed",
            "canonical_record": f"canon_{uuid4().hex[:8]}",
            "original_refs": memory_ids,
            "rollup_summary": f"Consolidated {len(memory_ids)} memories",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_consolidation_status(
        self, job_id: str, security_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock consolidation status."""
        from datetime import datetime, timezone

        return {
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "results": {
                "memories_processed": 15,
                "duplicates_found": 3,
                "rollups_created": 1,
            },
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }


class MockObservabilityService(ObservabilityServiceInterface):
    """Mock observability service for testing."""

    async def collect_metrics(
        self,
        metric_type: str,
        security_context: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Mock metrics collection."""
        from datetime import datetime, timezone

        # Mock Prometheus-style metrics
        mock_metrics = {
            "api": {
                "http_requests_total": 1234,
                "http_request_duration_seconds": 0.123,
                "http_errors_total": 5,
            },
            "storage": {
                "storage_operations_total": 567,
                "storage_size_bytes": 1024000,
                "storage_errors_total": 0,
            },
            "policy": {
                "policy_evaluations_total": 890,
                "policy_violations_total": 2,
                "policy_evaluation_duration_seconds": 0.015,
            },
        }

        return {
            "metric_type": metric_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": mock_metrics.get(metric_type, {}),
            "filters_applied": filters or {},
        }

    async def get_health_status(
        self,
        component: Optional[str] = None,
        security_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Mock health status."""
        from datetime import datetime, timezone

        components = {
            "api": {"status": "healthy", "response_time_ms": 45},
            "storage": {"status": "healthy", "disk_usage_percent": 35},
            "policy": {"status": "healthy", "cache_hit_rate": 0.92},
            "indexing": {"status": "healthy", "queue_depth": 5},
        }

        if component:
            return {
                "component": component,
                "health": components.get(component, {"status": "unknown"}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "overall_status": "healthy",
            "components": components,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def record_audit_event(
        self, event: Dict[str, Any], security_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock audit event recording."""
        from datetime import datetime, timezone
        from uuid import uuid4

        audit_id = f"audit_{uuid4().hex[:8]}"

        return {
            "audit_id": audit_id,
            "status": "recorded",
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_info": {
                "user_id": security_context.get("user_id"),
                "trace_id": security_context.get("trace_id"),
                "request_id": security_context.get("request_id"),
            },
        }


# ============================================================================
# DEFAULT REGISTRY INSTANCES
# ============================================================================

# Default mock registry for testing
default_service_registry = ServiceRegistry(mode="mock")


# Registry factory function
def create_service_registry(
    mode: str = "mock", config: Optional[Dict[str, Any]] = None
) -> ServiceRegistry:
    """Create a service registry with specified configuration."""
    return ServiceRegistry(mode=mode, config=config)

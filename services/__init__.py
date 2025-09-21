"""
MemoryOS Services Package
========================

Mock service implementations for testing API infrastructure.
Provides realistic service responses matching OpenAPI contracts.

Usage:
    from services import default_service_registry
    write_service = default_service_registry.get_write_service()
    result = await write_service.submit_memory(...)

Available Services:
- WriteService: Memory submission and storage
- RetrievalService: Memory search and recall
- IndexingService: Content indexing and search optimization
- ConsolidationService: Memory deduplication and rollups
- ObservabilityService: Metrics, health, and audit logging

Service Registry:
- ServiceRegistry: Service discovery and dependency injection
- Supports mock and production service implementations
- Configuration-driven service selection
"""

# Import service interfaces
from api.contracts.service_interfaces import (
    ConsolidationServiceInterface,
    IndexingServiceInterface,
    ObservabilityServiceInterface,
    RetrievalServiceInterface,
    ServiceRegistryInterface,
    WriteServiceInterface,
)

from .indexing_service import IndexingService, default_indexing_service

# Import service registry
from .registry import ServiceRegistry, create_service_registry, default_service_registry
from .retrieval_service import RetrievalService, default_retrieval_service

# Import service implementations
from .write_service import WriteService, default_write_service

__all__ = [
    # Service interfaces
    "WriteServiceInterface",
    "RetrievalServiceInterface",
    "IndexingServiceInterface",
    "ConsolidationServiceInterface",
    "ObservabilityServiceInterface",
    "ServiceRegistryInterface",
    # Service implementations
    "WriteService",
    "RetrievalService",
    "IndexingService",
    # Default service instances
    "default_write_service",
    "default_retrieval_service",
    "default_indexing_service",
    # Service registry
    "ServiceRegistry",
    "default_service_registry",
    "create_service_registry",
]

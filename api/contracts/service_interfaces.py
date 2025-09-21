"""
Service Interface Contracts for MemoryOS
========================================

Based on contracts/modules/services/ specifications and contracts/api/openapi/main.yaml.
These interfaces define the contract between API ports and backend services.

Following contracts first principle from .github/copilot_instructions.md:
- All I/O changes start in contracts/ and pass contract CI before coding
- Obey contracts/POLICY_VERSIONING.md for compatibility
- No silent breaks, no "lite" versions

Architecture Flow:
HTTP Request → Router → Middleware Chain → Ingress Adapter → Port → Service Interface → Service Implementation

Key Design Principles:
- Contract-compliant with existing OpenAPI specification
- Support for envelope-based operations (contracts/events/envelope.schema.json)
- Band-aware security (GREEN/AMBER/RED/BLACK)
- Space-scoped operations with MLS/E2EE support
- Observability hooks for metrics and tracing
- Idempotent operations with receipt hashes
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# ============================================================================
# CORE SERVICE INTERFACES
# ============================================================================


class WriteServiceInterface(ABC):
    """
    Write Service Interface - Memory Ingestion and Storage

    Based on contracts/modules/services/ and OpenAPI paths:
    - POST /v1/tools/memory/submit (Agents plane)
    - POST /api/v1/memories (App plane)

    Handles memory submission, validation, and routing to storage pipelines.
    Emits receipts and audit events per envelope schema requirements.
    """

    @abstractmethod
    async def submit_memory(
        self,
        envelope: Dict[str, Any],
        space_id: str,
        security_context: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Submit a memory for storage and processing.

        Args:
            envelope: Memory envelope with content, metadata, attachments
            space_id: Target memory space (personal:*, shared:*, etc.)
            security_context: User/device/auth context from middleware
            **kwargs: Additional processing options

        Returns:
            Dict with envelope_id, status, receipt_url, processing_info

        Raises:
            ValidationError: Invalid envelope or security context
            PolicyViolationError: RBAC/ABAC policy denial
            StorageError: Backend storage failure
        """
        pass

    @abstractmethod
    async def batch_submit(
        self,
        envelopes: List[Dict[str, Any]],
        space_id: str,
        security_context: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Submit multiple memories in a single transaction.

        Args:
            envelopes: List of memory envelopes
            space_id: Target memory space
            security_context: User/device/auth context
            **kwargs: Batch processing options

        Returns:
            Dict with batch_id, envelope_ids, status, failed_items
        """
        pass

    @abstractmethod
    async def get_receipt(
        self, envelope_id: str, security_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Retrieve processing receipt for submitted memory.

        Args:
            envelope_id: Memory envelope identifier
            security_context: User/device/auth context

        Returns:
            Dict with receipt details, processing status, audit trail
        """
        pass


class RetrievalServiceInterface(ABC):
    """
    Retrieval Service Interface - Memory Search and Recall

    Based on contracts/modules/services/ and OpenAPI paths:
    - POST /v1/tools/memory/recall (Agents plane)
    - GET /api/v1/memories/search (App plane)

    Handles memory search, filtering, ranking, and access control.
    Supports semantic, temporal, and hybrid search modes.
    """

    @abstractmethod
    async def recall_memories(
        self,
        query: Dict[str, Any],
        space_id: str,
        security_context: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Search and recall memories based on query parameters.

        Args:
            query: Search query with text, filters, ranking options
            space_id: Memory space to search within
            security_context: User/device/auth context for access control
            **kwargs: Search configuration options

        Returns:
            Dict with items, total_count, trace_info, search_metadata

        Raises:
            AccessDeniedError: Insufficient permissions for space
            ValidationError: Invalid query parameters
            SearchError: Backend search failure
        """
        pass

    @abstractmethod
    async def get_memory_details(
        self,
        memory_id: str,
        security_context: Dict[str, Any],
        include_content: bool = True,
    ) -> Dict[str, Any]:
        """
        Retrieve detailed information for a specific memory.

        Args:
            memory_id: Memory identifier
            security_context: User/device/auth context
            include_content: Whether to include full content or just metadata

        Returns:
            Dict with memory details, content, metadata, access_info
        """
        pass

    @abstractmethod
    async def get_memory_references(
        self, memory_id: str, security_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get references and relationships for a memory.

        Args:
            memory_id: Memory identifier
            security_context: User/device/auth context

        Returns:
            Dict with references, relationships, knowledge_graph_info
        """
        pass


class IndexingServiceInterface(ABC):
    """
    Indexing Service Interface - Content Processing and Search Index Management

    Based on contracts/modules/services/ and pipeline specifications.
    Handles content indexing, embedding generation, and search optimization.
    Supports incremental updates and real-time indexing.
    """

    @abstractmethod
    async def index_content(
        self,
        content: Dict[str, Any],
        space_id: str,
        security_context: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Index content for search and retrieval.

        Args:
            content: Content to index with metadata
            space_id: Memory space for indexing scope
            security_context: User/device/auth context
            **kwargs: Indexing configuration options

        Returns:
            Dict with index_id, status, processing_info, search_readiness

        Raises:
            IndexingError: Content processing failure
            PolicyViolationError: Content policy violation
        """
        pass

    @abstractmethod
    async def rebuild_index(
        self, space_id: str, security_context: Dict[str, Any], incremental: bool = True
    ) -> Dict[str, Any]:
        """
        Rebuild search index for a memory space.

        Args:
            space_id: Memory space to rebuild
            security_context: User/device/auth context
            incremental: Whether to do incremental or full rebuild

        Returns:
            Dict with job_id, estimated_duration, progress_url
        """
        pass

    @abstractmethod
    async def get_index_status(
        self, space_id: str, security_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get indexing status and health for a space.

        Args:
            space_id: Memory space identifier
            security_context: User/device/auth context

        Returns:
            Dict with index_health, last_update, pending_items, statistics
        """
        pass


class ConsolidationServiceInterface(ABC):
    """
    Consolidation Service Interface - Memory Deduplication and Rollups

    Based on contracts/modules/consolidation/ specifications.
    Handles memory consolidation, deduplication, and canonical record creation.
    Supports both automatic and manual consolidation workflows.
    """

    @abstractmethod
    async def consolidate_memories(
        self,
        space_id: str,
        security_context: Dict[str, Any],
        consolidation_rules: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Consolidate and deduplicate memories within a space.

        Args:
            space_id: Memory space for consolidation
            security_context: User/device/auth context
            consolidation_rules: Custom consolidation configuration

        Returns:
            Dict with job_id, affected_memories, rollup_records, status

        Raises:
            ConsolidationError: Consolidation process failure
            AccessDeniedError: Insufficient permissions
        """
        pass

    @abstractmethod
    async def create_rollup(
        self,
        memory_ids: List[str],
        rollup_config: Dict[str, Any],
        security_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a rollup record from multiple memories.

        Args:
            memory_ids: List of memory identifiers to rollup
            rollup_config: Rollup configuration and metadata
            security_context: User/device/auth context

        Returns:
            Dict with rollup_id, canonical_record, original_refs, status
        """
        pass

    @abstractmethod
    async def get_consolidation_status(
        self, job_id: str, security_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get status of a consolidation job.

        Args:
            job_id: Consolidation job identifier
            security_context: User/device/auth context

        Returns:
            Dict with job_status, progress, results, error_info
        """
        pass


class ObservabilityServiceInterface(ABC):
    """
    Observability Service Interface - Metrics, Traces, and Health Monitoring

    Based on contracts/modules/observability/ specifications.
    Handles system monitoring, health checks, and performance metrics.
    Provides observability data for operational monitoring.
    """

    @abstractmethod
    async def collect_metrics(
        self,
        metric_type: str,
        security_context: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Collect system metrics in Prometheus format.

        Args:
            metric_type: Type of metrics to collect (api, storage, etc.)
            security_context: User/device/auth context
            filters: Metric filtering options

        Returns:
            Dict with metrics data, timestamp, metadata
        """
        pass

    @abstractmethod
    async def get_health_status(
        self,
        component: Optional[str] = None,
        security_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get health status for system components.

        Args:
            component: Specific component to check (None for all)
            security_context: User/device/auth context (for auth'd checks)

        Returns:
            Dict with health status, component details, error info
        """
        pass

    @abstractmethod
    async def record_audit_event(
        self, event: Dict[str, Any], security_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Record an audit event for compliance tracking.

        Args:
            event: Audit event with action, resource, outcome
            security_context: User/device/auth context

        Returns:
            Dict with audit_id, timestamp, correlation_info
        """
        pass


# ============================================================================
# SERVICE REGISTRY INTERFACE
# ============================================================================


class ServiceRegistryInterface(ABC):
    """
    Service Registry Interface - Service Discovery and Dependency Injection

    Provides service discovery and lifecycle management for all backend services.
    Supports both mock and production service implementations.
    """

    @abstractmethod
    def get_write_service(self) -> WriteServiceInterface:
        """Get write service instance."""
        pass

    @abstractmethod
    def get_retrieval_service(self) -> RetrievalServiceInterface:
        """Get retrieval service instance."""
        pass

    @abstractmethod
    def get_indexing_service(self) -> IndexingServiceInterface:
        """Get indexing service instance."""
        pass

    @abstractmethod
    def get_consolidation_service(self) -> ConsolidationServiceInterface:
        """Get consolidation service instance."""
        pass

    @abstractmethod
    def get_observability_service(self) -> ObservabilityServiceInterface:
        """Get observability service instance."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Get overall service registry health."""
        pass


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Core service interfaces
    "WriteServiceInterface",
    "RetrievalServiceInterface",
    "IndexingServiceInterface",
    "ConsolidationServiceInterface",
    "ObservabilityServiceInterface",
    # Registry interface
    "ServiceRegistryInterface",
]

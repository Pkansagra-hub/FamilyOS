"""
Memory Steward Orchestrator - Hippocampal Memory Formation Coordination
=====================================================================

This module implements the central orchestrator for the Memory Steward service,
coordinating the complete hippocampal memory formation workflow:

1. Space Resolution (Dentate Gyrus pattern separation)
2. Content Redaction (Policy integration)
3. Deduplication & Consolidation (CA3 pattern completion)
4. Transactional Commitment (CA1 output with UnitOfWork)
5. Receipt Generation (Cryptographic audit trail)
6. Event Publication (Outbox pattern)

**Neuroscience Inspiration:**
The hippocampus coordinates memory encoding, consolidation, and storage through
specialized subregions. This orchestrator mirrors hippocampal processing by
managing the flow from initial sensory input through to long-term storage,
with appropriate policy enforcement and integrity guarantees.

**Research Backing:**
- Rolls & Kesner (2006): Hippocampal network for pattern separation/completion
- Squire et al. (2004): Memory consolidation and systems-level reorganization
- McClelland et al. (1995): Complementary learning systems theory
- O'Reilly & Norman (2002): Hippocampal and neocortical contributions to memory

The implementation follows the contracts-first methodology with ACID transactions,
policy-aware processing, and comprehensive observability.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from hippocampus.api import HippocampusAPI
from hippocampus.types import HippocampalEncoding
from memory_steward.commit_manager import MemoryCommitManager
from memory_steward.deduplication_engine import MemoryDeduplicationEngine
from memory_steward.receipt_generator import MemoryReceiptGenerator
from memory_steward.redaction_coordinator import MemoryRedactionCoordinator
from memory_steward.space_resolver import MemorySpaceResolver
from observability.logging import get_json_logger
from observability.trace import start_span

# Import metrics functions that are actually available
try:
    from observability.metrics import pipeline_timer, record_storage
except ImportError:
    # Fallback if metrics not available
    def record_storage(*args, **kwargs):
        pass

    def pipeline_timer(*args, **kwargs):
        return contextmanager(lambda: iter([None]))()


logger = get_json_logger(__name__)

# No metrics client needed - using individual metric functions


@dataclass
class MemoryWriteRequest:
    """
    Memory formation request from Attention Gate.

    Represents an ADMIT decision for WriteIntent that requires
    hippocampal memory formation orchestration.
    """

    request_id: str
    actor: Dict[
        str, Any
    ]  # {"person_id": "alice", "role": "member", "device_id": "phone-123"}
    space_id: Optional[str]  # May be None, requiring space resolution
    write_intent: Dict[str, Any]  # Content, attachments, context, temporal
    policy_obligations: List[
        str
    ]  # ["mask:pii:phone_numbers", "redact:location:precise"]
    salience: Dict[str, float]  # {"priority": 0.78, "urgency": 0.6, "novelty": 0.8}
    trace_id: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class MemoryFormationResult:
    """
    Result of complete memory formation workflow.

    Contains all processing artifacts and references for audit trail.
    """

    memory_id: str
    request_id: str
    space_id: str
    actor: Dict[str, Any]
    hippocampal_encoding: HippocampalEncoding
    redaction_applied: List[str]
    deduplication: Dict[str, Any]  # merge information
    receipt_id: str
    cognitive_events: List[Dict[str, Any]]
    processing_duration_ms: float
    status: str  # "committed", "failed", "partial"
    error_details: Optional[str] = None


@dataclass
class ProcessingStage:
    """Processing stage tracking for observability."""

    stage: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "in_progress"  # "in_progress", "completed", "failed"
    error: Optional[str] = None

    def complete(self, status: str = "completed", error: Optional[str] = None):
        """Mark stage as complete with timing."""
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status
        self.error = error


class MemoryStewardOrchestrator:
    """
    Central coordinator for hippocampal memory formation.

    Orchestrates the complete workflow from WriteIntent admission through
    to committed storage, maintaining ACID properties and generating
    comprehensive audit trails.

    **Key Responsibilities:**
    - Workflow coordination and error handling
    - Transactional integrity via UnitOfWork pattern
    - Policy enforcement and compliance
    - Performance monitoring and SLA adherence
    - Cognitive event emission for downstream processing
    """

    def __init__(
        self,
        # Component dependencies (injected for testability)
        space_resolver: Optional[MemorySpaceResolver] = None,
        redaction_coordinator: Optional[MemoryRedactionCoordinator] = None,
        deduplication_engine: Optional[MemoryDeduplicationEngine] = None,
        commit_manager: Optional[MemoryCommitManager] = None,
        receipt_generator: Optional[MemoryReceiptGenerator] = None,
        hippocampus_api: Optional[HippocampusAPI] = None,
        # Storage and infrastructure dependencies
        unit_of_work=None,
        event_bus=None,
        policy_engine=None,
        # Configuration
        config: Optional[Dict[str, Any]] = None,
    ):
        # Initialize components with dependency injection
        self.space_resolver = space_resolver or MemorySpaceResolver()
        self.redaction_coordinator = (
            redaction_coordinator or MemoryRedactionCoordinator()
        )
        self.deduplication_engine = deduplication_engine or MemoryDeduplicationEngine()
        self.commit_manager = commit_manager or MemoryCommitManager()
        self.receipt_generator = receipt_generator or MemoryReceiptGenerator()
        self.hippocampus_api = hippocampus_api or HippocampusAPI()

        # Infrastructure dependencies
        self.unit_of_work = unit_of_work
        self.event_bus = event_bus
        self.policy_engine = policy_engine

        # Configuration with defaults
        self.config = config or {}
        self.max_processing_time_ms = self.config.get("max_processing_time_ms", 5000)
        self.enable_deduplication = self.config.get("enable_deduplication", True)
        self.enable_semantic_extraction = self.config.get(
            "enable_semantic_extraction", True
        )
        self.parallel_processing = self.config.get("parallel_processing", True)

        # Performance tracking
        self._active_requests: Set[str] = set()
        self._processing_stages: Dict[str, List[ProcessingStage]] = {}

        logger.info(
            "MemoryStewardOrchestrator initialized",
            extra={
                "config": self.config,
                "max_processing_time_ms": self.max_processing_time_ms,
                "enable_deduplication": self.enable_deduplication,
                "enable_semantic_extraction": self.enable_semantic_extraction,
                "parallel_processing": self.parallel_processing,
            },
        )

    async def process_memory_formation(
        self, request: MemoryWriteRequest
    ) -> MemoryFormationResult:
        """
        Process complete memory formation workflow.

        Implements the hippocampal memory formation pipeline:
        1. Space Resolution (determine target memory space)
        2. Content Redaction (apply policy-based data minimization)
        3. Hippocampal Encoding (DG pattern separation via existing hippocampus system)
        4. Deduplication & Consolidation (CA3-like pattern completion and merging)
        5. Transactional Commitment (CA1-like output with ACID guarantees)
        6. Receipt Generation (cryptographic audit trail)
        7. Event Publication (reliable outbox pattern)

        Args:
            request: Memory write request from Attention Gate

        Returns:
            MemoryFormationResult with complete processing artifacts

        Raises:
            MemoryFormationError: If any critical stage fails
            TimeoutError: If processing exceeds SLA budget
        """
        start_time = datetime.now(timezone.utc)
        request_id = request.request_id

        # Initialize processing tracking
        self._active_requests.add(request_id)
        stages = []
        self._processing_stages[request_id] = stages

        # Start distributed tracing
        with start_span("memory_steward.orchestrator.process_memory_formation") as span:
            span.set_attribute("request_id", request_id)
            span.set_attribute("space_id", request.space_id or "unresolved")
            span.set_attribute(
                "actor.person_id", request.actor.get("person_id", "unknown")
            )
            span.set_attribute(
                "salience.priority", request.salience.get("priority", 0.0)
            )

            try:
                logger.info(
                    "Starting memory formation workflow",
                    extra={
                        "request_id": request_id,
                        "actor": request.actor,
                        "space_id": request.space_id,
                        "content_length": len(request.write_intent.get("content", "")),
                        "policy_obligations": request.policy_obligations,
                        "salience": request.salience,
                        "trace_id": request.trace_id,
                    },
                )

                # Track request volume metrics
                metrics.increment(
                    "memory_formation_requests_total",
                    tags={
                        "status": "started",
                        "space_id": request.space_id or "unresolved",
                    },
                )

                # Stage 1: Space Resolution (Dentate Gyrus - pattern separation)
                resolved_space_id = await self._execute_stage(
                    "space_resolution",
                    request_id,
                    stages,
                    self._resolve_target_space,
                    request,
                    span,
                )

                # Stage 2: Content Redaction (Policy enforcement)
                redacted_content, redaction_applied = await self._execute_stage(
                    "content_redaction",
                    request_id,
                    stages,
                    self._apply_content_redaction,
                    request,
                    resolved_space_id,
                    span,
                )

                # Stage 3: Hippocampal Encoding (existing hippocampus system)
                hippocampal_encoding = await self._execute_stage(
                    "hippocampal_encoding",
                    request_id,
                    stages,
                    self._perform_hippocampal_encoding,
                    resolved_space_id,
                    redacted_content,
                    request,
                    span,
                )

                # Stage 4: Deduplication & Consolidation (CA3 pattern completion)
                deduplication_result = await self._execute_stage(
                    "deduplication",
                    request_id,
                    stages,
                    self._perform_deduplication,
                    hippocampal_encoding,
                    resolved_space_id,
                    span,
                )

                # Stage 5: Memory Commitment (CA1 output - transactional storage)
                memory_id = await self._execute_stage(
                    "memory_commitment",
                    request_id,
                    stages,
                    self._commit_memory,
                    hippocampal_encoding,
                    deduplication_result,
                    resolved_space_id,
                    request,
                    span,
                )

                # Stage 6: Receipt Generation (audit trail)
                receipt_id = await self._execute_stage(
                    "receipt_generation",
                    request_id,
                    stages,
                    self._generate_receipt,
                    memory_id,
                    hippocampal_encoding,
                    redaction_applied,
                    request,
                    span,
                )

                # Stage 7: Event Publication (outbox pattern)
                cognitive_events = await self._execute_stage(
                    "event_publication",
                    request_id,
                    stages,
                    self._publish_cognitive_events,
                    memory_id,
                    hippocampal_encoding,
                    deduplication_result,
                    request,
                    span,
                )

                # Calculate total processing time
                end_time = datetime.now(timezone.utc)
                processing_duration_ms = (end_time - start_time).total_seconds() * 1000

                # Create successful result
                result = MemoryFormationResult(
                    memory_id=memory_id,
                    request_id=request_id,
                    space_id=resolved_space_id,
                    actor=request.actor,
                    hippocampal_encoding=hippocampal_encoding,
                    redaction_applied=redaction_applied,
                    deduplication=deduplication_result,
                    receipt_id=receipt_id,
                    cognitive_events=cognitive_events,
                    processing_duration_ms=processing_duration_ms,
                    status="committed",
                )

                # Success metrics and logging
                metrics.increment(
                    "memory_formation_requests_total",
                    tags={"status": "completed", "space_id": resolved_space_id},
                )
                metrics.observe(
                    "memory_formation_duration_seconds",
                    processing_duration_ms / 1000,
                    tags={"space_id": resolved_space_id},
                )

                logger.info(
                    "Memory formation workflow completed successfully",
                    extra={
                        "request_id": request_id,
                        "memory_id": memory_id,
                        "space_id": resolved_space_id,
                        "processing_duration_ms": processing_duration_ms,
                        "novelty": hippocampal_encoding.novelty,
                        "near_duplicates": len(hippocampal_encoding.near_duplicates),
                        "redaction_applied": redaction_applied,
                        "receipt_id": receipt_id,
                    },
                )

                return result

            except Exception as e:
                # Handle workflow failure
                end_time = datetime.now(timezone.utc)
                processing_duration_ms = (end_time - start_time).total_seconds() * 1000

                error_result = MemoryFormationResult(
                    memory_id="",
                    request_id=request_id,
                    space_id=request.space_id or "unresolved",
                    actor=request.actor,
                    hippocampal_encoding=None,
                    redaction_applied=[],
                    deduplication={},
                    receipt_id="",
                    cognitive_events=[],
                    processing_duration_ms=processing_duration_ms,
                    status="failed",
                    error_details=str(e),
                )

                # Error metrics and logging
                metrics.increment(
                    "memory_formation_requests_total",
                    tags={"status": "failed", "error_type": type(e).__name__},
                )

                logger.error(
                    "Memory formation workflow failed",
                    extra={
                        "request_id": request_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "processing_duration_ms": processing_duration_ms,
                        "stages_completed": [
                            s.stage for s in stages if s.status == "completed"
                        ],
                    },
                )

                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))

                raise

            finally:
                # Cleanup tracking
                self._active_requests.discard(request_id)
                self._processing_stages.pop(request_id, None)

    async def _execute_stage(
        self,
        stage_name: str,
        request_id: str,
        stages: List[ProcessingStage],
        stage_func,
        *args,
        **kwargs,
    ):
        """Execute a processing stage with error handling and timing."""
        stage = ProcessingStage(stage_name, datetime.now(timezone.utc))
        stages.append(stage)

        try:
            logger.debug(
                f"Starting stage: {stage_name}",
                extra={"request_id": request_id, "stage": stage_name},
            )

            # Execute stage function
            result = await stage_func(*args, **kwargs)

            stage.complete("completed")

            logger.debug(
                f"Completed stage: {stage_name}",
                extra={
                    "request_id": request_id,
                    "stage": stage_name,
                    "duration_ms": stage.duration_ms,
                },
            )

            return result

        except Exception as e:
            stage.complete("failed", str(e))
            logger.error(
                f"Stage failed: {stage_name}",
                extra={
                    "request_id": request_id,
                    "stage": stage_name,
                    "error": str(e),
                    "duration_ms": stage.duration_ms,
                },
            )
            raise

    async def _resolve_target_space(self, request: MemoryWriteRequest, span) -> str:
        """Stage 1: Resolve target memory space (Dentate Gyrus pattern separation)."""
        if request.space_id:
            # Space already specified, validate permissions
            resolved_space = await self.space_resolver.validate_space_access(
                space_id=request.space_id,
                actor=request.actor,
                content=request.write_intent.get("content", ""),
            )
        else:
            # Space resolution required
            resolved_space = await self.space_resolver.resolve_space(
                actor=request.actor,
                content=request.write_intent.get("content", ""),
                context=request.write_intent.get("context", {}),
                metadata=request.write_intent.get("meta", {}),
            )

        span.set_attribute("resolved_space_id", resolved_space)
        return resolved_space

    async def _apply_content_redaction(
        self, request: MemoryWriteRequest, space_id: str, span
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Stage 2: Apply policy-based content redaction."""
        redacted_content, redaction_applied = (
            await self.redaction_coordinator.coordinate_redaction(
                content=request.write_intent,
                obligations=request.policy_obligations,
                space_id=space_id,
                actor=request.actor,
            )
        )

        span.set_attribute("redaction_operations", len(redaction_applied))
        return redacted_content, redaction_applied

    async def _perform_hippocampal_encoding(
        self, space_id: str, content: Dict[str, Any], request: MemoryWriteRequest, span
    ) -> HippocampalEncoding:
        """Stage 3: Hippocampal encoding via existing hippocampus system."""
        # Generate event ID for hippocampal encoding
        event_id = f"mem_{request.request_id}_{uuid.uuid4().hex[:8]}"

        # Extract text content for encoding
        text_content = content.get("content", "")

        # Create metadata for hippocampus
        hippo_metadata = {
            "request_id": request.request_id,
            "actor": request.actor,
            "salience": request.salience,
            "policy_obligations": request.policy_obligations,
            "trace_id": request.trace_id,
        }

        # Perform hippocampal encoding
        encoding = await self.hippocampus_api.encode_event(
            space_id=space_id,
            event_id=event_id,
            text=text_content,
            metadata=hippo_metadata,
        )

        span.set_attribute("hippocampus.event_id", event_id)
        span.set_attribute("hippocampus.novelty", encoding.novelty)
        span.set_attribute("hippocampus.near_duplicates", len(encoding.near_duplicates))

        return encoding

    async def _perform_deduplication(
        self, encoding: HippocampalEncoding, space_id: str, span
    ) -> Dict[str, Any]:
        """Stage 4: Memory deduplication and consolidation (CA3 pattern completion)."""
        if not self.enable_deduplication:
            return {"strategy": "disabled", "merged_with": [], "similarity_score": 0.0}

        dedup_result = await self.deduplication_engine.check_and_merge(
            encoding=encoding, space_id=space_id
        )

        span.set_attribute(
            "deduplication.strategy", dedup_result.get("strategy", "none")
        )
        span.set_attribute(
            "deduplication.merged_count", len(dedup_result.get("merged_with", []))
        )

        return dedup_result

    async def _commit_memory(
        self,
        encoding: HippocampalEncoding,
        dedup_result: Dict[str, Any],
        space_id: str,
        request: MemoryWriteRequest,
        span,
    ) -> str:
        """Stage 5: Transactional memory commitment (CA1 output)."""
        memory_id = await self.commit_manager.commit_memory_formation(
            encoding=encoding,
            deduplication=dedup_result,
            space_id=space_id,
            request=request,
        )

        span.set_attribute("memory_id", memory_id)
        return memory_id

    async def _generate_receipt(
        self,
        memory_id: str,
        encoding: HippocampalEncoding,
        redaction_applied: List[str],
        request: MemoryWriteRequest,
        span,
    ) -> str:
        """Stage 6: Generate cryptographic receipt for audit trail."""
        receipt_id = await self.receipt_generator.generate_receipt(
            memory_id=memory_id,
            encoding=encoding,
            redaction_applied=redaction_applied,
            request=request,
        )

        span.set_attribute("receipt_id", receipt_id)
        return receipt_id

    async def _publish_cognitive_events(
        self,
        memory_id: str,
        encoding: HippocampalEncoding,
        dedup_result: Dict[str, Any],
        request: MemoryWriteRequest,
        span,
    ) -> List[Dict[str, Any]]:
        """Stage 7: Publish cognitive events via outbox pattern."""
        if not self.event_bus:
            logger.debug("No event bus configured, skipping event publication")
            return []

        events = [
            {
                "topic": "cognitive.memory.write.initiated",
                "payload": {
                    "request_id": request.request_id,
                    "memory_id": memory_id,
                    "space_id": encoding.space_id,
                    "actor": request.actor,
                    "trace_id": request.trace_id,
                },
            },
            {
                "topic": "cognitive.memory.write.committed",
                "payload": {
                    "memory_id": memory_id,
                    "event_id": encoding.event_id,
                    "space_id": encoding.space_id,
                    "novelty": encoding.novelty,
                    "near_duplicates": len(encoding.near_duplicates),
                    "deduplication": dedup_result,
                    "trace_id": request.trace_id,
                },
            },
        ]

        # Publish events via commit manager's outbox
        await self.commit_manager.publish_cognitive_events(events)

        span.set_attribute("cognitive_events_published", len(events))
        return events

    async def get_processing_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get current processing status for a request."""
        if request_id not in self._processing_stages:
            return None

        stages = self._processing_stages[request_id]
        return {
            "request_id": request_id,
            "is_active": request_id in self._active_requests,
            "stages": [
                {
                    "stage": s.stage,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                }
                for s in stages
            ],
            "completed_stages": len([s for s in stages if s.status == "completed"]),
            "total_stages": len(stages),
        }

    async def get_active_requests(self) -> List[str]:
        """Get list of currently active request IDs."""
        return list(self._active_requests)


class MemoryFormationError(Exception):
    """Base exception for memory formation failures."""

    def __init__(
        self,
        message: str,
        stage: str,
        request_id: str,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.stage = stage
        self.request_id = request_id
        self.cause = cause


# TODO: Production enhancements needed:
# - Add circuit breaker pattern for external dependencies
# - Implement retry logic with exponential backoff
# - Add request queuing and load shedding under high volume
# - Implement compensation patterns for partial failures
# - Add comprehensive health checks for all components
# - Implement request prioritization based on salience scores
# - Add batch processing optimization for high throughput
# - Implement request deduplication at the orchestrator level
